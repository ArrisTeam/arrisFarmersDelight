# -*- coding: utf-8 -*-
"""BoardMarks - 砧板的刀口落在食物哪里：刀口线、虚线的两端、刀吸附的距离、光标在不在食物上（双端）

移植自 Hands-On Delight：client/ItemVoxels.java 的 Cut（285-299 行），client/BoardBehavior.java 的 extent / mark / line / clip /
overItem（1074-1125、1197-1219）。图标的实心像素和主轴在 BoardIcon.py。HoD 里每一刀把图标的体素往两边挪开；
基岩版板上的东西切不开，所以这里只算"线在哪、线多长、刀离线多远"，画法在 Compat/Diegesis/BoardKnife.py。
坐标同 BoardIcon：场景像素，原点在食物中心，x 往操作者的左边长、z 往远处长。
"""
import math

from .BoardIcon import BLOCK_SCALE, BLOCK_SIZE, EPS, INFINITY, ITEM_SIZE, Axis, Icon, iconOf, normalized  # noqa: F401 - 测试和调用方从这里取
from .Cutting import MOST_LEAN, STYLE_ACROSS, STYLE_WEDGES
from .Mth import clamp

SNAP = 1.4                       # BoardBehavior.SNAP（84）：刀离下一刀的线这么近就吸附上去
REACH = 4.0                      # :68 刀离食物中心最远这么远（每个方向）
LONG = 1.4                       # :1114 比这更长的东西叫"长"
LONG_LEAN = math.radians(20.0)   # :1112 长的东西横切时刀口最多偏离垂直这么多（鱼切成排，不会顺着脊骨切）


class Cut(object):
    """食物上的一刀（ItemVoxels.Cut，285-299）：过 (x, z)、和 x 方向夹 angle 弧度的一条直线。"""

    __slots__ = ("x", "z", "angle")

    def __init__(self, x, z, angle):
        self.x, self.z, self.angle = x, z, angle

    def normalX(self):
        return -math.sin(self.angle)

    def normalZ(self):
        return math.cos(self.angle)

    def distance(self, px, pz):
        """(px, pz) 离这条线多远，在法线那一侧为正。"""
        return self.normalX() * (px - self.x) + self.normalZ() * (pz - self.z)


def axisOf(icon, isBlock=False):
    """BoardBehavior.axis（1128-1130）：图标画 ITEM_SIZE 像素时的主轴；方块类是 BLOCK_SIZE 见方。"""
    return Axis.square(BLOCK_SIZE / 2.0) if isBlock else icon.axis(ITEM_SIZE)


def line(axis, style, spot, angle):
    """BoardBehavior.line（1117-1125）：第 i 刀在这件食物上是哪条线。楔形：过食物中心、转 angle；其余：落在长边 spot 处，
    横切（ACROSS）在垂直于长边的基础上再偏 angle 份（长的东西最多偏 LONG_LEAN，别的 MOST_LEAN），卷和面条笔直横过去。"""
    if style == STYLE_WEDGES:
        return Cut(axis.x, axis.z, normalized(angle))
    at = axis.at(spot)
    lean = angle * (LONG_LEAN if axis.elongation >= LONG else MOST_LEAN) if style == STYLE_ACROSS else 0.0
    return Cut(at[0], at[1], normalized(axis.across() + lean))


def markOf(axis, style, spots, angles, index, count):
    """BoardBehavior.mark（1102-1109）：服务端给的第 index 刀；还没收到时（spots 不够长）按等分、笔直横过去。"""
    spot = spots[index] if index < len(spots) else (index + 1.0) / (count + 1.0)
    return line(axis, style, spot, angles[index] if index < len(angles) else 0.0)


def clip(start, along, low, high, first, last):
    """BoardBehavior.clip（1197-1204）：线 start + t * along 落在 [low, high] 里的那段 t，在 [first, last] 里再收窄。"""
    if abs(along) < 1.0e-4:
        return (first, last) if low <= start <= high else (0.0, 0.0)
    a, b = (low - start) / along, (high - start) / along
    return (max(first, min(a, b)), min(last, max(a, b)))


def extentOf(icon, isBlock=False):
    """BoardBehavior.extent（1074-1084）：实心的部分离食物中心多远：(右, 左, 近, 远)，x 往左长；方块类是正方形。"""
    if isBlock:
        half = BLOCK_SIZE / 2.0
        return (-half, half, -half, half)
    left, right, top, bottom = icon.bounds()
    pixel = icon.pixel(ITEM_SIZE)
    return ((icon.width / 2.0 - right - 1) * pixel, (icon.width / 2.0 - left) * pixel,
            (icon.height / 2.0 - bottom - 1) * pixel, (icon.height / 2.0 - top) * pixel)


def boxEnds(icon, cut, isBlock=False):
    """线 cut 在图标（或方块）的外框里从哪到哪（t 的两端）：方块类按它的盒子裁，图标按实心像素的外框裁。"""
    right, left, near, far = extentOf(icon, isBlock)
    found = clip(cut.x, math.cos(cut.angle), right, left, -100.0, 100.0)
    return clip(cut.z, math.sin(cut.angle), near, far, found[0], found[1])


def endsOf(icon, cut, isBlock=False):
    """drawMarks（1163-1175）：虚线沿这条线画多长（t 的两端）：图标按实心像素，方块类按方块的盒子裁。"""
    return boxEnds(icon, cut, True) if isBlock else icon.solidSpan(cut.x, cut.z, cut.angle, ITEM_SIZE)


def _points(cut, first, last):
    if not first < last:
        return None
    dx, dz = math.cos(cut.angle), math.sin(cut.angle)
    return [(cut.x + dx * first, cut.z + dz * first), (cut.x + dx * last, cut.z + dz * last)]


def ends(cut, icon, isBlock=False):
    """虚线两端在场景里的点：[(x0, z0), (x1, z1)]；线碰不到食物返回 None。"""
    return _points(cut, *endsOf(icon, cut, isBlock))


def dashOf(cut, icon, isBlock=False):
    """虚线两端：先照 HoD 的（实心像素），一个实心像素都碰不到时（碎成几块的图标，比如皮马铠）改按外框裁，免得这一刀没有线可看。"""
    found = ends(cut, icon, isBlock)
    return found if found is not None else _points(cut, *boxEnds(icon, cut, isBlock))


def overItem(x, z):
    """overItem（1214-1219）：光标在食物顶面上的点 (x, z)（离食物中心的像素）算不算在食物上，算就夹进 REACH 以内返回，不算 None。"""
    if abs(x) < ITEM_SIZE / 2.0 + 1.0 and abs(z) < ITEM_SIZE / 2.0 + 1.0:
        return (clamp(x, -REACH, REACH), clamp(z, -REACH, REACH))
    return None


def snapOffset(cut, x, z):
    """刀在 (x, z) 离这一刀的线多远（带符号）；够近（< SNAP）能吸附返回它，否则 None。刀要往线上挪 offset 份法线。"""
    off = cut.distance(x, z)
    return off if abs(off) < SNAP else None
