# -*- coding: utf-8 -*-
"""StoveMotion - 烤架上一件的动作：落到烤架上、翻面（跳起来转半圈）、被取走、被拒绝弹回；悬停时抬起一点（双端，纯计算）

移植自 Hands-On Delight：client/StoveBehavior.java 的 land（235-243）、turned（378-399）、taken（501-517）、onEffect 里的 REFUSED（482-490），
和 Diegesis 的 impl/client/anim/Tween.java / Easing.java（一段缓动：inOutCubic，跳的时候 y 上再加 height * sin(pi * 线性进度)）、
impl/client/scene/NodeInstance.java（节点的欧拉角先 Y 再 X 再 Z；可交互的节点悬停时抬起 0.6 像素，半衰期 0.06 秒）。
时间是秒，长度是像素，角度是度；位置是相对这一件自己的落点的偏移（JE 节点的 moveTo / hopTo 就是偏移）。

Motion 是一个节点的三条缓动（偏移、转角、缩放）加一串"过多久发个事件"；Piece 在它上面做烤位上的件的几套动作，
update(dt) 返回这一步到点的事件名：appear（晚到的那件该出现了）、landed（落到烤架上了：冒汽、嗞一声）、
swap（翻到一半：换成另一面的样子）、turned（翻完落下了：嗞一声、冒汽）。Ghost 是飞走 / 弹回的虚影，到点发 gone。
画法：偏移加在件的落点上，转角 (x, 转角 y = 摆放的偏航, z) 用 poseRows 变成站点空间的 3x3 姿态（贴图躺平）。
"""
import math

LAND_FROM = 4.0              # 落下前悬在烤架上方多高，px（StoveBehavior.java:51）
LAND_TIME = 0.2              # 从上面落下来多久，秒（50 行）；弧线再高 0.8（238 行）
LAND_ARC = 0.8
PLAYER_LAND_TIME = 0.32      # 从玩家那边飞来落下多久（53 行）；弧线再高 2.0（241 行）
PLAYER_LAND_ARC = 2.0
STAGGER = 0.14               # 一次放好几件：每件晚这么久（52 行）
FLIGHT = 0.3                 # 翻一次在空中多久（48 行）
RISE = 3.0                   # 翻的时候跳多高，px（49 行）
AWAY_TIME = 0.3              # 取走时虚影升起、缩没用多久（54 行）；升到 2.5 px、弧线再高 1.5（509 行）
AWAY_RISE, AWAY_ARC = 2.5, 1.5
REFUSE_START = LAND_FROM + 2.0   # 被拒绝的虚影从这么高落下（485 行），0.09 秒落到 1.5 px 高、再用 0.22 秒往后（-z）弹到 6 px 高（486-488 行）
REFUSE_DOWN, REFUSE_DROP_TIME = 1.5, 0.09
REFUSE_BOUNCE_TIME, REFUSE_BOUNCE_ARC, REFUSE_BACK = 0.22, 1.2, -6.0
HOVER_LIFT = 0.6             # 悬停时抬起多高，px（NodeInstance.computeLocal，809 行）
HOVER_HALF_LIFE = 0.06       # 抬起 / 放下的半衰期，秒（NodeInstance.HOVER_HALF_LIFE）
EPS = 1.0e-6                 # 事件到点的容差（秒）：逐帧减出来的 0.2 差一点点才到 0 也算到了
TILT = 90.0                  # 翻到一半时转到的角度：立起来、侧着对镜头（rotateTo(90, ...)，385 行）


def inOutCubic(t):
    """Easing.inOutCubic：慢起慢停。"""
    t = min(1.0, max(0.0, t))
    return 4.0 * t * t * t if t < 0.5 else 1.0 - math.pow(-2.0 * t + 2.0, 3.0) / 2.0


def approach(current, target, halfLife, dt):
    """Easing.approach：每过 halfLife 秒走完剩下的一半。"""
    if halfLife <= 0.0:
        return target
    return target + (current - target) * math.pow(0.5, dt / halfLife)


class Tween(object):
    """三个数从当前值走到目标（Tween.java）：seconds 为 0 就是直接跳过去；height 不为 0 是一跳：中途 y 再高 height * sin(pi * 线性进度)。"""

    def __init__(self, x=0.0, y=0.0, z=0.0):
        self.origin = [x, y, z]
        self.goal = [x, y, z]
        self.current = [x, y, z]
        self.elapsed = 0.0
        self.duration = 0.0
        self.arc = 0.0

    def start(self, x, y, z, seconds, height=0.0):
        self.arc = height
        self.origin = list(self.current)
        self.goal = [x, y, z]
        self.elapsed = 0.0
        self.duration = max(seconds, 0.0)
        if self.duration == 0.0:
            self.current = list(self.goal)

    @property
    def running(self):
        return self.elapsed < self.duration

    def update(self, dt):
        if self.elapsed < self.duration:
            self.elapsed = min(self.elapsed + dt, self.duration)
            t = inOutCubic(self.elapsed / self.duration)
            self.current = [a + (b - a) * t for a, b in zip(self.origin, self.goal)]
            self.current[1] += self.arc * math.sin(math.pi * self.elapsed / self.duration)
        return self.current


class Motion(object):
    """一个节点的动作：偏移、转角（x、偏航 y、z）、缩放三条缓动，和一串"过多久发个事件"。"""

    def __init__(self, yaw=0.0):
        self.offset = Tween(0.0, 0.0, 0.0)
        self.rotation = Tween(0.0, yaw, 0.0)
        self.scale = Tween(1.0, 1.0, 1.0)
        self.timers = []                      # [[还要多久, 事件名]]
        self.hover = 0.0                      # 悬停的抬起量 0..1

    def moveTo(self, x, y, z, seconds):
        self.offset.start(x, y, z, seconds)

    def hopTo(self, x, y, z, height, seconds):
        self.offset.start(x, y, z, seconds, height)

    def rotateTo(self, x, y, z, seconds):
        self.rotation.start(x, y, z, seconds)

    def scaleTo(self, factor, seconds):
        self.scale.start(factor, factor, factor, seconds)

    def after(self, seconds, name):
        self.timers.append([seconds, name])

    @property
    def moving(self):
        """偏移的缓动还没走完（NodeInstance.isMoving）：画的人这时候不要把位置和转角摆回原位。"""
        return self.offset.running

    def update(self, dt, hovered=False):
        """前进 dt 秒；返回这一步到点的事件名（按先后）。"""
        self.offset.update(dt)
        self.rotation.update(dt)
        self.scale.update(dt)
        self.hover = approach(self.hover, 1.0 if hovered else 0.0, HOVER_HALF_LIFE, dt)
        fired, waiting = [], []
        for entry in self.timers:
            entry[0] -= dt
            (fired if entry[0] <= EPS else waiting).append(entry)
        self.timers = waiting
        return [entry[1] for entry in fired]

    def pose(self):
        """(偏移 x y z（含悬停抬起）, 转角 x y z, 缩放)：画的人加在落点上。"""
        x, y, z = self.offset.current
        return ((x, y + HOVER_LIFT * self.hover, z), tuple(self.rotation.current), self.scale.current[0])


class Piece(Motion):
    """烤位上的一件。visible 为假时还没出现（一次放好几件，后面的在等）。"""

    def __init__(self, yaw=0.0):
        Motion.__init__(self, yaw)
        self.yaw = yaw
        self.visible = True
        self.fromOffset = None                # 一次放好几件时它从玩家那边飞来的起点 (x, z)，相对落点

    def arrive(self, delay=0.0, fromOffset=None):
        """新放上来的一件落到烤架上（StoveBehavior.refresh 的到达，162-179）：delay 秒后出现并落下，fromOffset 是一次放好几件时
        它们从玩家那边飞来的起点 (x, z)（相对落点），没有就从正上方落下。到点的事件：appear（晚到的现身）、landed（落到烤架上）。"""
        self.fromOffset = fromOffset
        self.visible = delay <= 0.0
        if delay > 0.0:
            self.after(delay, "appear")
        else:
            self._land()

    def _land(self):
        """落下（land，235-243）：从上面 LAND_FROM 高（或玩家那边的一点）带一跳落到落点；落地时 landed。"""
        self.visible = True
        if self.fromOffset is None:
            self.moveTo(0.0, LAND_FROM, 0.0, 0.0)
            self.hopTo(0.0, 0.0, 0.0, LAND_ARC, LAND_TIME)
            self.after(LAND_TIME, "landed")
        else:
            self.moveTo(self.fromOffset[0], LAND_FROM, self.fromOffset[1], 0.0)
            self.hopTo(0.0, 0.0, 0.0, PLAYER_LAND_ARC, PLAYER_LAND_TIME)
            self.after(PLAYER_LAND_TIME, "landed")

    def turn(self):
        """翻面（turned，378-399）：跳起 RISE 高、先转到立起来（FLIGHT 的一半），到点 swap（调用方换成另一面的样子），
        再从 -90 度转回平躺并落下；整个 FLIGHT 之后 turned。"""
        self.hopTo(0.0, 0.0, 0.0, RISE, FLIGHT)
        self.rotateTo(TILT, self.yaw, 0.0, FLIGHT / 2.0)
        self.after(FLIGHT / 2.0, "swap")
        self.after(FLIGHT, "turned")

    def update(self, dt, hovered=False):
        fired = Motion.update(self, dt, hovered)
        for name in fired:
            if name == "appear":
                self._land()
            elif name == "swap":
                self.rotateTo(-TILT, self.yaw, 0.0, 0.0)
                self.rotateTo(0.0, self.yaw, 0.0, FLIGHT / 2.0)
        return fired

    def settle(self):
        """摆回原位（draw 里"没在动就把位置和转角摆回去"，207-210 行）。"""
        self.moveTo(0.0, 0.0, 0.0, 0.0)
        self.rotateTo(0.0, self.yaw, 0.0, 0.0)


class Ghost(Motion):
    """飞走或弹回的虚影：一个借来的节点（JE 有三个轮着用，GHOSTS）。到点发 gone，之后不再显示。
    偏移相对虚影的基点：取走的虚影基点是那一件自己的落点，被拒绝的虚影基点是烤架中心。"""

    def __init__(self):
        Motion.__init__(self)
        self.visible = False

    def _show(self, yaw=0.0):
        self.visible = True
        self.timers = []
        self.rotateTo(0.0, yaw, 0.0, 0.0)
        self.scaleTo(1.0, 0.0)
        self.moveTo(0.0, 0.0, 0.0, 0.0)

    def taken(self, yaw):
        """一件被取走（taken，501-517）：虚影从它的位置升起 2.5 px、缩没，AWAY_TIME 之后 gone。"""
        self._show(yaw)
        self.hopTo(0.0, AWAY_RISE, 0.0, AWAY_ARC, AWAY_TIME)
        self.scaleTo(0.0, AWAY_TIME)
        self.after(AWAY_TIME, "gone")

    def refused(self):
        """放不上去的一件弹回（REFUSED，482-490）：从烤架中心上方 6 px 落到 1.5 px 高，再往后弹开，共 0.31 秒之后 gone。"""
        self._show()
        self.moveTo(0.0, REFUSE_START, 0.0, 0.0)
        self.moveTo(0.0, REFUSE_DOWN, 0.0, REFUSE_DROP_TIME)
        self.after(REFUSE_DROP_TIME, "bounce")
        self.after(REFUSE_DROP_TIME + REFUSE_BOUNCE_TIME, "gone")

    def update(self, dt, hovered=False):
        fired = Motion.update(self, dt, hovered)
        for name in fired:
            if name == "bounce":
                self.hopTo(0.0, REFUSE_START, REFUSE_BACK, REFUSE_BOUNCE_ARC, REFUSE_BOUNCE_TIME)
            elif name == "gone":
                self.visible = False
        return fired


# ---------------------------------------------------------------- 姿态

def _mul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def _rx(degrees):
    c, s = math.cos(math.radians(degrees)), math.sin(math.radians(degrees))
    return [[1.0, 0.0, 0.0], [0.0, c, -s], [0.0, s, c]]


def _ry(degrees):
    c, s = math.cos(math.radians(degrees)), math.sin(math.radians(degrees))
    return [[c, 0.0, s], [0.0, 1.0, 0.0], [-s, 0.0, c]]


def _rz(degrees):
    c, s = math.cos(math.radians(degrees)), math.sin(math.radians(degrees))
    return [[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]]


def poseRows(x, yaw, z):
    """JE 节点的转角（度，先偏航 Y、再 X、再 Z：R = Ry * Rx * Rz，Transform.toQuaternion）作用在一张平躺的贴图上，
    站点空间的 3x3 行表：Ry(yaw) * Rx(x) * Rz(z) * Rx(90)（客户端掉落物的贴图原来立着、正面朝 -Z；Rx(90) 让它躺平、正面朝上、顶边朝 +Z）。"""
    return _mul(_mul(_mul(_ry(yaw), _rx(x)), _rz(z)), _rx(90.0))
