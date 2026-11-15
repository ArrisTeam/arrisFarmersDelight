# -*- coding: utf-8 -*-
"""CookingPotScreen - 厨锅界面：登记界面代理，记下玩家打开的是哪口锅（客户端）

界面本身由引擎的自定义容器打开（方块 JSON 的 netease:block_container.screen_name）；
代理类在 CookingPotProxy.py，按字符串路径登记，改名 / 挪位置要同步改这里。
"""
from ...QuModLibs.Client import Listen
from ..Engine import clientApi, compFactory, playerId

SCREEN_NAME = "arrisCookingPot.arris_cooking_pot_screen"
PROXY_PATH = "arrisFarmersDelightScripts.Client.Ui.CookingPotProxy.arrisCookingPotProxy"
# 代理在 OnTick 里从这个 ModAttr 读当前厨锅的坐标
USED_POT_POS_ATTR = "arrisUsedCookingPotPos"

clientApi.GetNativeScreenManagerCls().instance().RegisterScreenProxy(SCREEN_NAME, PROXY_PATH)


@Listen("ClientBlockUseEvent")
def OnClientBlockUsed(args):
    if args["blockName"] == "arris:cooking_pot":
        compFactory.CreateModAttr(playerId).SetAttr(USED_POT_POS_ATTR, (args["x"], args["y"], args["z"]))
