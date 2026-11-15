# -*- coding: utf-8 -*-
from .QuModLibs.QuMod import *

MOD = EasyMod()

# 服务端：入口模块导入全部玩法模块，每个引擎事件只挂一次监听（见 Server/ModServer.py）
MOD.Server("Server.ModServer")

# 跨 MOD 联动（若对方副包未装则静默 no-op）
MOD.Server("compat.create.createCompat")

MOD.Client("modClient.farmersDelightCommon")
MOD.Client("modClient.cookingPot")
