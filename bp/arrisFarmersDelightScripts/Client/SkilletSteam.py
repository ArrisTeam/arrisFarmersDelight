# -*- coding: utf-8 -*-
"""SkilletSteam - 放下的煎锅自己的嗞嗞声、蒸汽、火焰附加的星星：加热着而且锅里有东西才有（客户端）

JE 的 SkilletBlock.animateTick 和 SkilletBlockEntity.animationTick（概率、位置、出处在 Shared/Rules/SkilletSteam.py）：
- 嗞嗞声：煎锅的方块 JSON 写了 netease:block_animate_random_tick（trigger_rate 1：动画刻每次轮到这座锅引擎都发一次 BlockAnimateRandomTickEvent，JE 的 animateTick 也是
  每次轮到都放，只有声音是 1/10），收到就 1/10 的概率响一声。方块级的组件，旧存档里的煎锅也有；
- 蒸汽、附魔星：方块 JSON 的 netease:block_entity 开了 client_tick（ModBlockEntityTickClientEvent，每秒 20 次，对上 JE 客户端方块实体每刻一次的 animationTick）。
  client_tick 是方块实体的标志，存档里的方块实体会盖过方块 JSON（和炉灶的火同一个情况，Client/StoveFlame.py）：这一版之前放下的煎锅要重新放才有蒸汽。
"加热着"读方块实体模型的 mod_heat（服务端推的，BlockEntityRestore 在加载时也补），"锅里有东西"读 BlockItems 记着的最后一份内容，火焰附加读方块实体数据里记着的那件煎锅；
场景接管了（mod_scene 为 1，装了前置包又开着煎锅站点）就不放：声音和烟是场景画的（Compat/Diegesis/PanFx）。
这个模块取代原来实体定义里"只要在热源上就每 15 秒响一声"的嗞嗞动画（空锅也响、没有蒸汽）。
"""
import random

from ..QuModLibs.Client import Listen
from . import BlockItems
from .Engine import blockEntityExData, compFactory, levelId, playerId, unwrapDeep
from ..Shared.Rules import SkilletRules, SoundMix
from ..Shared.Rules import SkilletSteam as Steam

REREAD_TICKS = 20          # 火焰附加的等级隔这么多刻读一次方块实体数据（放下去之后才记进去，之后不变；每刻读太重）
_levels = {}               # (维度, 坐标) -> [火焰附加的等级, 还有几刻重读]


def _cooking(dimensionId, pos):
    blockInfo = compFactory.CreateBlockInfo(levelId)
    if (blockInfo.GetBlockEntityMolangValue(pos, "variable.mod_scene") or 0.0) >= Steam.SCENE_ON:
        return False
    return Steam.cooking(blockInfo.GetBlockEntityMolangValue(pos, "variable.mod_heat") == 1.0, BlockItems.itemsAt(dimensionId, pos))


def _fireAspect(dimensionId, pos):
    key = (dimensionId, pos)
    entry = _levels.get(key)
    if entry is None or entry[1] <= 0:
        stored = unwrapDeep(blockEntityExData(pos).get(Steam.STORED_KEY))
        entry = _levels[key] = [SkilletRules.fireAspectLevel(stored) if isinstance(stored, dict) else 0, REREAD_TICKS]
    entry[1] -= 1
    return entry[0]


def _emit(identifier, spot):
    compFactory.CreateParticleSystem(None).Create(identifier, spot)


@Listen("BlockAnimateRandomTickEvent")
def OnSkilletAnimateTick(args):
    # 这个事件对所有带该组件的自定义方块都来（炉灶、闪亮沙拉也在听），别的方块不归这里
    if args["blockName"] != Steam.BLOCK:
        return
    pos = tuple(args["blockPos"])
    if not _cooking(compFactory.CreateGame(levelId).GetCurrentDimension(), pos) or random.random() >= Steam.SIZZLE_CHANCE:
        return
    volume, pitch = SoundMix.engineArgs(Steam.SIZZLE, Steam.SIZZLE_VOLUME, Steam.sizzlePitch(random.random()))
    compFactory.CreateCustomAudio(levelId).PlayCustomMusic(Steam.SIZZLE, Steam.sizzleSpot(pos), volume, pitch, False, None)


@Listen("ModBlockEntityTickClientEvent")
def OnSkilletClientTick(args):
    if args["blockName"] != Steam.BLOCK:
        return
    pos = (args["posX"], args["posY"], args["posZ"])
    if not _cooking(args["dimensionId"], pos):
        return
    viewer = compFactory.CreatePos(playerId).GetFootPos()
    if not viewer:
        return
    if random.random() < Steam.STEAM_CHANCE:
        _putAt(Steam.STEAM, pos, viewer)
    level = _fireAspect(args["dimensionId"], pos)
    if level > 0 and random.random() < Steam.sparkChance(level):
        _putAt(Steam.SPARK, pos, viewer)


def _putAt(identifier, pos, viewer):
    spot = Steam.surfaceSpot(pos, random.random(), random.random())
    if Steam.inRange(viewer, spot):
        _emit(identifier, spot)


@Listen("ModBlockEntityRemoveClientEvent")
def OnSkilletRemoved(args):
    _levels.pop((args["dimensionId"], (args["posX"], args["posY"], args["posZ"])), None)
