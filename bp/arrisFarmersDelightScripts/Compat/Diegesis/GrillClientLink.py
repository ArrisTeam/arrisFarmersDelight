# -*- coding: utf-8 -*-
"""GrillClientLink - 联动步骤 grill（客户端）：登记炉灶站点的表现，登记上了就让炉灶按 HoD 的样子画、让出灶上东西的烟

步骤表给这一步的条件是前置包接口的朝向钩子（FACING_HOOK，和服务端的 grill 步骤同一个条件）。配置里关了炉灶站点（stove）时
GrillView.register 返回 None，这一步记成 skipped：炉灶照农夫乐事原样用，FD 灶上东西的黑烟也照放。
"""
from . import GrillView, StoveScenes
from ...Client import StoveFlame


def link(ctx):
    if GrillView.register(ctx.api) is None:
        return False
    StoveScenes.enable()         # 炉灶从此按 HoD 的样子画：烤架上的东西、冒烟等翻、翻面落下取走（谁都看得见）
    StoveFlame.muteItemSmoke()   # HoD 的 StoveSmokeMixin：场景在，FD 灶上东西的黑烟就取消（火口的火星和噼啪声照旧）
    return True
