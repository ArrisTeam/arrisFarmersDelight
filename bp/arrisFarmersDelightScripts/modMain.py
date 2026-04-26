# -*- coding: utf-8 -*-
from .QuModLibs.QuMod import *

MOD = EasyMod()

MOD.Server("modServer.farmersDelightCommon")
MOD.Server("modServer.cookingPot")
MOD.Server("modServer.effect")
MOD.Server("modServer.ropeAndNet")
MOD.Server("modServer.farmCrop")
MOD.Server("modServer.platePackagedFood")
MOD.Server("modServer.skillet")
MOD.Server("modServer.cuttingBoard")
MOD.Server("modServer.stove")

# 跨 MOD 联动（若对方副包未装则静默 no-op）
MOD.Server("compat.create.createCompat")

MOD.Client("modClient.farmersDelightCommon")
MOD.Client("modClient.cookingPot")
