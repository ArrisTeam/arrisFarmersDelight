# -*- coding: utf-8 -*-
"""PanServerLink - 联动步骤 pan（服务端）：登记煎锅站点，登记上了就打开煎锅的世界外观广播

配置里关了煎锅站点（skillet）时 PanLogic.register 返回 None，这一步记成 skipped：煎锅照农夫乐事原样用，不广播。
"""
from . import PanLogic
from ...Server import PanLook


def link(ctx):
    if PanLogic.register(ctx.api) is None:
        return False
    PanLook.enable()             # 附近的人看得到锅里的东西、油在冒、锅被颠（Server/PanLook.py）
    return True
