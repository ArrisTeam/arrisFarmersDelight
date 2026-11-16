# -*- coding: utf-8 -*-
"""
不设上限的格子列表：分页存进键值后端（玩家或世界的 ExtraData），只写改动过的页。

每页 PAGE_SIZE 格，序列化成一个 str（只记非空格）。用 repr 写、ast.literal_eval 读：
userData 里的 str、整数类型、嵌套字典原样往返；不用 json，json 读回来全是 unicode，进不了引擎接口。
另有一个头键记版本、页数、最后一个非空格的下标与非空格数。
实例存储整体的存档版本另记在 前缀:v（migrate，docs/ARCHITECTURE.md 第 6 节、不变式 I8）。

后端接口（Backend）：get(key) -> str | None、set(key, value)、delete(key)、save()。
本模块不依赖引擎，服务端接 ExtraData，测试接内存表。
"""
import ast

from ..Common import Items

FORMAT_VERSION = 1
PAGE_SIZE = 128
VERSION_KEY = "v"   # 实例存储的存档版本：前缀:v（没记的是 1）


class StorageError(Exception):
    pass


def encodePage(slots):
    """{页内下标: 物品堆} -> str。物品堆写成 (名字, aux, 数量, userData) 元组，按下标排序。"""
    rows = []
    for offset in sorted(slots):
        stack = slots[offset]
        if stack:
            rows.append((offset, stack["newItemName"], stack["newAuxValue"], stack["count"], stack.get("userData")))
    return repr(rows)


def decodePage(text):
    """读出的物品堆也经 Items.normalize（存档里的收纳袋可能是旧写法）。"""
    rows = ast.literal_eval(text)
    page = {}
    for offset, name, aux, count, userData in rows:
        page[offset] = Items.normalize({"newItemName": name, "newAuxValue": aux, "count": count, "userData": userData})
    return page


def storedVersion(backend, prefix):
    """实例存储在后端里记的存档版本（没记的是 1：加版本之前的存档）。"""
    text = backend.get("%s:%s" % (prefix, VERSION_KEY))
    return int(text) if text else 1


def migrate(backend, prefix, version, migrations):
    """
    实例存储的存档迁移：存档记的版本低于 version 时，按 migrations[旧版本](backend, prefix) 一版一版改成下一版的写法，
    再记下 version；高于 version（更新的代码存的）时拒绝，免得旧代码读错、写坏。迁移函数只动这个前缀下的键。
    返回迁移了几版。
    """
    stored = storedVersion(backend, prefix)
    if stored > version:
        raise StorageError("save version %d of %s is newer than %d" % (stored, prefix, version))
    for step in range(stored, version):
        migrations[step](backend, prefix)
    if stored < version:
        backend.set("%s:%s" % (prefix, VERSION_KEY), str(version))
    return version - stored


class Backend(object):

    def get(self, key):
        raise NotImplementedError

    def set(self, key, value):
        raise NotImplementedError

    def delete(self, key):
        raise NotImplementedError

    def save(self):
        pass


class MemoryBackend(Backend):

    def __init__(self):
        self.data = {}
        self.saves = 0

    def get(self, key):
        return self.data.get(key)

    def set(self, key, value):
        self.data[key] = value

    def delete(self, key):
        self.data.pop(key, None)

    def save(self):
        self.saves += 1


_stores = {}   # 容器种类 -> 不设上限、跟着实例存的容器用的存储类（缺省 PagedStore）
_sizedStores = {}   # 容器种类 -> 有格数、跟着实例存的容器用的存储类（缺省没有：合在 GroupStore 里）


def registerStore(kind, factory, sized=False):
    """
    容器种类 kind 跟着实例存时用 factory(后端, 键前缀) 建存储：get(下标)、set(下标, 物品堆)、items(起, 止)、highestUsed()、
    flush() 与 PagedStore 一样。sized 为假时管不设上限的（缺省 PagedStore；种类存储 Std/ListSync 用它带上"种类 -> 下标"
    的索引），为真时管有格数的（缺省合在实例的 GroupStore 里，一个键；要分开存、换写法、接旧存档时登记）。
    """
    (_sizedStores if sized else _stores)[kind] = factory


def storeFor(kind, sized=False):
    """容器种类 kind 跟着实例存时用的存储类：不设上限的缺省 PagedStore；有格数的没登记时为 None（合在 GroupStore 里）。"""
    if sized:
        return _sizedStores.get(kind)
    return _stores.get(kind, PagedStore)


class PagedStore(object):
    """
    下标 -> 物品堆。读按页懒加载并缓存；写进缓存并记脏页，flush 时把脏页与头一起写回后端。

    prefix 是这份数据在后端里的键前缀（例如 "arris_dimbag:bag"）。
    """

    def __init__(self, backend, prefix):
        self.backend = backend
        self.prefix = prefix
        self._pages = {}
        self._dirty = set()
        self._top = -1
        self._used = 0
        self._pageCount = 0
        self._metaDirty = False
        self._load()

    def _key(self, name):
        return "%s:%s" % (self.prefix, name)

    def _load(self):
        text = self.backend.get(self._key("meta"))
        if not text:
            return
        meta = ast.literal_eval(text)
        if meta.get("v") != FORMAT_VERSION:
            raise StorageError("unsupported storage version %r" % (meta.get("v"),))
        self._top = meta.get("top", -1)
        self._used = meta.get("used", 0)
        self._pageCount = meta.get("pages", 0)

    def exists(self):
        """后端里有没有这份数据（还没存过的新容器为 False）。"""
        return bool(self.backend.get(self._key("meta")))

    def _page(self, number):
        page = self._pages.get(number)
        if page is None:
            text = self.backend.get(self._key("p%d" % number)) if number < self._pageCount else None
            page = decodePage(text) if text else {}
            self._pages[number] = page
        return page

    def get(self, index):
        return self._page(index // PAGE_SIZE).get(index % PAGE_SIZE)

    def set(self, index, stack):
        number, offset = divmod(index, PAGE_SIZE)
        page = self._page(number)
        had = offset in page
        if stack:
            page[offset] = stack
            if not had:
                self._used += 1
            if index > self._top:
                self._top = index
        elif had:
            del page[offset]
            self._used -= 1
            if index == self._top:
                self._top = self._scanTop(index - 1)
        else:
            return
        self._dirty.add(number)
        self._metaDirty = True

    def _scanTop(self, start):
        """从 start 往前找最后一个非空格。"""
        index = start
        while index >= 0:
            number, offset = divmod(index, PAGE_SIZE)
            page = self._page(number)
            if not page:
                index = number * PAGE_SIZE - 1
                continue
            below = [o for o in page if o <= offset]
            if below:
                return number * PAGE_SIZE + max(below)
            index = number * PAGE_SIZE - 1
        return -1

    def highestUsed(self):
        return self._top

    def usedCount(self):
        return self._used

    def items(self, start, end):
        """[start, end) 里的非空格：[(下标, 物品堆), ...]。"""
        out = []
        for number in range(start // PAGE_SIZE, (max(start, end) - 1) // PAGE_SIZE + 1):
            page = self._page(number)
            base = number * PAGE_SIZE
            for offset in sorted(page):
                index = base + offset
                if start <= index < end:
                    out.append((index, page[offset]))
        return out

    def flush(self):
        """把脏页与头写回后端（不调 save）。返回写了几页。"""
        written = 0
        for number in sorted(self._dirty):
            page = self._pages.get(number) or {}
            key = self._key("p%d" % number)
            if page:
                self.backend.set(key, encodePage(page))
            else:
                self.backend.delete(key)
            written += 1
        self._dirty.clear()
        if self._metaDirty:
            pages = self._top // PAGE_SIZE + 1 if self._top >= 0 else 0
            for number in range(pages, self._pageCount):
                self.backend.delete(self._key("p%d" % number))
            self._pageCount = pages
            if self._used:
                meta = {"v": FORMAT_VERSION, "top": self._top, "used": self._used, "pages": pages}
                self.backend.set(self._key("meta"), repr(meta))
            else:
                self.backend.delete(self._key("meta"))   # 空容器不留数据
            self._metaDirty = False
            written += 1
        return written


class GroupStore(object):
    """
    有格数的实例存储容器（熔炉的三格这种），一个实例的全部合在一个键里：前缀:x。
    值是 repr 的字典 {"v": 版本, "g": {容器名: [(格, 物品名, aux, 数量, userData), ...]}}；
    用到时才写，全空时删掉这个键。
    """

    def __init__(self, backend, prefix):
        self.backend = backend
        self.key = "%s:x" % prefix
        self._groups = {}
        self._texts = {}          # 容器名 -> 那个容器的行写好的文字（没改的容器写回时不再重写）
        self._dirty = set()       # 改过的容器名
        text = backend.get(self.key)
        if text:
            data = ast.literal_eval(text)
            if data.get("v") != FORMAT_VERSION:
                raise StorageError("unsupported group storage version %r" % (data.get("v"),))
            for gid, rows in (data.get("g") or {}).items():
                slots = self._groups.setdefault(gid, {})
                for index, name, aux, count, userData in rows:
                    slots[index] = Items.normalize({"newItemName": name, "newAuxValue": aux, "count": count,
                                                    "userData": userData})
                self._texts[gid] = repr(rows)

    def get(self, gid, index):
        slots = self._groups.get(gid)
        return slots.get(index) if slots else None

    def set(self, gid, index, stack):
        slots = self._groups.setdefault(gid, {})
        if stack:
            slots[index] = stack
        elif index in slots:
            del slots[index]
        else:
            return
        self._dirty.add(gid)

    def items(self, gid):
        """这个容器的非空格：[(格, 物品堆), ...]，按格排序。"""
        return sorted((self._groups.get(gid) or {}).items())

    def flush(self):
        """改过的容器重写它那一段，与没改的接成一个值写回（全空时删掉这个键）。返回写了几个键。"""
        if not self._dirty:
            return 0
        for gid in self._dirty:
            rows = [(index, stack["newItemName"], stack["newAuxValue"], stack["count"], stack.get("userData"))
                    for index, stack in sorted((self._groups.get(gid) or {}).items()) if stack]
            if rows:
                self._texts[gid] = repr(rows)
            else:
                self._texts.pop(gid, None)
        self._dirty = set()
        if self._texts:
            body = ", ".join("%r: %s" % (gid, self._texts[gid]) for gid in sorted(self._texts))
            self.backend.set(self.key, "{'v': %d, 'g': {%s}}" % (FORMAT_VERSION, body))
        else:
            self.backend.delete(self.key)
        return 1
