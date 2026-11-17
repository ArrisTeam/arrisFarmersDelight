# -*- coding: utf-8 -*-
"""GrillOpen - 炉灶站点开不开的服务端复查：站点登记时的 canOpen（服务端）

JE 的 StationManager 在服务端又测一遍站点的 openCondition（HoD 的 StoveStation.opens）；客户端那一遍是 GrillView.opensStation，
只是预判，改过的客户端可以不管它直接发开站请求。两边各读各的引擎、规则同一份：Shared/Rules/GrillStation.opens——
上面盖着锅 / 煎锅、手里拿着炉灶自己用得上的东西（打火石、铲子、桶、方块……）时服务端不让开。
厨锅的这一遍不在这里：它在 PotLogic.onOpen（PotServe.serveByHand，拒绝的同时盛一份菜，不是纯判断）。砧板、煎锅只看潜行，客户端挡。
站点朝哪也在这里（facingOf，站点登记时的 facing）：炉灶是 JE 的 Orientation.BLOCK，站点的北面永远是炉灶方块的正面，发给客户端的 Opened 里的 yaw 就是它。
"""
from ...Server.Helpers.Engine import GetBlockAux, GetBlockName, GetCarriedItem
from ...Server.Helpers.Items import GetItemType
from ...Shared.Rules import GrillStation as Rules
from ...Shared.Rules import StoveCover, StoveFacing


def facingOf(dimensionId, pos):
    """facing(dimensionId, pos)：这座炉灶的站点朝哪（度，北 0 / 东 90 / 南 180 / 西 270）：站点的北面是炉灶方块的正面，
    从哪一侧右键都一样（JE 的 StoveStation 是 Orientation.BLOCK）。读的是服务端的引擎，规则（StoveFacing.yawOfAux）和客户端的 GrillView.facingOf 同一份。"""
    return StoveFacing.yawOfAux(GetBlockAux(pos, dimensionId))


def isCovered(dimensionId, pos):
    """炉灶上面盖着东西（锅、煎锅、别的方块；空气和液体不算，Shared/Rules/StoveCover）：烤架是它们的，什么也不收、也不开站点。"""
    return StoveCover.covers(GetBlockName((pos[0], pos[1] + 1, pos[2]), dimensionId))


def opensStation(playerId, dimensionId, pos):
    """canOpen(playerId, dimensionId, pos)：主手拿着什么（引擎不认识的物品没有类型）、上面盖没盖东西，交给 GrillStation.opens。"""
    held = GetCarriedItem(playerId) or {}
    name = held.get("newItemName")
    return Rules.opens(name, (GetItemType(held) or "") if name else "", isCovered(dimensionId, pos))
