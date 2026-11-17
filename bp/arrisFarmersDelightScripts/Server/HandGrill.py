# -*- coding: utf-8 -*-
"""HandGrill - 炉灶的手工烧烤：手放的每一件先烤贴灶台那面，熟了等厨师翻，两面都熟留在灶台上等人取（服务端）

移植自 Hands-On Delight 的 station/StoveCooking.java；每个烤位的两面进度在 Shared/Rules/HandsOn/Grill.py。
每个炉灶一份 StoveHand，站点关了它还在；方块没了才删。进度同时存在方块实体数据 handGrill 里（JE 的 Grill 存在炉灶自己的方块实体里），
服务器重启后炉灶第一次 tick 接上。手放 / 手翻过的烤位由这里烤，别的（FD 自己的右键放上去的）照旧由 Server/Stove.py 每件 30 秒烤好弹出来（JE：营火配方的 600 刻）。
"""
from ..Shared.Rules import GrillStation
from ..Shared.Rules import HandsOnOptions as Options
from ..Shared.Rules.HandsOn import Grill

COOK_TIMER = 30                   # 与 Server/Stove.py 一致：烤位的 FD 计时（JE 的炉灶按营火配方 600 刻 = 30 秒）
SAVE_KEY = "handGrill"            # 方块实体数据里存手放进度的键（JE 的 Grill 存在炉灶自己的方块实体里：重启后也在）


class StoveHand(object):
    def __init__(self):
        self.grill = Grill.Grill(GrillStation.PLACES)
        self.cook = None                 # 最后放料 / 翻面的玩家
        self.finished = 0                # 两面烤好的件数（累计）
        self.just = []                   # 刚烤好、还没报给站点的烤位序号（站点每刻取走：报"烤好了"、放蒸汽和闪光）
        self.saved = self.grill.stateKey()   # 最后一次写进方块实体数据时的 Grill.stateKey()：变了才再写（空烤架不写）


_hands = {}


def handOf(dimensionId, blockPos, blockEntityData=None):
    """这个炉灶的手工烧烤；还没有时新建，给了方块实体数据就把存下的进度读回来（服务器重启后第一次）。"""
    key = (dimensionId, tuple(blockPos))
    hand = _hands.get(key)
    if hand is None:
        hand = _hands[key] = StoveHand()
        if blockEntityData is not None and hand.grill.load(blockEntityData[SAVE_KEY]):
            hand.saved = hand.grill.stateKey()
    return hand


def restore(dimensionId, blockPos, blockEntityData):
    """服务器重启后炉灶第一次 tick：存下过手放的进度就接上，没有返回 None（用不着手工烧烤的炉灶不建对象）。"""
    if blockEntityData is None or not blockEntityData[SAVE_KEY]:
        return None
    return handOf(dimensionId, blockPos, blockEntityData)


def save(hand, blockEntityData):
    """手放的进度写进方块实体数据（整体赋值才会存档）：只在变了（某件的进度走了 1/16 一格、手放的标记变了）时写。"""
    key = hand.grill.stateKey()
    if key != hand.saved:
        hand.saved = key
        blockEntityData[SAVE_KEY] = hand.grill.saved()


def peek(dimensionId, blockPos):
    return _hands.get((dimensionId, tuple(blockPos)))


def forget(dimensionId, blockPos):
    _hands.pop((dimensionId, tuple(blockPos)), None)


def slotItem(blockEntityData, place):
    slot = blockEntityData[str(place)]
    item = slot.get("itemDict") if slot else None
    return item if item and item.get("newItemName") else None


def handOver(hand, blockEntityData, place, item):
    """炉灶站点关了，没人能翻这一件了：交给 FD 原样烤，用配方的时间（站点关了倍率算 1.0），已经烤好的 1 刻就弹出来
    （StoveCooking.handOver / farmersDelightsTime；Grill.handOverSeconds 是它的时长）。"""
    hand.grill.farmersDelightsWay(place)
    done = GrillStation.grilledOf(item["newItemName"]) is None
    blockEntityData[str(place)] = {"itemDict": item, "cookTimer": Grill.handOverSeconds(GrillStation.RECIPE_SECONDS, done, Options.stoveTime())}


def grill(hand, blockEntityData, dt, lit=True):
    """手放的烤位烤 dt 秒（炉灶的 tick 调用）；lit 假（熄着的炉灶）不烤，进度也不凉（HoD 的 StoveCooking.tick：!lit 就 continue），空位复位的记账照走。
    返回 (这些烤位归手工管、FD 原样别碰, 有没有烤位换成了成品)。
    炉灶站点关了（配置里 stove 为假）：手放的都交给 FD 原样烤（StoveCooking.tick 的 !HandsOnConfig.stove()），这里一件也不管。"""
    handled, changed, side = set(), False, GrillStation.sideSeconds()
    for place in range(GrillStation.PLACES):
        if not hand.grill.byHand(place):
            continue
        item = slotItem(blockEntityData, place)
        if item is None:
            hand.grill.farmersDelightsWay(place)
            continue
        if not Options.stove():
            handOver(hand, blockEntityData, place, item)
            continue
        handled.add(place)
        grilled = GrillStation.grilledOf(item["newItemName"])
        if grilled is None:
            continue                     # 已经烤好，留在灶台上等人取
        if hand.grill.step(place, dt, side, GrillStation.isOneSided(item["newItemName"]), lit):
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
