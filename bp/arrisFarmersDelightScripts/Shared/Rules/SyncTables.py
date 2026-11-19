# -*- coding: utf-8 -*-
"""SyncTables - 哪些数据表要从服务端同步给客户端、两端共用的常量、并进去之后哪些缓存要重算（双端，纯规则）

背景：Api/LegacyModAttr.py 把 Shared/Data 里的配置表按引用交给下游模组，它们在服务端的 LoadServerAddonScriptsAfter 里往里追加自己的配方、刀、
可烹饪物、炉灶。客户端是另一个进程，有自己的一份 Shared/Data，下游追加的内容它没有——经典玩法全在服务端判，不受影响，但四个站点的客户端表现要读
这些表（托盘里哪些亮、借哪把刀、点板是切还是敲、食谱书的页、哪些方块开炉灶站点……）。所以服务端把"现在的表 - 导入时的表"发过去（TableDiff），
客户端并进自己的表（TableMerge）。表名就是联动契约的变量名；下面登记的是客户端真有地方读的那几张，别的在 NOT_SYNCED 里写明为什么不发。
三种表：ITEMS 名字列表（只追加）、MAP 字典（键可以是 (物品名, aux) 元组）、ROWS 按下标对应的列表（厨锅配方：书页的键就是下标，两端必须一一对上）。
"""
from ..Data import Cooking, CookingPotRecipes, Cutting, Dishes, Food
from . import BoardStation, CookingPot, DishStation
from .TableWire import Codec

ENDPOINT = "OnTableSync"      # 客户端端点名（Client/TableSync.py 里同名函数），服务端 Call 它
PROTOCOL = 1                  # 消息的版本：不认识的版本客户端一律不理
ITEMS, MAP, ROWS = "items", "map", "rows"

TABLES = (
    ("CuttingBoardDict", MAP, Cutting.CuttingBoardDict),                    # 砧板：能切什么、托盘里亮不亮、板上怎么画、食谱书
    ("knifeList", ITEMS, Cutting.knifeList),                                # 谁是刀：借刀、虚线、炉灶开不开
    ("axeList", ITEMS, Cutting.axeList),                                    # 斧：砧板配方的工具表
    ("CanCookedFoodDict", MAP, Cooking.CanCookedFoodDict),                  # 煎锅 / 炉灶能煎烤什么、食谱书、手持煎锅"煎还是吃"
    ("StoveList", ITEMS, Cooking.StoveList),                                # 哪些方块是炉灶：开不开站点、场景、方块上的物品
    ("CanProvideHeatBlockList", ITEMS, Cooking.CanProvideHeatBlockList),    # 热源方块：手持煎锅"身边有没有热源"
    ("CookingPotRecipeList", ROWS, CookingPotRecipes.CookingPotRecipeList),  # 厨锅：托盘里哪些亮、放不放得下、书页、汤色用的成品
    ("platePackagedFoodDict", MAP, Food.platePackagedFoodDict),             # 盘装的盛宴：砧板上的物品类型（客户端和服务端的 GetItemType 一致）
    ("DishList", ROWS, Dishes.DishList),                                    # 砧板摆盘的菜：托盘里哪些亮、层接不接得上、食谱书、悬着的成品
    ("OneSidedList", ITEMS, Cooking.OneSidedList),                          # 煎锅站点：只煎一面的不画翻面、不给翻
    ("NotOnGrillList", ITEMS, Cooking.NotOnGrillList),                      # 炉灶站点：烤架不收的，托盘里不亮、放不上去
)
BY_NAME = dict((name, (kind, container)) for name, kind, container in TABLES)

# 砧板配方的 tool 引用的就是这几个列表本身（Shared/Data/Cutting.py；下游按 obtain("knifeList") 拿到的也是它）：
# 编码时认出来写成引用，客户端换回它自己的那一个，所以之后往 knifeList 里追加的刀对所有配方一起生效，和服务端一样
REFS = {"knifeList": Cutting.knifeList, "axeList": Cutting.axeList, "pickaxeList": Cutting.pickaxeList,
        "shovelList": Cutting.shovelList, "hoeList": Cutting.hoeList, "shearsList": Cutting.shearsList}
CODEC = Codec(REFS)
# ROWS 的表里传不了的新增行用什么占着下标（TableDiff）：两端的索引都要把它当"不是一行"跳过。没写的表用厨锅配方的那一种
HOLES = {"DishList": {"result": ("", 0), "count": 1, "ingredients": [], "extras": [], "keeps": [], "source": ""}}

# 联动契约白名单（Api/LegacyModAttr.py）里没有同步的变量和原因：tests 核对"白名单 = 同步的 + 这里的"，新增变量时要在两处之一写明
NOT_SYNCED = {
    "ComposterItemDict": "只有服务端的堆肥逻辑读",
    "itemChangeBlockDict": "只有服务端的放置逻辑读（Server/ItemToBlock.py）",
    "shapedRecipeContainerDict": "只有服务端的合成剩余物读（Server/CraftReturns.py）",
    "pieList": "派的吃和切都在服务端；DishStation.isBlockResult 读它，但客户端不调（做成时的收尾由服务端算好随 assembled 事件发来）",
    "canClimbList": "只有服务端的爬绳逻辑读",
    "cabinetList": "只有服务端的存储逻辑读",
    "WildCropDict": "只有服务端的野生作物读",
    "cropsDict": "只有服务端的作物生长读",
    "negativeEffect": "只有服务端的食物效果读，而且是 frozenset，联动契约没法往里追加",
    "horseComponentsDict": "只有服务端的实体组件读",
    "wolfComponentsDict": "只有服务端的实体组件读",
    "uiGuideBookPath": "字符串常量，联动契约没法往里追加",
    "uiGuideBookScreen": "字符串常量，联动契约没法往里追加",
}


def recompute(name):
    """name 这张表被并进了新内容之后：依赖它的缓存重算（客户端的 TableMerge 调；站点读表是现读的，只有这两样自己存了一份）。"""
    if name == "CookingPotRecipeList":
        CookingPot.rebuildIndex()          # 按配方建的索引：哪些是食材 / 容器、各道菜煮多久、料怎么摆
    elif name in ("CuttingBoardDict", "knifeList", "axeList"):
        BoardStation.invalidate()          # 全部配方的工具名和物品类型
    elif name == "DishList":
        DishStation.rebuildIndex()         # 摆盘菜的索引：底座、收尾、哪些是成品
