# -*- coding: utf-8 -*-
"""ServerBoot - 场景交互前置的服务端联动入口：装了前置就登记切菜板、厨锅、煎锅、炉灶站点（服务端）

单独在 modMain 里登记，Server/ 不导入 Compat/。前置包没装时 ImportModule 返回 None，什么都不做，
砧板、厨锅、煎锅、炉灶照常走经典玩法（Server/CuttingBoard.py、CookingPot.py、Skillet.py、Stove.py）。只靠 API_VERSION 判断能力，不写清单依赖。
两次机会、只登记一次：导入时（前置包的服务端 Api 是纯 Python，早于它的服务端系统导入也安全），
以及 LoadServerAddonScriptsAfter（前置包比本包后加载时）。
砧板、厨锅、煎锅站点要前置包 API 3（2：光标栈随状态同步、站点逻辑的 ctx / dropped / userData、托盘；3：客户端悬着的半透明容器和输入方式），
炉灶要 2：更老的前置包上它们照旧走经典玩法（砧板没登记，工作台也就照旧出那些菜）。装了新前置包时顺手打开厨锅、煎锅的世界外观广播（Server/PotLook.py、Server/PanLook.py）。
炉灶站点登记上了就打开炉灶的世界外观广播（Server/StoveLook.py），客户端的 StoveScenes 照它画。
"""
from ...QuModLibs.Server import Listen, serverApi
from ...Server import BoardLook, PanLook, PotLook, StoveLook
from . import BoardLogic, DishCrafts, GrillLogic, PanLogic, PotLogic

API_MODULE = "arrisDiegesisScripts.Api.Server"
MIN_API_VERSION = 1
POT_API_VERSION = 3
_state = {"registered": False}


def getApi():
    """前置包的服务端接口；没装或版本太旧返回 None。"""
    api = serverApi.ImportModule(API_MODULE)
    return api if api is not None and getattr(api, "API_VERSION", 0) >= MIN_API_VERSION else None


def tryRegister():
    if _state["registered"]:
        return True
    api = getApi()
    if api is None:
        return False
    board = BoardLogic.register(api)       # API 不够新返回 None：砧板和它的工作台拦截一起没有
    if getattr(api, "API_VERSION", 0) >= POT_API_VERSION:
        PotLogic.register(api)
        PotLook.enable()
        PanLogic.register(api)
        PanLook.enable()
    if GrillLogic.register(api) is not None:
        StoveLook.enable()
    if board is not None:
        DishCrafts.register()        # 改在砧板上摆的菜：工作台不再出（照 HoD 在 JE 上的缺省）；砧板站点不在就一切照旧
        BoardLook.enable()           # 附近没开站点的人也听得到切菜声（站点里的人收站点自己的 effect）
    _state["registered"] = True
    return True


tryRegister()


@Listen("LoadServerAddonScriptsAfter")
def OnLoadServerAddonScriptsAfter(args=None):
    tryRegister()
