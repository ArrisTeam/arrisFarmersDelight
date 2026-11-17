# -*- coding: utf-8 -*-
"""BoardThing - 砧板站点里画出来的一样东西：Mover 管位置和缩放，客户端道具跟着（客户端）

从 BoardDraw.py 拆出来。位置是离板面中心的偏移 (x, 离板面的高, z)；y 是它底边的高，立着的中心在底边上半个高；
平躺的贴图中心离它躺着的面 FLAT_LIFT。看得见才有道具，看不见就删。
"""
import math
import random

from ...Shared.Rules.HandsOn import BoardMotion as Motion
from ...Shared.Rules.HandsOn import BoardScene as Scene

FLAT, UPRIGHT = "flat", "upright"
TO_CAMERA = (0.0, -1.0)            # 立着的东西缺省正面朝镜头（站点里玩家在北面，镜头在 -z）


def _one(item):
    return {"newItemName": item["newItemName"], "newAuxValue": item.get("newAuxValue") or 0, "count": 1}


class Thing(object):
    """一样画出来的东西：Mover（偏移、缩放、看得见不）+ 一个客户端道具（看得见才有）。y 是它底边离板面的高；立着的中心在底边上半个高。"""

    def __init__(self, draw):
        self.draw = draw
        self.mover = Motion.Mover(visible=False)
        self.item = None
        self.kind = FLAT
        self.size = Scene.itemScale()
        self.turn = 0.0
        self.facing = TO_CAMERA              # 立着的：贴图的正面朝哪（站点方向 x, z）
        self.roll = 0.0                      # 立着的：在贴图平面里顺时针转多少度
        self.prop = None
        self.dirty = True
        self.shaking = None                  # [幅度, 总时间, 剩下的时间]：抖一下（shake）
        self.offset = (0.0, 0.0, 0.0)        # 抖动现在的偏移
        self.rng = random.random

    def shake(self, pixels=Motion.SHAKE_PIXELS, seconds=Motion.SHAKE_SECONDS):
        """抖一下：每帧在 ±幅度里随机偏一点，幅度线性变小（NodeInstance.shake）。"""
        self.shaking = [max(0.0, pixels), max(0.01, seconds), max(0.01, seconds)]

    def set(self, item, kind=FLAT, scale=None, turn=0.0, facing=TO_CAMERA, roll=0.0):
        """换成 item（只留名字和 aux）。位置、缩放另外用 mover 摆。facing / roll 只有立着的用：插着的工具朝着板的背面、按类型转角度（Draw.carved）。"""
        one = _one(item)
        if self.item != one or self.kind != kind:
            self.drop()
            self.item, self.kind = one, kind
        self.size = scale if scale is not None else self.size
        self.turn = turn
        self.facing, self.roll = facing, roll
        self.dirty = True

    def blank(self):
        """这一层什么也不画（倒进去的液体：容器倒完就走了，BoardHands.lookOf 是 None）。"""
        self.drop()
        self.item = None
        self.mover.visible = False
        self.dirty = True

    def put(self, x, y, z, visible=True):
        """直接摆到偏移 (x, y, z)，缩放回到 1（不走动画）。"""
        self.mover.move(x, y, z)
        self.mover.scaleTo(1.0)
        self.mover.visible = visible
        self.dirty = True

    def hide(self):
        self.mover.visible = False
        self.dirty = True

    def reset(self):
        """收起来，缩放也还原（JE 的 tick 里层沉完：scaleTo(1, 0) + setVisible(false)）：下一回这一格再摆东西不会还是缩着的。"""
        self.mover.scaleTo(1.0)
        self.hide()

    def drop(self):
        if self.prop is not None:
            self.draw.view.props.remove(self.prop)
            self.prop = None

    def frame(self, dt):
        if self.mover.busy:
            self.mover.update(dt)
            self.dirty = True
        if self.shaking is not None:
            self.shaking[2] = max(0.0, self.shaking[2] - dt)
            self.offset = Motion.shakeOffset(self.shaking[0], self.shaking[1], self.shaking[2], self.rng)
            self.dirty = True
            if self.shaking[2] <= 0.0:
                self.shaking = None
        if not self.dirty:
            return
        self.dirty = False
        if not self.mover.visible or self.item is None or self.mover.scale <= 0.02:
            self.drop()
            return
        x, y, z = (a + b for a, b in zip(self.mover.pos, self.offset))
        scale = self.size * self.mover.scale
        upright = self.kind == UPRIGHT
        if upright and self.draw.isBlock(self.item):
            lift = Scene.blockLift(scale)                 # 方块类：立方体，轴心的规矩和贴图物品不一样
        else:
            lift = Scene.uprightLift(scale) if upright else Scene.FLAT_LIFT * self.mover.scale
        center = (self.draw.cx + x, Scene.TOP + y + lift, self.draw.cz + z)
        along = (math.cos(math.radians(self.turn)), math.sin(math.radians(self.turn)))
        if self.prop is None:
            self.prop = self.draw.view.props.item(self.item, center, flat=not upright, along=along, facing=self.facing, roll=self.roll, scale=scale)
        else:
            self.prop.move(center=center, along=along, facing=self.facing, roll=self.roll, scale=scale)
