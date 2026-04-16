# -*- coding: utf-8 -*-
from ...Client import clientApi, levelId
from Util import SharedBox

lambda: "By Zero123"

_OPERATION = clientApi.GetEngineCompFactory().CreateOperation(levelId)
""" operation组件 """

class PlayerSharedAPI:
    """ 玩家共享API 基于引用计数管理 """
    canNotMove = SharedBox(
        lambda: _OPERATION.SetCanMove(False),
        lambda: _OPERATION.SetCanMove(True)
    )
    """ 禁止玩家移动 """