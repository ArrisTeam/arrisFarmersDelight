# -*- coding: utf-8 -*-
from ..QuModLibs.Client import *
# 加固版 QuModLibs 不再导出 compFactory，由本模组自己取
compFactory = clientApi.GetEngineCompFactory()

NativeScreenManager = clientApi.GetNativeScreenManagerCls()
NativeScreenManager.instance().RegisterScreenProxy("arrisCookingPot.arris_cooking_pot_screen", "arrisFarmersDelightScripts.proxys.arrisCookingPotProxy.arrisCookingPotProxy")

@Listen("ClientBlockUseEvent")
def OnClientBlockUsed(args):
    blockName = args["blockName"]
    if blockName != "arris:cooking_pot":
        return
    x, y, z = args["x"], args["y"], args["z"]
    compFactory.CreateModAttr(playerId).SetAttr("arrisUsedCookingPotPos", (x, y, z))
