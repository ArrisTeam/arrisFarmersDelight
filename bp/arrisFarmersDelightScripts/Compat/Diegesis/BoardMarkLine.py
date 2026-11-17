# -*- coding: utf-8 -*-
"""BoardMarkLine - 砧板上下一刀的虚线：一段一颗粒子，白混凝土、半透明、新的一条渐显（客户端）

对应 Hands-On Delight：client/BoardBehavior.java 的 drawMarks（1142-1194）、fade（1206-1208）。HoD 把虚线画成一段一段的小长方形（半宽 MARK_WIDTH 0.16、
每段 DASH 0.6、隔 DASH_GAP 0.45），贴图是白混凝土、满亮度，染 MARK_COLOR 0xA0FFFFFF（不透明度 0xA0），新的一条用 MARK_FADE 0.18 秒从 0 渐显。
客户端掉落物染不了色也做不成半透明，所以每一段是一颗粒子 arris:board_mark（rp/particles/arris_board_mark.json：平躺的四边形 emitter_transform_xz、
particles_blend、贴图是 JE 那张白混凝土，没有 lighting 组件 = 满亮度）；一个发射器只发一颗、活到被删；一条线的所有段同一个朝向、同一个不透明度（变量 alpha 逐帧写）。
数（每段长、宽、不透明度、渐显）在 Shared/Rules/HandsOn/BoardDashes，粒子怎么摆（SetRot 的偏航）在 Shared/Rules/ParticleQuad。
进世界头几秒粒子系统还没好（Create 回 0）：这一帧先用前置包的掉落物虚线（不透明、没有渐显），下一帧再试粒子，建出来就换掉它。
"""
from ...Client.Engine import compFactory
from ...Shared.Rules import ParticleQuad
from ...Shared.Rules.HandsOn import BoardDashes as Dashes

MARK = "arris:board_mark"
PIXEL = 1.0 / 16.0
MARK_LIFT = 0.25       # 虚线画在食物顶面上方这么高（像素）：实机上平躺的掉落物顶面比算出来的高 0.15 左右，贴着面的零厚度四边形会陷进食物里（JE 是 +0.03，见 drawMarks 1177）


class MarkLine(object):
    """一条虚线。a、b 是两端（站点像素 x, z），surface 是食物顶面离站点地面多高，key 是这一条的身份（换了就该重画）。
    建出来这一帧还看不见（JE：换了一条的那一帧 markFade = 0），之后每帧调一次 frame 推进渐显。"""

    def __init__(self, view, key, a, b, surface):
        self.view, self.key = view, key
        height = surface + MARK_LIFT
        self.a, self.b = (a[0], height, a[1]), (b[0], height, b[1])
        self.ids = []                  # 每一段的发射器编号
        self.fallback = None           # 粒子建不出来时的掉落物虚线（前置包的 props.line）
        self.age, self.alpha = 0.0, 0.0
        self.frame(0.0)

    def frame(self, dt):
        """渐显推进 dt 秒；粒子还没建好就（再）试，建不出来这一帧先用掉落物的虚线。"""
        if not self.ids:
            self.ids = self._create()
            if not self.ids:
                if self.fallback is None:
                    self.fallback = self.view.props.line(self.a, self.b, hot=False)
                return
            self._dropFallback()
        self.age += dt
        alpha = Dashes.markAlpha(self.age)
        if alpha != self.alpha:
            self.alpha = alpha
            system = compFactory.CreateParticleSystem(None)
            for particleId in self.ids:
                system.SetVariable(particleId, "variable.alpha", alpha)

    def _create(self):
        """每一段一颗粒子：平躺、长的那条边顺着线，一颗也不能少（建不出来就全不要，返回 []）。"""
        view, system = self.view, compFactory.CreateParticleSystem(None)
        start, end = view.toWorld(*self.a), view.toWorld(*self.b)
        yaw = ParticleQuad.flatYaw(end[0] - start[0], end[2] - start[2])
        ids = []
        for middle, half in Dashes.layout((self.a[0], self.a[2]), (self.b[0], self.b[2])):
            particleId = system.Create(MARK, view.toWorld(middle[0], self.a[1], middle[1]))
            if not particleId:                        # 回 0（不是 None）：不能当编号去设变量
                for made in ids:
                    system.Remove(made)
                return []
            system.SetRot(particleId, (0.0, yaw, 0.0))
            system.SetVariable(particleId, "variable.half_wide", Dashes.MARK_WIDTH * PIXEL)
            system.SetVariable(particleId, "variable.half_len", half * PIXEL)
            ids.append(particleId)
        return ids

    def _dropFallback(self):
        if self.fallback is not None:
            self.view.props.remove(self.fallback)
            self.fallback = None

    def remove(self):
        system = compFactory.CreateParticleSystem(None)
        for particleId in self.ids:
            system.Remove(particleId)
        self.ids = []
        self._dropFallback()
