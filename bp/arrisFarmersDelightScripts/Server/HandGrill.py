# -*- coding: utf-8 -*-
"""HandGrill - 炉灶的手工烧烤：手放的每一件先烤贴灶台那面，熟了等厨师翻，两面都熟留在灶台上等人取（服务端）

移植自 Hands-On Delight 的 station/StoveCooking.java；每个烤位的两面进度在 Shared/Rules/HandsOn/Grill.py。
每个炉灶一份 StoveHand，只活在内存里，站点关了它还在；方块没了才删。手放 / 手翻过的烤位由这里烤，
别的（FD 自己的右键放上去的）照旧由 Server/Stove.py 每件 30 秒烤好弹出来（JE：营火配方的 600 刻）。
"""
from ..Shared.Rules import GrillStation
from ..Shared.Rules.HandsOn import Grill

COOK_TIMER = 30                   # 与 Server/Stove.py 一致：烤位的 FD 计时（JE 的炉灶按营火配方 600 刻 = 30 秒）


class StoveHand(object):
    def __init__(self):
        self.grill = Grill.Grill(GrillStation.PLACES)
        self.cook = None                 # 最后放料 / 翻面的玩家
        self.finished = 0                # 两面烤好的件数（累计）
        self.just = []                   # 刚烤好、还没报给站点的烤位序号（站点每刻取走：报"烤好了"、放蒸汽和闪光）


_hands = {}


def handOf(dimensionId, blockPos):
    key = (dimensionId, tuple(blockPos))
    hand = _hands.get(key)
    if hand is None:
        hand = _hands[key] = StoveHand()
    return hand


def peek(dimensionId, blockPos):
    return _hands.get((dimensionId, tuple(blockPos)))


def forget(dimensionId, blockPos):
    _hands.pop((dimensionId, tuple(blockPos)), None)


def slotItem(blockEntityData, place):
    slot = blockEntityData[str(place)]
    item = slot.get("itemDict") if slot else None
    return item if item and item.get("newItemName") else None


def grill(hand, blockEntityData, dt):
    """手放的烤位烤 dt 秒（炉灶的 tick 调用）。返回 (这些烤位归手工管、FD 原样别碰, 有没有烤位换成了成品)。"""
    handled, changed, side = set(), False, GrillStation.sideSeconds()
    for place in range(GrillStation.PLACES):
        if not hand.grill.byHand(place):
            continue
        item = slotItem(blockEntityData, place)
        if item is None:
            hand.grill.farmersDelightsWay(place)
            continue
        handled.add(place)
        grilled = GrillStation.grilledOf(item["newItemName"])
        if grilled is None:
            continue                     # 已经烤好，留在灶台上等人取
        if hand.grill.step(place, dt, side, GrillStation.isOneSided(item["newItemName"])):
            done = {"newItemName": grilled, "newAuxValue": item.get("newAuxValue", 0), "count": 1}
            blockEntityData[str(place)] = {"itemDict": done, "cookTimer": COOK_TIMER}
            hand.grill.done(place)
            hand.finished += 1
            hand.just = (hand.just + [place])[-GrillStation.PLACES:]       # 没人开站点时不取，只留最近几个
            changed = True
    return handled, changed


def turn(hand, playerId, place, now, item):
    """playerId 翻 place 上的这件：有东西可烤（有营火配方就行，蛋也算）、离这件上次翻够久才算。FD 原样烤着的从此归厨师、从生开始算。"""
    hasFood = bool(item) and GrillStation.hasRecipe(item.get("newItemName"))
    if not hand.grill.toss(place, now, hasFood):
        return False
    hand.cook = playerId
    return True
