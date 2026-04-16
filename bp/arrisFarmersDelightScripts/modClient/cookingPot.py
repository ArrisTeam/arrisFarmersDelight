# -*- coding: utf-8 -*-
from ..QuModLibs.Client import *

NativeScreenManager = clientApi.GetNativeScreenManagerCls()
NativeScreenManager.instance().RegisterScreenProxy("arrisCookingPot.arrisCookingPotMain", "arrisFarmersDelightScripts.proxys.arrisCookingPotProxy.arrisCookingPotProxy")

@Listen("ClientBlockUseEvent")
def OnClientBlockUsed(args):
    blockName = args["blockName"]
    if blockName != "arris:cooking_pot":
        return
    x, y, z = args["x"], args["y"], args["z"]
    compFactory.CreateModAttr(playerId).SetAttr("arrisUsedCookingPotPos", (x, y, z))
