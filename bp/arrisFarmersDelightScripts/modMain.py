# -*- coding: utf-8 -*-
from .QuModLibs.QuMod import *

MOD = EasyMod()

# 服务端：入口模块导入全部玩法模块，每个引擎事件只挂一次监听（见 Server/ModServer.py）
MOD.Server("Server.ModServer")

MOD.Client("Client.ModClient")

# 跨模组联动（对方未安装时静默不做任何事）
MOD.Server("Compat.Create.CreateRecipes")
MOD.Client("Compat.Jei.JeiClient")
