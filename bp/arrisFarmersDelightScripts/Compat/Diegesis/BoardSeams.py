# -*- coding: utf-8 -*-
"""BoardSeams - 砧板上切过的那几刀留下的缝：每刀一条暗色半透明的细条，跟着新的一刀一起张开（客户端）

对应 Hands-On Delight：client/BoardBehavior.java 的 cutsMade（729-737）、refresh 里的 gap = 0 / opening（412-416）、frame 里的张开（790-793），
和 client/ItemVoxels.java 的 build（305-345）：图标的每个像素沿每一刀的法线往两边各挪 gap / 2，两半之间露出 gap 宽的缝（GAP 0.8 像素，GAP_TIME 0.12 秒张开）。
基岩版板上的东西是客户端掉落物，切不开，所以原来每一刀只有落刀、声音、碎屑和下一条虚线，看不出切到哪了。这里在每条切过的线上、食物顶面上方
画一条 gap 宽的黑色半透明细条（粒子 arris:board_seam，平躺的四边形，一条缝一颗），只画在图标的实心像素那一段（和虚线同一个 solidSpan）。
- 已经切了几刀：服务端说的加上本地刚落、还没回话的（JE 的 pendingChops）；
- 同一件东西又多切了一刀：所有的缝从 0 重新张开（JE 的 gap 只有一个数，build 时每一刀都用它）；
- 开站时板上已经切过几刀的、等着回话的那几刀作废了：直接是张开的（JE 只有刀数变多才从 0 起）；
- 方块类（原木这些：JE 里不是体素图标，没有缝）、插着的工具、摆着层的板、不用切的东西：不画。
和 JE 不一样的：食物的两半并不真的挪开（宽出 0.8 像素），缝里看到的不是板和切面、是压暗的食物；只有开着站点的人看得到。
进世界头几秒粒子系统还没好（Create 回 0）：这一帧不画，下一帧再试。
"""
import math

from ...Client.Engine import compFactory
from ...Shared.Rules import ParticleQuad
from ...Shared.Rules.HandsOn import BoardDashes as Dashes
from ...Shared.Rules.HandsOn import BoardMarks as Marks

SEAM = "arris:board_seam"
PIXEL = 1.0 / 16.0
SEAM_LIFT = 0.4        # 缝画在食物顶面上方这么高（像素）：实机量过零厚度的四边形从 +0.35 起才露出来（BoardMarkLine.MARK_LIFT 的说明），比虚线的 0.45 低一点——
#                        楔形的几刀都过中心，同一个高度上两片半透明的四边形叠在一起会闪


class Seams(object):
    def __init__(self, owner):
        self.owner = owner              # BoardViewMixin：要它的 view、draw、cutter、board()、layers()
        self.key = None                 # 画着的是什么：(这件食物和它的摆法, 切了几刀)；没有要切的平躺食物是 None
        self.strips = []                # 每条缝两端的世界坐标 [(a, b), ...]
        self.ids = []                   # 每条缝的发射器编号（和 strips 一一对应；还没建出来是空的）
        self.gap = Dashes.GAP           # 缝现在多宽（像素）
        self.wide = None                # 上次写给粒子的半宽

    def _key(self):
        owner = self.owner
        board, data, draw = owner.board(), owner.view.data, owner.draw
        plan = int(data.get("plan") or 0)
        if board is None or owner.layers() or plan <= 0 or draw.kindOf(board) != "flat":
            return None
        what = (board["newItemName"], plan, data.get("style"), tuple(data.get("spots") or ()), tuple(data.get("angles") or ()),
                round(draw.surface(), 3), round(draw.cx, 3), round(draw.cz, 3))
        return (what, min(plan, int(data.get("marks") or 0) + owner.cutter.pending.count))

    def _strips(self, made):
        """切过的每一刀在世界里从哪到哪；线上一个实心像素都没有的那一刀没有缝。"""
        owner = self.owner
        board, data, draw, view = owner.board(), owner.view.data, owner.draw, owner.view
        icon = Marks.iconOf(board["newItemName"])
        height = draw.surface() + SEAM_LIFT
        out = []
        for cut in Marks.cutsMade(Marks.axisOf(icon), data.get("style"), data.get("spots") or [], data.get("angles") or [], made, int(data["plan"])):
            ends = Marks.ends(cut, icon)
            if ends is not None:
                out.append(tuple(view.toWorld(draw.cx + x, height, draw.cz + z) for x, z in ends))
        return out

    def frame(self, dt):
        """每帧：板上的东西或切过的刀数变了就重画，张开中的缝接着张开。"""
        key = self._key()
        if key != self.key:
            more = key is not None and self.key is not None and key[0] == self.key[0] and key[1] > self.key[1]
            self._drop()
            self.key = key
            self.gap = 0.0 if more else Dashes.GAP
            self.strips = self._strips(key[1]) if key is not None else []
        elif self.gap < Dashes.GAP:
            self.gap = Dashes.gapAfter(self.gap, dt)
        if not self.strips:
            return
        system = compFactory.CreateParticleSystem(None)
        if not self.ids:
            self.ids = self._create(system)
            if not self.ids:
                return
        half = self.gap / 2.0 * PIXEL
        if half != self.wide:
            self.wide = half
            for particleId in self.ids:
                system.SetVariable(particleId, "variable.half_wide", half)

    def _create(self, system):
        """一条缝一颗粒子：平躺、长的那条边顺着线；一颗也不能少（建不出来就全不要，返回 []）。"""
        ids = []
        for a, b in self.strips:
            particleId = system.Create(SEAM, tuple((first + second) / 2.0 for first, second in zip(a, b)))
            if not particleId:                        # 回 0（不是 None）：不能当编号去设变量
                for made in ids:
                    system.Remove(made)
                return []
            system.SetRot(particleId, (0.0, ParticleQuad.flatYaw(b[0] - a[0], b[2] - a[2]), 0.0))
            system.SetVariable(particleId, "variable.half_len", math.hypot(b[0] - a[0], b[2] - a[2]) / 2.0)
            system.SetVariable(particleId, "variable.alpha", Dashes.SEAM_ALPHA)
            ids.append(particleId)
        self.wide = None
        return ids

    def _drop(self):
        if self.ids:
            system = compFactory.CreateParticleSystem(None)
            for particleId in self.ids:
                system.Remove(particleId)
        self.ids, self.strips = [], []

    def close(self):
        self._drop()
        self.key = None
