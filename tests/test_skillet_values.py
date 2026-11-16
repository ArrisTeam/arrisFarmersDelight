# -*- coding: utf-8 -*-
# runner: both
"""煎锅数值与数据对 JE 1.3.4：营火配方表（煎锅 / 炉灶 / 手持煎锅都读它）、煎锅物品（铁档武器）与打人音效。

参照表抄自 JE 的 data 与 SkilletItem.java：原版 campfire_cooking 配方、FD 的 SmeltingRecipes.foodSmeltingRecipes、
Tiers.IRON（耐久 250、附魔能力 14、攻击力加成 2.0、修复材料铁锭），不依赖 .refs。
"""
from __future__ import print_function, unicode_literals

import io
import json
import os

import fdtest
import jefood

Cooking = fdtest.load("Shared.Data.Cooking")
Rules = fdtest.load("Shared.Rules.SkilletRules")
SOUNDS = os.path.join(fdtest.ROOT, "rp", "sounds")

# JE 的营火烹饪配方：原版 9 条 + FD 的 7 条（FD 的物品换成本模组的名字），时间一律 600 刻（30 秒）
JE_CAMPFIRE_RECIPES = {
    "minecraft:beef": "minecraft:cooked_beef",
    "minecraft:chicken": "minecraft:cooked_chicken",
    "minecraft:cod": "minecraft:cooked_cod",
    "minecraft:kelp": "minecraft:dried_kelp",
    "minecraft:mutton": "minecraft:cooked_mutton",
    "minecraft:porkchop": "minecraft:cooked_porkchop",
    "minecraft:potato": "minecraft:baked_potato",
    "minecraft:rabbit": "minecraft:cooked_rabbit",
    "minecraft:salmon": "minecraft:cooked_salmon",
    # FD：fried_egg / beef_patty / cooked_chicken_cuts / cooked_cod_slice / cooked_salmon_slice / cooked_bacon / cooked_mutton_chops
    "minecraft:egg": "arris:fried_egg",
    "arris:minced_beef": "arris:beef_patty",
    "arris:chicken_cuts": "arris:cooked_chicken_cuts",
    "arris:cod_slice": "arris:cooked_cod_slice",
    "arris:salmon_slice": "arris:cooked_salmon_slice",
    "arris:bacon": "arris:cooked_bacon",
    "arris:mutton_chops": "arris:cooked_mutton_chops",
}


def testCookableFoodIsExactlyTheJeCampfireRecipes():
    table = dict(Cooking.CanCookedFoodDict)
    missing = sorted(set(JE_CAMPFIRE_RECIPES) - set(table))
    extra = sorted(set(table) - set(JE_CAMPFIRE_RECIPES))
    assert not missing and not extra, "缺 %s，多 %s" % (missing, extra)
    assert table == JE_CAMPFIRE_RECIPES


def testSkilletItemIsDeclaredAsAnIronTierWeapon():
    # 不写 custom_item_type 就是普通物品，netease:weapon 里的攻击、附魔能力、修复都不生效（tests/test_knife_values.py 同理）
    assert jefood.description("skillet_item").get("custom_item_type") == "weapon"
    item = jefood.beh("skillet_item")
    assert item["minecraft:max_stack_size"] == 1
    # 耐久照小刀的约定：max_damage = JE 材质档的 uses（基岩版"损伤 > 最大耐久才坏"，和原版基岩工具一致，不再减一）
    assert item["minecraft:max_damage"] == 250                       # Tiers.IRON.getUses()
    weapon = item["netease:weapon"]
    assert weapon["type"] == "sword"
    assert weapon["enchantment"] == 14                               # Tiers.IRON.getEnchantmentValue()
    assert weapon["level"] == 2                                      # 网易文档：level 2 = 铁砧用铁锭修；JE getRepairIngredient = 铁锭
    # 基岩版生肉放不进副手，手持烹饪常用"煎锅放副手、原料拿主手"（SkilletHandRules.skilletHand）：煎锅得能进副手
    assert item["netease:allow_offhand"] == {"value": True}


def testSkilletAttackDamageIsTheJeModifier():
    # SkilletItem：5.0F + SKILLET_TIER.getAttackDamageBonus()（铁 2.0）= 7，是加在玩家基础 1 上的修饰符，揍一下实际 8
    assert jefood.beh("skillet_item")["netease:weapon"]["attack_damage"] == 5 + 2


def testSkilletTooltipIsThePlaceableSneakingTipAndKeepsTheBuiltInLines():
    # SkilletItem.appendHoverText：TextUtils.PLACEABLE_SNEAKING = tooltip.farmersdelight.placeable_sneaking（深灰斜体"潜行可放置"）。
    # netease:customtips 是整段悬停文字的格式串（官方文档的物品信息字典一节）：自带的附魔、攻击伤害两行要自己用 %enchanting% / %attack_damage% 放回去，
    # 否则煎锅变成武器之后附魔和攻击伤害不显示（是替换还是追加没实机核，见 docs/ARCHITECTURE.md 的待验证清单）
    assert jefood.beh("skillet_item")["netease:customtips"]["value"] == "§8§o潜行可放置§r%enchanting%%attack_damage%"


def _definitions():
    with io.open(os.path.join(SOUNDS, "sound_definitions.json"), encoding="utf-8") as handle:
        return json.load(handle)["sound_definitions"]


def testAttackSoundsExistWithJeVolumes():
    # playSkilletAttackSound：重击 音量 1.0（音调 0.9–1.1），轻击 音量 0.8、音调 0.9；本模组的定义里重击音量是 2.0
    definitions = _definitions()
    strong = definitions[Rules.SOUND_STRONG]["sounds"][0]
    weak = definitions[Rules.SOUND_WEAK]["sounds"][0]
    assert abs(weak["volume"] - 0.8 * strong["volume"]) < 1e-9
    assert weak["pitch"] == 0.9
    for sound in (strong, weak):
        assert os.path.isfile(os.path.join(fdtest.ROOT, "rp", sound["name"] + ".ogg")), sound["name"]


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
