# -*- coding: utf-8 -*-
"""Input - 跳跃键（爬绳往上）、指南书物品、对着方块拿原版南瓜派不吃（客户端）"""
from ..QuModLibs.Client import Listen, Call
from .Engine import clientApi, compFactory, levelId, playerId
from ..Shared.Data import Food
from ..Shared.Rules.Placement import eatsPumpkinPie

GUIDE_BOOK_ITEM = "arris:farmer_delight_guide_book"


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
