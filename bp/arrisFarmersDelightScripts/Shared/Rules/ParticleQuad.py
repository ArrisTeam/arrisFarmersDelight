# -*- coding: utf-8 -*-
"""ParticleQuad - 脚本放的粒子四边形怎么摆：SetRot 的偏航（双端，纯逻辑）

没绑定的发射器 SetRot((0, ψ, 0)) 得到 E = Ry(ψ)，它的三列是 E.x = (cos ψ, 0, -sin ψ)、E.y = (0, 1, 0)、E.z = (sin ψ, 0, cos ψ)；
emitter_transform_* 的四边形铺在 E 的轴上（Strata 引擎知识库 PARTICLE_ENGINE §5.3 / §5.4，粒子的 size 是半边长）：
- emitter_transform_xz（平躺）：图标右 = E.x、上 = -E.z、朝上。**实机核对过**（2026-11-17，物品图标粒子）：不转时上边朝世界 -z、右边朝 +x，
  转 ψ 后上边朝 (-sin ψ, -cos ψ)、右边朝 (cos ψ, -sin ψ)。
方向是世界里的水平方向 (x, z)。
"""
import math


def flatYaw(dx, dz):
    """平躺的四边形（emitter_transform_xz）：图标的上边要朝世界水平方向 (dx, dz) 时，SetRot 的偏航（度）。"""
    return math.degrees(math.atan2(-dx, -dz))
