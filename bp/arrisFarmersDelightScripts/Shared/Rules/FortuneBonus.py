# -*- coding: utf-8 -*-
"""FortuneBonus - 农夫乐事的作物、野生作物、沙地灌木被打掉时，时运多掉几个（双端，纯规则）

照 JE 农夫乐事 1.3.4 方块战利品表里的 apply_bonus（附魔 fortune；data/farmersdelight/loot_tables/blocks/*.json 一共 11 张）。
基岩的战利品表没有时运，bp/loot_tables 只写了不带时运的那一份（tests/test_farm_loot_tables.py 对过），多出来的由脚本补：
- binomial_with_bonus_count（extra 3、p 0.5714286）：JE 掷 时运等级 + 3 次、每次 p 多一个；表里已经有那 3 次，补的是多出来的 等级 次；
- uniform_bonus_count（bonusMultiplier n）：JE 多 random.nextInt(n × 等级 + 1) 个，也就是 0 到 n × 等级 均匀取一个。
补的条件照 JE 那一条：只有熟的作物方块在表里（JE 的条目带 block_state_property）；野生作物、沙地灌木拿剪刀打是掉它自己（JE 的
can_tool_perform_action 那一支），不补；沙地灌木的甜菜种子本身只有 12.5%，所以只在战利品表真掉了种子时才补。创造模式不补（没有掉落）。
沃土上的原版作物（成熟的 arris:rich_soil_wheat7 / beetroot3 / carrots3 / potatoes3）在 JE 里就是原版作物、吃原版的时运；要"和种在普通
耕地上一样"，照的是基岩原版作物的时运——2026-11-26 实机量的（钻石锄时运 0~III 各 196 株，INGAME-FACTS-1 第三轮），不是 JE 的公式：
小麦种子、甜菜种子每级多掷 1 次，胡萝卜、土豆每级多掷 2 次，每次约 8/15 多一个（按数据推的模型）；小麦、甜菜根本身和毒马铃薯不受时运影响。
"""
FORTUNE = 18                               # 时运的附魔编号（网易 EnchantType.MiningLoot）
SHEARS = "minecraft:shears"
BINOMIAL, UNIFORM = "binomial", "uniform"
BINOMIAL_P = 0.5714286        # JE binomial_with_bonus_count 的 probability（4/7）
BEDROCK_CROP_P = 0.5333333    # 基岩原版作物实测的 8/15

# 方块 -> (补的物品, 公式, 参数, 剪刀打的不补, 战利品表真掉了这件才补)；BINOMIAL 的参数是 (每次的概率, 每级多掷几次)，UNIFORM 的是倍数
TABLE = {
    "arris:cabbages_stage7": ("arris:cabbage_seeds", BINOMIAL, (BINOMIAL_P, 1), False, False),
    "arris:onions_stage3": ("arris:onion", BINOMIAL, (BINOMIAL_P, 1), False, False),
    "arris:budding_tomatoes_stage6": ("arris:tomato", UNIFORM, 1, False, False),
    "arris:tomatoes_vine_stage3": ("arris:tomato", UNIFORM, 1, False, False),
    "arris:sandy_shrub": ("minecraft:beetroot_seeds", UNIFORM, 2, True, True),
    "arris:wild_beetroots": ("minecraft:beetroot_seeds", UNIFORM, 2, True, False),
    "arris:wild_cabbages": ("arris:cabbage_seeds", UNIFORM, 2, True, False),
    "arris:wild_carrots": ("minecraft:carrot", UNIFORM, 2, True, False),
    "arris:wild_onions": ("arris:onion", UNIFORM, 2, True, False),
    "arris:wild_potatoes": ("minecraft:potato", UNIFORM, 2, True, False),
    "arris:wild_tomatoes": ("arris:tomato_seeds", UNIFORM, 2, True, False),
    # 沃土上的原版作物：基岩原版实测（见模块说明），不是 JE 的表
    "arris:rich_soil_wheat7": ("minecraft:wheat_seeds", BINOMIAL, (BEDROCK_CROP_P, 1), False, False),
    "arris:rich_soil_beetroot3": ("minecraft:beetroot_seeds", BINOMIAL, (BEDROCK_CROP_P, 1), False, False),
    "arris:rich_soil_carrots3": ("minecraft:carrot", BINOMIAL, (BEDROCK_CROP_P, 2), False, False),
    "arris:rich_soil_potatoes3": ("minecraft:potato", BINOMIAL, (BEDROCK_CROP_P, 2), False, False),
}
# 照 JE 的表搬的那 11 个（另外 4 个是基岩原版实测的）
JE_BLOCKS = tuple(name for name in TABLE if not name.startswith("arris:rich_soil_"))


def fortuneLevel(itemDict):
    """手上物品的时运等级（enchantData：[(附魔编号, 等级)]），没有是 0。"""
    for entry in (itemDict or {}).get("enchantData") or ():
        if entry[0] == FORTUNE:
            return max(0, int(entry[1]))
    return 0


def isShears(toolName, toolType):
    """JE 的 can_tool_perform_action(shears_dig)：原版剪刀，或者引擎说物品类型是 shears 的（别的模组的剪刀）。"""
    return toolName == SHEARS or toolType == "shears"


def bonus(blockName, toolName, toolType, level, droppedNames, rng):
    """打掉 blockName 时多掉的 (物品, 个数)，不多掉返回 None。
    toolName 是手上的物品名（空手 None），toolType 是引擎给的物品类型（GetItemBasicInfo 的 itemType），level 是时运等级，
    droppedNames 是战利品表这一下掉出来的物品名，rng 要有 random()（[0, 1)）和 randint(a, b)（两头都含）。"""
    entry = TABLE.get(blockName)
    if entry is None or level <= 0:
        return None
    itemName, formula, parameter, shearsExempt, needsDrop = entry
    if shearsExempt and isShears(toolName, toolType):
        return None
    if needsDrop and itemName not in droppedNames:
        return None
    if formula == BINOMIAL:
        probability, perLevel = parameter
        count = sum(1 for _ in range(perLevel * level) if rng.random() < probability)
    else:
        count = rng.randint(0, parameter * level)
    return (itemName, count) if count > 0 else None
