# -*- coding: utf-8 -*-
"""Eating - 吃一份食物的饥饿值与饱和度结算（双端，纯规则）

照 Java 版 FoodData.eat：饥饿值 + 营养值（最多 20）；饱和度 + 营养值 × 饱和度修饰 × 2，不超过当时的饥饿值。
基岩版的 saturation_modifier 同一个意思（poor 0.1、low 0.3、normal 0.6、good 0.8、max 1.0）。
"""
MAX_HUNGER = 20
# AttrType.SATURATION（ModAPI 的属性枚举值）
SATURATION = 5


def eatenFood(hunger, saturation, nutrition, saturationModifier):
    """吃一份营养值 nutrition、饱和度修饰 saturationModifier 的食物 -> (新的饥饿值, 新的饱和度)。"""
    newHunger = min(MAX_HUNGER, hunger + nutrition)
    newSaturation = min(newHunger, saturation + nutrition * saturationModifier * 2)
    return newHunger, newSaturation
