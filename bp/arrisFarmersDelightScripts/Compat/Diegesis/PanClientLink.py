# -*- coding: utf-8 -*-
"""PanClientLink - 联动步骤 pan（客户端）：登记煎锅站点的表现，登记上了就让煎锅按 HoD 的样子画

配置里关了煎锅站点（skillet）时 PanView.register 返回 None（和服务端的 PanLogic.register 同一个条件），这一步记成 skipped。
"""
from . import PanScenes, PanView


def link(ctx):
    if PanView.register(ctx.api) is None:
        return False
    PanScenes.enable()           # 煎锅从此按 HoD 的样子画：食物落进来、颠锅翻面、油星热气（谁都看得见）
    return True
