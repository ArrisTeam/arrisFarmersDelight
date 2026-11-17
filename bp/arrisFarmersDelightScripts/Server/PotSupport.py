# -*- coding: utf-8 -*-
"""PotSupport - 厨锅的支架：挂在天花板下面放下就是吊把手，潜行空手右键在吊把手和托盘 / 没有之间切（服务端）

照 FD 的 CookingPotBlock（规则和 JE 的行号在 Shared/Rules/PotSupport.py）：
- 放下时：点的是方块的下面（Facing.Down）就挂着吊把手。引擎放方块时事件里才看得到点的是哪一面（ServerEntityTryPlaceBlockEvent 的 face），
  这时记一笔，方块实体建好时（attach）取走；记录按位置、5 秒过期；
- 潜行空手右键（CookingPotHost.use 调 toggle）：吊把手 <-> 按正下方算的托盘 / 没有，响一声挂灯；不开界面、不盛菜。
状态存在方块实体数据的 handleEnable（1.0 / 0.0）；托盘 shelfEnable 由 Helpers/Heat.RefreshHeat 按它和正下方算，两个旗都同步给各客户端的方块实体模型
（variable.mod_handle / mod_shelf）和世界外观广播（Server/PotLook 的 support）。/setblock、结构放出的锅没有放置事件，handleEnable 缺键就是没有吊把手。
"""
import time

from .EventRegistry import registerHandler
from .Helpers.Engine import ItemPosType, GetBlockEntityData, GetBlockName, GetCarriedItem, compFactory
from .Helpers.Fx import ToAllPlayerPlaySound
from .Helpers.Heat import RefreshHeat
from .Helpers.Player import SetPlayerUsedCD
from ..Shared.Rules import PotItem, PotSupport

_hanging = PotItem.Pending()           # (维度, x, y, z) -> 刚才放这口锅时点的是不是方块的下面


@registerHandler("ServerEntityTryPlaceBlockEvent", match=PotItem.POT)
def OnTryPlacePotAgainst(args):
    # 每次放置都记（放置被取消、下一次换了面再放同一格时，要用最后一次的）；方块实体建好时 attach 取走，没人取的几秒后自己作废
    _hanging.put((args["dimensionId"], args["x"], args["y"], args["z"]), PotSupport.hangs(args["face"]), time.time())


def attach(blockEntityData, dimensionId, blockPos):
    """方块实体建好了（刚放下的锅）：点的是方块的下面就挂着吊把手。没有记录的（别的方式放的、活塞推来的）原来有旗就留着，没有就是没有吊把手。"""
    hangs = _hanging.take((dimensionId,) + tuple(blockPos), time.time())
    if hangs is not None or blockEntityData["handleEnable"] is None:
        blockEntityData["handleEnable"] = 1.0 if hangs else 0.0


def sneaking(playerId):
    return bool(compFactory.CreatePlayer(playerId).isSneaking())


def _empty(item):
    return not item or item.get("newItemName") in (None, "", "minecraft:air")


def toggle(playerId, dimensionId, blockPos):
    """潜行右键：吊把手 <-> 按正下方算的托盘 / 没有，响一声挂灯（FD 的 CookingPotBlock.use 第一支，创造模式也一样）。
    返回这一下是不是归它：切了，或按住右键时冷却内不重复切，都是 True。
    原版潜行时任何一只手拿着东西，方块的 use 根本不调（ServerPlayerGameMode.useItemOn），所以主手副手都得空着：不然返回 False，
    调用方放过这一下（手里的东西照常用）。"""
    data = GetBlockEntityData(dimensionId, blockPos)
    offhand = compFactory.CreateItem(playerId).GetPlayerItem(ItemPosType.OFFHAND, 0, True)
    if not data or not _empty(GetCarriedItem(playerId)) or not _empty(offhand):
        return False
    if SetPlayerUsedCD(playerId):
        return True
    data["handleEnable"] = 0.0 if data["handleEnable"] == 1.0 else 1.0
    belowPos = (blockPos[0], blockPos[1] - 1, blockPos[2])
    RefreshHeat(data, blockPos, belowPos, dimensionId, GetBlockName(belowPos, dimensionId))
    ToAllPlayerPlaySound(dimensionId, (blockPos[0] + 0.5, blockPos[1] + 0.5, blockPos[2] + 0.5), *PotSupport.TOGGLE_SOUND)
    return True
