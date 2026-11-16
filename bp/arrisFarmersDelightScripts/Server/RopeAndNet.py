# -*- coding: utf-8 -*-
"""RopeAndNet - 绳子攀爬、敲钟、卷绳子，安全网弹跳，爬绳时免摔落伤害与不踩坏耕地（服务端）

绳子与安全网照 JE 的 RopeBlock / SafetyNetBlock，规则在 Shared/Rules/RopeReel.py、NetBounce.py。
"""
from ..QuModLibs.Server import AllowCall, InjectHttpPlayerId
from .EventRegistry import registerHandler
from .Helpers.Engine import compFactory, levelId, System, GetBlockName, GetCarriedItem, GetEngineTypeStr, IsLiving
from .Helpers.Fx import ToAllPlayerPlaySound
from .Helpers.Player import SetPlayerUsedCD, IsCreative
from ..Shared.Data import Blocks
from ..Shared.Data.Blocks import canClimbList
from ..Shared.Rules import NetBounce, RopeReel
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
    abilities = compFactory.CreatePlayer(playerId).GetPlayerAbilities()
    if not (abilities and abilities.get("build")):
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
