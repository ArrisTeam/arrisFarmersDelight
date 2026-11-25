# -*- coding: utf-8 -*-
"""RopeAndNet - 绳子攀爬、敲钟、卷绳子、拿绳子点绳子往下接，安全网弹跳，爬绳时免摔落伤害与不踩坏耕地（服务端）

绳子与安全网照 JE 的 RopeBlock / RopeItem / SafetyNetBlock，规则在 Shared/Rules/RopeReel.py、RopeExtend.py、NetBounce.py。
"""
from ..QuModLibs.Server import AllowCall, InjectHttpPlayerId
from .EventRegistry import registerHandler
from .Helpers.Engine import compFactory, levelId, System, GetBlockName, GetCarriedItem, GetEngineTypeStr, IsLiving
from .Helpers.Fx import ToAllPlayerPlaySound
from .Helpers.Player import SetPlayerUsedCD, SetNotCreateItem, IsCreative
from ..Shared.Data import Blocks
from ..Shared.Data.Blocks import canClimbList
from ..Shared.Rules import NetBounce, RopeExtend, RopeReel
import math

ROPE = "arris:rope"
SAFETY_NET = "arris:safety_net"
# 从绳子往上找钟的最远距离（格）
BELL_SEARCH = 25
CLIMB_SPEED = 0.15


def _blockAt(pos, dimensionId):
    """实体浮点坐标所在方块的名字（负坐标也向下取整）。"""
    floored = (int(math.floor(pos[0])), int(math.floor(pos[1])), int(math.floor(pos[2])))
    return GetBlockName(floored, dimensionId)


def _nameAt(pos, dimensionId):
    """这一格的方块名；没加载的格子 None。"""
    info = compFactory.CreateBlockInfo(levelId).GetBlockNew(pos, dimensionId)
    return info["name"] if info else None


def _mayBuild(playerId):
    # JE 的 mayBuild：冒险、旁观和没有建造权限的玩家不行
    abilities = compFactory.CreatePlayer(playerId).GetPlayerAbilities()
    return bool(abilities and abilities.get("build"))


def _itemName(args):
    return args["itemDict"]["newItemName"]


@AllowCall
@InjectHttpPlayerId
def SetPlayerIsJumpExtra(playerId, data):
    # 客户端报告跳跃键是否按住（爬绳往上）；playerId 由服务端注入
    if not playerId:
        return
    isJump = data.get("isJump") if isinstance(data, dict) else None
    if isJump is None:
        return
    compFactory.CreateExtraData(playerId).SetExtraData("isJump", isJump)


@registerHandler("OnEntityInsideBlockServerEvent", match=canClimbList)
def OnEntityInsideClimbable(args):
    # 只有玩家能爬；按住跳跃往上，否则（不在飞行时）慢慢往下
    entityId = args["entityId"]
    if GetEngineTypeStr(entityId) != "minecraft:player":
        return
    if compFactory.CreateExtraData(entityId).GetExtraData("isJump") is True:
        compFactory.CreateActorMotion(entityId).SetPlayerMotion((0, CLIMB_SPEED, 0))
    elif compFactory.CreateFly(entityId).IsPlayerFlying() is False:
        compFactory.CreateActorMotion(entityId).SetPlayerMotion((0, -CLIMB_SPEED, 0))


@registerHandler("MobGriefingBlockServerEvent", match="minecraft:farmland")
def OnTrampleFarmlandOnRope(args):
    # 顺着绳子落下时不踩坏耕地
    pos = compFactory.CreatePos(args["entityId"]).GetPos()
    if pos is not None and _blockAt(pos, args["dimensionId"]) in canClimbList:
        args["cancel"] = True


@registerHandler("OnBeforeFallOnBlockServerEvent", match=SAFETY_NET)
def OnFallOnSafetyNet(args):
    # JE SafetyNetBlock：潜行的玩家照常摔（不弹）；其余一点摔落伤害都没有，竖直速度反过来乘 0.6（生物）/ 0.8（别的实体）
    entityId = args["entityId"]
    isPlayer = GetEngineTypeStr(entityId) == "minecraft:player"
    if isPlayer and compFactory.CreatePlayer(entityId).isSneaking() is not False:
        return
    args["cancel"] = True
    speed = NetBounce.bounceSpeed(args["fallDistance"], IsLiving(entityId))
    if speed <= 0:
        return
    if isPlayer:
        compFactory.CreateActorMotion(entityId).SetPlayerMotion((0, speed, 0))
    else:
        compFactory.CreateActorMotion(entityId).SetMotion((0, speed, 0))


def _reelRope(args):
    # 潜行：这根绳子最下面的一节收回背包（JE：destroyBlock(pos, false)，不掉落；背包放不下什么都不做）
    playerId = args["playerId"]
    dimensionId = args["dimensionId"]
    if not _mayBuild(playerId):
        return
    target = RopeReel.lowestRope((args["x"], args["y"], args["z"]), lambda pos: GetBlockName(pos, dimensionId) == ROPE)
    ropeItem = {"itemName": ROPE, "count": 1, "auxValue": 0}
    if not IsCreative(playerId) and not compFactory.CreateItem(playerId).SpawnItemToPlayerInv(ropeItem, playerId):
        return
    compFactory.CreateBlockInfo(levelId).SetBlockNew(target, {"name": "minecraft:air"}, 0, dimensionId)
    ToAllPlayerPlaySound(dimensionId, target, "dig.cloth")


@registerHandler("ServerBlockUseEvent", match=ROPE)
def OnUseRope(args):
    # JE RopeBlock.use：手里得是空的；潜行（配置 enableRopeReeling 开着）卷绳子，否则一路连到上方的钟时敲钟
    playerId = args["playerId"]
    if GetCarriedItem(playerId):
        return
    if SetPlayerUsedCD(playerId) is True:
        return
    if Blocks.enableRopeReeling and compFactory.CreatePlayer(playerId).isSneaking() is True:
        _reelRope(args)
        return
    x, y, z = args["x"], args["y"], args["z"]
    dimensionId = args["dimensionId"]
    names = [GetBlockName((x, i, z), dimensionId) for i in range(y, y + BELL_SEARCH)]
    if "minecraft:bell" not in names:
        return
    index = names.index("minecraft:bell")
    if names[0:index].count(ROPE) == index:
        System.CreateEngineEntityByTypeStr("arris:toll_entity", (x + 0.5, y + index + 0.6, z + 0.5), (0, 0), dimensionId)


# 优先级 98：和物品放成方块（ItemToBlock、榻榻米垫）同一档，见 Server/ModServer.py 的优先级表
@registerHandler("ServerItemUseOnEvent", match=ROPE, keyOf=_itemName, priority=98)
def OnPlaceRopeOnRope(args):
    # JE RopeItem：拿着绳子点绳子（潜行时也认挂着绳子的那一面），不潜行往下接到第一格能放的地方，潜行照点到的面放
    dimensionId = args["dimensionId"]
    playerId = args["entityId"]
    sneaking = compFactory.CreatePlayer(playerId).isSneaking() is True
    start = RopeExtend.startRope((args["x"], args["y"], args["z"]), args["face"], sneaking, lambda pos: _nameAt(pos, dimensionId))
    if start is None:
        return                                         # 和绳子无关（或者不潜行点在绳子旁边的方块上）：引擎照常
    args["ret"] = True                                 # 引擎自己放的那一格（点到的面外侧）不要，放不放都由这里定
    if SetPlayerUsedCD(playerId) is True or not _mayBuild(playerId):
        return True
    target = RopeExtend.placeAt(start, args["face"], sneaking, lambda pos: _nameAt(pos, dimensionId))
    if target is None or not compFactory.CreateBlockInfo(levelId).SetBlockNew(target, {"name": ROPE}, 0, dimensionId):
        return True
    ToAllPlayerPlaySound(dimensionId, (target[0] + 0.5, target[1] + 0.5, target[2] + 0.5), "dig.cloth")
    SetNotCreateItem(playerId, args["itemDict"])
    return True


# 优先级 60：DamageEvent 里排在展示实体（100）与食物效果（70）之后，与旧版模块加载顺序一致
@registerHandler("DamageEvent", priority=60)
def OnFallDamageInClimb(args):
    # 爬在绳子上时不受摔落伤害
    entityId = args["entityId"]
    if args["cause"] != "fall" or GetEngineTypeStr(entityId) != "minecraft:player":
        return
    pos = compFactory.CreatePos(entityId).GetPos()
    if pos is None:
        return
    dimensionId = compFactory.CreateDimension(entityId).GetEntityDimensionId()
    if _blockAt(pos, dimensionId) in canClimbList:
        args["damage"] = 0
