# -*- coding: utf-8 -*-
"""GrillServerLink - 联动步骤 grill（服务端）：登记炉灶站点，登记上了就打开炉灶的世界外观广播

步骤表给这一步的条件是前置包接口的朝向钩子（FACING_HOOK）。配置里关了炉灶站点（stove）时 GrillLogic.register 返回 None，
这一步记成 skipped：炉灶照农夫乐事原样用，不广播。
"""
from . import GrillLogic
from ...Server import StoveLook


def link(ctx):
    if GrillLogic.register(ctx.api) is None:
        return False
    StoveLook.enable()           # 客户端的 StoveScenes 照它画烤架（Server/StoveLook.py）
    return True
