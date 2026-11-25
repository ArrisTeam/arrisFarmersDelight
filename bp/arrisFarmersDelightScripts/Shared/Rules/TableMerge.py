# -*- coding: utf-8 -*-
"""TableMerge - 客户端把服务端发来的差异并进自己的数据表（客户端用，纯规则；两端各一份 Shared/Data，这里改的是本端那一份）

收到的消息是 TableDiff 编的：{"proto", "table", "kind", "ops", "rev", ...}，一条一张表。并表规矩：
- 就地改，不换对象：站点登记时拿着的 GrillStation.STOVE_BLOCKS（前置包按"方块名 in 它"认站点方块）每次都按 StoveList 这个列表对象判，砧板配方的 tool 引用着 knifeList，
  换成新列表就全断了；
- 幂等：同一条收两遍、晚收、先收到后面的再收到前面的，结果一样——本端已经有一样的东西就不动它（同一个进程里两端共用一份表时也不会把对象换成副本）；
- 加和改；字典表（MAP）还照删（服务端发 {"k", "gone": true}：基线里有的或发过的键删掉了），本端没有那个键就什么也不做；名字列表只加不删；
  ROWS 里本端已有的行就地合并（行字典和它的 Recipe 列表都不换对象：拿着它们的人看得到新内容）；
- 一条一条隔离：某个条目换不回来（格式不对、引用不认识）记进 problems 跳过，别的照并；消息本身不对（版本、表名、种类）整条不理；
  ROWS 的消息带服务端基线的行数，本端比它还短说明两端的表不是同一版，整条不并（不然下标就错位了）。
- 并进去有变化的表，SyncTables.recompute 重算依赖它的缓存。
"""
from . import SyncTables
from .TableWire import TEXT, WireError, isInt, toStr


def _items(container, ops, codec, problems):
    changed = False
    for wire in ops:
        try:
            item = codec.decode(wire)
        except WireError as error:
            problems.append("名字 %r 换不回来：%s" % (wire, error))
            continue
        if not isinstance(item, TEXT):
            problems.append("名字 %r 不是 str，已跳过" % (item,))
        elif item not in container:
            container.append(item)
            changed = True
    return changed


def _map(container, ops, codec, problems):
    changed = False
    for op in ops:
        try:
            key = codec.decode(op["k"])
            hash(key)
            gone = op.get("gone") is True
            value = None if gone else codec.decode(op["v"])
        except (WireError, KeyError, TypeError, AttributeError) as error:
            problems.append("条目 %r 换不回来：%s" % (op, error))
            continue
        if gone:
            if key in container:
                del container[key]
                changed = True
        elif key not in container or container[key] != value:
            container[key] = value
            changed = True
    return changed


def _mergeRow(old, new):
    """本端已有的行就地改成 new：字段对字段，列表字段（Recipe）原地换内容，对象不换。"""
    for key in [key for key in old if key not in new]:
        del old[key]
    for key, value in new.items():
        current = old.get(key)
        if isinstance(current, list) and isinstance(value, list):
            if current != value:
                current[:] = value
        elif key not in old or current != value:
            old[key] = value


def _rows(container, ops, codec, problems, base=None):
    if not isInt(base) or len(container) < base:
        problems.append("本端的表只有 %d 行，服务端的基线有 %r 行，不是同一版，不并" % (len(container), base))
        return False
    changed = False
    for op in ops:
        try:
            at, row = op["at"], codec.decode(op["v"])
            if not isInt(at) or at < 0 or not isinstance(row, dict):
                raise WireError("下标或内容不对")
        except (WireError, KeyError, TypeError) as error:
            problems.append("行 %r 换不回来：%s" % (op, error))
            continue
        if at > len(container):
            problems.append("第 %d 行放不进去：本端只有 %d 行，前面缺了几行" % (at, len(container)))
        elif at == len(container):
            container.append(row)
            changed = True
        elif container[at] != row:
            if isinstance(container[at], dict):
                _mergeRow(container[at], row)
            else:
                container[at] = row
            changed = True
    return changed


def _check(message, tables, problems):
    """消息的外壳对不对：(表名, 种类, 容器, ops)；不对返回 None 并记原因。"""
    if not isinstance(message, dict):
        problems.append("消息不是字典")
        return None
    name, kind = toStr(message.get("table")), toStr(message.get("kind"))
    if message.get("proto") != SyncTables.PROTOCOL:
        problems.append("消息的版本 %r 不认识（本端是 %d）" % (message.get("proto"), SyncTables.PROTOCOL))
    elif not isinstance(name, str) or name not in tables:
        problems.append("不认识的表 %r" % (message.get("table"),))
    elif tables[name][0] != kind:
        problems.append("表 %r 的种类 %r 对不上" % (name, message.get("kind")))
    elif not isinstance(message.get("ops"), list):
        problems.append("消息里没有条目列表")
    else:
        return name, tables[name][0], tables[name][1], message["ops"]
    return None


def apply(message, tables=None, codec=None):
    """把一条消息并进本端的表。返回 {"table": 表名（消息不对是 None）, "changed": 表有没有变, "problems": [跳过的条目和原因]}；从不抛异常给调用方
    （换不回来的条目、不对的消息都只进 problems）。tables 缺省是 SyncTables.BY_NAME（只有用缺省表时才重算缓存），codec 缺省是 SyncTables.CODEC
    （测试可以换）。"""
    result = {"table": None, "changed": False, "problems": []}
    found = _check(message, SyncTables.BY_NAME if tables is None else tables, result["problems"])
    if found is None:
        return result
    name, kind, container, ops = found
    codec = SyncTables.CODEC if codec is None else codec
    result["table"] = name
    if kind == SyncTables.ITEMS:
        result["changed"] = _items(container, ops, codec, result["problems"])
    elif kind == SyncTables.MAP:
        result["changed"] = _map(container, ops, codec, result["problems"])
    else:
        result["changed"] = _rows(container, ops, codec, result["problems"], message.get("base"))
    if result["changed"] and tables is None:
        SyncTables.recompute(name)
    return result
