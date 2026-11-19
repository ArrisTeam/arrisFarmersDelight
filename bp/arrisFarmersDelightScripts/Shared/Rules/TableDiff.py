# -*- coding: utf-8 -*-
"""TableDiff - 服务端怎么算"下游追加了什么"：导入时记基线，之后随时算"现在 - 基线"，编成能直接 Call 的消息（服务端用，纯规则）

基线是模块导入那一刻各张表的样子（SyncTables.TABLES）：这时下游还没追加（它们在 LoadServerAddonScriptsAfter 里才追加，晚于任何模块的导入），
客户端自己的 Shared/Data 导入后也是这个样子，所以"现在 - 基线"正好是客户端缺的。发的是累计的差异（不是"上次以来"）：客户端并表是幂等的
（TableMerge），重复收、晚收、漏了前一条都不会错，服务端不用记每个客户端收到哪一步，只记它收到了哪一版（rev）：差异每变一次 rev 加 1，
每张表记着自己的消息最近一次变成现在这样是第几版，已经收过第 N 版的人补发时只要版本比 N 新的那几张表。
- ITEMS：基线里没有的名字，按表里的顺序；MAP：键不在基线里，或值和基线不一样的条目（{"k": 键, "v": 值}）；
  ROWS：下标不在基线里，或那一行和基线不一样的行（{"at": 下标, "v": 行}，消息里带基线的行数 base）；
- 只同步新增和改动，不同步删除（联动契约只有追加）；
- 值编不了的条目（自定义对象、键不是 str 的嵌套字典……）跳过并记进 problems；ROWS 里新增的那一行编不了时放一个空行占着下标
  （书页的键就是下标，后面几行的下标不能错位）；
- 变没变先拿"上次算差异时各表的深拷贝"在 C 层比（changed，一次定时检查不到一毫秒），变了才重新编码；
  差异和上一次不一样才算新的一版。
"""
import copy

from . import SyncTables
from .TableWire import TEXT, Codec, WireError, toStr

CHUNK_CHARS = 20000     # 一条消息里的条目写出来大约多少字符：差异大的表拆成几条发，单条载荷不会太大
_BAD = object()         # 基线里编不了的条目：和任何东西都不相等，现在的版本（如果编得了）当作改动发出去
_UNCOPYABLE = object()  # 拷不了的表（下游放了 deepcopy 不认的东西）：每次检查都当它变了、重新算差异（编码是逐条隔离的，坏条目只被跳过）
_HOLE = {"Recipe": [], "CookResult": ("", 0), "PushItem": [], "text": ""}   # 编不了的新增行用它占下标：书和索引都把它当"不是配方"跳过


class Syncer(object):
    """基线 + 差异。tables / refs 缺省是 SyncTables 登记的（测试可以换）。"""

    def __init__(self, tables=None, refs=None, limit=CHUNK_CHARS):
        self.tables = tuple(SyncTables.TABLES if tables is None else tables)
        self.codec = SyncTables.CODEC if refs is None else Codec(refs)
        self.limit = limit
        self.rev = 0                 # 差异变了几次
        self.problems = []           # 最近一次算差异时跳过的条目和原因
        self._revs = {}              # 表名 -> 这张表的消息最近一次变成现在这样是第几版
        self._holes = dict((name, self.codec.encode(SyncTables.HOLES.get(name, _HOLE))) for name, kind, _ in self.tables if kind == SyncTables.ROWS)
        self._base = dict((name, self._baseline(kind, container)) for name, kind, container in self.tables)
        self._seen = self._copies()
        self._messages = None        # {表名: [消息]}（没有差异的表不在里面）；None：还没算过

    # ---------------------------------------------------------------- 基线与变没变

    def _try(self, value):
        try:
            return self.codec.encode(value)
        except WireError:
            return _BAD

    def _baseline(self, kind, container):
        if kind == SyncTables.ITEMS:
            return set(item for item in container if isinstance(item, TEXT))
        if kind == SyncTables.MAP:
            return dict((key, self._try(value)) for key, value in container.items())
        return [self._try(row) for row in container]

    def _copies(self):
        found = {}
        for name, _kind, container in self.tables:
            try:
                found[name] = copy.deepcopy(container)
            except Exception:  # noqa: BLE001 - 表里放了什么是下游的事：拷不了就退成"每次都重算"，不能让同步整个停掉
                found[name] = _UNCOPYABLE
        return found

    def changed(self):
        """有哪张表和上次算差异时不一样了（深拷贝在 C 层比）。"""
        return any(self._seen[name] is _UNCOPYABLE or container != self._seen[name] for name, _kind, container in self.tables)

    # ---------------------------------------------------------------- 差异

    def refresh(self):
        """第一次、或表变了就重新算差异；有哪张表的消息和上一次不一样（要补发）返回 True：rev 加 1，那几张表的版本记成新的 rev。"""
        if self._messages is not None and not self.changed():
            return False
        built, problems = self._build()
        self._seen = self._copies()
        self.problems = problems
        previous, self._messages = self._messages or {}, built
        moved = [name for name in set(built) | set(previous) if built.get(name) != previous.get(name)]
        if not moved:
            return False
        self.rev += 1
        for name in moved:
            self._revs[name] = self.rev
        return True

    def messages(self, since=0):
        """现在的差异（累计，相对基线）里版本比 since 新的那几张表的消息，每条带那张表的版本 rev：新进服的人要全部（since=0），
        已经收过第 N 版的人只补 N 以后变了的表。没有追加任何东西是 []。要先 refresh 过。"""
        found = []
        for name, _kind, _container in self.tables:
            rev = self._revs.get(name, 0)
            if rev > since:
                found.extend(dict(message, rev=rev) for message in (self._messages or {}).get(name, ()))
        return found

    def counts(self):
        """每张有差异的表发了几个条目（调试用）：{表名: 条目数}。"""
        return dict((name, sum(len(message["ops"]) for message in messages)) for name, messages in (self._messages or {}).items())

    def _build(self):
        built, problems = {}, []
        for name, kind, container in self.tables:
            if kind == SyncTables.ITEMS:
                ops = self._diffItems(name, container, problems)
            elif kind == SyncTables.MAP:
                ops = self._diffMap(name, container, problems)
            else:
                ops = self._diffRows(name, container, problems)
            for chunk in self._chunks(ops):
                message = {"proto": SyncTables.PROTOCOL, "table": name, "kind": kind, "ops": chunk}
                if kind == SyncTables.ROWS:
                    message["base"] = len(self._base[name])
                built.setdefault(name, []).append(message)
        return built, problems

    def _diffItems(self, name, container, problems):
        base, seen, ops = self._base[name], set(), []
        for item in container:
            if not isinstance(item, TEXT):
                problems.append("%s 里有不是 str 的名字 %r，已跳过" % (name, item))
            elif item not in base and item not in seen:
                seen.add(item)
                ops.append(toStr(item))
        return ops

    def _diffMap(self, name, container, problems):
        base, ops = self._base[name], []
        for key, value in container.items():
            try:
                wireKey, wireValue = self.codec.encode(key), self.codec.encode(value)
            except WireError as error:
                problems.append("%s 的条目 %r 传不了，已跳过：%s" % (name, key, error))
                continue
            if key not in base or base[key] != wireValue:
                ops.append({"k": wireKey, "v": wireValue})
        ops.sort(key=lambda op: repr(op["k"]))     # 字典的遍历次序会变，消息的次序不能跟着变（不然没变也算新的一版）
        return ops

    def _diffRows(self, name, container, problems):
        base, ops = self._base[name], []
        for index, row in enumerate(container):
            try:
                wireRow = self.codec.encode(row)
            except WireError as error:
                problems.append("%s 的第 %d 行传不了，%s：%s" % (name, index, "用空行占着下标" if index >= len(base) else "客户端保持原样", error))
                if index < len(base):
                    continue
                wireRow = self._holes[name]
            if index >= len(base) or base[index] != wireRow:
                ops.append({"at": index, "v": wireRow})
        return ops

    def _chunks(self, ops):
        chunk, size = [], 0
        for op in ops:
            cost = len(repr(op))
            if chunk and size + cost > self.limit:
                yield chunk
                chunk, size = [], 0
            chunk.append(op)
            size += cost
        if chunk:
            yield chunk
