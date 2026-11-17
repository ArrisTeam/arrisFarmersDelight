# -*- coding: utf-8 -*-
"""BoardFinishPlace - 串、摆、夹、成形、冻：一片片放到底座上的五种收尾（双端，纯规则）

移植自 Hands-On Delight 的 client/BoardBehavior.java：skewer（1722-1755）、arrange（1798-1821）、sandwich（1827-1860）、shape（1866-1898）、freeze（1904-1931）。
和 BoardFinishGroup 一样往一份 Plan 里排动作（位置是离板面中心的偏移 (x, 离板面的高, z)，角度是 JE 节点的欧拉角，时刻从收尾开始算）。
串 / 冻沿着签子放、成形沿着米饭的长边放：JE 读底座图标的轴（ItemVoxels.Icon.axis，这里是 BoardIcon 的同一个算法）；基岩版摆盘表里这三种菜的底座只有签子和做熟的米饭，
它们的图标在 Shared/Data/ItemMasks（tools/gen_item_masks.py 的 FINISH_BASES），所以轴就按这两件算。
"""
import math

from .. import BoardSounds as Sounds
from .BoardFinishKit import (ARRANGE_RING, ARRANGE_SCALE, ARRANGE_SLIDE, ARRANGE_STAGGER, FREEZE_AT, FREEZE_GATHER, FREEZE_SET, FROST, ICES, LAYER_STEP,
                             LID, LID_CLOSE, LID_HEIGHT, LID_LIFT, LID_PRESS, MELT_TIME, SHAPE_GATHER, SHAPE_LAY, SHAPE_PRESS, SKEWER_FIRST, SKEWER_LAST,
                             SKEWER_PUSH, SKEWER_SCALE, SKEWER_SLIDE, SKEWER_STAGGER, SKEWER_STAND)
from .BoardIcon import ITEM_SIZE, iconOf
from .BoardMotion import layerJitter, layerTurn
from .BoardScene import TOP

STICK, RICE = "minecraft:stick", "arris:cooked_rice"
LID_START = 0.15           # 夹：JE 的下半和上半合成一整块面包躺在板面上；掉落物切不开，盖子是同一块面包的又一份，起点比底座高一点，免得两张一样的图贴在同一个面上闪
SHAPE_DIP = -0.25          # :1894 成形最后压一下：各层往下沉 0.25 再回来（hopTo 的高度是负的）


def skewer(plan, count):
    """串：一片接一片地先滑到签子尖、立起来（-60 度，脸朝柄也就是朝镜头）、缩到 0.7，再一起往柄推；先上去的推得最远，最后一片留在尖附近。"""
    stick = iconOf(STICK).axis(ITEM_SIZE)
    pieces = max(1, count - 1)
    baseX, baseZ = layerJitter(0)
    tip = stick.at(0.0)
    stand = math.degrees(math.atan2(stick.dirX, stick.dirZ))
    for index in range(1, count):
        share = (SKEWER_FIRST + SKEWER_LAST) / 2.0 if pieces == 1 else SKEWER_LAST - (SKEWER_LAST - SKEWER_FIRST) * (index - 1) / (pieces - 1.0)
        spot = stick.at(share)
        plan.rest[index] = (baseX + spot[0], LAYER_STEP, baseZ + spot[1])
        start = (index - 1) * SKEWER_STAGGER
        plan.move(start, index, (baseX + tip[0], LAYER_STEP, baseZ + tip[1]), SKEWER_SLIDE)
        plan.rotate(start, index, (SKEWER_STAND, stand, 0.0), SKEWER_SLIDE)
        plan.scale(start, index, SKEWER_SCALE, SKEWER_SLIDE)
        plan.sound(start + SKEWER_SLIDE * 0.8, (Sounds.BOARD_PLACE, 0.3, 1.4 + 0.06 * index))
    push = SKEWER_SLIDE + (count - 1) * SKEWER_STAGGER
    for index in range(1, count):
        plan.move(push, index, plan.rest[index], SKEWER_PUSH)
    plan.sound(push, (Sounds.WOOD_HIT, 0.25, 1.6))


def arrange(plan, count):
    """摆：主料（第 1 层）滑到碗中央，其余依次（隔 0.08 秒）滑到绕它半径 2.4 的一圈上、缩到 0.8；不飞，每片落位响一声。"""
    sides = max(1, count - 2)
    centerX, centerZ = layerJitter(0)
    for index in range(1, count):
        x, z = centerX, centerZ
        if index > 1:
            around = 2.0 * math.pi * (index - 2) / sides + 0.6
            x, z = x + math.cos(around) * ARRANGE_RING, z + math.sin(around) * ARRANGE_RING
        plan.rest[index] = (x, LAYER_STEP, z)
        start = max(0, index - 2) * ARRANGE_STAGGER
        plan.move(start, index, plan.rest[index], ARRANGE_SLIDE)
        plan.scale(start, index, 1.0 if index == 1 else ARRANGE_SCALE, ARRANGE_SLIDE)
        plan.rotate(start, index, (0.0, layerTurn(index) * 0.5, 0.0), ARRANGE_SLIDE)
        plan.sound(start + ARRANGE_SLIDE * 0.8, (Sounds.BOARD_PLACE, 0.3, 1.25 + 0.05 * index))


def sandwich(plan, count):
    """夹：面包的上半（盖子）抬起 3 像素、移到馅上合住、压一下（先下沉 0.3 再回），然后随各层融掉；合上那一刻一声。
    JE 把面包沿长边劈成上下两半（Icon.half），下半留在底座、上半是盖子；掉落物切不开，所以底座和盖子都是整块面包（盖子起点见 LID_START）。"""
    x, z = layerJitter(0)
    over = count * LAYER_STEP
    close = LID_LIFT + LID_CLOSE
    plan.lid = True
    plan.move(0.0, LID, (x, LID_START, z))
    plan.move(0.0, LID, (x, over + LID_HEIGHT, z), LID_LIFT)
    plan.move(LID_LIFT, LID, (x, over, z), LID_CLOSE)
    plan.sound(close, (Sounds.BOARD_PLACE, 0.6, 0.9))
    plan.move(close, LID, (x, over - 0.3, z), LID_PRESS / 2.0)
    plan.move(close + LID_PRESS / 2.0, LID, (x, over, z), LID_PRESS / 2.0)
    plan.scale(close + LID_PRESS, LID, 0.1, MELT_TIME)                                   # 随各层融掉（和 pop 里各层同一个走法）
    plan.move(close + LID_PRESS, LID, (x * 0.4, over * 0.08, z * 0.4), MELT_TIME)
    plan.show(close + LID_PRESS + MELT_TIME, LID, False)


def shape(plan, count):
    """成形（握寿司）：米饭压成块（缩到 0.8、跳 0.3）；片一片片沿米饭的长边放上去（每片转到沿着它再加 45 度）；最后各层一起往下压一下。"""
    rice = iconOf(RICE).axis(ITEM_SIZE)
    along = math.degrees(-rice.along())
    x0, z0 = layerJitter(0)
    plan.scale(0.0, 0, 0.8, SHAPE_GATHER)
    plan.move(0.0, 0, (x0, 0.0, z0), SHAPE_GATHER, 0.3)
    plan.sound(0.0, (Sounds.WOOL_STEP, 0.35, 1.1))
    for index in range(1, count):
        shift = (index - (count - 1) / 2.0 - 0.5) * 0.8
        plan.rest[index] = (x0 + rice.dirX * shift, LAYER_STEP * 0.8 + (index - 1) * 0.15, z0 + rice.dirZ * shift)
        start = SHAPE_GATHER + (index - 1) * SHAPE_LAY
        plan.move(start, index, plan.rest[index], SHAPE_LAY)
        plan.rotate(start, index, (0.0, along + 45.0, 0.0), SHAPE_LAY)
        plan.sound(start, (Sounds.BOARD_PLACE, 0.3, 1.3 + 0.05 * index))
    plan.rest[0] = (x0, 0.0, z0)
    press = SHAPE_GATHER + max(1, count - 1) * SHAPE_LAY
    for index in range(count):
        plan.move(press, index, plan.rest[index], SHAPE_PRESS, SHAPE_DIP)
    plan.sound(press, (Sounds.WOOL_STEP, 0.4, 0.9))


def freeze(plan, count, names):
    """冻（冰棒）：水果聚到签子顶一团（缩到 0.75），冰缩没；聚好那一刻冒一阵霜、一点霜色的闪光，响一声玻璃碎。names 是各层的物品名（认冰）。
    JE 这时还把各层染成霜色（setTint(FROST)），掉落物染不了色，没有这一步。"""
    stick = iconOf(STICK).axis(ITEM_SIZE)
    top = stick.at(FREEZE_AT)
    x0, z0 = layerJitter(0)
    x, z = x0 + top[0], z0 + top[1]
    for index in range(1, count):
        ice = names[index] in ICES
        plan.rest[index] = (x + ((index * 37) % 5 - 2) * 0.35, LAYER_STEP + index * 0.12, z + ((index * 53) % 5 - 2) * 0.35)
        plan.move(0.0, index, plan.rest[index], FREEZE_GATHER)
        plan.scale(0.0, index, 0.0 if ice else 0.75, FREEZE_GATHER + FREEZE_SET * 0.5 if ice else FREEZE_GATHER)
    at = (x, TOP + LAYER_STEP * 2.0, z)
    plan.dust(FREEZE_GATHER, (at, (0.0, 1.5, 0.0), 1.8, 10), FROST)
    plan.glint(FREEZE_GATHER, at, FROST, 4)
    plan.sound(FREEZE_GATHER, (Sounds.GLASS_BREAK, 0.2, 1.8))
