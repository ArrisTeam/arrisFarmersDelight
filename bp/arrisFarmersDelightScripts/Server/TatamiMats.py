# -*- coding: utf-8 -*-
"""TatamiMats - 长榻榻米垫（两格）一起放、一起拆；长短两种垫子脚下没了方块就碎（服务端）

照 JE 的 TatamiMatBlock / TatamiHalfMatBlock（规则在 Shared/Rules/TatamiMat.py）：
- 放置：手里的长垫子对方块使用时，脚放在点到的格子、头放在面朝方向的下一格，两格下面都要有方块，放不下就什么都不做。
  引擎自己只会放一格，所以它的放置被取消，两格由这里一起放（同时扣一个物品、放一声布料的响）；
  点到的是自己会处理右键的方块（砧板、厨锅、煎锅、炉灶、橱柜、篮子、展示框）时让它们处理，潜行才放（JE：方块的 use 优先）；
- 拆除：拆哪一半，另一半都静默跟着没。掉落由被拆的那一半的战利品表给，两半都指向同一个物品，所以只掉一个，创造模式一个也不掉；
- 脚下的方块没了：这一半碎掉并掉落（长垫子的另一半静默跟着没，不会掉两个）；短垫子照 JE 的 canSurvive 也一样。
"""
from .EventRegistry import registerHandler
from .Helpers.Engine import compFactory, levelId
from .Helpers.Fx import ToAllPlayerPlaySound
from .Helpers.Player import SetPlayerUsedCD, SetNotCreateItem
from ..Shared.Rules import TatamiMat

# 游戏模式：冒险和旁观不能放方块
_CANNOT_BUILD = (2, 3)


def _itemName(args):
    return args["itemDict"]["newItemName"]


def _nameAt(pos, dimensionId):
    info = compFactory.CreateBlockInfo(levelId).GetBlockNew(pos, dimensionId)
    return info["name"] if info else None


def _directionAt(pos, dimensionId):
    states = compFactory.CreateBlockState(levelId).GetBlockStates(pos, dimensionId)
    return states["direction"] if states and "direction" in states else None


def _setBlock(pos, name, dimensionId, direction=None):
    compFactory.CreateBlockInfo(levelId).SetBlockNew(pos, {"name": name}, 0, dimensionId)
    if direction is not None:
        states = compFactory.CreateBlockState(levelId).GetBlockStates(pos, dimensionId) or {}
        states["direction"] = direction
        compFactory.CreateBlockState(levelId).SetBlockStates(pos, states, dimensionId)


def _removeSilently(pos, dimensionId):
    # 不掉落、不通知邻居（另一半不会因此再来一次邻居变化）
    compFactory.CreateBlockInfo(levelId).SetBlockNew(pos, {"name": TatamiMat.AIR}, 0, dimensionId, False, False)


def _breakWithDrops(pos, dimensionId):
    compFactory.CreateBlockInfo(levelId).SetBlockNew(pos, {"name": TatamiMat.AIR}, 1, dimensionId)


# 优先级 98：和 ItemToBlock 同一档（物品放成方块），见 Server/ModServer.py 的优先级表
@registerHandler("ServerItemUseOnEvent", match=TatamiMat.PAIR, keyOf=_itemName, priority=98)
def OnPlaceFullMat(args):
    # 手里是长垫子（创造模式中键取到的头方块物品也当长垫子用）
    args["ret"] = True                         # 不管放不放得下，引擎自己那一格都不要
    playerId = args["entityId"]
    if TatamiMat.usesTheClick(args["blockName"]) and compFactory.CreatePlayer(playerId).isSneaking() is not True:
        return True                            # 点到的方块自己会处理右键：让它处理，不抢交互冷却（潜行才放垫子）
    if SetPlayerUsedCD(playerId) is True:
        return True
    if compFactory.CreateGame(levelId).GetPlayerGameType(playerId) in _CANNOT_BUILD:
        return True
    rot = compFactory.CreateRot(playerId).GetRot()
    if not rot:
        return True
    dimensionId = args["dimensionId"]
    plan = TatamiMat.placementPlan((args["x"], args["y"], args["z"]), args["face"], args["blockName"], rot[1],
                                   lambda pos: _nameAt(pos, dimensionId))
    if plan is None:
        return True
    foot, head, direction = plan
    _setBlock(foot, TatamiMat.FOOT, dimensionId, direction)       # 脚先放好朝向，头放上去时脚才读得到它
    _setBlock(head, TatamiMat.HEAD, dimensionId, direction)
    ToAllPlayerPlaySound(dimensionId, (foot[0] + 0.5, foot[1] + 0.5, foot[2] + 0.5), "dig.cloth")
    SetNotCreateItem(playerId, args["itemDict"])
    return True


@registerHandler("ServerItemUseOnEvent", match=TatamiMat.HALF, keyOf=_itemName, priority=98)
def OnPlaceHalfMat(args):
    # 短垫子照常由引擎放，只是下面是空气时不许放（JE 的 canSurvive）
    dimensionId = args["dimensionId"]
    if not TatamiMat.halfMatPlaceable((args["x"], args["y"], args["z"]), args["face"], args["blockName"],
                                      lambda pos: _nameAt(pos, dimensionId)):
        args["ret"] = True


def _breakWithPartner(name, pos, dimensionId):
    # 脚下没了方块：另一半静默跟着没，这一半碎掉掉落（一个）
    if name in TatamiMat.PAIR:
        direction = _directionAt(pos, dimensionId)
        if direction is not None:
            partner = TatamiMat.partnerPos(name, pos, direction)
            if _nameAt(partner, dimensionId) == TatamiMat.partnerName(name):
                _removeSilently(partner, dimensionId)
    _breakWithDrops(pos, dimensionId)


@registerHandler("BlockNeighborChangedServerEvent", match=TatamiMat.SUPPORTED)
def OnMatNeighborChanged(args):
    name = args["blockName"]
    pos = (args["posX"], args["posY"], args["posZ"])
    dimensionId = args["dimensionId"]
    neighbor = (args["neighborPosX"], args["neighborPosY"], args["neighborPosZ"])
    toName = args["toBlockName"]
    if TatamiMat.supportLost(pos, neighbor, toName):
        if _nameAt(pos, dimensionId) == name:                 # 事件到的时候这一格可能已经被别的处理清掉了
            _breakWithPartner(name, pos, dimensionId)
    elif name in TatamiMat.PAIR and TatamiMat.isSideNeighbor(pos, neighbor):
        direction = _directionAt(pos, dimensionId)
        if direction is not None and TatamiMat.partnerLost(name, pos, direction, neighbor, toName):
            if _nameAt(pos, dimensionId) == name:
                _removeSilently(pos, dimensionId)
