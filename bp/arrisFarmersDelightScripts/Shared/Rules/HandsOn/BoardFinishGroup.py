# -*- coding: utf-8 -*-
"""BoardFinishGroup - 拌、卷、揉、一起切：各层一起动的四种收尾（双端，纯规则）

移植自 Hands-On Delight 的 client/BoardBehavior.java：toss（1657-1681）、roll（1687-1715）、knead（1760-1792）、chopTogether（1937-1961）。
每个函数往一份 Plan（BoardFinishKit）里排动作：位置是离板面中心的偏移 (x, 离板面的高, z)，JE 的 moveTo(x, y - index * LAYER_STEP, z) 是从层自己的高度算起，
这里直接写离板面的高；角度是 JE 节点的欧拉角。动作和声音的时刻从收尾开始算。
"""
from .. import BoardSounds as Sounds
from .BoardFinishKit import (CHOP_PART, CHOP_STROKE, CHOPS, KNEAD_PRESS, KNEAD_PUSH, KNEAD_PUSHES, KNEAD_SPREAD, KNEAD_TURN, LAYER_STEP, ROLL_GATHER,
                             ROLL_STROKE, ROLL_TRAVEL, ROLL_TURN, ROLLS, TOSS_HEIGHT, TOSS_JERK, TOSS_JERK_TIME, TOSS_TILT, TOSS_TIME, TOSS_TUMBLE)
from .BoardMotion import layerJitter, layerTurn
from .BoardScene import TOP


def toss(plan, count):
    """拌：碗向上一颠、后仰一下；碗里的料各飞各的高、翻着跟头，倒着次序落回（最上面的落最低），每片落定响一声，开头一声皮革响。"""
    plan.move(0.0, 0, (layerJitter(0)[0], 0.0, layerJitter(0)[1]), TOSS_JERK_TIME, TOSS_JERK)
    plan.rotate(0.0, 0, (-TOSS_TILT, 0.0, 0.0), TOSS_JERK_TIME / 2.0)
    plan.rotate(TOSS_JERK_TIME / 2.0, 0, (0.0, 0.0, 0.0), TOSS_JERK_TIME / 2.0)
    for index in range(1, count):
        lands = count - index                                  # 倒着次序落回：最上面的落最低、最下面的落最高
        x, z = layerJitter(lands)
        plan.rest[index] = (x, lands * LAYER_STEP, z)
        side = 1.0 if index % 2 == 0 else -1.0
        spin = layerTurn(lands) + side * (120.0 + (index * 53 % 80))       # 翻滚着、从不翻到背面：一片是从图标的正面造的，没有背面
        plan.move(0.0, index, plan.rest[index], TOSS_TIME, TOSS_HEIGHT + (index * 37 % 5) * 0.6)
        plan.rotate(0.0, index, (side * TOSS_TUMBLE, (layerTurn(index) + spin) / 2.0, -side * TOSS_TUMBLE * 0.6), TOSS_TIME / 2.0)
        plan.rotate(TOSS_TIME / 2.0, index, (0.0, spin, 0.0), TOSS_TIME / 2.0)
        plan.sound(TOSS_TIME - 0.02 * index, (Sounds.BOARD_PLACE, 0.3, 1.3 + 0.05 * index))
    plan.sound(0.0, (Sounds.ARMOR_EQUIP_LEATHER, 0.5, 1.4))


def roll(plan, count):
    """卷：各层先合拢成一根，再来回滚三趟、最后回正（每趟位移和转角都比上一趟小），前三趟各响一声（一声比一声高）。"""
    for index in range(count):
        plan.rest[index] = (0.0, index * LAYER_STEP * 0.6, 0.0)
        plan.move(0.0, index, plan.rest[index], ROLL_GATHER)
        plan.rotate(0.0, index, (0.0, layerTurn(index) * 0.3, 0.0), ROLL_GATHER)
    for stroke in range(ROLLS + 1):
        amount = 0.0 if stroke == ROLLS else (1.0 if stroke % 2 == 0 else -1.0) * (ROLLS - stroke) / float(ROLLS)
        at = ROLL_GATHER + stroke * ROLL_STROKE
        for index in range(count):
            plan.move(at, index, (0.0, plan.rest[index][1], amount * ROLL_TRAVEL), ROLL_STROKE)
            plan.rotate(at, index, (amount * ROLL_TURN, layerTurn(index) * 0.3, 0.0), ROLL_STROKE)
        if stroke < ROLLS:
            plan.sound(at, (Sounds.WOOL_STEP, 0.3, 1.2 + 0.1 * stroke))


def knead(plan, count):
    """揉：压成一坨（高度缩到 0.35），再推平三次（各层各向两边摊、扭一扭）又合拢；开头一声，每次推平一声。"""
    for index in range(count):
        x, z = layerJitter(index)
        plan.rest[index] = (x * 0.5, index * LAYER_STEP * 0.35, z * 0.5)
        plan.move(0.0, index, plan.rest[index], KNEAD_PRESS)
    plan.sound(0.0, (Sounds.BOARD_PLACE, 0.5, 0.7))
    for push in range(KNEAD_PUSHES):
        twist = (1.0 if push % 2 == 0 else -1.0) * KNEAD_TURN
        at = KNEAD_PRESS + push * KNEAD_PUSH * 2.0
        for index in range(count):
            out = (1.0 if index % 2 == 0 else -1.0) * KNEAD_SPREAD
            x, y, z = plan.rest[index]
            plan.move(at, index, (x + out, 0.0, z + out * 0.6), KNEAD_PUSH)            # 推平：压到板面上
            plan.rotate(at, index, (0.0, layerTurn(index) + twist, 0.0), KNEAD_PUSH * 2.0)
            plan.move(at + KNEAD_PUSH, index, (x, y, z), KNEAD_PUSH)
        plan.sound(at, (Sounds.WOOL_STEP, 0.45, 0.75))


def chop(plan, count, color):
    """一起切开（Culinary Compat 在板上的做法）：刀过两次，每次各层交替往两边错开再回来；每刀一阵碎屑（最上面一层的颜色 color）和一声刀声。
    刀声的音调 0.95 + 0.15 * 随机，随机由 plan.rng 给。"""
    at = (0.0, TOP + count * LAYER_STEP + 0.5, 0.0)
    for stroke in range(CHOPS):
        side = 1.0 if stroke % 2 == 0 else -1.0
        start = stroke * CHOP_STROKE
        for index in range(count):
            x, y, z = plan.rest[index]
            out = (side if index % 2 == 0 else -side) * CHOP_PART
            plan.move(start, index, (x + out, y, z), CHOP_STROKE * 0.4)
            plan.move(start + CHOP_STROKE * 0.5, index, (x, y, z), CHOP_STROKE * 0.5)
        plan.dust(start, (at, (0.0, 4.0, 0.0), 1.2, 5), color)
        plan.sound(start, (Sounds.KNIFE_CUT, 0.8, 0.95 + 0.15 * plan.rng()))
