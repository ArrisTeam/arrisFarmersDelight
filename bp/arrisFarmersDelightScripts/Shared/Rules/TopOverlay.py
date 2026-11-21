# -*- coding: utf-8 -*-
"""TopOverlay - 叠在一件平躺的客户端掉落物朝上那面上的那张图标粒子：摆在哪、SetRot 转多少、多大，掉落物停稳了没有（双端，纯计算）

用处：煎锅 / 炉灶上煎着的东西朝上那面的熟色（颜色在 FryingTint.overlay，粒子 arris:fry_tint，客户端 Compat/Diegesis/FryTints）。
- 掉落物（ItemPose）：姿态 M 是世界里的 3x3 行表，从正面看图标的右边是 M·(-1, 0, 0)、上边是 M·(0, 1, 0)，正面朝 M·(0, 0, -1)
  （前置包 Shared/CarryPose.shadowOf 的说明）；给的中心是贴图正中（ItemPose.pivotFor 换成轴心之前的那个点），边长 ITEM_SPAN x 缩放 站点像素。
- 粒子（rp/particles/arris_fry_tint.json，emitter_transform_xz）：四边形铺在发射器朝向 E 的 xz 面上，图标右 = E.x、上 = -E.z、法线 = E.y，
  size 是半边长（Strata 引擎知识库 PARTICLE_ENGINE §5.1、§5.4）；没绑定的发射器 SetRot((x, y, z)) 得 E = Rz(z)·Ry(y)·Rx(x)（度，
  EFFECT_BINDING_ENGINE §1.4，反编译核过；实机只核对过只转 y 的那一支，Shared/Rules/ParticleQuad）。
  要它和掉落物朝上那面严丝合缝：E.x = M·(-1, 0, 0)、E.z = -M·(0, 1, 0)、E.y = M·(0, 0, -1)，即 E = M·P（emitterMatrix）；P 是个转动，贴图不用镜像。
  平躺朝上（M = Ry(a)·Rx(90)）时 E = Ry(a + 180)：SetRot((0, a + 180, 0))。
- 高度：沿正面的法线抬 lift(缩放) 像素。掉落物有厚度：贴图逐像素挤出一个贴图像素厚（贴图边长的 1/16），从轴心平面往正面那一侧挤
  （Strata 引擎知识库 ITEM_RENDER_ENGINE §3.2–§4：网格的厚度 -> 物品局部的 -Z，正面朝 -Z），平躺朝上时顶面就在中心平面上方 TOP_FACE x 缩放；
  零厚度的四边形贴得太近会陷进去，再抬 LIFT_MARGIN。
- 受光：物品的材质按法线算明暗（实体着色器的 _lightIntensity，FANCY：(1 + N.y)/2 x 0.55 - 0.1 N.x² + 0.1 N.z² + 0.45），朝上的面正好是 1，
  顶面 = 贴图 x TILE_LIGHT_COLOR；粒子带 particle_appearance_lighting 也只乘所在处的光，所以两者在顶面上应该受一样的光（知识库推的，实机再核）。
- 只给平躺朝上的（正面和竖直差不到 FLAT_TILT 度），斜着的、扣着的、立着的给 None：锅里、烤架上停着的件都平躺朝上（颠完、翻完都转回 0），
  斜着的只在颠起、翻面、落下的半路上，那时本来就收着（Stillness）。斜着的那一支的数学（emitterEuler 的全角度分解）留着：粒子带俯仰 / 侧倾转得对不对，
  要进游戏量过才敢放开。
- 什么时候亮（Stillness）：掉落物的位置按游戏刻插值、晚到一两帧，转角当帧生效；粒子的位置当帧生效、颜色晚一个渲染帧（PARTICLE_ENGINE §5.3）——
  动着的时候两者对不齐，所以样子一变就收着，连着 SETTLE 秒（两个游戏刻）没变才亮。
"""
import math

from .ItemPose import ITEM_SPAN

TOP_FACE = ITEM_SPAN / 16.0   # 平躺的贴图物品掉落物，正面在中心平面上方多高（站点像素 x 缩放）：一个贴图像素的厚度，0.45。和 2026-11-17 砧板上的实测对得上：
#                               缩放 1.25 时顶面在中心上方 0.5625，零厚度的虚线在 0.555 陷在里面、0.655 露出来（BoardMarkLine.MARK_LIFT 的说明；那时板上 FLAT_LIFT 0.32）
LIFT_MARGIN = 0.1    # 再抬这么多（站点像素，不跟缩放）：贴得太近两层抢深度会闪。估的（照这个算，砧板的缝今天在顶面上方约 0.08、虚线约 0.13，缩放 1.39）
FLAT_TILT = 2.0      # 正面和竖直差多少度以内算平躺
FLAT_COS = math.cos(math.radians(FLAT_TILT))
SETTLE = 0.1         # 掉落物停稳多久粒子才亮（秒）：两个游戏刻，引擎插值的位置追上了
ANGLE_DIGITS = 1     # SetRot 的角度留到小数点后 1 位（前置包的影子、砧板的缝一样是 0.1 度）
PURE_YAW = 1.0e-9    # 发射器朝向里这几个数都小于它：只转了 y


def lift(scale):
    """粒子离掉落物的中心平面多高（站点像素）：正面的高度 TOP_FACE x 缩放，再加 LIFT_MARGIN。"""
    return TOP_FACE * scale + LIFT_MARGIN


def emitterMatrix(matrix):
    """掉落物的姿态 M -> 粒子发射器的朝向 E = M·P（3x3 行表）：E.x = -M.x（图标右）、E.y = -M.z（正面）、E.z = -M.y（图标上的反方向）。"""
    return [[-row[0], -row[2], -row[1]] for row in matrix]


def _angle(radians):
    """弧度 -> 度，夹到 (-180, 180]。"""
    value = math.fmod(math.degrees(radians), 360.0)
    return value - 360.0 if value > 180.0 else (value + 360.0 if value <= -180.0 else value)


def emitterEuler(e):
    """发射器朝向 E -> SetRot 的 (x, y, z) 度，E = Rz(z)·Ry(y)·Rx(x)。只转了 y 的给 (0, y, 0)（实机核对过的那一支）；
    别的取 |x| + |z| 小的那一组（离只转 y 不远的转动，俯仰、侧倾也小）。y 转到 ±90 度时 x 和 z 合成一个转角，全记在 z 上。"""
    if max(abs(e[0][1]), abs(e[1][0]), abs(e[1][2]), abs(e[2][1])) < PURE_YAW:
        return (0.0, _angle(math.atan2(e[0][2], e[0][0])), 0.0)
    if abs(e[2][0]) > 1.0 - 1.0e-12:
        return (0.0, _angle(math.asin(max(-1.0, min(1.0, -e[2][0])))), _angle(math.atan2(-e[0][1], e[1][1])))
    y = math.asin(-e[2][0])
    x, z = math.atan2(e[2][1], e[2][2]), math.atan2(e[1][0], e[0][0])
    first = (_angle(x), _angle(y), _angle(z))
    second = (_angle(x + math.pi), _angle(math.pi - y), _angle(z + math.pi))      # 同一个转动的另一组角
    return first if abs(first[0]) + abs(first[2]) <= abs(second[0]) + abs(second[2]) else second


def _sent(degrees):
    """送给引擎的角度：留 ANGLE_DIGITS 位（-0.0 写成 0.0），没变的就不重发。"""
    return round(degrees, ANGLE_DIGITS) + 0.0


def frameOf(center, matrix, scale):
    """一件平躺朝上的掉落物上面叠的粒子怎么摆。center：贴图正中的世界坐标（格）；matrix：世界里的姿态（3x3 行表）；scale：送给引擎的缩放。
    返回 {"pos": 粒子的世界位置（格）, "rot": SetRot 的 (x, y, z) 度（留 1 位小数）, "half": 半边长（格）}；不是平躺朝上的（斜着、扣着、立着）返回 None。"""
    front = (-matrix[0][2], -matrix[1][2], -matrix[2][2])
    if front[1] < FLAT_COS:
        return None
    up = lift(scale) / 16.0
    return {"pos": (center[0] + front[0] * up, center[1] + front[1] * up, center[2] + front[2] * up),
            "rot": tuple(_sent(value) for value in emitterEuler(emitterMatrix(matrix))), "half": ITEM_SPAN * scale / 32.0}


class Stillness(object):
    """一件掉落物停稳了没有。每帧 step(dt, 样子)：样子是任何能比相等的东西（画的物品、中心、姿态、缩放），变了从头算，连着 SETTLE 秒没变才算停稳。"""

    __slots__ = ("pose", "still")

    def __init__(self):
        self.pose, self.still = None, 0.0

    def step(self, dt, pose):
        if pose != self.pose:
            self.pose, self.still = pose, 0.0
            return False
        self.still += dt
        return self.still >= SETTLE - 1.0e-9
