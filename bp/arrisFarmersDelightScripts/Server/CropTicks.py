# -*- coding: utf-8 -*-
"""CropTicks - 作物随机刻：按 JE 的概率长一级、稻苗长穗、番茄沿绳子往上爬（服务端）

概率与阶段换算在 Shared/Rules/CropTick.py、CropGrowth.py、GrowthRates.py（JE 的公式，已换成 Bedrock 随机刻的概率）；
这里读事件、读世界、把修改落地。下游往 cropsDict 里追加的作物（本模组不认识的）仍按旧办法：光照 9-15 时每次随机刻长一级。
"""
import random

from .EventRegistry import registerHandler
from .FarmWorld import FarmWorld
from ..Shared.Data.Farming import cropsDict
from ..Shared.Rules import CropTick, FarmEdits
from ..Shared.Rules.CompostRules import COMPOST_STAGES
from ..Shared.Rules.CropGrowth import splitStage

LEGACY_LIGHT = (9, 15)
# cropsDict 里不是作物的条目：有机肥有自己的处理（OrganicCompost.py），沃土不往下长
_NOT_CROPS = frozenset(COMPOST_STAGES + ("arris:rich_soil",))


@registerHandler("BlockRandomTickServerEvent", match=cropsDict)
def OnCropRandomTick(args):
    blockName = args["fullName"]
    pos = (args["posX"], args["posY"], args["posZ"])
    world = FarmWorld(args["dimensionId"])
    if splitStage(blockName)[0] is not None:
        world.apply(CropTick.randomTick(world, blockName, pos, args["brightness"], random))
    elif blockName not in _NOT_CROPS and cropsDict[blockName]:
        # 下游登记的作物：成熟阶段映射到空字符串，不再往下长
        if LEGACY_LIGHT[0] <= args["brightness"] <= LEGACY_LIGHT[1]:
            world.apply([FarmEdits.block(pos, cropsDict[blockName])])
