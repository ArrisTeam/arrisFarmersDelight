# -*- coding: utf-8 -*-
"""RecipeIds - 配方 ID 的规矩：写法、哪些命名空间不让登记、没登记过 ID 的配方派生的 ID（双端，不碰引擎）

- 配方 ID 写成 "命名空间:类型/名字"（和机械动力一样）：第三方用自己的命名空间，如 mymod:cooking/stew；
- farmersdelight: 留给主包：只能用它覆盖主包已有的配方（同 ID 再登记 = 覆盖），不能新加；
- legacy: 是旧格式（联动契约 ModAttr）追加进来的配方的派生 ID，只读：能查、能删，不能用它登记。
  厨锅：legacy:cooking/<成品的命名空间>/<成品名>，同一成品的第 2、3 条按表的先后加 _2、_3（不用表里的序号：序号跟着下游包的加载顺序走）；
  派生的名字被占了（明写的或先派生的）就接着加 _n 直到没人用（成品 pie、pie、pie_2 三行是 pie、pie_2、pie_2_2）；旧接口追加的行里
  明写的 Id 是 legacy: 开头的、写法不对的、或者是主包自带的砧板 / 营火配方的 ID，都当没写、照样派生（cookingIds）；
  砧板：legacy:cutting/<原料的命名空间>/<原料名>（aux 不是 0 时加 _aux），按标签的 legacy:cutting/tag/<标签的命名空间>/<标签名>；
  营火：legacy:campfire_cooking/<原料的命名空间>/<原料名>；
- 主包自己的砧板、营火配方（本模块导入时就在表里的，早于任何下游追加）派生成同样写法的 farmersdelight:cutting/...、
  farmersdelight:campfire_cooking/...；主包按标签的砧板配方照 JE 叫 farmersdelight:cutting/tag_<标签名>（JE 的 tag_dough）。
  这些自带的砧板、营火 ID 是从原料派生的，和原料绑死：用它登记（覆盖、删掉后加回来）时原料必须还是那一样（input_mismatch）、
  也只能登记回原来那一类配方（type_mismatch），
  不然原来的原料再被旧接口加回来时会派生出同一个 ID。想换原料：删掉自带的那条，用自己的 ID 登记。
主包的厨锅配方都写着 Id（JE 的 farmersdelight:cooking/<文件名>）。
砧板派生 ID 的已知重名：(mymod:foo, 2) 和 (mymod:foo_2, 0) 都派生成 legacy:cutting/mymod/foo_2，按 ID 只碰得到排在前面的那条
（字典表没有稳定的先后，加序号会让 ID 跟着别的键变，所以不改）。
"""
from ...Shared.Data.Cooking import CanCookedFoodDict
from ...Shared.Data.Cutting import CuttingBoardDict, CuttingTagDict

HOST = "farmersdelight"
LEGACY = "legacy"
TYPES = {"cooking": "cooking", "farmersdelight:cooking": "cooking", "cutting": "cutting", "farmersdelight:cutting": "cutting",
         "campfire_cooking": "campfire_cooking", "minecraft:campfire_cooking": "campfire_cooking"}
_IDS = {}                    # 自带的砧板 / 营火配方 ID -> (类型, 原料的键)：_builtInIds 第一次用到时填
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
    if parts[0] == LEGACY or (parts[0] == HOST and not exists and recipeId not in _builtInIds()):
        return "reserved_namespace"
    return None


def _builtInIds():
    """农夫乐事自带的砧板、营火配方的 ID -> (类型, 原料的键)（模块导入时表里的那些；删掉之后还能用原来的 ID 加回来，和厨锅的墓碑能复活对称）。"""
    if not _IDS:
        _IDS.update((cuttingIdOf(key), ("cutting", key)) for key in _BUILT_IN["cutting"])
        _IDS.update((cuttingIdOf(tag), ("cutting", tag)) for tag in _BUILT_IN["tags"])
        _IDS.update((campfireIdOf(name), ("campfire_cooking", name)) for name in _BUILT_IN["campfire_cooking"])
    return _IDS


def builtInKeyOf(recipeId):
    """农夫乐事自带的砧板 / 营火配方 ID 派生自的 (类型, 原料的键)：这些 ID 和原料绑死（用它登记时原料必须还是这一样，input_mismatch）；
    别的 ID 是 None。"""
    return _builtInIds().get(recipeId)


def _itemPath(name, aux=0):
    namespace, _colon, path = name.partition(":")
    return "%s/%s%s" % (namespace, path, "_%d" % aux if aux else "")


def cookingIds(table):
    """厨锅配方表每一行的 ID（不是配方的行是 None），按表的先后、结果是确定的：
    先收明写的 Id（写法对、不是 legacy: 开头、不是农夫乐事自带的砧板 / 营火配方的 ID；同一个只认第一行——旧接口追加的行可能带着
    从别的行拷来的 "Id"）；再给没有 ID 的行（含明写 legacy:、写法不对、自带砧板 / 营火 ID 的）派生 legacy:cooking/<成品的命名空间>/<成品名>，
    被占了（明写的或先派生的）就接着加 _2、_3……直到没人用（成品 pie、pie、pie_2 三行是 pie、pie_2、pie_2_2）。
    自带砧板 / 营火的 ID 不收：厨锅的 ID 先查（RecipeTables.find），一行厨锅配方写着它，那条切法 / 营火配方就按 ID 找不到、删不掉，
    墓碑还会一直占着它。"""
    ids, taken = [None] * len(table), set()
    for index, row in enumerate(table):
        given = row.get("Id") if isinstance(row, dict) else None
        parts = split(given) if isinstance(given, _TEXT) else None
        if parts is not None and parts[0] != LEGACY and given not in taken and builtInKeyOf(given) is None:
            taken.add(given)
            ids[index] = given
    for index, row in enumerate(table):
        result = row.get("CookResult") if isinstance(row, dict) else None
        if ids[index] is not None or not (isinstance(result, (tuple, list)) and len(result) == 2 and isinstance(result[0], _TEXT) and result[0]):
            continue
        base = candidate = "%s:cooking/%s" % (LEGACY, _itemPath(result[0]))
        count = 1
        while candidate in taken:
            count += 1
            candidate = "%s_%d" % (base, count)
        taken.add(candidate)
        ids[index] = candidate
    return ids


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
