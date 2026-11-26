# -*- coding: utf-8 -*-
from .QuModLibs.QuMod import *

MOD = EasyMod()

# 容器界面库 dolorContainer（拷在 dolorContainer/ 下，tools/vendor.py 生成，不手改）：两端服务先登记。
# 厨锅的界面模型、方块宿主在 Server/CookingPotHost.py 与 Client/CookingPotUi.py 里，随下面两端的入口导入
MOD.Server("dolorContainer.Server.Service")
MOD.Client("dolorContainer.Client.Service")

# 服务端：入口模块导入全部玩法模块，每个引擎事件只挂一次监听（见 Server/ModServer.py）
MOD.Server("Server.ModServer")

MOD.Client("Client.ModClient")

# 跨模组联动（对方未安装时静默不做任何事）
MOD.Server("Compat.Create.CreateRecipes")
MOD.Server("Compat.Create.PotatoCannonServer")
MOD.Client("Compat.Create.PotatoCannonClient")
MOD.Client("Compat.Jei.JeiClient")
MOD.Server("Compat.Advancements.AdvBoot")          # 成就系统（arrisAdvancements）：JE 的 21 条进度
# 沉浸式交互前置（arrisDiegesis）：亲手做菜的站点（Hands-On Delight）。入口只挂 Compat/Diegesis/Presence：找到前置包、接口够新才按步骤表
# （ServerSteps / ClientSteps）一站一站导入站点模块、联动；前置包没装或太旧时 Compat/Diegesis 里别的模块一个也不导入，HoD 的东西一样也不跑。
MOD.Server("Compat.Diegesis.ServerBoot")
MOD.Client("Compat.Diegesis.ClientBoot")
