# -*- coding: utf-8 -*-
"""SkilletHand - 手持煎锅烹饪：一只手煎锅、另一只手原料，在热源旁按住右键，煎好一件（服务端）

JE SkilletItem.use / getUseDuration / onUseTick / releaseUsing / finishUsingItem：
- 一只手煎锅、另一只手原料（JE 两只手都认；基岩版生肉放不进副手，常用的是煎锅放副手、原料拿主手，见 SkilletHandRules.skilletHand），
  玩家着火或脚下 3x3x3 里有热源才能开始（热源只看方块：名单或两个热源标签，营火熄没熄不管，Shared/Rules/HeatSources.nearHeat；
  食物要有营火配方：CanCookedFoodDict，表里没有的问引擎的营火配方，Shared/Rules/Grilling）；
- 煎一件的时间 = SkilletBlock.getSkilletCookingTime(营火配方 600 刻, 这把煎锅的火焰附加)：6 / 4 / 3 秒；
- 另一只手没有能煎的食物：提示"用另一只手拿着原料！"；头泡在水里：提示"在水里可没法煎啊……"（潜行时不提示：潜行右键方块是放煎锅，
  那一下 JE 不走 use()，总不能每放一次煎锅都冒一句）；
- 按住期间每刻 1/50 的概率响一声滋滋（JE 是本地声音，只有自己听得到）；
- 按住时点一下左键翻面（FlipSkilletMessage）：13 刻之后响一声下料（音量 0.4，音调 0.9 ~ 1.1，所有人听得到，JE 是服务端放的声音），翻的过程中再点不算；
  JE 翻的是煎锅里的 Flipped 记号、画面上手里的锅翻一下，这里画不了（物品模型是静态的），只有那一声；
- 松手什么都不发生。JE 把那一件放回背包；这里食物到做好那一刻才从拿原料的那只手拿走，所以掉线、死亡、换物品都不会丢东西；
- 做好：原料少 1 件（创造模式也扣，JE 就是这样）、成品进背包（满了掉在脚下）、煎锅不磨损；
  按住不放就接着煎下一件（JE 里按住右键会每 4 刻重新使用一次，这里是客户端下一次"按着"的报告）。
客户端的"按着 / 松开"报告由 Server/SkilletHold.py 收下，调这里的 onHeld / onRelease。
"""
import math
import random
import time

from .Helpers.Engine import compFactory, levelId, Call, ItemPosType, GetBlockName, GetCarriedItem, ShowTip
from .Helpers.Fx import ToAllPlayerPlaySound
from .Helpers.Player import GiveOrDropItem
from ..Shared.Data import Tips
from ..Shared.Rules import Grilling, HeatSources
from ..Shared.Rules import SkilletHandRules as Hand
from ..Shared.Rules import SkilletRules as Rules

# 手持烹饪每 STEP 秒看一次：还按着吗、手里还是煎锅吗、该做好了吗
STEP = 0.25
# 站着时眼睛比脚高多少（判断头泡没泡在水里）
EYE_HEIGHT = 1.62
SIZZLE_SOUND = "ambient.skillet.sizzle"
FLIP_SOUND = "ambient.skillet.addfood"          # FD 的 block.skillet.add_food（放进煎锅的下料声）
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


def _hands(playerId):
    """(煎锅那件物品, 原料那只手里的物品, 原料在哪只手的 ItemPosType)；两只手都没拿煎锅返回 None。"""
    main, off = GetCarriedItem(playerId, True), _offhand(playerId)
    side = Hand.skilletHand(main and main["newItemName"], off and off["newItemName"], Rules.SKILLET_ITEM)
    if side == Hand.MAIN:
        return main, off, ItemPosType.OFFHAND
    if side == Hand.OFF:
        return off, main, ItemPosType.CARRIED
    return None


def _underWater(footPos, dimensionId):
    """JE player.isUnderWater()：眼睛所在那一格有水。"""
    eye = (int(math.floor(footPos[0])), int(math.floor(footPos[1] + EYE_HEIGHT)), int(math.floor(footPos[2])))
    liquid = compFactory.CreateBlockInfo(levelId).GetLiquidBlock(eye, dimensionId)
    return bool(liquid) and liquid.get("name") in _WATER


def _begin(playerId, now):
    hands = _hands(playerId)
    if hands is None:
        return
    held, food = hands[0], hands[1]
    dimensionId = compFactory.CreateDimension(playerId).GetEntityDimensionId()
    footPos = compFactory.CreatePos(playerId).GetFootPos()
    onFire = bool(compFactory.CreateAttr(playerId).IsEntityOnFire())
    if not Rules.nearHeat(footPos, lambda pos: GetBlockName(pos, dimensionId), HeatSources.NEAR, onFire):
        return
    result = Grilling.resultOf(food["newItemName"], food.get("newAuxValue") or 0) if food else None
    quiet = compFactory.CreatePlayer(playerId).isSneaking() is True
    if result is None:
        if not quiet:
            ShowTip(playerId, Tips.SKILLET_HOW_TO_COOK)
        return
    if _underWater(footPos, dimensionId):
        if not quiet:
            ShowTip(playerId, Tips.SKILLET_UNDERWATER_HAND)
        return
    seconds = Rules.cookingSeconds(Rules.CAMPFIRE_TICKS, Rules.fireAspectLevel(held))
    _sessions[playerId] = Hand.HandCook(food["newItemName"], result, seconds, now)
    compFactory.CreateGame(levelId).AddTimer(STEP, _step, playerId)


def onFlip(playerId):
    """客户端报告按住时点了一下左键（JE 的 FlipSkilletMessage）：正在煎、而且不在翻面中才算，13 刻后翻一次、响一声。"""
    session = _sessions.get(playerId)
    if session is None or session.flipping:
        return
    session.flipping = True
    compFactory.CreateGame(levelId).AddTimer(Hand.FLIP_SECONDS, _flipped, playerId, session)


def _flipped(playerId, session):
    """翻面到点：还在煎同一件（中途松手、做好了就不翻，JE 的 onUseTick 只在使用中才走）才响一声；位置是玩家脚下（x、z 各加 0.5，FD 原样）。"""
    if _sessions.get(playerId) is not session:
        return
    session.flipping = False
    footPos = compFactory.CreatePos(playerId).GetFootPos()
    dimensionId = compFactory.CreateDimension(playerId).GetEntityDimensionId()
    ToAllPlayerPlaySound(dimensionId, (footPos[0] + 0.5, footPos[1], footPos[2] + 0.5), FLIP_SOUND, Hand.FLIP_VOLUME, Hand.flipPitch(random.random()))


def _step(playerId):
    session = _sessions.get(playerId)
    if session is None:
        return
    now = _now()
    if not _holds.held(playerId, now) or _hands(playerId) is None:
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
    """JE finishUsingItem：成品给玩家。食物这时才从拿原料的那只手拿走一件（那只手换了别的东西就什么都不做）。"""
    hands = _hands(playerId)
    food = hands[1] if hands else None
    if not food or food["newItemName"] != session.food:
        return
    food["count"] -= 1
    compFactory.CreateItem(playerId).SetEntityItem(hands[2], food if food["count"] > 0 else None, 0)
    GiveOrDropItem(playerId, {"itemName": session.result, "auxValue": 0, "count": 1})
