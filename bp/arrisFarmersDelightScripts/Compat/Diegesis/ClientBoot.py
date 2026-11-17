# -*- coding: utf-8 -*-
"""ClientBoot - 场景交互前置的客户端联动入口：装了前置就登记切菜板、厨锅、煎锅、炉灶站点的表现（客户端）

单独在 modMain 里登记，Client/ 不导入 Compat/。前置包没装时 ImportModule 返回 None，什么都不做。
HoD 的配置（Shared/Data/HandsOnConfig.py，和服务端是同一份）里关了的站点，它的 View.register 返回 None（和服务端的 Logic.register 同一个条件），
这里就不登记它、也不开它的场景和旁观的声音：方块照农夫乐事原样用，右键开经典界面或放料取料。
"""
from ...QuModLibs.Client import Listen, clientApi
from . import BoardView, BoardWatch, GrillView, PanScenes, PanView, PotScenes, PotView, StoveScenes
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
            if PotView.register(api) is not None:
                PotScenes.enable(BrothColors.get)     # 厨锅从此按 HoD 的样子画：开盖、汤面、漂着的料（谁都看得见）
            if PanView.register(api) is not None:
                PanScenes.enable()                # 煎锅从此按 HoD 的样子画：食物落进来、颠锅翻面、油星热气（谁都看得见）
        if GrillView.register(api) is not None:
            StoveScenes.enable()                      # 炉灶从此按 HoD 的样子画：烤架上的东西、冒烟等翻、翻面落下取走（谁都看得见）
