# -*- coding: utf-8 -*-
"""StoveFacing - 炉灶的朝向：方块的 aux -> 站点朝哪，"炉灶自己的坐标"换到世界（双端，纯规则）

JE 的炉灶站点是 Orientation.BLOCK（HoD 的 StoveStation）：站点的北面永远是炉灶方块的正面（FD 的 FACING 属性），场景按"炉灶朝北"写
（stove.json），从哪一侧右键镜头都飞到正面；厨锅、砧板才是 PLAYER（朝着玩家站的那一侧）。FD 自己画烤架上的东西（DefaultStoveRenderer）、
冒烟（StoveBlockEntity.addSmokeParticles）也都按 FACING 转，所以六件东西的位置、翻面落下的动作、粒子声音的位置全跟着炉灶转。
基岩版的炉灶是 netease:face_directional 的 direction 状态（就是方块的 aux）：0 南、1 西、2 北、3 东，写在 north 的贴图（点着的火口）
出现在世界的那一面（Strata 引擎知识库 BLOCK_LEGACY_ENGINE §10.2），所以炉灶的"正面"朝哪就是 PotModelMath.facingOf(aux)；
站点朝向（度，北 0 / 东 90 / 南 180 / 西 270，Diegesis 的 stationToWorld）就是这一面的方向。
客户端的朝向钩子（GrillView.facingOf，读 GetBlock 的 aux）和服务端的（GrillOpen.facingOf，读 GetBlockNew 的 aux）都过 yawOfAux，说同一个答案。

炉灶自己的坐标就是站点空间：像素（16 = 1 格），原点在方块西北下角，按"炉灶朝北"写（HoD 的 stove.json），+x 在画面左边（面朝南时世界 +x 在左），
+z 朝远处，烤架面 y = 16。站点朝哪、炉灶就朝哪，所以开着站点的人用的坐标、谁都看得见的场景用的坐标、没装前置包时世界里的展示用的坐标
是同一套，只差怎么换到世界：绕方块中心转 yaw 度（和前置包的 Geometry.stationPointToWorld 一样，PotModelMath 的 localToWorld 同一个转法）。
"""
from . import PotModelMath as Pot

YAWS ={Pot.NORTH: 0, Pot.EAST: 90, Pot.SOUTH: 180, Pot.WEST: 270}      # 正面朝哪 -> 站点朝向（度）
FACINGS = dict((yaw, facing) for facing, yaw in YAWS.items())


def yawOfAux(aux):
    """炉灶方块的 aux（direction 状态）-> 站点朝向（度）：站点的北面转到炉灶的正面那一侧。aux 读不到按 0（引擎的缺省状态，朝南）。"""
    return YAWS[Pot.facingOf(aux)]


def facingOfYaw(yaw):
    """站点朝向（度，0 / 90 / 180 / 270）-> PotModelMath 的朝向名；别的角度按朝北。"""
    return FACINGS.get(int(yaw) % 360, Pot.NORTH)


def turnOffset(yaw, dx, dz):
    """炉灶自己的坐标里的一个水平偏移（或方向）(dx, dz) -> 世界里的：站点转 yaw 度，北（-z）转到 yaw 那一侧。单位不变。"""
    return Pot.localToWorld(facingOfYaw(yaw), dx, dz)


def worldPoint(yaw, blockPos, x, y, z):
    """炉灶自己的坐标里的一点（像素）-> 世界坐标（格）；blockPos 是方块位置。"""
    return Pot.localPoint(facingOfYaw(yaw), blockPos, x, y, z)


def turnFraction(yaw, x, z):
    """方块里的一点（占方块宽的比例 x, z，炉灶朝北的那一份）-> 炉灶朝 yaw 时同一点的比例：绕方块中心转。"""
    dx, dz = turnOffset(yaw, x - 0.5, z - 0.5)
    return (0.5 + dx, 0.5 + dz)


def _axes(yaw):
    ax, az = turnOffset(yaw, 1.0, 0.0)
    bx, bz = turnOffset(yaw, 0.0, 1.0)
    return ((ax, 0.0, bx), (0.0, 1.0, 0.0), (az, 0.0, bz))


_AXES = dict((yaw, _axes(yaw)) for yaw in YAWS.values())


def axes(yaw):
    """炉灶自己的 x / y / z 轴在世界里的方向，3x3 行表，列是轴（ItemPose.framed 把炉灶坐标里算好的姿态换到世界要它）。共用的，别改它的内容。"""
    return _AXES[YAWS[facingOfYaw(yaw)]]
