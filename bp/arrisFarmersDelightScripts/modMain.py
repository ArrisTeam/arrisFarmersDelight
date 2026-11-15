# -*- coding: utf-8 -*-
from .QuModLibs.QuMod import *

MOD = EasyMod()

# 服务端：入口模块导入全部玩法模块，每个引擎事件只挂一次监听（见 Server/ModServer.py）
MOD.Server("Server.ModServer")

MOD.Client("Client.ModClient")

# 跨模组联动（对方未安装时静默不做任何事）
MOD.Server("Compat.Create.CreateRecipes")
MOD.Client("Compat.Jei.JeiClient")
# 场景交互前置（arrisDiegesis）：亲手做菜的站点；前置没装时不做任何事
MOD.Server("Compat.Diegesis.ServerBoot")
MOD.Client("Compat.Diegesis.ClientBoot")
