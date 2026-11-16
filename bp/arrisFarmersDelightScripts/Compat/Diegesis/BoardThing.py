# -*- coding: utf-8 -*-
"""BoardThing - 砧板站点里画出来的一样东西：Mover 管位置和缩放，客户端道具跟着（客户端）

从 BoardDraw.py 拆出来。位置是离板面中心的偏移 (x, 离板面的高, z)；y 是它底边的高，立着的中心在底边上半个高；
平躺的贴图中心离它躺着的面 FLAT_LIFT。看得见才有道具，看不见就删。
"""
import math

from ...Shared.Rules.HandsOn import BoardMotion as Motion
from ...Shared.Rules.HandsOn import BoardScene as Scene

FLAT, UPRIGHT = "flat", "upright"


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
        self.prop = None
        self.dirty = True

    def set(self, item, kind=FLAT, scale=None, turn=0.0):
        """换成 item（只留名字和 aux）。位置、缩放另外用 mover 摆。"""
        one = _one(item)
        if self.item != one or self.kind != kind:
            self.drop()
            self.item, self.kind = one, kind
        self.size = scale if scale is not None else self.size
        self.turn = turn
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

    def drop(self):
        if self.prop is not None:
            self.draw.view.props.remove(self.prop)
            self.prop = None

    def frame(self, dt):
        if self.mover.busy:
            self.mover.update(dt)
            self.dirty = True
        if not self.dirty:
            return
        self.dirty = False
        if not self.mover.visible or self.item is None or self.mover.scale <= 0.02:
            self.drop()
            return
        x, y, z = self.mover.pos
        scale = self.size * self.mover.scale
        upright = self.kind == UPRIGHT
        center = (self.draw.cx + x, Scene.TOP + y + (Scene.uprightLift(scale) if upright else Scene.FLAT_LIFT * self.mover.scale),
                  self.draw.cz + z)
        along = (math.cos(math.radians(self.turn)), math.sin(math.radians(self.turn)))
        if self.prop is None:
            self.prop = self.draw.view.props.item(self.item, center, flat=not upright, along=along, facing=(0.0, -1.0),
                                                  roll=Scene.KNIFE_ROLL if self.draw.rolled(self.item, upright) else 0.0, scale=scale)
        else:
            self.prop.move(center=center, along=along, scale=scale)
