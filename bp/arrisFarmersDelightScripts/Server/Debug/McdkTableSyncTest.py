# -*- coding: utf-8 -*-
"""McdkTableSyncTest - 下游追加的表同步到客户端的游戏内自检（服务端）：测试函数，仅供 MCDK-MCP 的 execute_code / 开发调试调用

不会自动运行，没有 RPC 端点。在服务端照下游模组的写法（经 ModAttr("arris") 的联动契约三个函数）追加四样东西：一把刀（石剑）、
一条切菜配方（黏土球用刀切成 2 个糖，tool 是 obtain("knifeList") 拿到的那个列表）、一条厨锅配方（linkage.md 的示例：2 根木棍或 3 个圆石煮成钻石，碗盛，吐一个苹果）、
一个可煎烤的东西（胡萝卜 -> 金胡萝卜），再立刻调 Server/TableSync.step(everyone=True) 补发给在线的玩家（热重载脚本之后进过服的名单是空的，everyone 连没进过服的在线玩家也发；平时定时器最多 5 秒后发给进过服的人）。
之后在客户端调 Client/Debug/McdkTableSyncTest 的 mcdk_test_table_sync_client() 看客户端的表和站点的判断，再进四个站点看：
砧板托盘里黏土球和石剑亮、拿黏土球放上板后手空着借得到石剑、点板是落刀；厨锅托盘里木棍和圆石亮、书里多一页钻石；煎锅 / 炉灶托盘里胡萝卜亮、书里多一页。
mcdk_test_table_sync_remove() 把追加的从服务端的表里拿掉（只拿服务端的：联动契约只有追加，已经发给客户端的客户端留着，重开游戏才清）。
    from arrisFarmersDelightScripts.Server.Debug import McdkTableSyncTest as T
    return T.mcdk_test_table_sync_add()
"""
from .. import TableSync
from ..Helpers.Engine import compFactory
from ...Shared.Rules import BoardStation, CookingPot

KNIFE = "minecraft:stone_sword"
CUT_KEY = ("minecraft:clay_ball", 0)
COOKABLE, COOKED = "minecraft:carrot", "minecraft:golden_carrot"
RECIPE_TEXT = "表同步自检：钻石"       # 追加的厨锅配方的名字，拿掉时按它找


def _contract():
    attr = compFactory.CreateModAttr("arris")
    return attr.GetAttr("ArrisFarmersDelightInterface"), attr.GetAttr("ArrisFarmersDelightObtain")


def _recipe():
    return {"Recipe": [[("minecraft:stick", 0), ("minecraft:stick", 0)], [("minecraft:cobblestone", 0)] * 3],
            "CookResult": ("minecraft:diamond", 0), "Vessel": ("minecraft:bowl", 0), "PushItem": [("minecraft:apple", 0)], "text": RECIPE_TEXT}


def mcdk_test_table_sync_add():
    """测试函数：追加刀、切菜配方、厨锅配方、可煎烤的东西（已经有的不重复追加），补发；返回结构化结果。"""
    interface, obtain = _contract()
    if not interface or not obtain:
        return {"case": "table_sync_add", "ok": False, "error": "ModAttr arris 里没有联动契约的函数（Server/LegacyApi 没导入？）"}
    knives, cutting = obtain("knifeList"), obtain("CuttingBoardDict")
    if KNIFE not in knives:
        knives.append(KNIFE)
    if CUT_KEY not in cutting:
        interface("CuttingBoardDict", {CUT_KEY: {"itemList": [{"itemName": "minecraft:sugar", "count": 2}], "tool": knives}})
    if not [row for row in obtain("CookingPotRecipeList") if row.get("text") == RECIPE_TEXT]:
        interface("CookingPotRecipeList", _recipe())
    if COOKABLE not in obtain("CanCookedFoodDict"):
        interface("CanCookedFoodDict", {COOKABLE: COOKED})
    TableSync.step(everyone=True)
    return {"case": "table_sync_add", "ok": not TableSync.syncer.problems, "rev": TableSync.syncer.rev, "tables": TableSync.syncer.counts(),
            "problems": TableSync.syncer.problems, "players": sorted(TableSync._known)}


def mcdk_test_table_sync_remove():
    """测试函数：把上面追加的从服务端的表里拿掉（客户端留着，重开游戏才清）。"""
    _interface, obtain = _contract()
    if not obtain:
        return {"case": "table_sync_remove", "ok": False, "error": "ModAttr arris 里没有联动契约的函数"}
    knives, cutting, cookable, rows = obtain("knifeList"), obtain("CuttingBoardDict"), obtain("CanCookedFoodDict"), obtain("CookingPotRecipeList")
    removed = {"knife": KNIFE in knives, "cutting": CUT_KEY in cutting, "cookable": COOKABLE in cookable}
    while KNIFE in knives:
        knives.remove(KNIFE)
    cutting.pop(CUT_KEY, None)
    cookable.pop(COOKABLE, None)
    removed["recipes"] = len([row for row in rows if row.get("text") == RECIPE_TEXT])
    rows[:] = [row for row in rows if row.get("text") != RECIPE_TEXT]
    CookingPot.rebuildIndex()
    BoardStation.invalidate()
    return {"case": "table_sync_remove", "ok": True, "removed": removed}
