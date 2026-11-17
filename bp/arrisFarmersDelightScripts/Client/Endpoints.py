# -*- coding: utf-8 -*-
"""Endpoints - 服务端调用的客户端端点：音效、粒子、方块实体 molang、挥手（客户端）

服务端用 Call("*", ...) 广播给全部客户端，这里按维度过滤（见 Server/Helpers/Fx.py）。
端点名就是函数名，服务端按名字调用，改名要两边一起改。
"""
from ..QuModLibs.Client import AllowCall
from .Engine import compFactory, levelId, playerId


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
