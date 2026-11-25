# -*- coding: utf-8 -*-
"""RecipeIds - 配方 ID 的规矩：写法、哪些命名空间不让登记、没登记过 ID 的配方派生的 ID（双端，不碰引擎）

- 配方 ID 写成 "命名空间:类型/名字"（和机械动力一样）：第三方用自己的命名空间，如 mymod:cooking/stew；
- farmersdelight: 留给主包：只能用它覆盖主包已有的配方（同 ID 再登记 = 覆盖），不能新加；
- legacy: 是旧格式（联动契约 ModAttr）追加进来的配方的派生 ID，只读：能查、能删，不能用它登记。
  厨锅：legacy:cooking/<成品的命名空间>/<成品名>，同一成品的第 2、3 条按表的先后加 _2、_3（不用表里的序号：序号跟着下游包的加载顺序走）；
  砧板：legacy:cutting/<原料的命名空间>/<原料名>（aux 不是 0 时加 _aux），按标签的 legacy:cutting/tag/<标签的命名空间>/<标签名>；
  营火：legacy:campfire_cooking/<原料的命名空间>/<原料名>；
- 主包自己的砧板、营火配方（本模块导入时就在表里的，早于任何下游追加）派生成同样写法的 farmersdelight:cutting/...、
  farmersdelight:campfire_cooking/...；主包按标签的砧板配方照 JE 叫 farmersdelight:cutting/tag_<标签名>（JE 的 tag_dough）。
主包的厨锅配方都写着 Id（JE 的 farmersdelight:cooking/<文件名>）。
"""
from ...Shared.Data.Cooking import CanCookedFoodDict
from ...Shared.Data.Cutting import CuttingBoardDict, CuttingTagDict

HOST = "farmersdelight"
LEGACY = "legacy"
TYPES = {"cooking": "cooking", "farmersdelight:cooking": "cooking", "cutting": "cutting", "farmersdelight:cutting": "cutting",
         "campfire_cooking": "campfire_cooking", "minecraft:campfire_cooking": "campfire_cooking"}
_BUILT_IN = {"cutting": frozenset(CuttingBoardDict), "tags": frozenset(CuttingTagDict), "campfire_cooking": frozenset(CanCookedFoodDict)}

try:
    _TEXT = (str, unicode)  # noqa: F821 - py2
except NameError:
    _TEXT = (str,)


def typeOf(recipeType):
    """配方类型的写法 -> "cooking" / "cutting" / "campfire_cooking"（带不带 farmersdelight: / minecraft: 前缀都认）；不认识是 None。"""
    return TYPES.get(recipeType) if isinstance(recipeType, _TEXT) else None


def split(recipeId):
    """"ns:path" -> (ns, path)；写法不对（没有冒号、有空格、两边有空的）是 None。"""
    if not isinstance(recipeId, _TEXT) or recipeId.count(":") != 1 or " " in recipeId:
        return None
    namespace, path = recipeId.split(":")
    return (namespace, path) if namespace and path else None


def problemOf(recipeId, exists):
    """登记用的 ID 有什么不对：invalid_id（写法不对）、reserved_namespace（legacy:，或者 farmersdelight: 却不是覆盖已有的）；没问题是 None。"""
    parts = split(recipeId)
    if parts is None:
        return "invalid_id"
    if parts[0] == LEGACY or (parts[0] == HOST and not exists):
        return "reserved_namespace"
    return None


def _itemPath(name, aux=0):
    namespace, _colon, path = name.partition(":")
    return "%s/%s%s" % (namespace, path, "_%d" % aux if aux else "")


def cookingIds(table):
    """厨锅配方表每一行的 ID（写着 Id 的用它；没写的派生 legacy:cooking/...，同一成品按先后加 _2、_3；不是配方的行是 None）。"""
    found, seen = [], {}
    for row in table:
        result = row.get("CookResult") if isinstance(row, dict) else None
        if isinstance(row, dict) and isinstance(row.get("Id"), _TEXT):
            found.append(row["Id"])
        elif isinstance(result, (tuple, list)) and len(result) == 2 and isinstance(result[0], _TEXT) and result[0]:
            base = "%s:cooking/%s" % (LEGACY, _itemPath(result[0]))
            seen[base] = seen.get(base, 0) + 1
            found.append(base if seen[base] == 1 else "%s_%d" % (base, seen[base]))
        else:
            found.append(None)
    return found


def cuttingIdOf(key):
    """没登记过 ID 的砧板配方的 ID：key 是 (物品名, aux)（CuttingBoardDict）或标签名（CuttingTagDict）。"""
    if isinstance(key, tuple):
        namespace = HOST if key in _BUILT_IN["cutting"] else LEGACY
        return "%s:cutting/%s" % (namespace, _itemPath(key[0], key[1]))
    if key in _BUILT_IN["tags"]:
        return "%s:cutting/tag_%s" % (HOST, key.partition(":")[2])
    return "%s:cutting/tag/%s" % (LEGACY, _itemPath(key))


def campfireIdOf(name):
    """没登记过 ID 的营火烹饪条目（CanCookedFoodDict 的键）的 ID。"""
    namespace = HOST if name in _BUILT_IN["campfire_cooking"] else LEGACY
    return "%s:campfire_cooking/%s" % (namespace, _itemPath(name))
