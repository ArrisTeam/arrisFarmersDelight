# -*- coding: utf-8 -*-
"""StoveFlame - 点着的炉灶自己的火：火口的火星和烟、噼啪声、没有站点时灶上每件东西冒的烟（客户端）

JE 的 StoveBlock.animateTick 和 StoveBlockEntity.particleTick（概率、位置的算式和出处在 Shared/Rules/StoveFlame.py）：
- 火口：点着的 arris:stove 的方块 JSON 写了 netease:block_animate_random_tick（trigger_rate 1：动画刻每次轮到这座炉灶引擎都发一次 BlockAnimateRandomTickEvent，
  JE 的 animateTick 也是每次轮到都放，只有噼啪声是 1/10），收到就在正面放一颗烟一颗火，1/10 的概率响一声营火噼啪。方块级的组件，旧存档里的炉灶也有；
- 灶上每件东西的烟：方块 JSON 的 netease:block_entity 开了 client_tick（ModBlockEntityTickClientEvent，每秒 20 次，对上 JE 客户端方块实体每刻一次的 particleTick），
  灶上哪几格有东西读 BlockItems 记着的最后一份内容（经典的展示就是靠它画的）。HoD 的炉灶站点显示时取消这一个方法（StoveSmokeMixin：它自己的蒸汽和烟说烤得怎样，
  FD 的黑烟看着像弄脏了食物），所以前置包的炉灶站点登记了（Compat/Diegesis/ClientBoot 调 muteItemSmoke）就不放；没装前置包、或者 HoD 配置里关了炉灶站点才有。
  client_tick 是方块实体的标志，存档里的方块实体会盖过方块 JSON（ModBlockActor::load 先照组件建、再拿存的 _tickClient 盖）：这一版之前放下的炉灶要重新放（或点火 / 灭火换一次方块）才有这圈烟。
粒子是 rp/particles 里自带的两个自动发射的（arris:stove_flame / arris:stove_smoke）：原版的 basic_flame_particle / basic_smoke_particle 用 emitter_rate_manual，
Create 之后不调 EmitManually 一颗也不出，调了又要自己管发射器的寿命（世界里的发射器不会自己消失）。
"""
import random

from ..QuModLibs.Client import Listen
from . import BlockItems
from .Engine import compFactory, levelId, playerId
from ..Shared.Rules import StoveFlame as Flame

_state = {"muted": False}


def muteItemSmoke():
    """炉灶站点在场：灶上每件东西的烟交给站点（HoD 的 StoveSmokeMixin 取消的就是这一个方法），火口的火星和噼啪声照旧。"""
    _state["muted"] = True


def muted():
    return _state["muted"]


def _emit(identifier, spot, count=1):
    particles = compFactory.CreateParticleSystem(None)
    for _ in range(count):
        particles.Create(identifier, spot)


@Listen("BlockAnimateRandomTickEvent")
def OnStoveAnimateTick(args):
    # 这个事件对所有带该组件的自定义方块都来（闪亮沙拉也在听），别的方块不归这里
    if args["blockName"] != Flame.BLOCK:
        return
    pos = args["blockPos"]
    if random.random() < Flame.CRACKLE_CHANCE:
        compFactory.CreateCustomAudio(levelId).PlayCustomMusic(Flame.CRACKLE, Flame.crackleSpot(pos), 1.0, 1.0, False, None)
    spot = Flame.flameSpot(pos, args["auxData"], random.random(), random.random())
    _emit(Flame.SMOKE, spot)
    _emit(Flame.FLAME, spot)


@Listen("ModBlockEntityTickClientEvent")
def OnStoveClientTick(args):
    if _state["muted"] or args["blockName"] != Flame.BLOCK:
        return
    pos = (args["posX"], args["posY"], args["posZ"])
    slots = [index for index in Flame.occupiedSlots(BlockItems.itemsAt(args["dimensionId"], pos)) if random.random() < Flame.ITEM_SMOKE_CHANCE]
    if not slots:
        return
    viewer = compFactory.CreatePos(playerId).GetFootPos()
    block = compFactory.CreateBlockInfo(levelId).GetBlock(pos)
    if not viewer or not block:
        return
    for index in slots:
        spot = Flame.itemSmokeSpot(pos, block[1], index)
        if Flame.inRange(viewer, spot):
            _emit(Flame.SMOKE, spot, Flame.ITEM_SMOKE_PUFFS)
