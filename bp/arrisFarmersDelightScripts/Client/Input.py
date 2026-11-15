# -*- coding: utf-8 -*-
"""Input - 跳跃键（爬绳往上）与指南书物品（客户端）"""
from ..QuModLibs.Client import Listen, Call
from .Engine import clientApi, compFactory, levelId, playerId

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
    if args["itemDict"]["newItemName"] == GUIDE_BOOK_ITEM:
        compFactory.CreateCustomAudio(levelId).PlayCustomMusic("item.book.page_turn", (1, 1, 1), 1, 1, False, playerId)
        clientApi.PushScreen("arris", "farmerDelightGuideBook")
