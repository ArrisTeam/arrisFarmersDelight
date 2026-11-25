# -*- coding: utf-8 -*-
"""Input - 跳跃键（爬绳往上）、指南书物品、对着方块拿原版南瓜派不吃、手里有煎锅时右键的按住 / 松开（客户端）"""
import time

from ..QuModLibs.Client import Listen, Call
from .Engine import clientApi, compFactory, levelId, playerId
from ..Shared.Data import Food
from ..Shared.Rules import Grilling, HeatSources
from ..Shared.Rules.Placement import eatsPumpkinPie
from ..Shared.Rules.SkilletHandRules import HoldReporter, cooksInsteadOfEating, skilletHand
from ..Shared.Rules.SkilletRules import SKILLET_ITEM, nearHeat

GUIDE_BOOK_ITEM = "arris:farmer_delight_guide_book"
# 手持煎锅烹饪要知道右键有没有按住，服务端没有"按住"的事件：主手或副手拿着煎锅时由这里报告（规则见 SkilletHandRules.HoldReporter）
_skilletHold = HoldReporter()


@Listen("ClientJumpButtonPressDownEvent")
def ClientJumpButtonPressDown(args):
    # playerId 由服务端通过 @InjectHttpPlayerId 注入，客户端不传
    Call("SetPlayerIsJumpExtra", {"isJump": True})


@Listen("ClientJumpButtonReleaseEvent")
def ClientJumpButtonRelease(args):
    Call("SetPlayerIsJumpExtra", {"isJump": False})


@Listen("ClientItemTryUseEvent")
def OnClientItemTryUse(args):
    itemName = args["itemDict"]["newItemName"]
    if itemName == GUIDE_BOOK_ITEM:
        compFactory.CreateCustomAudio(levelId).PlayCustomMusic("item.book.page_turn", (1, 1, 1), 1, 1, False, playerId)
        clientApi.PushScreen("arris", "farmerDelightGuideBook")
    elif itemName == Food.PUMPKIN_PIE:
        # JE 的 PlacePumpkinPieMixin：对着方块用南瓜派，放得下放不下都不会开始吃（放方块在服务端 Server/ItemToBlock.py）。
        # 服务端取消 ServerItemUseOnEvent 拦不住"吃"（实测按住右键会放一个再吃一个），要在这里取消"使用物品"。
        aimsAtBlock = (compFactory.CreateCamera(levelId).PickFacing() or {}).get("type") == "Block"
        sneaking = compFactory.CreatePlayer(playerId).isSneaking()
        if not eatsPumpkinPie(aimsAtBlock, sneaking, Food.PUMPKIN_PIE_SNEAK_TO_PLACE):
            args["cancel"] = True
    elif cooksInsteadOfEating(itemName, _offhandName(), SKILLET_ITEM, Grilling.canCook(itemName, args["itemDict"].get("newAuxValue") or 0),
                              _nearHeat()):
        # 副手煎锅、主手原料（营火配方：表，或引擎的配方，和服务端同一个 Grilling）、身边有热源：这一下是手持煎（Server/SkilletHand.py），不是吃
        args["cancel"] = True


def _offhandName():
    item = compFactory.CreateItem(playerId).GetOffhandItem()
    return item.get("newItemName") if item else None


def _nearHeat():
    """身边 3x3x3 里有没有热源方块（和服务端同一条规则 HeatSources.nearHeat：名单或两个热源标签，不看点没点着——客户端本来也读不到方块状态；
    客户端读不到"着火"，那种情况只由服务端认）。"""
    footPos = compFactory.CreatePos(playerId).GetFootPos()
    if not footPos:
        return False
    blockInfo = compFactory.CreateBlockInfo(levelId)
    return nearHeat(footPos, lambda pos: (blockInfo.GetBlock(pos) or (None,))[0], HeatSources.NEAR)


def _carryingSkillet():
    item = compFactory.CreateItem(playerId).GetCarriedItem()
    return skilletHand(item.get("newItemName") if item else None, _offhandName(), SKILLET_ITEM) is not None


def _reportSkilletHold(held):
    if held is not None:
        Call("SkilletUseHeld", {"held": held})


@Listen("RightClickBeforeClientEvent")
def OnRightClickDown(args=None):
    _reportSkilletHold(_skilletHold.press(time.time(), _carryingSkillet()))


@Listen("RightClickReleaseClientEvent")
def OnRightClickUp(args=None):
    _reportSkilletHold(_skilletHold.release())


@Listen("LeftClickBeforeClientEvent")
def OnLeftClickDown(args=None):
    # JE 的 KeybindEvents：用着煎锅（按住右键煎）时点攻击键就是翻面，由服务端核对是不是真在煎、在不在翻（Server/SkilletHold.SkilletFlip）
    if _skilletHold.down and _carryingSkillet():
        Call("SkilletFlip", {})


@Listen("OnScriptTickClient")
def OnSkilletHoldTick(args=None):
    # 每帧一次，引擎不带参数
    _reportSkilletHold(_skilletHold.tick(time.time(), _carryingSkillet))
