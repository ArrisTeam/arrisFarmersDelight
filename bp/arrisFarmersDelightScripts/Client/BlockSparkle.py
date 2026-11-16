# -*- coding: utf-8 -*-
"""BlockSparkle - 闪亮沙拉冒闪光：客户端动画刻到了就在方块上放一个闪光粒子（客户端）

JE 的 GleamingSaladBlock.animateTick 在客户端按 0.05 × 剩余份数的概率放 SparkleParticle。基岩版：四个有份数的阶段方块
写了 netease:block_animate_random_tick（引擎按 trigger_rate 的概率给本端发 BlockAnimateRandomTickEvent，不用服务端参与），
这里收到就在 JE 的位置放一个 arris:sparkle（概率、位置的算式在 Shared/Rules/Sparkle.py）。
"""
import random

from ..QuModLibs.Client import Listen
from .Engine import compFactory
from ..Shared.Rules.Sparkle import SPARKLE, SPARKLE_SERVINGS, sparkleSpot


@Listen("BlockAnimateRandomTickEvent")
def OnBlockAnimateRandomTick(args):
    # 这个事件对所有带该组件的自定义方块都来，别的方块（别的模组的）不归这里
    if args["blockName"] not in SPARKLE_SERVINGS:
        return
    compFactory.CreateParticleSystem(None).Create(SPARKLE, sparkleSpot(args["blockPos"], random.random(), random.random()))
