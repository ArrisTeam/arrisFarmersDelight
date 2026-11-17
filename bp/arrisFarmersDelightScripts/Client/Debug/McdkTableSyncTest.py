# -*- coding: utf-8 -*-
"""McdkTableSyncTest - 下游追加的表同步到客户端的游戏内自检（客户端）：测试函数，仅供 MCDK-MCP 的 execute_code（is_client 为 true）/ 开发调试调用

不会自动运行，没有 RPC 端点。配套服务端的 Server/Debug/McdkTableSyncTest（mcdk_test_table_sync_add 在服务端追加了石剑当刀、黏土球的切菜配方、
木棍 / 圆石煮钻石的厨锅配方、胡萝卜可煎烤）。这里看本端的表有没有收到，和站点的客户端判断（读的是同一批 Shared/Rules 函数）认不认得：
并表之前全是 False，并表之后（进服时、或服务端补发后）全是 True。
    from arrisFarmersDelightScripts.Client.Debug import McdkTableSyncTest as T
    return T.mcdk_test_table_sync_client()
"""
from .. import TableSync
from ...Shared.Data import Cutting
from ...Shared.Rules import BoardStation, CookingPot, GrillStation, PanStation, PotStation, StationBooks

# 和 Server/Debug/McdkTableSyncTest 是同一批（两端互不导入，各写一份）
KNIFE = "minecraft:stone_sword"
CUT_KEY = ("minecraft:clay_ball", 0)
COOKABLE = "minecraft:carrot"
STICK = ("minecraft:stick", 0)


def _item(name):
    return {"newItemName": name, "newAuxValue": 0, "count": 1}


def mcdk_test_table_sync_client():
    """测试函数：本端的表和站点判断认不认得服务端追加的东西；返回结构化结果。"""
    env = BoardStation.Env(lambda name: name in Cutting.knifeList, lambda item: "food")        # 砧板表现的 Env，刀和类型换成最简单的
    recipe = Cutting.CuttingBoardDict.get(CUT_KEY)
    checks = {
        "knife_in_table": KNIFE in Cutting.knifeList,
        "cutting_recipe_shares_knife_list": recipe is not None and recipe["tool"] is Cutting.knifeList,
        "board_clay_ball_is_cuttable": bool(env.cuttable(_item(CUT_KEY[0]))),
        "board_tray_lights_clay_ball_and_stone_sword": bool(env.usable(_item(CUT_KEY[0]))) and bool(env.usable(_item(KNIFE))),
        "board_borrows_stone_sword": bool(env.cutsWith(_item(CUT_KEY[0]), _item(KNIFE))),
        "pot_tray_lights_stick": bool(PotStation.usable(STICK)) and CookingPot.isIngredient(STICK),
        "pot_book_has_diamond_page": bool([page for page in StationBooks.potPages() if page["item"]["newItemName"] == "minecraft:diamond"]),
        "pan_tray_lights_carrot": bool(PanStation.usable(COOKABLE)),
        "grill_tray_lights_carrot": bool(GrillStation.usable(COOKABLE)),
        "pan_book_has_carrot_page": COOKABLE in [page["key"] for page in StationBooks.panPages()],
    }
    return {"case": "table_sync_client", "ok": all(checks.values()), "checks": checks, "sync": TableSync.status()}
