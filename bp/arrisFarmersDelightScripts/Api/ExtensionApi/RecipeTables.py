# -*- coding: utf-8 -*-
"""RecipeTables - 新接口的配方存进那几张契约表：登记一条、同 ID 覆盖、删、按 ID 找、写成 JE 配方 JSON 的样子（双端，不碰引擎）

不另起一份存储（表同步、六个下游包、十几个读表的地方都建在这几张表上）：
- 厨锅（cooking）：CookingPotRecipeList 的一行，带 Id、Slots；Recipe 是按登记那一刻标签的成员展开的写法快照（最多 64 种，只给只认物品的
  旧读者看，配方以 Slots 为准）。同 ID 再登记就地换掉那一行（下标、行对象都不变）；删 = 打墓碑（Disabled）：下标是身份，不摘。
- 砧板（cutting）：原料是物品的进 CuttingBoardDict，是标签的进 CuttingTagDict（键是标签名）；一种原料只有一条，被别的 ID 占着时拒绝
  （input_taken：要改它就用它的 ID 覆盖）；删 = 真删（表同步会把删除发给客户端）。登记用的 ID 写进条目（多一个可选键 "id"，旧读者不看它），
  随表同步到客户端，两端按 ID 查到的一样。
- 营火（campfire_cooking）：CanCookedFoodDict[原料] = 成品（值照旧是物品名，放不下 ID）；规矩同砧板。登记用的 ID 记在本模块，只有服务端知道：
  客户端查新接口登记的营火配方，给的是派生的 ID。
改完表让依赖它的缓存作废（CookingPot.rebuildIndex、BoardStation.invalidate）。登记 / 删除返回 {"ok", "error", "id"}。
"""
from . import RecipeIds
from ...Shared.Data.Cooking import CanCookedFoodDict
from ...Shared.Data.CookingPotRecipes import CookingPotRecipeList
from ...Shared.Data.Cutting import CuttingBoardDict, CuttingTagDict, axeList, hoeList, knifeList, pickaxeList, shearsList, shovelList
from ...Shared.Rules import BoardStation, CookingPot, ItemTags, PotSlots

try:
    _TEXT = (str, unicode)  # noqa: F821 - py2
except NameError:
    _TEXT = (str,)

SNAPSHOT_WAYS = 64
TOOLS = {"knife": (knifeList, None, "knife_dig"), "axe": (axeList, "axe", "axe_dig"), "pickaxe": (pickaxeList, "pickaxe", "pickaxe_dig"),
         "shovel": (shovelList, "shovel", "shovel_dig"), "hoe": (hoeList, "hoe", "hoe_dig"), "shears": (shearsList, "shears", "shears_dig")}
_ids = {"cutting": {}, "campfire_cooking": {}}       # 登记过的 ID -> 表里的键（砧板：(物品名, aux) 或标签名；营火：原料名）
_keys = {"cutting": {}, "campfire_cooking": {}}      # 反过来：表里的键 -> 登记它的 ID


def answer(ok, error, recipeId, **extra):
    found = {"ok": ok, "error": error, "id": recipeId}
    found.update(extra)
    return found


def _table(kind, key):
    if kind == "campfire_cooking":
        return CanCookedFoodDict
    return CuttingTagDict if not isinstance(key, tuple) else CuttingBoardDict


def _keysOf(kind):
    return list(CanCookedFoodDict) if kind == "campfire_cooking" else list(CuttingBoardDict) + list(CuttingTagDict)


def idOfKey(kind, key):
    """砧板 / 营火表里这个键的 ID。砧板：新接口登记的把 ID 写在条目里（"id"，随表同步到客户端，两端查到的一样），没写的派生；
    营火：表里的值是物品名、放不下 ID，登记过的记在本模块（只有服务端知道：客户端查到的是派生的 ID），没登记过的派生（RecipeIds）。"""
    if kind == "cutting":
        entry = _table(kind, key).get(key)
        written = entry.get("id") if isinstance(entry, dict) else None
        return written if isinstance(written, _TEXT) and written else RecipeIds.cuttingIdOf(key)
    found = _keys[kind].get(key)
    if found is not None:
        return found
    return RecipeIds.campfireIdOf(key)


def _keyOf(kind, recipeId):
    key = _ids[kind].get(recipeId)
    if key is not None and key in _table(kind, key) and idOfKey(kind, key) == recipeId:
        return key
    for key in _keysOf(kind):
        if idOfKey(kind, key) == recipeId:
            return key
    return None


def _cookingIndex(recipeId):
    ids = RecipeIds.cookingIds(CookingPotRecipeList)
    return ids.index(recipeId) if recipeId in ids else None


def find(recipeId):
    """这个 ID 现在的配方：("cooking", 下标) / ("cutting", 键) / ("campfire_cooking", 原料名)；没有（含已删的）是 None。"""
    index = _cookingIndex(recipeId)
    if index is not None:
        return ("cooking", index) if CookingPot.isLive(CookingPotRecipeList[index]) else None
    for kind in ("cutting", "campfire_cooking"):
        key = _keyOf(kind, recipeId)
        if key is not None:
            return kind, key
    return None


def idsOf(kind):
    """这一类现在的全部配方 ID（按表的先后；砧板先物品后标签，各按键排）。"""
    if kind == "cooking":
        return [recipeId for recipeId, row in zip(RecipeIds.cookingIds(CookingPotRecipeList), CookingPotRecipeList) if CookingPot.isLive(row)]
    keys = sorted(CanCookedFoodDict) if kind == "campfire_cooking" else sorted(CuttingBoardDict) + sorted(CuttingTagDict)
    return [idOfKey(kind, key) for key in keys]


def _remember(kind, recipeId, key):
    old = _ids[kind].pop(recipeId, None)
    if old is not None:
        _keys[kind].pop(old, None)
    other = _keys[kind].pop(key, None)
    if other is not None:
        _ids[kind].pop(other, None)
    _ids[kind][recipeId], _keys[kind][key] = key, recipeId


def _forget(kind, key):
    del _table(kind, key)[key]
    recipeId = _keys[kind].pop(key, None)
    if recipeId is not None:
        _ids[kind].pop(recipeId, None)
    BoardStation.invalidate()


def register(spec, recipeId):
    """规整的配方（Shared/Rules/RecipeJson.parse 的结果）以 recipeId 登记：新的追加，同 ID 的覆盖。"""
    kind = spec["type"]
    located = _cookingIndex(recipeId)
    current = ("cooking", located) if located is not None else find(recipeId)
    problem = RecipeIds.problemOf(recipeId, current is not None)
    if problem is not None:
        return answer(False, problem, recipeId)
    if current is not None and current[0] != kind:
        return answer(False, "type_mismatch", recipeId, current=current[0])
    if kind == "cooking":
        return _cooking(spec, recipeId, located)
    key = (spec["input"][1:] if not isinstance(spec["input"], tuple) else spec["input"]) if kind == "cutting" else spec["input"]
    if key in _table(kind, key) and idOfKey(kind, key) != recipeId:
        return answer(False, "input_taken", recipeId, by=idOfKey(kind, key))
    if current is not None and current[1] != key:
        _forget(kind, current[1])
    _table(kind, key)[key] = _cuttingEntry(spec, recipeId) if kind == "cutting" else spec["result"]
    _remember(kind, recipeId, key)
    BoardStation.invalidate()
    return answer(True, None, recipeId)


def _option(option):
    return option if not isinstance(option, tuple) else (option[0] if option[1] == 0 else option)


def _cooking(spec, recipeId, index):
    slots = [[_option(option) for option in slot] for slot in spec["slots"]]
    old = CookingPotRecipeList[index] if index is not None and isinstance(CookingPotRecipeList[index], dict) else None
    row = {"Id": recipeId, "Slots": slots, "Recipe": _ways(slots, old),
           "CookResult": tuple(spec["result"]), "CookCount": spec["count"], "PushItem": [], "text": _text(spec, old),
           "CookTime": spec["cookingTime"] / 20.0, "Experience": float(spec["experience"])}
    if spec.get("container"):
        row["Vessel"] = tuple(spec["container"])
    if index is None:
        CookingPotRecipeList.append(row)
    elif isinstance(CookingPotRecipeList[index], dict):
        CookingPotRecipeList[index].clear()
        CookingPotRecipeList[index].update(row)
    else:
        CookingPotRecipeList[index] = row
    CookingPot.rebuildIndex()
    return answer(True, None, recipeId)


def _text(spec, old):
    """经典界面食谱格里的名字：给了用给的；覆盖时没给沿用旧行的（农夫乐事的中文名不丢）；新登记的没给用成品的物品名
    （界面的标题、搜索都读这个键，没有它旧的原生界面会出错，所以不空着）。"""
    given = spec.get("text")
    if given:
        return given
    kept = old.get("text") if old is not None else None
    return kept if isinstance(kept, _TEXT) and kept else spec["result"][0]


def _ways(slots, old):
    """新行的 Recipe：按登记那一刻标签的成员展开的快照，再接上旧行里别的模组用旧接口（AddCookingPotRecipe）加的写法
    （旧行的 extraWays：格子不收的那几种），覆盖时不丢，和谁先加载无关。"""
    ways = [[tuple(entry) for entry in way] for way in PotSlots.expand(slots, ItemTags.itemsOf, SNAPSHOT_WAYS)]
    for way in (CookingPot.extraWays(old) if old is not None else ()):
        way = [tuple(entry) for entry in way]
        if way not in ways:
            ways.append(way)
    return ways


def _cuttingEntry(spec, recipeId):
    tool, itemType = spec["tool"], None
    if not isinstance(tool, list):
        tool, itemType = TOOLS[tool][0], TOOLS[tool][1]
    entry = {"itemList": [dict(result) for result in spec["results"]], "tool": tool, "id": recipeId}
    if itemType:
        entry["item_type"] = itemType
    return entry


def remove(recipeId):
    """删一条：厨锅打墓碑，砧板 / 营火真删。没有这个 ID（或已经删了）是 not_found。"""
    found = find(recipeId)
    if found is None:
        return answer(False, "not_found", recipeId)
    kind, key = found
    if kind == "cooking":
        CookingPotRecipeList[key]["Disabled"] = True
        CookingPot.rebuildIndex()
    else:
        _forget(kind, key)
    return answer(True, None, recipeId)
