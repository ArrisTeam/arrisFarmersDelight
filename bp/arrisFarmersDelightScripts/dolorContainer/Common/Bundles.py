# -*- coding: utf-8 -*-
"""
收纳袋（引擎的"存储物品"）：规格、内容的规范写法、重量。纯逻辑，两端共用。

收纳袋在玩家背包或原版容器里时，引擎把内容放在跟着它走的动态容器里；脚本读到的物品字典是"摊平"的：
userData 的 storage_item_component_content 是内容列表，每项是一个物品的 NBT（Slot、Name、Count、Damage、tag……），
bundle_weight 是总重量。按字典生成收纳袋时，引擎照内容列表重建动态容器：每项按 Slot 放格
（没写 Slot 的都放进 0 号格、互相覆盖，只剩最后一个）。

本框架里的收纳袋一律用规范写法（Items.normalize 经 canonicalUserData 整理）：内容按格序排紧，每项去掉
引擎读出时附带的 Block、WasPickedUp，空占位项不要，Slot 按排紧后的位置重写；bundle_weight 与 bundle_id 不留
（引擎重建时自己算、自己分配）。这样同一个收纳袋从引擎读出、或由本框架算出，比较起来完全相同。

内容的顺序照原版：下标 0 是最早放进去的，最后一项是"最上面"的（右键取出、提示里排在最前的就是它）。
重量照原版：普通物品每个 64 / 最大堆叠数（64 堆叠的 1，16 堆叠的 4，不堆叠的 64）；收纳袋自身重 4，
装着东西时再加上内容的重量。原版收纳袋的内容总重上限 64、最多 64 项，潜影盒放不进去，收纳袋可以套收纳袋。
"""
from . import Items, Shared

CONTENT_KEY = "storage_item_component_content"
WEIGHT_KEY = "bundle_weight"
ID_KEY = "bundle_id"
FULL_WEIGHT = 64                       # 一整组 64 堆叠物品的重量；每个物品重 FULL_WEIGHT // 最大堆叠数
_DROPPED_ENTRY_KEYS = ("Block", "WasPickedUp", "Slot")

_BYTE, _SHORT, _STRING = 1, 2, 8       # NBT 标记类型（引擎物品字典里 {"__type__": 类型, "__value__": 值} 的写法）

COLORS = ("white", "orange", "magenta", "light_blue", "yellow", "lime", "pink", "gray", "light_gray", "cyan",
          "purple", "blue", "brown", "green", "red", "black")
VANILLA_SOUNDS = ("bundle.insert", "bundle.insert_fail", "bundle.remove_one")   # 装进去、装不进、取出
SHULKER_BOXES = frozenset(["minecraft:shulker_box", "minecraft:undyed_shulker_box"]
                          + ["minecraft:%s_shulker_box" % color for color in COLORS])


class StorageSpec(object):
    """
    一种收纳袋的规格（对应引擎物品组件 storage_item / storage_weight_* / bundle_interaction 的参数）：
    maxSlots 最多几项，weightLimit 内容总重上限，ownWeight 自身放进别的收纳袋时的重量（0 表示不能放进别的收纳袋），
    allowNested 能不能装收纳袋，banned / allowed 不收 / 只收的物品名（allowed 为空表示都收），
    viewableSlots 悬停提示里最多显示几格，sounds 是 (装进去, 装不进, 取出) 的音效名（原版收纳袋的三个）。
    """

    __slots__ = ("maxSlots", "weightLimit", "ownWeight", "allowNested", "banned", "allowed", "viewableSlots", "sounds")

    def __init__(self, maxSlots=64, weightLimit=64, ownWeight=4, allowNested=True, banned=(), allowed=(),
                 viewableSlots=12, sounds=VANILLA_SOUNDS):
        self.maxSlots = maxSlots
        self.weightLimit = weightLimit
        self.ownWeight = ownWeight
        self.allowNested = allowNested
        self.banned = frozenset(banned)
        self.allowed = frozenset(allowed)
        self.viewableSlots = viewableSlots
        self.sounds = tuple(sounds)

    def admits(self, stack):
        name = stack.get("newItemName")
        if self.allowed and name not in self.allowed:
            return False
        return name not in self.banned

    def fields(self):
        """登记进共享表的写法：只有字段的字典（别的版本的库读它时不认识的字段跳过）。"""
        return {"maxSlots": self.maxSlots, "weightLimit": self.weightLimit, "ownWeight": self.ownWeight,
                "allowNested": self.allowNested, "banned": tuple(sorted(self.banned)),
                "allowed": tuple(sorted(self.allowed)), "viewableSlots": self.viewableSlots, "sounds": self.sounds}


VANILLA = StorageSpec(banned=SHULKER_BOXES)
_SPECS = dict([("minecraft:bundle", VANILLA)] + [("minecraft:%s_bundle" % color, VANILLA) for color in COLORS])
_registered = Shared.table().storage   # 各模组登记的收纳袋（几份库共用）：物品名 -> 字段字典
_converted = {}                        # 物品名 -> (字段字典, StorageSpec)：同一份字典只换算一次


def register(name, spec):
    """
    登记一种收纳袋（别的模组用存储物品组件做的袋子）；spec 为 None 时取消登记。原版收纳袋也可以登记（改了它的物品定义时
    照改过的给）：登记的优先于库里带的原版规格，取消登记后回到原版规格。
    登记在几份库共用的表里：别的模组的容器界面里，这种袋子也按收纳袋的规矩装入取出。
    """
    if spec is None:
        _registered.pop(name, None)
    else:
        _registered[name] = spec.fields()


def specOf(stack):
    if Items.isEmpty(stack):
        return None
    name = stack.get("newItemName")
    fields = _registered.get(name)
    if fields is None:
        return _SPECS.get(name)
    converted = _converted.get(name)
    if converted is None or converted[0] is not fields:
        known = dict((key, value) for key, value in fields.items() if key in StorageSpec.__slots__)
        converted = _converted[name] = (fields, StorageSpec(**known))
    return converted[1]


def isBundle(stack):
    return specOf(stack) is not None


# ---------------------------------------------------------------- 内容的规范写法


def _plain(value):
    return value["__value__"] if isinstance(value, dict) and "__value__" in value else value


def _typed(kind, value):
    return {"__type__": kind, "__value__": value}


def _slotOf(entry, fallback):
    slot = _plain(entry.get("Slot"))
    return slot if isinstance(slot, int) and not isinstance(slot, bool) else fallback


def _entryCount(entry):
    count = _plain(entry.get("Count"))
    return count if isinstance(count, int) and not isinstance(count, bool) else 0


def _canonicalEntries(raw):
    """内容列表 -> 规范写法的项（排紧、重写 Slot、去掉引擎附带的键、tag 递归整理）。"""
    if not isinstance(raw, (list, tuple)):
        return []
    slotted = []
    for position, entry in enumerate(raw):
        if not isinstance(entry, dict) or not _plain(entry.get("Name")) or _entryCount(entry) <= 0:
            continue
        slotted.append((_slotOf(entry, position), position, entry))
    slotted.sort(key=lambda item: (item[0], item[1]))
    out = []
    for slot, (_, _, entry) in enumerate(slotted):
        clean = dict((key, value) for key, value in entry.items() if key not in _DROPPED_ENTRY_KEYS)
        tag = Items.canonicalUserData(clean.get("tag"))
        if tag is None:
            clean.pop("tag", None)
        else:
            clean["tag"] = tag
        clean["Slot"] = _typed(_BYTE, slot)
        out.append(clean)
    return out


def canonicalUserData(userData):
    """带收纳袋内容的 userData 的规范写法（Items.canonicalUserData 遇到收纳袋的键时调用）。"""
    out = dict((key, value) for key, value in userData.items() if key not in (CONTENT_KEY, WEIGHT_KEY, ID_KEY))
    entries = _canonicalEntries(userData.get(CONTENT_KEY))
    if entries:
        out[CONTENT_KEY] = entries
    return out


def entries(stack):
    """收纳袋内容的各项（规范写法，最早放进的在前）；不是收纳袋或空袋为空列表。项不要原地修改。"""
    if Items.isEmpty(stack):
        return []
    user = stack.get("userData")
    if not isinstance(user, dict):
        return []
    raw = user.get(CONTENT_KEY)
    return list(raw) if isinstance(raw, list) else []


def entryItem(entry):
    """内容的一项 -> 物品堆（四个键的规整写法）。"""
    tag = entry.get("tag")
    return Items.normalize({"newItemName": str(_plain(entry.get("Name"))), "newAuxValue": int(_plain(entry.get("Damage")) or 0),
                            "count": _entryCount(entry), "userData": tag if tag else None})


def entryExtras(entry):
    """项里除了名字、数量、aux、附加数据、格号之外的键（例如冒险模式的 CanPlaceOn）：这种项不与外来的物品叠放。"""
    return dict((key, value) for key, value in entry.items() if key not in ("Name", "Count", "Damage", "tag", "Slot"))


def makeEntry(stack):
    """物品堆 -> 内容的一项（Slot 由 withEntries 写）。"""
    entry = {"Name": _typed(_STRING, stack["newItemName"]), "Count": _typed(_BYTE, Items.count(stack)),
             "Damage": _typed(_SHORT, int(stack.get("newAuxValue") or 0))}
    if stack.get("userData"):
        entry["tag"] = stack["userData"]
    return entry


def entryWithCount(entry, count):
    """数量改为 count 的副本（count <= 0 时为 None）。"""
    if count <= 0:
        return None
    copy = dict(entry)
    copy["Count"] = _typed(_BYTE, int(count))
    return copy


def withEntries(bundle, items):
    """内容换成 items（规范写法的项，按顺序）的收纳袋副本。"""
    user = dict(bundle.get("userData") or {})
    for key in (CONTENT_KEY, WEIGHT_KEY, ID_KEY):
        user.pop(key, None)
    if items:
        slotted = []
        for slot, entry in enumerate(items):
            copy = dict(entry)
            copy["Slot"] = _typed(_BYTE, slot)
            slotted.append(copy)
        user[CONTENT_KEY] = slotted
    copy = dict(bundle)
    copy["userData"] = user or None
    return copy


def walk(stack):
    """stack 本身以及（如果是收纳袋）里面一层层的东西，逐个给出物品堆。"""
    if Items.isEmpty(stack):
        return
    yield stack
    for entry in entries(stack):
        for inner in walk(entryItem(entry)):
            yield inner


# ---------------------------------------------------------------- 重量


def perItemWeight(stack, rules):
    """普通物品每个的重量：64 / 最大堆叠数。最大堆叠数超过 64 的（模组改过堆叠数）算不出，为 0，不能放进收纳袋。"""
    largest = rules.maxStack(stack)
    return FULL_WEIGHT // largest if 0 < largest <= FULL_WEIGHT else 0


def weightOf(stack, rules):
    """一堆东西放进收纳袋时占的重量；收纳袋是自身重量加内容重量。"""
    if Items.isEmpty(stack):
        return 0
    spec = specOf(stack)
    if spec is not None:
        return spec.ownWeight + contentsWeight(stack, rules)
    return perItemWeight(stack, rules) * Items.count(stack)


def contentsWeight(bundle, rules):
    return sum(weightOf(entryItem(entry), rules) for entry in entries(bundle))


def remainingWeight(bundle, rules):
    spec = specOf(bundle)
    return max(0, spec.weightLimit - contentsWeight(bundle, rules)) if spec is not None else 0


# ---------------------------------------------------------------- 悬停提示的排布


def _gridForCount(count):
    """
    原版提示网格：在 11:6 的比例下放下 count 格，行数取 sqrt(6 * count / 11) 向上取整、列数 count / 行数向上取整，
    列数不足 4 时固定 4 列。count 为 0 时 4 列 0 行。
    """
    import math
    if count <= 0:
        return 4, 0
    rows = int(math.ceil(math.sqrt(6.0 * count / 11.0)))
    columns = int(math.ceil(float(count) / rows))
    if columns < 4:
        columns = 4
        rows = int(math.ceil(count / 4.0))
    return columns, rows


class TooltipLayout(object):
    """
    悬停提示里内容的排布，照原版：最多显示 viewableSlots 格；放不下时最后一格写"+N"（N 是没显示的那些项的物品总数），
    显示的是最上面的那些项。格子从网格的某一格开始排，让最上面的一项落在第一行、最早的落在右下角：
        起始格 = ((列数 - 1) × 项数) % 列数，第 k 格（从起始格算起）显示从上往下数第 k 项。
    """

    def __init__(self, bundle, spec=None):
        spec = spec or specOf(bundle)
        items = entries(bundle)
        total = len(items)
        viewable = min(total, spec.viewableSlots if spec is not None else 12)
        self.columns, self.rows = _gridForCount(viewable)
        if total == 0:
            self.columns, self.rows = 4, 0
        capacity = self.rows * self.columns
        hidden = total > capacity
        if hidden:
            shown = (self.rows - 1) * self.columns - 1 + ((total - 1) % self.columns + 1)
        else:
            shown = total
        self.total = total
        self.shown = shown
        self.hidden = total - shown
        self.hiddenCount = sum(_entryCount(entry) for entry in items[:self.hidden])
        self.start = ((self.columns - 1) * total) % self.columns if self.columns else 0
        self.items = items

    def cells(self):
        """网格格数（行 × 列）。"""
        return self.rows * self.columns

    def entryIndexAt(self, cell):
        """网格第 cell 格显示的是内容的第几项（不显示东西时为 None）。"""
        if cell < self.start or cell >= self.start + self.shown:
            return None
        return self.total - (cell - self.start + 1)

    def cellOfEntry(self, index):
        """内容第 index 项在网格的第几格（没显示时为 None）。"""
        cell = self.start + (self.total - 1 - index)
        return cell if self.start <= cell < self.start + self.shown else None

    def moreCell(self):
        """写"+N"的那一格（没有隐藏的项时为 None）。"""
        return self.cells() - 1 if self.hidden > 0 else None

    def firstAndLast(self):
        """能选中的格子范围 [第一格, 最后一格]（原版滚轮与摇杆在这个范围里移动）。"""
        return self.start, self.start + self.shown - 1
