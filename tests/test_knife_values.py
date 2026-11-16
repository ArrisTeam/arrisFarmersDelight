# -*- coding: utf-8 -*-
# runner: both
"""小刀物品 JSON 对 JE 材质档：耐久 = uses，附魔能力 = enchantmentValue，下界合金刀防火（tests/jefood.py 的 KNIVES）。

基岩版的耐久比较是"损伤 > 最大耐久才坏"，所以 max_damage = N 的工具能用 N+1 次，和原版基岩工具（铁剑 251）一致，
这里不再另外减一。攻击伤害、挖掘等级不在这个对照里。

netease:weapon 里的 attack_damage / level / enchantment 只有 description.custom_item_type 是 weapon 时才会被读
（网易"自定义武器及工具"文档；引擎里 Item::initServer 对 netease:weapon 只做"最大堆叠 1"，不写类型就是普通物品），
所以小刀必须带 custom_item_type，附魔能力才生效。
"""
from __future__ import print_function, unicode_literals

import fdtest
import jefood
from jefood import KNIVES


def _knife(tier):
    return jefood.beh("%s_knife" % tier)


def testDurabilityMatchesJeTierUses():
    for tier, (uses, _enchant, _fire) in sorted(KNIVES.items()):
        assert _knife(tier)["minecraft:max_damage"] == uses, tier


def testEnchantabilityMatchesJeTier():
    for tier, (_uses, enchant, _fire) in sorted(KNIVES.items()):
        weapon = _knife(tier)["netease:weapon"]
        assert weapon["enchantment"] == enchant, tier
        assert weapon["type"] == "sword" and weapon["attack_damage"] > 0, "%s：攻击伤害保持原样、还是剑类" % tier


def testKnivesAreDeclaredAsWeapons():
    for tier in sorted(KNIVES):
        declared = jefood.description("%s_knife" % tier).get("custom_item_type")
        assert declared == "weapon", "%s：不写 custom_item_type 就是普通物品，netease:weapon 的攻击和附魔能力不生效" % tier


def testOnlyTheNetheriteKnifeIsFireResistant():
    for tier, (_uses, _enchant, fire) in sorted(KNIVES.items()):
        resistant = _knife(tier).get("netease:fire_resistant", {}).get("value", False)
        assert resistant is fire, tier


def testEveryKnifeItemIsCovered():
    knives = set(short[:-len("_knife")] for short in jefood.shortNames(jefood.BEH) if short.endswith("_knife"))
    assert knives == set(KNIVES), knives ^ set(KNIVES)


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
