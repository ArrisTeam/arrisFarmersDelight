# -*- coding: utf-8 -*-
"""TableClientLink - 联动步骤 table（客户端）：前置包原版工作台的配方书不列砧板菜

服务端在 board 那一步给前置包的原版工作台登了砧板菜的否决（BoardServerLink -> TableHooksLink.addDishVeto：砧板站点登上了、
remove_crafting_recipes 开着）。书在客户端，不知道服务端拦了什么：被拦的配方书里照样列出来，点了做才被拒（前置包第 6 轮实机）。
这里用同一个条件——这一端 board 那一步登上了（ctx.done，BoardView.register 没说不）、remove_crafting_recipes 开着——给它客户端的登记口
（clientApi.ImportModule(HOOKS)：addHidden，接口说明在前置包的 Vanilla/Client/TableBookHooks.py）登上"砧板菜不进书"。判法和否决同一套
（Shared/Rules/DishStation：书里按成品 + 配方每格能放的料对得上砧板的某条配方，isDishRecipe；拦配方不拦成品，同一成品的别的配方照列）。
前置包没有这个登记口（太旧、没装内容包，或者它导入出错——经 Compat/OtherMods 打一次日志）：skipped，和服务端 table 一步接口不在时一样；
登记口在、条件不满足：什么都不登（书照旧全列），记 ok。拒绝时给玩家看的话（带本包语言文件的键）在服务端那条否决里，前置包的客户端自己按玩家的语言查。
"""
from . import SettingsClientLink, Steps
from .. import OtherMods
from ...QuModLibs.Client import clientApi
from ...Shared.Rules import DishStation
from ...Shared.Rules import HandsOnOptions as Options

HOOKS = "arrisDiegesisScripts.Vanilla.Client.TableBookHooks"
API_VERSION = 1                     # addHidden 从它的第 1 版起就有


def hooks():
    """前置包配方书的客户端登记口；没有（前置包太旧、没装内容包）、它导入出错或接口版本不够是 None。"""
    found = OtherMods.find(clientApi.ImportModule, HOOKS)
    return found if found is not None and getattr(found, "API_VERSION", 0) >= API_VERSION else None


def hidden(product, ingredients):
    """书里不列：这条配方是砧板菜（ingredients 是每格能放的几种 [(物品名, aux 或 None)]）。
    这个玩家在设置里关了砧板（或总开关）时照列：他开不了砧板站点，服务端收到他报的值也不否决（SettingsClientLink，每次现读）。"""
    if not SettingsClientLink.boardOnForMe():
        return False
    return DishStation.isDishRecipe((product or {}).get("newItemName"), ingredients)


def link(ctx):
    found = hooks()
    if found is None:
        return False
    if ctx.done.get("board") == Steps.OK and Options.removeCraftingRecipes():
        found.addHidden(hidden)
    return True
