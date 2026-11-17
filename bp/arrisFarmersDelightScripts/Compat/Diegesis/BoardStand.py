# -*- coding: utf-8 -*-
"""BoardStand - 砧板上立在食物上方的一把工具（刀、斧、镐……）：借来的画成半透明的粒子，拿在手里的是实心的掉落物（客户端）

对应 Hands-On Delight：client/BoardBehavior.java 的 moveKnife / moveTool 给工具节点染色（868、932）：手空着、悬在食物上的是背包里借来的，只是个提议，
染 OFFERED 0x8CFFFFFF（半透明），落下去的那一下（刀的 chopAge、别的工具的 strokeAge 在走）变实；光标栈上拿着的一直是实的。
客户端掉落物染不了色也做不成半透明，所以借来的画成粒子 arris:board_tool（rp/particles/arris_board_tool.json）：一张竖立的四边形（emitter_transform_xy、
particles_blend），贴图是物品图集 atlas.items，这件物品的图标在图集里的位置由 3.10 的 GetIconInfo 给（view.ports.iconUV）、经变量写进发射器，
不透明度、图标在平面里的转角、半边长也是变量；一个发射器只发一颗、活到被删，SetPos / SetRot 每帧挪它，变了的变量才发（和前置包的影子粒子同一个做法）。
怎么摆（SetRot 的偏航、转角的符号）在 Shared/Rules/ParticleQuad。粒子满亮度（没有 lighting 组件），不随环境光变暗。
进世界头几秒图集和粒子系统还没好（iconUV 回 None、Create 回 0）：这一帧先画实心的掉落物，下一帧再试粒子，建出来就换掉它。
"""
from ...Client.Engine import compFactory
from ...Shared.Rules import ParticleQuad
from ...Shared.Rules.HandsOn import BoardScene as Scene

PARTICLE = "arris:board_tool"
HALF = Scene.KNIFE_SCALE * Scene.SPRITE_SPAN / 2.0 / 16.0       # 图标的半边长（格）：画 0.45 个图标大
DIGITS = 6                                                      # 变量比到小数点后几位，没变的不重发


class Stand(object):
    """一把立着的工具。view 是站点视图（要它的 props、ports、toWorld）；show 每帧调一次，remove 收起来。"""

    def __init__(self, view):
        self.view = view
        self.prop = None               # 实心的客户端掉落物
        self.particleId = None         # 半透明的粒子发射器
        self._sent = {}

    def show(self, tool, center, facing, roll, alpha):
        """摆一把工具。center 是图标中心（站点像素），facing 是正面朝哪（站点里的 (dx, dz)），roll 是图标在平面里顺时针转几度（掉落物的 roll）。
        alpha 是 None：实心的掉落物；是 0..1 的数：粒子（1 就是实心）。粒子这一帧画不出来就退回掉落物，下一帧再试。"""
        if alpha is not None and self._particle(tool, center, facing, roll, alpha):
            self._dropProp()
            return
        self._dropParticle()
        self._prop(tool, center, facing, roll)

    def remove(self):
        self._dropProp()
        self._dropParticle()

    # ---------------------------------------------------------------- 掉落物

    def _prop(self, tool, center, facing, roll):
        one = {"newItemName": tool["newItemName"], "newAuxValue": tool.get("newAuxValue") or 0, "count": 1}
        if self.prop is not None and self.prop.item != one:
            self._dropProp()
        if self.prop is None:
            self.prop = self.view.props.item(one, center, flat=False, facing=facing, roll=roll, scale=Scene.KNIFE_SCALE)
        else:
            self.prop.move(center=center, facing=facing, roll=roll)

    def _dropProp(self):
        if self.prop is not None:
            self.view.props.remove(self.prop)
            self.prop = None

    # ---------------------------------------------------------------- 粒子

    def _particle(self, tool, center, facing, roll, alpha):
        uv = self.view.ports.iconUV(tool)
        if uv is None:
            return False
        system, view = compFactory.CreateParticleSystem(None), self.view
        world = view.toWorld(*center)
        if self.particleId is None:
            self.particleId = system.Create(PARTICLE, world) or None       # 建不出来回 0
            if self.particleId is None:
                return False
            self._sent = {}
        ahead = view.toWorld(center[0] + facing[0], center[1], center[2] + facing[1])
        yaw = round(ParticleQuad.uprightYaw(ahead[0] - world[0], ahead[2] - world[2]), 1)
        for name, value in zip(("u", "v", "w", "h"), uv):
            self._send(system, name, value)
        self._send(system, "half", HALF)
        self._send(system, "turn", ParticleQuad.uprightRotation(roll))
        self._send(system, "alpha", alpha)
        system.SetPos(self.particleId, world)
        if self._sent.get("yaw") != yaw:
            self._sent["yaw"] = yaw
            system.SetRot(self.particleId, (0.0, yaw, 0.0))
        return True

    def _send(self, system, name, value):
        value = round(float(value), DIGITS)
        if self._sent.get(name) != value:
            self._sent[name] = value
            system.SetVariable(self.particleId, "variable." + name, value)

    def _dropParticle(self):
        if self.particleId is not None:
            compFactory.CreateParticleSystem(None).Remove(self.particleId)
            self.particleId = None
            self._sent = {}
