# -*- coding: utf-8 -*-
"""RopeAndNet - 绳子攀爬、绳子敲钟、安全网弹跳、爬绳时免摔落伤害与不踩坏耕地（服务端）"""
from ..QuModLibs.Server import AllowCall, InjectHttpPlayerId
from .EventRegistry import registerHandler
from .Helpers.Engine import compFactory, System, GetBlockName, GetEngineTypeStr
from .Helpers.Player import SetPlayerUsedCD
from ..Shared.Data.Blocks import canClimbList
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


def _bounce(fallDistance):
    if fallDistance <= 10:
        return fallDistance * 0.1
    if fallDistance <= 50:
        return fallDistance * 0.05
    return fallDistance * 0.01


@registerHandler("OnBeforeFallOnBlockServerEvent", match=SAFETY_NET)
def OnFallOnSafetyNet(args):
    # 落在安全网上的实体弹起来并取消伤害；潜行的玩家不弹
    entityId = args["entityId"]
    fallDistance = args["fallDistance"]
    if fallDistance <= 0.5:
        return
    if GetEngineTypeStr(entityId) == "minecraft:player":
        if compFactory.CreatePlayer(entityId).isSneaking() is not False:
            return
        compFactory.CreateActorMotion(entityId).SetPlayerMotion((0, _bounce(fallDistance), 0))
    else:
        compFactory.CreateActorMotion(entityId).SetMotion((0, _bounce(fallDistance), 0))
    args["cancel"] = True


@registerHandler("ServerBlockUseEvent", match=ROPE)
def OnUseRope(args):
    # 绳子一路连到上方的钟时，右键绳子敲钟
    x, y, z = args["x"], args["y"], args["z"]
    dimensionId = args["dimensionId"]
    if SetPlayerUsedCD(args["playerId"]) is True:
        return
    names = [GetBlockName((x, i, z), dimensionId) for i in range(y, y + BELL_SEARCH)]
    if "minecraft:bell" not in names:
        return
    index = names.index("minecraft:bell")
    if names[0:index].count(ROPE) == index:
        System.CreateEngineEntityByTypeStr("arris:toll_entity", (x + 0.5, y + index + 0.6, z + 0.5), (0, 0), dimensionId)


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
