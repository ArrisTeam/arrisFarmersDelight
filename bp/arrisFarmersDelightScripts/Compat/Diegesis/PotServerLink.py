# -*- coding: utf-8 -*-
"""PotServerLink - 联动步骤 pot（服务端）：登记厨锅站点，登记上了就打开厨锅的世界外观广播

配置里关了厨锅站点（cooking_pot）时 PotLogic.register 返回 None，这一步记成 skipped：锅照农夫乐事原样用（右键开经典界面），不广播。
"""
from . import PotLogic
from ...Server import PotLook


def link(ctx):
    if PotLogic.register(ctx.api) is None:
        return False
    PotLook.enable()             # 附近的人看得到汤里的料、勺子在转、锅在煮（Server/PotLook.py）
    return True
