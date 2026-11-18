# -*- coding: utf-8 -*-
"""TatamiPairs - 榻榻米方块两两配对（服务端）

规则在 Shared/Rules/TatamiPair.py（JE TatamiBlock）；样子全靠方块态 + permutations（bp/netease_blocks/arris_tatami.json，
tools/gen_tatami.py 生成），客户端没有代码。这里只写两个方块态：
- 放下（EntityPlaceBlockAfterServerEvent，face 是点的那一面）：按点的面定朝向；玩家没潜行、点的是没配对的榻榻米时两块配成一对。
- 邻格变了（BlockNeighborChangedServerEvent，方块 JSON 带 netease:neighborchanged_sendto_script）：配对的块看 FACING 那一格，
  不再是榻榻米就拆开（JE updateShape）。变的正是那一格时用事件给的新方块名；别的邻格变了也读一下那一格
  （活塞推走 / 推来的、/setblock 摆出来的不成对的状态，下一次邻格变化时就理顺）。
SetBlockStates 不触发邻居事件，写回不会引出回声。/setblock、/fill、结构放下的不发放置事件，是缺省状态：朝下、没配对（JE 的缺省）。
"""
from .EventRegistry import registerHandler
from .Helpers.Engine import compFactory, levelId, GetEngineTypeStr
from ..Shared.Rules import TatamiPair

_PLAYER = "minecraft:player"


def _nameAt(pos, dimensionId):
    info = compFactory.CreateBlockInfo(levelId).GetBlockNew(pos, dimensionId)
    return info["name"] if info else None


def _statesAt(pos, dimensionId):
    return compFactory.CreateBlockState(levelId).GetBlockStates(pos, dimensionId) or {}


def _setStates(pos, changes, dimensionId):
    states = dict(_statesAt(pos, dimensionId))
    states.update(changes)
    compFactory.CreateBlockState(levelId).SetBlockStates(pos, states, dimensionId)


@registerHandler("EntityPlaceBlockAfterServerEvent", match=TatamiPair.TATAMI)
def OnTatamiPlaced(args):
    face = args["face"]
    if face not in range(6):
        return
    pos = (args["x"], args["y"], args["z"])
    dimensionId = args["dimensionId"]
    entityId = args["entityId"]
    byPlayer = GetEngineTypeStr(entityId) == _PLAYER
    sneaking = byPlayer and compFactory.CreatePlayer(entityId).isSneaking() is True
    clicked = TatamiPair.step(pos, TatamiPair.opposite(face))
    clickedName = _nameAt(clicked, dimensionId)
    clickedStates = _statesAt(clicked, dimensionId) if clickedName == TatamiPair.TATAMI else {}
    mine, partner = TatamiPair.placement(face, byPlayer, sneaking, clickedName, clickedStates)
    _setStates(pos, mine, dimensionId)
    if partner is not None:
        _setStates(clicked, partner, dimensionId)


@registerHandler("BlockNeighborChangedServerEvent", match=TatamiPair.TATAMI)
def OnTatamiNeighborChanged(args):
    pos = (args["posX"], args["posY"], args["posZ"])
    dimensionId = args["dimensionId"]
    states = _statesAt(pos, dimensionId)
    if not TatamiPair.isPaired(states):
        return
    partner = TatamiPair.step(pos, TatamiPair.facingOf(states))
    neighbor = (args["neighborPosX"], args["neighborPosY"], args["neighborPosZ"])
    partnerName = args["toBlockName"] if neighbor == partner else _nameAt(partner, dimensionId)
    if not TatamiPair.keepsPairWith(partnerName) and _nameAt(pos, dimensionId) == TatamiPair.TATAMI:
        _setStates(pos, {TatamiPair.PAIRED: 0}, dimensionId)
