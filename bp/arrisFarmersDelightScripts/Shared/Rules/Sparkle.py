# -*- coding: utf-8 -*-
"""Sparkle - 闪亮沙拉的闪光粒子：哪些方块冒、冒的概率、冒在哪（双端，纯规则）

JE 的 GleamingSaladBlock.animateTick（客户端动画刻）：剩余份数 servings > 0 时，以 0.05 × servings 的概率在方块中央
（水平各偏 ±0.25 格、高度在方块中间）放一个 SparkleParticle。基岩版由方块 JSON 的 netease:block_animate_random_tick
按 trigger_rate 的概率给客户端发 BlockAnimateRandomTickEvent（概率写在 JSON 里，tests/test_gleaming_sparkle.py 守着它等于这里的算式），
客户端收到就在 sparkleSpot 算出的位置放一个 SPARKLE 粒子（rp/particles/sparkle.json）。
"""
SPARKLE = "arris:sparkle"
CHANCE_PER_SERVING = 0.05

# 会冒闪光的方块 -> 剩余份数（空盘 servings = 0，JE 直接返回，不冒）
SPARKLE_SERVINGS = {
    "arris:gleaming_salad_block_stage0": 4,
    "arris:gleaming_salad_block_stage1": 3,
    "arris:gleaming_salad_block_stage2": 2,
    "arris:gleaming_salad_block_stage3": 1,
}


def sparkleChance(servings):
    """一次动画刻冒闪光的概率（JE：random.nextFloat() < 0.05F * servings）。"""
    return CHANCE_PER_SERVING * servings


def sparkleSpot(blockPos, randomX, randomZ):
    """闪光的位置。randomX / randomZ 是 [0, 1) 的随机数（JE 的 random.nextDouble()）：
    x = 方块x + 0.5 + (r * 0.5 - 0.25)，y = 方块y + 0.5，z 同 x。"""
    return (blockPos[0] + 0.5 + (randomX * 0.5 - 0.25), blockPos[1] + 0.5, blockPos[2] + 0.5 + (randomZ * 0.5 - 0.25))
