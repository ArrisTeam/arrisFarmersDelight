# -*- coding: utf-8 -*-
"""BoardKnife - 砧板上的刀怎么走、点一下算什么、点下去等服务端回话（双端）

移植自 Hands-On Delight 的 client/BoardBehavior.java：moveKnife（834-906）、chop（1257-1279）、onStateChanged 里的 pendingChops 记账
（396-406）、frame 里的 PENDING_WAIT（795-798）、refused 的撤回（1363-1367）、nextMark（1133-1136）。时间一律是秒，位置是场景像素
（原点在食物中心，x 往操作者左边长、z 往远处长），角度是弧度。

切不是划，是点：刀跟着光标走（每帧追 1 - exp(-22 dt)）；光标在食物上时，下一刀的线离光标 < SNAP（1.4）像素就吸附上去，
刀站到线上、顺着线摆正，这时 overMark 是下一刀的序号；点下去刀落下（0.05 秒下、0.14 秒起）。点的时候没吸附上（overMark < 0）
只是"敲"一声，不发给服务端；吸附上了才发 chop {mark, at}。手上拿着别的工具（斧、镐……）的动作在 BoardStroke.py。
触屏没有悬停（JE 没有，给手机的适配）：手指落下的那一下 overMark 还是上一帧的，所以点按先 land（按这一刻的落点现算，吸附带放到无限），再 click。
"""
import math

from .BoardMarks import SNAP, snapOffset

CHOP_DOWN = 0.05         # BoardBehavior.CHOP_DOWN（76）：刀从悬着落到食物顶面
CHOP_UP = 0.14           # :77 再抬回悬着的高度
HOVER = 2.4              # :73 刀悬在食物顶面上方多高（刀刃那一点）
EDGE = 1.0               # :79 刀刃比刀的中心低这么多（图标中心 = 刃 + EDGE）
REST_HEIGHT = 4.0        # :74 没在食物上时刀的高度（食物顶面之上再加）
REST_Z = -6.0            # :75 没在食物上时停在板的近边
FOLLOW = 22.0            # :890 刀追光标的速度：每帧挪 1 - exp(-FOLLOW * dt) 的距离
PENDING_WAIT = 1.0       # :201 画了切开却等不到服务端的话，这么久之后撤回

KNOCK = "knock"
CHOP = "chop"


class Knife(object):
    """一把悬在食物上的刀（moveKnife / chop 的状态）。frame 每帧调一次，click 在点下去时调。"""

    def __init__(self):
        self.x = 0.0                 # 刀刃现在的位置（离食物中心）
        self.z = REST_Z
        self.y = REST_HEIGHT         # 刀悬着的高度（离板面）
        self.angle = 0.0             # 刀顺着的那条线：这一刀的角度
        self.age = None              # 落刀已经过了多久；None 是没在落
        self.overMark = -1           # 刀吸附着的那一刀的序号；没吸附是 -1
        self.shown = False           # 刀画不画（光标在食物上，或正在落刀）

    def reset(self):
        self.__init__()

    @property
    def chopping(self):
        return self.age is not None

    def frame(self, dt, over, cut, index, top, haveTool=True, reach=SNAP):
        """推进一帧。over：光标在食物顶面的点 (x, z)（离食物中心，已夹进 REACH）或 None（不在食物上）；cut：下一刀（BoardMarks.Cut）或 None；
        index：它的序号；top：食物顶面离板面多高；haveTool：有刀可用；reach：离线多近吸附（缺省 SNAP，触屏是 TAP_SNAP）。
        返回刀现在的姿态 (x, 刀刃的高度, z, 角度)，不画刀时返回 None。"""
        self.overMark = -1
        self.shown = haveTool and (over is not None or self.chopping)
        if not self.shown:
            self.y = top + HOVER + REST_HEIGHT
            return None
        wantX, wantZ, wantY = self.x, self.z, top + HOVER
        if cut is not None:
            self.angle = cut.angle
        if over is not None:
            wantX, wantZ = over
            offset = snapOffset(cut, wantX, wantZ, reach) if cut is not None else None
            if offset is not None:                       # 线就在手边：刀站到线上、顺着线
                self.overMark = index
                wantX -= cut.normalX() * offset
                wantZ -= cut.normalZ() * offset
        follow = 1.0 - math.exp(-dt * FOLLOW)
        self.x += (wantX - self.x) * follow
        self.z += (wantZ - self.z) * follow
        self.y += (wantY - self.y) * follow
        height = self.y
        if self.chopping:
            self.age += dt
            down = self.age / CHOP_DOWN if self.age < CHOP_DOWN else max(0.0, 1.0 - (self.age - CHOP_DOWN) / CHOP_UP)
            height += (top - self.y) * down
            if self.age > CHOP_DOWN + CHOP_UP:
                self.age = None
        return (self.x, height, self.z, self.angle)

    def land(self, over, cut, index, reach):
        """触屏的一下点按：手指落下的这一刻就是落点，没有悬停让刀先吸附（frame 算 overMark 用的是上一帧的光标）——按这一刻的落点现算：
        离线 < reach（触屏给 TAP_SNAP：点在食物上就落在线上）就当场吸附上去，刀站到线上离手指最近的一点、顺着线摆正，之后的 click 就是 CHOP。
        落刀还没完、不在食物上、没有下一刀什么也不动。"""
        if over is None or cut is None or index < 0 or self.chopping:
            return
        offset = snapOffset(cut, over[0], over[1], reach)
        if offset is None:
            return
        self.x, self.z = over[0] - cut.normalX() * offset, over[1] - cut.normalZ() * offset
        self.angle = cut.angle
        self.overMark = index

    def click(self, over):
        """点下去（chop，1257-1279）：不在食物上、或这一刀还没落完，什么也不是（None）；落在线上返回 (CHOP, 序号, 刀刃的 z)，
        没吸附上返回 (KNOCK,)。"""
        if over is None or self.chopping:
            return None
        self.age = 0.0
        if self.overMark < 0:
            return (KNOCK,)
        return (CHOP, self.overMark, self.z)


class Pending(object):
    """点下去、服务端还没回话的几刀：本地先把它们画成切开，不让刀等着（pendingChops / answeredMarks / pendingSince）。"""

    def __init__(self):
        self.count = 0
        self.answered = 0
        self.since = 0.0

    def reset(self):
        self.count = 0

    def add(self, clock):
        """又发了一刀。"""
        self.count += 1
        self.since = clock

    def state(self, marks, boardChanged=False):
        """服务端的状态来了（onStateChanged，396-406）：板上换了东西或已切的刀数倒退，等着的全作废；刀数涨了，每涨一刀就回了一刀。"""
        if boardChanged or marks < self.answered:
            self.count = 0
        elif marks > self.answered:
            self.count = max(0, self.count - (marks - self.answered))
        self.answered = marks

    def refused(self):
        """服务端说不收这一刀（refused）：撤回。返回有没有东西撤。"""
        had = self.count > 0
        self.count = 0
        return had

    def expire(self, clock):
        """等了 PENDING_WAIT 秒还没回话：撤回。返回有没有东西撤。"""
        if self.count > 0 and clock - self.since > PENDING_WAIT:
            self.count = 0
            return True
        return False

    def made(self, marks, plan):
        """画出来的已切刀数：服务端说的加上等着的，不超过一共几刀（cutsMade，730-737）。"""
        return min(plan, marks + self.count)

    def next(self, marks, plan):
        """下一刀的序号（nextMark，1133-1136）：一共几刀都切了是 -1。"""
        following = marks + self.count
        return following if following < plan else -1
