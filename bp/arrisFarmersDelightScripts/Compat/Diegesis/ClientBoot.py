# -*- coding: utf-8 -*-
"""ClientBoot - 场景交互前置的客户端联动入口：装了前置就登记切菜板、厨锅、煎锅、炉灶站点的表现（客户端）

单独在 modMain 里登记，Client/ 不导入 Compat/。前置包没装时 ImportModule 返回 None，什么都不做。
"""
from ...QuModLibs.Client import Listen, clientApi
from . import BoardView, BoardWatch, GrillView, PanScenes, PanView, PotScenes, PotView
from ...Shared.Data.BrothColors import BrothColors

API_MODULE = "arrisDiegesisScripts.Api.Client"
MIN_API_VERSION = 1
POT_API_VERSION = 3                           # 和 ServerBoot 的同一个数：厨锅站点两端一起有、一起没有


@Listen("LoadClientAddonScriptsAfter")
def OnLoadClientAddonScriptsAfter(args=None):
    api = clientApi.ImportModule(API_MODULE)
    if api is not None and getattr(api, "API_VERSION", 0) >= MIN_API_VERSION:
        if BoardView.register(api) is not None:
            BoardWatch.enable(api.Geometry)       # 砧板站点登记了：旁边别人用的砧板，也听得到切菜声、看得到碎屑（服务端的 BoardLook 发过来）
        if api.API_VERSION >= POT_API_VERSION:
            PotView.register(api)
            PotScenes.enable(BrothColors.get)     # 厨锅从此按 HoD 的样子画：开盖、汤面、漂着的料（谁都看得见）
            if PanView.register(api) is not None:
                PanScenes.enable()                # 煎锅从此按 HoD 的样子画：食物落进来、颠锅翻面、油星热气（谁都看得见）
        GrillView.register(api)
