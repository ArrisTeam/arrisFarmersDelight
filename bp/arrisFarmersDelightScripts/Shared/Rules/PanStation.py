# -*- coding: utf-8 -*-
"""PanStation - 煎锅站点的纯规则：站点声明（schema）、放得进吗、蛋只煎一面、一面要多久（双端）

对应 Hands-On Delight：station/SkilletStation.java（schema：PAN 槽一格、kept、什么都不让"库"自己放）与 station/SkilletCooking.java 的
takes / isOneSided / sideTicks / place。两面进度的状态机在 HandsOn/Frying.py。本移植的煎锅一件 6 秒（营火 30 秒的 20%，FD 原样，
火焰附加 I 4 秒、II 起 3 秒），手放的一批按 Frying.sideSeconds 算一面：6 * sqrt(件数) / 1.5 / 2，一件 2 秒一面、16 件 8 秒一面。

JE 的 PAN 槽是 FD 煎锅自己那一格的窗口，放和取都不走库的点击：放走自定义动作 place（光标上的一叠，左键整叠、右键一个；托盘里 Shift 点
走 onInventoryShiftClick），取走 take。基岩版内核对非空槽先问 mayTake，所以光标栈放进有东西的锅只能走 place；托盘里 Shift 点是内核的
QUICK_MOVE，它只看 pan 槽组的规则（accepts、一批 16 件的上限）和 mayPlace——两条路用的是同一份判断（mayPlace / SlotRules）。
"""
from ..Data.Cooking import CanCookedFoodDict
from .HandsOn import Frying

STATION_ID = "arris:skillet"
PAN_BLOCKS = ("arris:skillet",)
GROUP_PAN = "pan"                             # 站点的槽组：一格 = 方块实体数据 cookingDict（SkilletStation.PAN）
BATCH = Frying.BATCH                          # 一锅最多放几件
SKILLET_SECONDS = 6.0                         # FD 原样煎一件要多久（Server/Skillet.py 的 COOK_TIMER 从 7 倒数到 1）
CAMPFIRE_SECONDS = 30.0                       # 营火配方的时间（600 刻）：煎锅的时间从它算
ONE_SIDED = frozenset(("minecraft:egg",))     # 只煎一面、不用翻（HoD 的 KitchenTags.ONE_SIDED）


def canFry(itemName):
    return itemName in CanCookedFoodDict


def friedOf(itemName):
    return CanCookedFoodDict.get(itemName)


def isOneSided(itemName):
    return itemName in ONE_SIDED


def sideSeconds(batch, fireAspect=0):
    """手放的一批一面要多久。fireAspect 是方块里那件煎锅的火焰附加等级（JE：SkilletBlock.getSkilletCookingTime 再按 sideTicks 算）。"""
    seconds = SKILLET_SECONDS if not fireAspect else Frying.skilletSeconds(CAMPFIRE_SECONDS, fireAspect)
    return Frying.sideSeconds(seconds, batch)


def acceptsFryable(item):
    """schema 里 pan 槽组的 accepts：营火配方里有的才收（煎好的、别的东西都不收）。"""
    return canFry(item.get("newItemName"))


def acceptsNothing(item):
    return False


def buildSchema(kit):
    """站点的声明，两端各建一份一模一样的。kit 是带 StationSchema / SlotRules 的东西：前置包的服务端 Api 模块，或它的 Shared/Schema 模块。
    pan 一格、最多一批 16 件、关站不退还（kept：东西留在锅里接着煎）。"""
    return kit.StationSchema.builder().slots(GROUP_PAN, 1, kit.SlotRules.DEFAULT.withMaxStack(BATCH).kept().withAccepts(acceptsFryable)).build()


def mayPlace(inPan, item):
    """SkilletCooking.takes：这件东西现在放得进锅吗——煎得了，锅里是空的或是同一种（认 名字 + aux）。数量上限由槽组的 limitFor 管。
    水里泡着的锅不收，那要问方块（服务端的 PanLogic.mayPlace 另查）。"""
    if not item or not canFry(item.get("newItemName")):
        return False
    if not inPan or (inPan.get("count") or 0) <= 0:
        return True
    return (inPan.get("newItemName"), inPan.get("newAuxValue") or 0) == (item.get("newItemName"), item.get("newAuxValue") or 0)


def usable(name):
    """背包托盘里这种东西亮不亮：营火配方里有的（HoD 的 setInventoryFilter：SkilletCooking.recipe 有就亮）。"""
    return canFry(name)
