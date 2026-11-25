# -*- coding: utf-8 -*-
"""GrillStation - 炉灶站点的纯规则：站点的声明（六个烤位的槽组）、什么能摆上去、一面多久、这一下右键开不开站点（双端）

对应 Hands-On Delight：station/StoveStation.java 的 SCHEMA 与 opens、station/StoveCooking.java 的 sideTicks / takes / canGrill / isDone；
每个烤位的两面进度在 HandsOn/Grill.py，烤位的位置和画法在 HandsOn/StoveLayout.py 等。
炉灶一件 30 秒（和 JE 一样按营火配方的 600 刻，Server/Stove.py），手放的一件按 Grill.sideSeconds 算一面：30 / 1.5 / 2 = 10 秒；不看批量。
能烤什么和煎锅同一个判断（PanStation.canFry → Grilling：CanCookedFoodDict，表里没有的问引擎的营火配方），但炉灶不收蛋
（HoD 的 NOT_ON_GRILL：蛋会从烤架的缝里漏下去，煎锅才收；农夫乐事自己的右键仍然能放）。
烤位的位置不在这里：HoD 场景里的像素坐标（HandsOn/StoveLayout，炉灶朝北那一份）就是站点空间，站点朝炉灶的正面（StoveFacing）；
世界里的展示用同一份换成方块内的比例（BlockDisplay.STOVE_SLOTS）。
"""
from ..Data.Cooking import NotOnGrillList
from .BlockDisplay import STOVE_SLOTS
from . import HandsOnOptions as Options
from . import Knives
from .GrillBlocks import GRILL_BLOCKS
from .HandsOn import Grill
from .PanStation import canFry as hasRecipe, friedOf as grilledOf, isCracked, isOneSided  # noqa: F401 - 炉灶与煎锅同一张表

STATION_ID = "arris:stove"
STOVE_BLOCKS = GRILL_BLOCKS       # 活的"in"容器：点着的（StoveList，附属包追加的炉灶也开站）和熄着的炉灶都开站，HoD 的 opens 不看 LIT
RECIPE_SECONDS = 30.0             # FD 原样烤一件要多久（Server/Stove.py 的 COOK_TIMER，JE 的营火配方 600 刻）
PLACES = len(STOVE_SLOTS)
GROUP_GRILL = "grill"             # 站点的槽组：六个烤位 = 方块实体数据里的 "0".."5"（一格一件）
NOT_ON_GRILL = NotOnGrillList     # 从烤架的缝里漏下去的（HoD 的 KitchenTags.NOT_ON_GRILL，默认是蛋）：数据表里的那个列表本身，下游经联动契约追加的也算
STOVE_USES = ("minecraft:flint_and_steel", "minecraft:fire_charge")     # 炉灶自己用得上的：点火（铲子、桶按物品类型认）
KITCHEN_THINGS = ("minecraft:bowl", "minecraft:glass_bottle", "minecraft:shears")
CUTTING_TYPES = ("axe", "pickaxe", "hoe")                                # 砧板上用的工具（刀另查 Knives.isKnife）


def sideSeconds():
    """手放的一件一面要多久；配置里的 stove_time（HandsOnConfig.stoveTime，炉灶站点关了是 1）是倍数，FD 自己的右键放上去的照旧 30 秒一件。"""
    return Grill.sideSeconds(RECIPE_SECONDS, Options.stoveTime())


def canGrill(itemName):
    """烤架收不收这种东西（StoveCooking.canGrill）：有营火配方、而且不是会漏下去的。"""
    return bool(itemName) and hasRecipe(itemName) and itemName not in NOT_ON_GRILL


def isDone(itemName):
    """烤架上的这件烤好了（StoveCooking.isDone）：再没有什么可以烤的了。"""
    return bool(itemName) and not hasRecipe(itemName)


def mayPlace(item):
    """schema 里 grill 槽组的 accepts 和逻辑的 mayPlace：只收烤架收的东西（StoveStation.SCHEMA 拒绝一切，所有的摆放都走 place 动作；
    本移植让内核自己的点击也能摆，Shift 点背包里的食物才能一次摆上去）。item 是物品字典。"""
    return canGrill(item.get("newItemName") if item else None)


def usable(itemName):
    """底部托盘里列哪些背包物品：烤得了的（StoveBehavior.onOpen 的 setInventoryFilter）。"""
    return canGrill(itemName)


def buildSchema(kit):
    """站点的声明，两端各建一份一模一样的（服务端登记站点、客户端登记表现时用）：一个 grill 槽组，六格、一格一件，留在方块里。
    kit 是带 StationSchema / SlotRules 的东西：前置包的服务端 Api 模块，或它的 Shared/Schema 模块（客户端经 ImportModule 拿）。"""
    rules = kit.SlotRules.DEFAULT.kept().withMaxStack(1).withAccepts(mayPlace)
    return kit.StationSchema.builder().slots(GROUP_GRILL, PLACES, rules).build()


def opens(held, itemType, covered):
    """这一下右键开不开炉灶的站点（StoveStation.opens）。held 是主手的物品名（空手 None），itemType 是引擎给的物品类型
    （"food" / "block" / "shovel" / "bucket" ...），covered 是炉灶上面盖着东西（StoveCover.covers：锅、煎锅、任何方块；FD 对盖住的炉灶
    还会把烤架上的东西全丢出来，Server/Stove.py）。

    上面盖着东西：烤架是它们的（锅、煎锅有自己的站点），不开。空手、有营火配方的（蛋也算，开了站点再把它弹回）、食物、刀和砧板上用的工具、碗、玻璃瓶：开。
    炉灶自己用得上的（打火石、火焰弹点火，铲子、桶灭火，不是食物的方块——往上摆锅）和别的东西：不开，照原来的用法。
    刀和别处同一条规则（Knives.isKnife：knifeList，或带 arris:knife / common:knife 标签；原来这里只看 knifeList，只挂了标签的刀开不了站点）。
    """
    if covered:
        return False
    if not held or hasRecipe(held) or itemType == "food":
        return True
    if itemType in ("block", "shovel", "bucket") or held in STOVE_USES:
        return False
    return Knives.isKnife(held) or itemType in CUTTING_TYPES or held in KITCHEN_THINGS
