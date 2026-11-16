# -*- coding: utf-8 -*-
"""SkilletHand - 手持煎锅烹饪：主手煎锅、副手食物，在热源旁按住右键，煎好一件（服务端）

JE SkilletItem.use / getUseDuration / onUseTick / releaseUsing / finishUsingItem：
- 主手煎锅，玩家着火或脚下 3x3x3 里有热源才能开始（热源只看方块，营火熄没熄不管；食物要有营火配方，即 CanCookedFoodDict）；
- 煎一件的时间 = SkilletBlock.getSkilletCookingTime(营火配方 600 刻, 这把煎锅的火焰附加)：6 / 4 / 3 秒；
- 副手没有能煎的食物：提示"用另一只手拿着原料！"；头泡在水里：提示"在水里可没法煎啊……"（潜行时不提示：潜行右键方块是放煎锅，
  那一下 JE 不走 use()，总不能每放一次煎锅都冒一句）；
- 按住期间每刻 1/50 的概率响一声滋滋（JE 是本地声音，只有自己听得到）；
- 松手什么都不发生。JE 把那一件放回背包；这里食物到做好那一刻才从副手拿走，所以掉线、死亡、换物品都不会丢东西；
- 做好：副手少 1 件（创造模式也扣，JE 就是这样）、成品进背包（满了掉在脚下）、煎锅不磨损；
  按住不放就接着煎下一件（JE 里按住右键会每 4 刻重新使用一次，这里是客户端下一次"按着"的报告）。
客户端的"按着 / 松开"报告由 Server/SkilletHold.py 收下，调这里的 onHeld / onRelease。
"""
import math
import random
import time

from .Helpers.Engine import compFactory, levelId, Call, ItemPosType, GetBlockName, GetCarriedItem, ShowTip
from .Helpers.Player import GiveOrDropItem
from ..Shared.Data.Cooking import CanCookedFoodDict, CanProvideHeatBlockList
from ..Shared.Rules import SkilletHandRules as Hand
from ..Shared.Rules import SkilletRules as Rules

# 手持烹饪每 STEP 秒看一次：还按着吗、手里还是煎锅吗、该做好了吗
STEP = 0.25
# 站着时眼睛比脚高多少（判断头泡没泡在水里）
EYE_HEIGHT = 1.62
SIZZLE_SOUND = "ambient.skillet.sizzle"
_WATER = ("minecraft:water", "minecraft:flowing_water")

_holds = Hand.HoldTracker()
_sessions = {}          # 玩家 -> 正在煎的这一件（Hand.HandCook）
_now = time.time        # 测试里换成假时钟


def onHeld(playerId):
    """客户端报告右键按着（按下时一次，按住期间约每 0.2 秒一次）。没有在煎的话这就是 JE 的 use()：满足条件就开始煎。"""
    now = _now()
    _holds.beat(playerId, now)
    if playerId not in _sessions:
        _begin(playerId, now)


def onRelease(playerId):
    """客户端报告松开。正在煎的那一件在下一步看到不按着就算了（食物还在副手，什么都没丢）。"""
    _holds.release(playerId)


def _offhand(playerId):
    return compFactory.CreateItem(playerId).GetPlayerItem(ItemPosType.OFFHAND, 0, True)


def _underWater(footPos, dimensionId):
    """JE player.isUnderWater()：眼睛所在那一格有水。"""
    eye = (int(math.floor(footPos[0])), int(math.floor(footPos[1] + EYE_HEIGHT)), int(math.floor(footPos[2])))
    liquid = compFactory.CreateBlockInfo(levelId).GetLiquidBlock(eye, dimensionId)
    return bool(liquid) and liquid.get("name") in _WATER


def _begin(playerId, now):
    held = GetCarriedItem(playerId, True)
    if not held or held["newItemName"] != Rules.SKILLET_ITEM:
        return
    dimensionId = compFactory.CreateDimension(playerId).GetEntityDimensionId()
    footPos = compFactory.CreatePos(playerId).GetFootPos()
    onFire = bool(compFactory.CreateAttr(playerId).IsEntityOnFire())
    if not Rules.nearHeat(footPos, lambda pos: GetBlockName(pos, dimensionId), CanProvideHeatBlockList, onFire):
        return
    food = _offhand(playerId)
    result = CanCookedFoodDict.get(food["newItemName"]) if food else None
    quiet = compFactory.CreatePlayer(playerId).isSneaking() is True
    if result is None:
        if not quiet:
            ShowTip(playerId, Rules.TIP_HOW_TO_COOK)
        return
    if _underWater(footPos, dimensionId):
        if not quiet:
            ShowTip(playerId, Rules.TIP_UNDERWATER_HAND)
        return
    seconds = Rules.cookingSeconds(Rules.CAMPFIRE_TICKS, Rules.fireAspectLevel(held))
    _sessions[playerId] = Hand.HandCook(food["newItemName"], result, seconds, now)
    compFactory.CreateGame(levelId).AddTimer(STEP, _step, playerId)


def _step(playerId):
    session = _sessions.get(playerId)
    if session is None:
        return
    now = _now()
    held = GetCarriedItem(playerId) if _holds.held(playerId, now) else None
    if not held or held["newItemName"] != Rules.SKILLET_ITEM:
        del _sessions[playerId]                 # JE releaseUsing：松手 / 手里换了东西，什么都不做
        return
    if random.random() < Hand.sizzleChance(STEP):
        _sizzle(playerId)
    if session.finished(now):
        del _sessions[playerId]
        _finish(playerId, session)
        return
    compFactory.CreateGame(levelId).AddTimer(STEP, _step, playerId)


def _sizzle(playerId):
    dimensionId = compFactory.CreateDimension(playerId).GetEntityDimensionId()
    Call(playerId, "OnPlaySound", {"soundName": SIZZLE_SOUND, "pos": compFactory.CreatePos(playerId).GetFootPos(), "dimensionId": dimensionId})


def _finish(playerId, session):
    """JE finishUsingItem：成品给玩家。食物这时才从副手拿走一件（副手换了别的东西就什么都不做）。"""
    food = _offhand(playerId)
    if not food or food["newItemName"] != session.food:
        return
    food["count"] -= 1
    compFactory.CreateItem(playerId).SetEntityItem(ItemPosType.OFFHAND, food if food["count"] > 0 else None, 0)
    GiveOrDropItem(playerId, {"itemName": session.result, "auxValue": 0, "count": 1})
