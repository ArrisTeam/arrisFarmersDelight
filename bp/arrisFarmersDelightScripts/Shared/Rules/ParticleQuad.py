# -*- coding: utf-8 -*-
"""ParticleQuad - 脚本放的粒子四边形怎么摆：SetRot 的偏航、竖立的图标在平面里的转角（双端，纯逻辑）

没绑定的发射器 SetRot((0, ψ, 0)) 得到 E = Ry(ψ)，它的三列是 E.x = (cos ψ, 0, -sin ψ)、E.y = (0, 1, 0)、E.z = (sin ψ, 0, cos ψ)；
emitter_transform_* 的四边形铺在 E 的轴上（Strata 引擎知识库 PARTICLE_ENGINE §5.3 / §5.4，粒子两个字段 size 是半边长）：
- emitter_transform_xz（平躺）：图标右 = E.x、上 = -E.z、朝上。**实机核对过**（2026-11-17，物品图标粒子）：不转时上边朝世界 -z、右边朝 +x，
  转 ψ 后上边朝 (-sin ψ, -cos ψ)、右边朝 (cos ψ, -sin ψ)；
- emitter_transform_xy（竖立）：图标右 = E.x、上 = 竖直向上、正面（法线）= E.z = (sin ψ, 0, cos ψ)；从正面看图标不镜像（贴图 u 沿右、v 沿下）。
  这一支只有知识库（平躺那一支的知识库公式实机对上了），没有实机核对；
- 图标在自己平面里再转 rotation 度（particle_motion_parametric.rotation，PARTICLE_ENGINE §4.6 / §5.5）：正值从正面看逆时针。
方向都是世界里的水平方向 (x, z)。客户端道具（掉落物）的 roll 是"从正面看顺时针转几度"，所以 rotation = -roll。
"""
import math


def flatYaw(dx, dz):
    """平躺的四边形（emitter_transform_xz）：图标的上边要朝世界水平方向 (dx, dz) 时，SetRot 的偏航（度）。"""
    return math.degrees(math.atan2(-dx, -dz))


def uprightYaw(dx, dz):
    """竖立的四边形（emitter_transform_xy）：正面要朝世界水平方向 (dx, dz) 时，SetRot 的偏航（度）。"""
    return math.degrees(math.atan2(dx, dz))


def uprightRotation(roll):
    """竖立的图标在平面里从正面看顺时针转 roll 度（掉落物的 roll）：粒子的 rotation 逆时针为正，所以取反。"""
    return -roll
