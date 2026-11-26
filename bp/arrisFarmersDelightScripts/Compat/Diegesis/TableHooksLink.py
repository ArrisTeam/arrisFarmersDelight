# -*- coding: utf-8 -*-
"""TableHooksLink - 前置包的原版工作台站点上登记农夫乐事的两条规则：砧板菜不让在那里做、无序配方做完还容器（服务端）

沉浸式交互前置的原版工作台（它的内容包 Vanilla/）是脚本合成，引擎的 CraftItemOutputChangeServerEvent 不再触发：农夫乐事挂在这个事件上的
DishCrafts（拦砧板菜）、Server/CraftReturns（补还无序配方的容器）在那张工作台上不起作用。这里把同样的两条规则登到它的接口上
（serverApi.ImportModule(HOOKS)：addVeto / addRemainder，接口说明在前置包的 Vanilla/Server/TableHooks.py），规则还是那两份纯规则：
- dishVeto（board 那一步登：砧板站点登上了、配置的 remove_crafting_recipes 开着，和 DishCrafts 同一个条件）：九格里的原料正好是砧板菜的
  某条配方（Shared/Rules/DishStation.isDishCraft）就拒，给玩家看的话是 Tips.DISH_ON_BOARD（语言键 + 中文，前置包那边按玩家的语言查）；
- returns（table 那一步登）：成品对上本包的无序配方（Shared/Data/CraftReturns，Crafting.entryFor / returnsOf，一份每格还一件）就把容器
  放回原来那一格（前置包那边：放不回进背包，再放不下掉在脚下）；下游包在 Food.shapedRecipeContainerDict 登记的成品照旧契约每份还一个（进背包）。
九格是前置包给的配方朝向的物品字典（或 None），这两条规则只看有哪些原料，朝向不要紧。
前置包里没有这个模块（旧版本，比如还没有 Vanilla/ 的：引擎这时抛 ImportError: No module named …，不给 None，经 Compat/OtherMods
安静地当没有）：两样都不登，那张工作台本来也不存在；这个模块导入出错（经 Compat/OtherMods，打一次日志）也当它不在——
board 那一步登否决时不再把异常抛出去，后面收砧板开关、旁观的切菜声照开。
"""
from . import BoardSwitch
from .. import OtherMods
from ...QuModLibs.Server import serverApi
from ...Shared.Data import Tips
from ...Shared.Data.CraftReturns import CraftReturns
from ...Shared.Data.Food import shapedRecipeContainerDict
from ...Shared.Rules import Crafting, DishStation

HOOKS = "arrisDiegesisScripts.Vanilla.Server.TableHooks"
API_VERSION = 1                     # 这里用到的接口（addVeto / addRemainder、话可以带语言键）从它的第 1 版起就有


def hooks():
    """前置包的工作台接口模块；前置包里没有它（旧版本：引擎抛 ImportError，OtherMods 不出声）、它导入出错（OtherMods 打一次日志）或接口版本不够是 None。"""
    found = OtherMods.find(serverApi.ImportModule, HOOKS)
    return found if found is not None and getattr(found, "API_VERSION", 0) >= API_VERSION else None


def _name(item):
    return (item or {}).get("newItemName") or (item or {}).get("itemName")


def gridOf(cells):
    """九格（物品字典或 None）-> {格: (物品名, 个数)}：和 Server/CraftReturns.readGrid 读出来的是同一种写法，Shared/Rules/Crafting 直接用。"""
    return dict((index, (_name(cell), int(cell.get("count") or 1))) for index, cell in enumerate(cells or ()) if cell and _name(cell))


def dishVeto(playerId, product, cells):
    """改在砧板上摆的菜：这张工作台不做，告诉玩家去砧板。这个玩家在设置里关了砧板（报上来的，BoardSwitch）就照做：他开不了砧板站点。"""
    if not BoardSwitch.boardOn(playerId):
        return None
    if not DishStation.isDishCraft(_name(product), Crafting.namesOf(gridOf(cells))):
        return None
    return Tips.DISH_ON_BOARD


def returns(playerId, product, cells):
    """这一份另外还回来的容器：[(格或 None, 物品)]。"""
    result = _name(product)
    entries = CraftReturns.get(result)
    if entries:
        grid = gridOf(cells)
        entry = Crafting.entryFor(entries, grid)
        if entry is None:
            return []
        return [(index, {"newItemName": left, "newAuxValue": 0, "count": count}) for index, left, count in Crafting.returnsOf(entry, grid, 1)]
    container = shapedRecipeContainerDict.get(result)
    if container:
        return [(None, {"newItemName": container["itemName"], "newAuxValue": container.get("auxValue", 0), "count": 1})]
    return []


def addDishVeto():
    """board 那一步调（砧板站点登上了、remove_crafting_recipes 开着）：登上否决。返回登上了没有。"""
    found = hooks()
    if found is not None:
        found.addVeto(dishVeto)
    return found is not None


def addReturns():
    """table 那一步调：登上还容器。返回登上了没有。"""
    found = hooks()
    if found is not None:
        found.addRemainder(returns)
    return found is not None
