# -*- coding: utf-8 -*-
"""BoardThing - 砧板站点里画出来的一样东西：Mover 管位置、缩放和转角，客户端道具跟着（客户端）

从 BoardDraw.py 拆出来。位置是离板面中心的偏移 (x, 离板面的高, z)；y 是它底边的高，立着的中心在底边上半个高；
平躺的贴图中心离它躺着的面 FLAT_LIFT。看得见才有道具，看不见就删。
平躺的东西按姿态矩阵摆（和炉灶的烤件一样：JE 节点的欧拉角 Ry * Rx * Rz 作用在一张躺平的贴图上，ItemPose.lyingMatrix）：没转过就是 turn 度的偏转，
收尾动画（BoardFinishPlay）让层翻、立、滚时转角由 Mover 给。
"""
import math
import random

from ...Shared.Rules import BoardStation as Rules
from ...Shared.Rules import ItemPose
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
        """直接摆到偏移 (x, y, z)，缩放回到 1、转角回到没转过（不走动画）。"""
        self.mover.move(x, y, z)
        self.mover.scaleTo(1.0)
        self.mover.unturn()
        self.mover.visible = visible
        self.dirty = True

    def moveTo(self, x, y, z, seconds=0.0, hop=0.0):
        """从现在的位置走到偏移 (x, y, z)（Mover.move：seconds 是 0 就是跳过去，hop 是中途的弧高）；收尾动画一条条排进来用。"""
        self.mover.move(x, y, z, seconds, hop)
        self.dirty = True

    def scaleTo(self, factor, seconds=0.0):
        self.mover.scaleTo(factor, seconds)
        self.dirty = True

    def rotateTo(self, x, y, z, seconds=0.0):
        """转到 (x, y, z) 度（JE 节点的欧拉角，Mover.rotateTo）。没转过的先从摆着的样子起（Ry(-turn)：和 frame 里没转过时画的是同一个朝向，不跳一下）。"""
        if self.mover.rotation is None:
            self.mover.rotateTo(0.0, -self.turn, 0.0)
        self.mover.rotateTo(x, y, z, seconds)
        self.dirty = True

    def show(self, visible=True):
        self.mover.visible = bool(visible)
        self.dirty = True

    def hide(self):
        self.show(False)

    def reset(self):
        """收起来，缩放和转角也还原（JE 的 tick 里层沉完：scaleTo(1, 0) + setVisible(false)）：下一回这一格再摆东西不会还是缩着、转着的。"""
        self.mover.scaleTo(1.0)
        self.mover.unturn()
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
            lift = Scene.blockLift(scale, self.draw.span)         # 方块类：立方体，轴心的规矩和贴图物品不一样
        else:
            lift = Scene.uprightLift(scale) if upright else Scene.FLAT_LIFT * self.mover.scale
        center = (self.draw.cx + x, Scene.TOP + y + lift, self.draw.cz + z)
        if upright:
            along = (math.cos(math.radians(self.turn)), math.sin(math.radians(self.turn)))
            if self.prop is None:
                self.prop = self.draw.view.props.item(self.item, center, flat=False, along=along, facing=self.facing, roll=self.roll, scale=scale)
            else:
                self.prop.move(center=center, along=along, facing=self.facing, roll=self.roll, scale=scale)
            return
        rx, ry, rz = self.mover.rotation if self.mover.rotation is not None else (0.0, -self.turn, 0.0)
        matrix = ItemPose.lyingMatrix(ry, rx, rz)
        if self.draw.isRaised(self.item):                 # 花、野生作物：引擎照方块物品的规矩抬高着画，摆之前扣掉
            center = tuple(a + b for a, b in zip(center, ItemPose.raisedShift(matrix, scale)))
        if self.prop is None:
            self.prop = self.draw.view.props.item(Rules.shownItem(self.item), center, flat=True, scale=scale, matrix=matrix)       # 蘑菇丛画成它的平面物品
        else:
            self.prop.move(center=center, scale=scale, matrix=matrix)
