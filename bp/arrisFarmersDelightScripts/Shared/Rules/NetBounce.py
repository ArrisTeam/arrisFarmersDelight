# -*- coding: utf-8 -*-
"""NetBounce - 安全网的弹跳（双端，纯规则）

JE SafetyNetBlock（FD 1.3.4）：
- fallOn：实体在潜行（isSuppressingBounce）时照常摔（super.fallOn）；否则 causeFallDamage(fallDistance, 0.0F)，一点伤害都没有。
- updateEntityAfterFallOn：潜行时竖直速度照常清零；否则撞上去时在往下掉（vy < 0）就把速度反过来：
  vy = -vy × 系数，系数是生物（LivingEntity）0.6，其它实体（掉落物、船、矿车……）0.8。
引擎的 OnBeforeFallOnBlockServerEvent 给的是摔落距离，不是撞上去那一刻的速度，速度用自由落体推回来
（每刻先按当前速度走一步，再 v = (v + 0.08) × 0.98，往下的速度；JE 与基岩版的重力、阻力都是这两个数）。
"""
LIVING_FACTOR = 0.6
OTHER_FACTOR = 0.8
GRAVITY = 0.08
DRAG = 0.98
# 摔落距离不到这么多不弹（落地的小颠簸；JE 站在网上会一直微微颠，这里不跟）
MIN_FALL = 0.5
# 自由落体的末速度 ≈ 3.92 格/刻，几十刻就到；保险上限
MAX_TICKS = 400


def impactSpeed(fallDistance):
    """从静止自由落体 fallDistance 格，撞上去那一刻往下的速度（格/刻，正数）。"""
    speed = 0.0
    fallen = 0.0
    for _ in range(MAX_TICKS):
        if fallen + speed >= fallDistance:
            return speed
        fallen += speed
        speed = (speed + GRAVITY) * DRAG
    return speed


def bounceFactor(living):
    """生物 0.6，其它实体 0.8。"""
    return LIVING_FACTOR if living else OTHER_FACTOR


def bounceSpeed(fallDistance, living):
    """弹起来的竖直速度（格/刻，向上为正）；落得太近、不弹返回 0。"""
    if fallDistance <= MIN_FALL:
        return 0.0
    return impactSpeed(fallDistance) * bounceFactor(living)
