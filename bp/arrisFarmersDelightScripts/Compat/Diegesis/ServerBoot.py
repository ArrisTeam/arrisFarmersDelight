# -*- coding: utf-8 -*-
"""ServerBoot - 场景交互前置的服务端联动入口：只挂 Presence，装了前置包才按步骤表联动（服务端）

单独在 modMain 里登记，Server/ 不导入 Compat/。这里不导入任何站点模块：它们在 ServerSteps 的步骤里才被导入，
所以前置包没装时 Compat/Diegesis 里除了本入口、Presence、Steps、两张步骤表，别的模块一个也不导入——没有监听、没有端点，
砧板、厨锅、煎锅、炉灶照常走经典玩法（Server/CuttingBoard.py、CookingPot.py、Skillet.py、Stove.py），Hands-On Delight 的东西一样也不跑
（没联动时 Shared/Rules/HandsOnOptions 说 HoD 不在）。
什么时候找前置包、怎么判定本端的运行模式（Shared/Rules/HandsOnMode）、一步失败怎么办，都在 Presence.attach：导入时找一次，
LoadServerAddonScriptsAfter 里再找一次（前置包比本包后加载时），还没有就是没装。docs/ARCHITECTURE.md 的「联动（场景交互前置）」是总说明。
"""
from ...QuModLibs.Server import ImportModule, Listen, serverApi
from . import Presence
from .ServerSteps import STEPS

Presence.attach("server", STEPS, listen=Listen, find=serverApi.ImportModule, load=ImportModule)
