# -*- coding: utf-8 -*-
"""Grilling - 能煎烤什么、煎烤成什么：先查 CanCookedFoodDict，查不到再问引擎的营火配方（双端，纯规则）

JE 的煎锅、炉灶、手持煎锅读的是原版的营火烹饪配方（RecipeType.CAMPFIRE_COOKING：SkilletBlockEntity、AbstractStoveBlockEntity、SkilletItem），
不是一张表。这边原来只有一张表（Shared/Data/Cooking.CanCookedFoodDict：JE 的 16 条营火配方，联动契约，下游追加、两端同步）。现在：
- 表照旧是第一来源，契约不变（下游追加的马上生效）；
- 表里没有的再问引擎的营火配方：CreateRecipe(levelId).GetRecipesByInput(名字, "campfire", aux, 1)（两端都有，3.10 实机两端都能用；
  官方备注"需要遍历较多数据，不建议频繁调用"：按 (名字, aux) 缓存，没有配方也记着）。别的模组给自己的生肉写了营火配方（配方 JSON 的
  tags 带 campfire），放到煎锅 / 炉灶上就能煎，煎成它配方里的东西。
引擎口两端各装一个（setPort，和 ItemTags 一样；口就是 TagPort.EnginePort）：port.campfireRecipes(名字, aux) -> 配方列表或 None。
单机（和开房的那台机器）两端共用这一份模块、两个口都在，而 GetRecipesByInput 只在自己那一端的线程里答得出（2026-11-26 实机，探针包的番茄
fdprobe:tomato 只靠营火配方能烤：客户端线程里服务端的口给 None、客户端的口给 [{'input': 'fdprobe:tomato', 'output': 'minecraft:iron_nugget'}]；
服务端线程里服务端的口给列表；没有营火配方的泥土在自己线程里给 []，服务端的口在客户端线程里给 None，客户端的口在服务端线程里照常答）。
以前只问排在前面的服务端的口：客户端线程先问（站点的托盘先亮、客户端预测）时把 None 记进缓存，服务端读到的也是它，这一局都烤不了。
所以问的时候按 SIDES 的先后挨个问，第一个不是 None 的答案算数（None：这个口在这个线程里答不了；[]：没有配方，是有效答案）；
都答 None 时当没有配方、也不记（换个线程问也许答得出）。标签那几个接口（LookupItemsByItemTag / GetItemTags / LookupBlocksByBlockTag /
GetBlockTags）跨线程照常答，ItemTags 照旧用排在前面的口。
"准备好没有"照旧看排在前面的那个口（单机是服务端的：它探的是标签反查，跨线程也答得对）：没有口（离线、沙箱）或者没准备好（客户端
进世界之前：配方随进世界才到，和标签同一个时候）时只认表，和以前一样；准备好的那一刻缓存清空。
返回值的形状（3.10 实机，2026-11-26，两端一样）：一个列表，每条是带 input / output 两个字符串键的 dict，output 是产物名——
GetRecipesByInput("minecraft:beef", "campfire", 0, 1) → [{'input': 'minecraft:beef', 'output': 'minecraft:cooked_beef'}]；牛肉末 → arris:beef_patty，
三种蛋 → arris:fried_egg。解析照旧写得宽容，留给别的版本（官方文档说熔炉配方输出数量大于 1 时 output 是 dict）：output / result；
字符串 "名字" / "名字:aux"；dict 的 item / itemName / newItemName / fullItemName / name；列表取第一个。认不出来就当没有这条配方，不抛。
产物只取名字（aux 照各处原来的写法）。
食谱书、JEI 里"列出全部能煎烤的东西"的地方照旧只列表里的（StationBooks、Compat/Jei）。
"""
from ..Data.Cooking import CanCookedFoodDict

SIDES = ("server", "client")          # 问的先后；"准备好没有"看排在前面的那个
RECIPE_TAG = "campfire"
_TEXT = (type(""), type(u""))
_NAME_KEYS = ("item", "itemName", "newItemName", "fullItemName", "name")
_ports = {}                           # 端 -> 口
_state = {"ready": False}
_cache = {}                           # (名字, aux) -> 产物名或 None：只在口准备好、有口答得出时写


def setPort(side, port):
    """装上一端的引擎口（port 为 None 是卸下）。side："server" / "client"。"""
    if side not in SIDES:
        raise ValueError("side 只能是 %s，给的是 %r" % ("、".join(SIDES), side))
    if port is None:
        _ports.pop(side, None)
    else:
        _ports[side] = port
    _state["ready"] = False
    _cache.clear()


def refresh():
    """丢掉缓存（下次重新问引擎）。"""
    _cache.clear()


def _ask(port, name, *args):
    try:
        return getattr(port, name)(*args)
    except Exception:  # noqa: BLE001 - 口出什么错都当没答，只认表
        return None


def _ready():
    """准备好没有：看排在前面的那个口；从没准备好变成准备好（或者反过来）时缓存清空。"""
    port = None
    for side in SIDES:
        port = _ports.get(side)
        if port is not None:
            break
    ok = port is not None and bool(_ask(port, "ready"))
    if ok != _state["ready"]:
        _state["ready"] = ok
        _cache.clear()
    return ok


def _recipesOf(itemName, aux):
    """按 SIDES 的先后挨个问装着的口，第一个不是 None 的答案算数（None：这个口在这个线程里答不了；[]：没有配方）；都答 None 是 None。"""
    for side in SIDES:
        port = _ports.get(side)
        found = _ask(port, "campfireRecipes", itemName, aux) if port is not None else None
        if found is not None:
            return found
    return None


def resultOf(itemName, aux=0):
    """这件东西（物品名、aux）能煎烤成什么（产物的物品名）；煎不了 None。"""
    if not itemName:
        return None
    found = CanCookedFoodDict.get(itemName)
    if found:
        return found
    if not _ready():
        return None
    key = (itemName, aux or 0)
    if key not in _cache:
        recipes = _recipesOf(itemName, aux or 0)
        if recipes is None:
            return None                   # 哪个口在这个线程里都答不了：不记（记下的 None 会挡住答得出的那一端）
        _cache[key] = cookedOf(recipes, itemName)
    return _cache[key]


def canCook(itemName, aux=0):
    """能不能煎烤（有产物）。"""
    return resultOf(itemName, aux) is not None


def cookedOf(recipes, itemName=None):
    """GetRecipesByInput 的返回 -> 第一条认得出来的配方的产物名（和原料一样的不算）；认不出 None。"""
    if not isinstance(recipes, (list, tuple)):
        return None
    for recipe in recipes:
        found = _outputName(recipe)
        if found and found != itemName:
            return found
    return None


def _outputName(recipe):
    if isinstance(recipe, dict) and len(recipe) == 1:
        key = list(recipe)[0]
        if isinstance(key, _TEXT) and key.startswith("minecraft:recipe") and isinstance(recipe[key], dict):
            recipe = recipe[key]                    # 整份配方 JSON 的样子：{"minecraft:recipe_furnace": {...}}
    if not isinstance(recipe, dict):
        return None
    for key in ("output", "result"):
        name = _itemName(recipe.get(key))
        if name:
            return name
    return None


def _itemName(value):
    """产物的写法 -> 物品名：字符串 "名字" / "名字:aux"、dict 里的名字键（值也可能是列表，1.20 起配方的 item 可以是一组）、列表取第一个。"""
    if isinstance(value, (list, tuple)):
        value = value[0] if value else None
    if isinstance(value, dict):
        for key in _NAME_KEYS:
            if isinstance(value.get(key), _TEXT + (list, tuple)):
                return _itemName(value[key])
        return None
    if isinstance(value, _TEXT):
        return _withoutAux(value)
    return None


def _withoutAux(text):
    """"minecraft:cooked_beef:0" -> "minecraft:cooked_beef"；没写命名空间的补上 minecraft:；空的、段数不对的 None。"""
    parts = text.strip().split(":")
    if len(parts) > 2 and parts[-1].lstrip("-").isdigit():
        parts = parts[:-1]
    if len(parts) == 1:
        parts = ["minecraft"] + parts
    if len(parts) != 2 or not parts[0] or not parts[1]:
        return None
    return ":".join(parts)
