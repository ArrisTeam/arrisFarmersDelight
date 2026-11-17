# -*- coding: utf-8 -*-
"""PotClientLink - 联动步骤 pot（客户端）：登记厨锅站点的表现，登记上了就让厨锅按 HoD 的样子画

配置里关了厨锅站点（cooking_pot）时 PotView.register 返回 None（和服务端的 PotLogic.register 同一个条件），这一步记成 skipped。
"""
from . import PotScenes, PotView
from ...Shared.Data.BrothColors import BrothColors


def link(ctx):
    if PotView.register(ctx.api) is None:
        return False
    PotScenes.enable(BrothColors.get)        # 厨锅从此按 HoD 的样子画：开盖、汤面、漂着的料（谁都看得见）
    return True
