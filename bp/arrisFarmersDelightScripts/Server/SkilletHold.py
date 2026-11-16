# -*- coding: utf-8 -*-
"""SkilletHold - 客户端报告"右键按住"的服务端端点：手持煎锅烹饪要知道玩家有没有按住（服务端）

基岩版没有"按住使用"的服务端事件，Client/Input.py 在主手或副手拿着煎锅时报告右键：按下一次、按住期间约每 0.2 秒一次、松开一次。
这里只收下玩家 ID（服务端注入，不信客户端传的）和一个布尔值；主手、副手、热源、水这些条件全由 SkilletHand 重新核对。
"""
from ..QuModLibs.Server import AllowCall, InjectHttpPlayerId
from . import SkilletHand


@AllowCall
@InjectHttpPlayerId
def SkilletUseHeld(playerId, data):
    if not playerId or not isinstance(data, dict):
        return
    held = data.get("held")
    if held is True:
        SkilletHand.onHeld(playerId)
    elif held is False:
        SkilletHand.onRelease(playerId)
