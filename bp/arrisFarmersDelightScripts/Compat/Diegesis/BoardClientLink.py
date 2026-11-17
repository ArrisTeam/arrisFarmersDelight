# -*- coding: utf-8 -*-
"""BoardClientLink - 联动步骤 board（客户端）：登记切菜板站点的表现，登记上了就开旁观的声音

配置里关了砧板站点（cutting_board）时 BoardView.register 返回 None（和服务端的 BoardLogic.register 同一个条件），这一步记成 skipped。
"""
from . import BoardView, BoardWatch


def link(ctx):
    if BoardView.register(ctx.api) is None:
        return False
    BoardWatch.enable(ctx.api.Geometry)      # 旁边别人用的砧板，也听得到切菜声、看得到碎屑（服务端的 BoardLook 发过来）
    return True
