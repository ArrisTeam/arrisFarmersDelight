# -*- coding: utf-8 -*-
# runner: both
"""食物物品 JSON 对 JE 1.3.4（FoodValues.java + ModItems.java）：营养、饱和度、容器、使用时长、可随时吃、堆叠、喝的动画、
效果（名字 / 秒 / 等级 / 概率）、效果提示。

参照表在 tests/jefood.py。饱和度必须写数字（网易旧格式只认 poor / low / normal / good / max / supernatural，
"high" 之类的名字读成缺省 0.6）；Java 与基岩版的公式相同：回复的饱和度 = 营养 × 饱和系数 × 2。
"""
from __future__ import print_function, unicode_literals

import io
import json
import os
import re

import fdtest
import jefood
from jefood import BEH, FOODS, DRINKS, DRINKABLE, CONTAINERS


def _food(short):
    return jefood.beh(short)["minecraft:food"]


def testEveryFoodItemIsCovered():
    # 有 minecraft:food 的物品都要在参照表里，免得新加的食物漏对 JE
    withFood = set(short for short in jefood.shortNames(BEH) if "minecraft:food" in jefood.beh(short))
    assert withFood == set(FOODS) | set(DRINKS), sorted(withFood ^ (set(FOODS) | set(DRINKS)))


def testNutritionMatchesJe():
    for short, row in sorted(FOODS.items()):
        assert _food(short).get("nutrition", 0) == row[0], "%s 营养应为 %s" % (short, row[0])


def testSaturationIsNumericAndMatchesJe():
    for short in sorted(set(FOODS) | set(DRINKS)):
        saturation = _food(short).get("saturation_modifier")
        assert saturation is None or isinstance(saturation, (int, float)), "%s 饱和度必须是数字: %r" % (short, saturation)
    for short, row in sorted(FOODS.items()):
        saturation = _food(short).get("saturation_modifier")
        if row[0] == 0:
            assert saturation is None, "%s 没有营养，不写饱和度" % short
        else:
            assert saturation is not None and abs(saturation - row[1]) < 1e-9, "%s 饱和度应为 %s，现为 %r" % (short, row[1], saturation)


def testContainersMatchJe():
    for short, row in sorted(FOODS.items()):
        assert _food(short).get("using_converts_to") == CONTAINERS[row[3]], "%s 的容器" % short
    for short in ("ham", "smoked_ham", "barbecue_stick"):
        assert "using_converts_to" not in _food(short), "%s：JE 不还东西（不是骨头 / 木棍）" % short
    for short in DRINKS:
        assert _food(short)["using_converts_to"] == "minecraft:glass_bottle", short


def testUseDurationMatchesJe():
    # 旧格式的 minecraft:use_duration 直接是 tick，不做除法
    for short, row in sorted(FOODS.items()):
        value = jefood.beh(short)["minecraft:use_duration"]
        assert value == row[2] and isinstance(value, int), "%s 使用时长应为 %s 刻，现为 %r" % (short, row[2], value)
    for short in DRINKS:
        assert jefood.beh(short)["minecraft:use_duration"] == 32, short


def testAlwaysEatMatchesJe():
    for short, row in sorted(FOODS.items()):
        assert bool(_food(short).get("can_always_eat")) == row[4], "%s 可随时吃" % short
    for short in DRINKS:
        assert _food(short).get("can_always_eat") is True, "%s 不是 FoodProperties，JE 里随时能喝" % short


def testStackSizeMatchesJe():
    for short, row in sorted(FOODS.items()):
        assert jefood.beh(short)["minecraft:max_stack_size"] == row[5], "%s 堆叠" % short
    for short in DRINKS:
        assert jefood.beh(short)["minecraft:max_stack_size"] == 16, short


def testDrinkAnimationOnlyOnDrinkables():
    # JE 里 DrinkableItem（苹果酒、骨汤、牛奶瓶、热可可、西瓜汁）播放喝的动画，其余用吃的
    for short in jefood.shortNames(jefood.RES):
        animation = jefood.res(short).get("minecraft:use_animation")
        assert (animation == "drink") == (short in DRINKABLE), "%s 的使用动画 %r" % (short, animation)


def _effects(short):
    return [(fx["name"], fx["duration"], fx["amplifier"], fx["chance"]) for fx in _food(short).get("effects", [])]


def testEffectsMatchJe():
    # 名字 / 秒 / 等级 / 概率。西瓜汁（回血）和冰棒（灭火）在 JE 里不是效果，由脚本结算，所以这里是空的
    for short in sorted(set(FOODS) | set(DRINKS)):
        assert _effects(short) == jefood.EFFECTS.get(short, []), "%s 的效果" % short


def testNourishmentUsesTheFourJeTiers():
    seen = set()
    for short in sorted(FOODS):
        for name, seconds, _amplifier, _chance in _effects(short):
            if name == jefood.NOURISHMENT:
                assert seconds in (30, 60, 180, 300), "%s：JE 的滋养只有 30 秒 / 1 / 3 / 5 分钟四档" % short
                seen.add(seconds)
    assert seen == set([30, 60, 180, 300])


def testNoFoodGrantsComfortAnyMore():
    # JE 1.3.2 起舒适弃用：效果和处理还在，但没有食物再给
    for short in jefood.shortNames(BEH):
        assert "arris:comfort" not in json.dumps(jefood.beh(short)), short


def testCustomEffectsAreRegistered():
    names = set(fx[0] for effects in jefood.EFFECTS.values() for fx in effects if ":" in fx[0])
    identifiers = set()
    for name in os.listdir(jefood.EFFECT_DIR):
        with io.open(os.path.join(jefood.EFFECT_DIR, name), encoding="utf-8") as handle:
            identifiers.add(json.load(handle)["minecraft:effect"]["description"]["identifier"])
    assert names <= identifiers, "食物用到的自定义效果必须在 netease_effects 里注册: %r" % (names - identifiers)
    assert "arris:comfort" in identifiers, "舒适保留注册"


# JE 只有 ConsumableItem（hasFoodEffectTooltip 为真）显示吃下去的效果：小麦面团、生意面、鸡块是普通 Item，
# 下界沙拉是 ConsumableItem(…, false)——有效果也没有提示
NO_EFFECT_TOOLTIP = frozenset(("wheat_dough", "raw_pasta", "chicken_cuts", "nether_salad"))
JE_ITEMS = os.path.join(fdtest.ROOT, ".refs", "FarmersDelight", "src", "main", "java", "vectorwing", "farmersdelight", "common",
                        "registry", "ModItems.java")


def testTooltipsAgreeWithTheEffectTable():
    for short in sorted(set(FOODS) | set(DRINKS) | set(["horse_feed"])):
        tips = jefood.beh(short).get("netease:customtips")
        if short in jefood.CUSTOM_TIPS:
            assert tips and tips["value"], "%s 保留自己的说明" % short
        elif short in jefood.EFFECTS and short not in NO_EFFECT_TOOLTIP:
            assert tips is not None, "%s 有效果但没有提示" % short
            assert tips["value"] == jefood.tooltipOf(jefood.EFFECTS[short]), "%s 的提示和效果不一致: %r" % (short, tips["value"])
        else:
            assert tips is None, "%s 在 JE 里不显示效果提示: %r" % (short, tips)


def testFoodsWithoutJavasEffectTooltipAreJavasOwn():
    if not os.path.isfile(JE_ITEMS):
        print("跳过：没有 JE 的源码（.refs/FarmersDelight）")
        return
    source = io.open(JE_ITEMS, encoding="utf-8").read()
    silent = set()
    for short in jefood.EFFECTS:
        found = re.search(r'register\w*\("%s",\s*\(\) -> new (\w+)\((.*?)\)\);' % short, source, re.S)
        if found is None:
            continue
        kind, body = found.groups()
        args, depth, part = [], 0, ""
        for char in body:                                      # 按最外层的逗号分参数（第二个是 hasFoodEffectTooltip）
            depth += {"(": 1, ")": -1}.get(char, 0)
            if char == "," and depth == 0:
                args.append(part.strip())
                part = ""
            else:
                part += char
        args.append(part.strip())
        if kind == "Item" or (len(args) > 1 and args[1] == "false"):
            silent.add(short)
    assert silent == NO_EFFECT_TOOLTIP, sorted(silent ^ NO_EFFECT_TOOLTIP)


def testPiesSayTheyArePlaceableLikeJava():
    # JE PlaceableItem：一行"可放置"（tooltip.farmersdelight.placeable，深灰、斜体）
    for short in ("apple_pie_item", "sweet_berry_cheesecake_item", "chocolate_pie_item"):
        assert jefood.beh(short)["netease:customtips"]["value"] == "§8§o可放置", short


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
