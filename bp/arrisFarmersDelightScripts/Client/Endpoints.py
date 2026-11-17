# -*- coding: utf-8 -*-
"""Endpoints - 服务端调用的客户端端点：音效、碎屑、粒子、方块实体 molang、挥手（客户端）

服务端用 Call("*", ...) 广播给全部客户端，这里按维度过滤（见 Server/Helpers/Fx.py）。
端点名就是函数名，服务端按名字调用，改名要两边一起改。
"""
from ..QuModLibs.Client import AllowCall
from .Engine import compFactory, levelId, playerId
from ..Shared.Data.FoodColors import FoodColors
from ..Shared.Rules import BoardDust


def _elsewhere(args):
    # 服务端广播给所有玩家，这里按维度本地过滤，跨维度的直接丢弃
    dimensionId = args.get("dimensionId")
    return dimensionId is not None and dimensionId != compFactory.CreateGame(levelId).GetCurrentDimension()


@AllowCall
def OnPlaySound(args):
    if _elsewhere(args):
        return
    compFactory.CreateCustomAudio(levelId).PlayCustomMusic(args["soundName"], args["pos"], args.get("volume", 1), args.get("pitch", 1), False, None)


@AllowCall
def PlayCrumbs(args):
    # 砧板切了一件：FD 的 spawnCuttingParticles（方块中心上方 5 颗这件东西的碎屑）。基岩版没有按物品贴图碎开的粒子，用站点也用的 arris:board_dust，按这件东西的颜色染
    if _elsewhere(args):
        return
    system = compFactory.CreateParticleSystem(None)
    at = tuple(float(corner + shift) for corner, shift in zip(args["blockPos"], BoardDust.CRUMB_AT))
    particleId = system.Create(BoardDust.CRUMB_PARTICLE, at)
    if not particleId:                    # 进世界头几秒粒子系统还没好：引擎回 0（不是 None），不能当编号去设变量
        return
    color = FoodColors.get(args["itemName"], BoardDust.CRUMB_COLOR)
    for name, shift in (("variable.tint_r", 16), ("variable.tint_g", 8), ("variable.tint_b", 0)):
        system.SetVariable(particleId, name, ((color >> shift) & 0xFF) / 255.0)
    system.SetVariable(particleId, "variable.tint_set", 1.0)
    for name, value in (("variable.count", BoardDust.CRUMB_COUNT), ("variable.vx", 0.0), ("variable.vy", BoardDust.CRUMB_SPEED), ("variable.vz", 0.0),
                        ("variable.spread", BoardDust.CRUMB_SPREAD)):
        system.SetVariable(particleId, name, float(value))


@AllowCall
def PlayParticle(pos):
    compFactory.CreateParticleSystem(None).Create("minecraft:crop_growth_emitter", pos)


@AllowCall
def SetEntityBlockMolang(args):
    blockInfo = compFactory.CreateBlockInfo(levelId)
    blockInfo.SetEnableBlockEntityAnimations(args["blockPos"], True)
    blockInfo.SetBlockEntityMolangValue(args["blockPos"], args["name"], args["molang"])


@AllowCall
def PlayAttackAnimationCommon(args):
    compFactory.CreatePlayer(playerId).Swing()
