# -*- coding: utf-8 -*-
"""PotRecipeTable - 厨锅配方表的索引和记着的答案：哪一行算配方、旧写法的查表、格子配对的结果、一锅种类的各种摆法（双端，纯规则）

Shared/Rules/CookingPot.py 的公共函数都从这里取，别处不直接用。表改过（touch：联动接口追加 / 登记 / 删除、客户端并表之后）下次用到时
重算；标签的答案变了（ItemTags.generation：远端客户端进世界之后标签才全）只清记着的答案。登记一条配方不再整张重建。
标签的引擎口准备好之前不记答案（_remember），照 ItemTags 的规矩：那时按单件问的答案还会变。
"""
from ..Data.CookingPotRecipes import CookingPotRecipeList
from . import ItemTags, PotSlots
from .TableWire import isInt

DEFAULT_COOK_SECONDS = 10.0  # JE 的厨锅配方缺省 200 刻
DEFAULT_EXPERIENCE = 1.0     # 旧格式没写 Experience 时给的经验（新接口登记的配方把经验明写进行里，JE 的缺省是 0）
MEMO_LIMIT = 1024            # 记着多少种摆法 / 种类的答案：满了清掉重记
MISS = (None, None)

try:
    _TEXT = (str, unicode)  # noqa: F821 - py2
except NameError:
    _TEXT = (str,)

_state = {"dirty": True, "generation": None, "revision": 0}
_table = {}                  # _rebuild 算出来的，键见那里
_memo = {}                   # 排好序的输入 -> (配方序号, 配上的那种旧写法或 None)；配不上是 MISS
_candidates = {}             # frozenset(种类) -> [(配方序号, {种类: 占几格}), ...]
_tagged = {}                 # (物品名, aux) -> 某条配方的标签格收不收它


def touch():
    """配方表改过了：版本加一，下次用到时重算。"""
    _state["revision"] += 1
    _state["dirty"] = True


def revision():
    return _state["revision"]


def isPair(value):
    """(物品名, aux)：名字是文字，aux 是整数（过了线的元组是列表，也算）。"""
    if not (isinstance(value, (tuple, list)) and len(value) == 2):
        return False
    return isinstance(value[0], _TEXT) and isInt(value[1])          # py2 的 long 也算（引擎给的 aux 可能是 long）


def isLive(recipe):
    """这一行是一条配方：成品写对了、不是墓碑（下游写坏的行、表同步占位的空行都不算）。"""
    return isinstance(recipe, dict) and not recipe.get("Disabled") and isPair(recipe.get("CookResult")) and bool(recipe["CookResult"][0])


def waysOf(recipe):
    """这条配方写对了的旧写法 [[(物品名, aux), ...], ...]（1 到 6 件；写坏的那种跳过）。"""
    found = []
    for variant in (recipe.get("Recipe") if isinstance(recipe, dict) else None) or ():
        if isinstance(variant, (list, tuple)) and 1 <= len(variant) <= PotSlots.MOST_SLOTS and all(isPair(entry) for entry in variant):
            found.append([(entry[0], entry[1]) for entry in variant])
    return found


def slotsOf(recipe):
    """这条配方写对了的 Slots；没有或写坏了是 None。"""
    slots = recipe.get("Slots") if isinstance(recipe, dict) else None
    return slots if slots and PotSlots.isValid(slots) else None


def number(value, default):
    """配方里的数（煮几秒、给多少经验、一份几个）：写坏了用缺省，不抛。"""
    try:
        return float(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def countOf(recipe):
    """一份出几个（CookCount，缺省 1）。"""
    return max(1, int(number(recipe.get("CookCount"), 1)))


def _rebuild():
    legacy, legacyParts, exact, tags, vessels, slotted = {}, {}, set(), set(), set(), []
    seconds, perItem, perServing = {}, {}, {}
    for index, recipe in enumerate(CookingPotRecipeList):
        if not isLive(recipe):
            continue
        name = recipe["CookResult"][0]
        seconds.setdefault(name, number(recipe.get("CookTime"), DEFAULT_COOK_SECONDS) or DEFAULT_COOK_SECONDS)
        given = number(recipe.get("Experience"), DEFAULT_EXPERIENCE)
        perItem.setdefault(name, given / countOf(recipe))
        perServing.setdefault(name, given)
        if isPair(recipe.get("Vessel")):
            vessels.add(recipe["Vessel"][0])
        for variant in waysOf(recipe):
            legacy.setdefault(tuple(sorted(variant)), (index, variant))
            parts = {}
            for kind in variant:
                parts[kind] = parts.get(kind, 0) + 1
            exact.update(parts)
            legacyParts.setdefault(frozenset(parts), []).append((index, parts))
        slots = slotsOf(recipe)
        if slots is not None:
            slotted.append((index, slots))
            exact.update(PotSlots.itemsIn(slots))
            tags.update(PotSlots.tagsIn(slots))
    _table.clear()
    _table.update(legacy=legacy, legacyParts=legacyParts, exact=exact, tags=tags, vessels=vessels, slotted=slotted,
                  seconds=seconds, perItem=perItem, perServing=perServing)


def table():
    """现在的索引（{键: ...}，键见 _rebuild）：表改过就重算；标签的代数变了清掉记着的答案。"""
    generation = ItemTags.generation()
    if _state["dirty"]:
        _rebuild()
        _state["dirty"] = False
        _state["generation"] = None
    if generation != _state["generation"]:
        _state["generation"] = generation
        _memo.clear()
        _candidates.clear()
        _tagged.clear()
    return _table


def _remember(store, key, value):
    """记下答案（满了清掉重记）。标签的引擎口还没准备好时不记：那时按单件问引擎的答案可能不全、准备好之前还会变（ItemTags 自己也不缓存
    那时的答案；万一口一直没准备好，记下的"配不上"会一直错下去）。没装口（离线、沙箱）也算没准备好：只是不记，答案一样。"""
    if not ItemTags.ready():
        return value
    if len(store) >= MEMO_LIMIT:
        store.clear()
    store[key] = value
    return value


def resolve(key):
    """排好序的输入 -> (配方序号, 配上的那种旧写法或 None)：表里靠前的赢；配不上是 MISS。先调过 table()。"""
    found = _memo.get(key)
    if found is not None:
        return found
    legacy = _table["legacy"].get(key)
    found = legacy or MISS
    for index, slots in _table["slotted"]:
        if legacy is not None and index >= legacy[0]:
            break
        if len(slots) == len(key) and PotSlots.fits(slots, key, ItemTags.has):
            found = (index, None)
            break
    return _remember(_memo, key, found)


def candidates(kinds):
    """种类集合正好是 kinds 的各种摆法 [(配方序号, {种类: 占几格}), ...]：按配方表的先后，同一条配方里旧写法在前（原来的先后）、
    格子多给出来的摆法接在后面（重复的不要）。先调过 table()。"""
    key = frozenset((kind[0], kind[1]) for kind in kinds)
    found = _candidates.get(key)
    if found is not None:
        return found
    legacy = {}
    for index, parts in _table["legacyParts"].get(key, ()):
        legacy.setdefault(index, []).append(parts)
    slotted = dict(_table["slotted"])
    ordered = sorted(key)
    found = []
    for index in sorted(set(legacy) | set(slotted)):
        mine = list(legacy.get(index, ()))
        if index in slotted:
            mine += [parts for parts in PotSlots.partsOf(slotted[index], ordered, ItemTags.has) if parts not in mine]
        found += [(index, parts) for parts in mine]
    return _remember(_candidates, key, found)


def tagged(kind):
    """某条配方的标签格收不收这种料（记着）。先调过 table()。"""
    found = _tagged.get(kind)
    if found is None:
        found = _remember(_tagged, kind, any(ItemTags.has(kind[0], tag) for tag in _table["tags"]))
    return found
