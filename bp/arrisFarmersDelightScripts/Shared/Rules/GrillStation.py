# -*- coding: utf-8 -*-
"""GrillStation - 炉灶站点的纯规则：站点的声明（六个烤位的槽组）、什么能摆上去、一面多久、这一下右键开不开站点（双端）

对应 Hands-On Delight：station/StoveStation.java 的 SCHEMA 与 opens、station/StoveCooking.java 的 sideTicks / takes / canGrill / isDone；
每个烤位的两面进度在 HandsOn/Grill.py，烤位的位置和画法在 HandsOn/StoveLayout.py 等。
炉灶一件 30 秒（和 JE 一样按营火配方的 600 刻，Server/Stove.py），手放的一件按 Grill.sideSeconds 算一面：30 / 1.5 / 2 = 10 秒；不看批量。
能烤什么和煎锅同一张表（PanStation），但炉灶不收蛋（HoD 的 NOT_ON_GRILL：蛋会从烤架的缝里漏下去，煎锅才收；农夫乐事自己的右键仍然能放）。
烤位坐标与 Shared/Rules/BlockDisplay.STOVE_SLOTS 一致（方块内的比例）。
"""
from ..Data.Cooking import StoveList
from ..Data.Cutting import knifeList
from .BlockDisplay import STOVE_SLOTS
from .HandsOn import Grill
from .PanStation import canFry as hasRecipe, friedOf as grilledOf, isOneSided  # noqa: F401 - 炉灶与煎锅同一张表

STATION_ID = "arris:stove"
STOVE_BLOCKS = StoveList          # 同一个列表对象：附属包追加的炉灶也开站
RECIPE_SECONDS = 30.0             # FD 原样烤一件要多久（Server/Stove.py 的 COOK_TIMER，JE 的营火配方 600 刻）
PLACES = len(STOVE_SLOTS)
GROUP_GRILL = "grill"             # 站点的槽组：六个烤位 = 方块实体数据里的 "0".."5"（一格一件）
NOT_ON_GRILL = frozenset(["minecraft:egg"])      # 从烤架的缝里漏下去的（HoD 的 KitchenTags.NOT_ON_GRILL，默认是蛋）
STOVE_USES = ("minecraft:flint_and_steel", "minecraft:fire_charge")     # 炉灶自己用得上的：点火（铲子、桶按物品类型认）
KITCHEN_THINGS = ("minecraft:bowl", "minecraft:glass_bottle", "minecraft:shears")
CUTTING_TYPES = ("axe", "pickaxe", "hoe")                                # 砧板上用的工具（刀另查 knifeList）


def sideSeconds():
    return Grill.sideSeconds(RECIPE_SECONDS)


def slotCenter(place):
    """第 place 个烤位在方块里的位置（方块内的比例 x, z）。"""
    return STOVE_SLOTS[place]


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
    （"food" / "block" / "shovel" / "bucket" ...），covered 是炉灶上面盖着东西。

    上面摆着锅或煎锅：烤架是它们的，不开。空手、有营火配方的（蛋也算，开了站点再把它弹回）、食物、刀和砧板上用的工具、碗、玻璃瓶：开。
    炉灶自己用得上的（打火石、火焰弹点火，铲子、桶灭火，不是食物的方块——往上摆锅）和别的东西：不开，照原来的用法。
    """
    if covered:
        return False
    if not held or hasRecipe(held) or itemType == "food":
        return True
    if itemType in ("block", "shovel", "bucket") or held in STOVE_USES:
        return False
    return held in knifeList or itemType in CUTTING_TYPES or held in KITCHEN_THINGS
