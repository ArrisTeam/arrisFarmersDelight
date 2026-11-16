# -*- coding: utf-8 -*-
"""ClientBoot - 场景交互前置的客户端联动入口：装了前置就登记切菜板、厨锅、煎锅、炉灶站点的表现（客户端）

单独在 modMain 里登记，Client/ 不导入 Compat/。前置包没装时 ImportModule 返回 None，什么都不做。
"""
from ...QuModLibs.Client import Listen, clientApi
from . import BoardView, GrillView, PanView, PotView

API_MODULE = "arrisDiegesisScripts.Api.Client"
MIN_API_VERSION = 1


@Listen("LoadClientAddonScriptsAfter")
def OnLoadClientAddonScriptsAfter(args=None):
    api = clientApi.ImportModule(API_MODULE)
    if api is not None and getattr(api, "API_VERSION", 0) >= MIN_API_VERSION:
        BoardView.register(api)
        PotView.register(api)
        PanView.register(api)
        GrillView.register(api)
