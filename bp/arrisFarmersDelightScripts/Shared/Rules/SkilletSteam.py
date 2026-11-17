# -*- coding: utf-8 -*-
"""SkilletSteam - 放下的煎锅（经典玩法，没有站点）自己的嗞嗞声、蒸汽、火焰附加的星星：什么时候放、概率、放在哪（双端，纯规则）

JE（FD 1.20）：
- SkilletBlock.animateTick（SkilletBlock.java:157-169，客户端动画刻）：skillet.isCooking()（加热着，而且锅里有东西，SkilletBlockEntity.java:113-115）才放，
  每次 1/10 的概率在锅脚下放 block.skillet.sizzle（音量 0.4，音调 0.9 ~ 1.1）。空锅放在热源上不响；
- SkilletBlockEntity.animationTick（:70-91，客户端方块实体每刻）：加热着而且锅里有东西时，每刻 20% 的概率放一颗 FD 的蒸汽（x、z 在方块中心 ±0.2，y + 0.1，
  向上 0.015 或 0.005 格每刻）；带火焰附加（fireAspectLevel > 0）的锅再每刻 level * 5% 的概率放一颗 ENCHANTED_HIT（同一块范围）。
基岩版：嗞嗞声由方块 JSON 的 netease:block_animate_random_tick（trigger_rate 1，每次轮到都发 BlockAnimateRandomTickEvent，和 JE 的 animateTick 同一个节奏），
蒸汽和星星由 netease:block_entity 的 client_tick（ModBlockEntityTickClientEvent，每秒 20 次，对上 JE 的每刻）给出每次机会（和炉灶的火同一种做法，
Shared/Rules/StoveFlame.py）；这里只管概率和位置，放声音放粒子在 Client/SkilletSteam.py。
装了场景交互前置、煎锅站点开着时，场景（Compat/Diegesis/PanFx）画煎锅的声音和烟，方块实体的 mod_scene 为 1：这里不放，免得两份。
"""
from .BlockDisplay import isItem
from .StoveFlame import PARTICLE_RANGE, inRange  # noqa: F401 - 粒子离镜头超过 32 格不放（LevelRenderer.addParticleInternal），炉灶的火也是这一条

BLOCK = "arris:skillet"
SIZZLE = "ambient.skillet.sizzle"           # FD 的 block.skillet.sizzle（本包的声音定义，每个采样自带 20 倍音量，Shared/Rules/SoundMix 除回去）
STEAM = "arris:skillet_steam"               # JE 的 ModParticleTypes.STEAM：rp/particles/arris_skillet_steam.json（厨锅的 arris:steam_0 飘得又高又快，是厨锅那一路的数）
SPARK = "arris:skillet_spark"               # JE 的 ParticleTypes.ENCHANTED_HIT：rp/particles/arris_skillet_spark.json
SIZZLE_CHANCE = 0.1                         # SkilletBlock.java:164 random.nextInt(10) == 0
SIZZLE_VOLUME = 0.4                         # :165
SIZZLE_PITCH = (0.9, 0.2)                   # :165 random.nextFloat() * 0.2F + 0.9F：(最低, 幅度)
STEAM_CHANCE = 0.2                          # SkilletBlockEntity.java:73 random.nextFloat() < 0.2F
SPARK_CHANCE_PER_LEVEL = 0.05               # :80 random.nextFloat() < fireAspectLevel * 0.05F
SPREAD = 0.4                                # :74 / :81 random.nextDouble() * 0.4D - 0.2D：x、z 在方块中心 ±0.2
HEIGHT = 0.1                                # :75 / :82 pos.getY() + 0.1D
FOOD_SLOT = "0"                             # Client/BlockItems 记着的煎锅内容：{"0": 锅里的东西}
SCENE_ON = 0.5                              # 方块实体的 mod_scene 到这么大就是场景接管了（rp/entity/skillet.json 的动画条件也是 < 0.5）
STORED_KEY = "skilletItem"                  # 方块实体数据里记着的那件煎锅（带附魔，Server/SkilletItem）


def holdsFood(items):
    """锅里有东西吗（items 是 Client/BlockItems 记着的那份 {"0": 物品}，空的槽是 {} / None）。"""
    return isItem(items.get(FOOD_SLOT))


def cooking(heated, items):
    """SkilletBlockEntity.isCooking：加热着，而且锅里有东西。"""
    return bool(heated) and holdsFood(items)


def sizzlePitch(roll):
    """嗞嗞声的音调：roll 是 [0, 1) 的随机数（JE 的 random.nextFloat()）。"""
    return SIZZLE_PITCH[0] + roll * SIZZLE_PITCH[1]


def sizzleSpot(blockPos):
    """嗞嗞声放在哪：方块底面的中心（SkilletBlock.java:159-161 的 x、y、z）。"""
    return (blockPos[0] + 0.5, float(blockPos[1]), blockPos[2] + 0.5)


def surfaceSpot(blockPos, rollX, rollZ):
    """蒸汽和星星放在哪（SkilletBlockEntity.java:74-76）：rollX / rollZ 是 [0, 1) 的随机数（JE 的两个 random.nextDouble()）。"""
    return (blockPos[0] + 0.5 + (rollX * SPREAD - SPREAD / 2.0), blockPos[1] + HEIGHT, blockPos[2] + 0.5 + (rollZ * SPREAD - SPREAD / 2.0))


def sparkChance(level):
    """带火焰附加 level 级的锅每刻放一颗星星的概率（没有附魔是 0）。"""
    return max(0, int(level)) * SPARK_CHANCE_PER_LEVEL
