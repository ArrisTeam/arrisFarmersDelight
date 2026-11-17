# -*- coding: utf-8 -*-
"""SceneScatter - Diegesis 的 SceneParticles.spawn 的散布：起点 at + gauss * spread、初速 velocity + gauss * max(0.3, |velocity| * 0.25)（双端，纯规则）

JE：DGJ/impl/client/fx/SceneParticles.java 的 spawn（:68-70）和 gauss()（:158-160，nextGaussian() * 0.5F：标准差是一半）；spawnInLiquid（:131-156）里液内泡
的起点高度只取池底上 0.2 到液面之间的下 60%（:143 lerp(random * 0.6F, bottom + 0.2F, fill)）、初速 velocity + (gauss * jitter * 0.3, gauss * jitter, gauss * jitter * 0.3)
（:146-147，左右只有 0.3 倍）、寿命是样式寿命的 3 倍（:148）；update（:162-197）里泡先问有没有浮到液面（pos.y >= ceiling）：浮到了就换成破泡，破泡的寿命到了液面才起一圈水波，
寿命先到的泡悄悄没了。泡的升速是样式的浮力和阻力（DiegesisParticles.java:46-47 的 gravity(-6) / drag(0.8) / life(0.6, 1.4)，破泡 :52 的 life(0.45, 0.85)）。
数的单位和调用方一致：起点和 spread 是像素，初速是像素每秒。煎锅（Compat/Diegesis/PanFx）、炉灶（GrillFx）、厨锅（PotSceneFx）的粒子都经这里；
砧板碎屑（Shared/Rules/BoardDust）的散布在粒子 JSON 里（rp/particles/arris_board_dust.json：方盒发射器 / 方向的均匀随机，半宽 sqrt(3) * 0.5 = 0.866 倍，方差和这里的高斯一样，
tests/test_board_dust.py 对着这里的常数核对）。
"""
import math
import random

GAUSS = 0.5                 # SceneParticles.gauss()：nextGaussian() * 0.5F
JITTER_MIN = 0.3            # :69 Math.max(0.3F, velocity.length() * 0.25F)：初速抖动的下限（像素每秒）
JITTER_PER_SPEED = 0.25     # 同一行：初速长度的四分之一
LOWER_PART = 0.6            # spawnInLiquid :143：液内泡的起点高度取下 60%
LIQUID_FLOOR_GAP = 0.2      # 同一行：离池底 0.2 像素起
LIQUID_SIDE_JITTER = 0.3    # :147：液内泡左右（x、z）的初速抖动只有上下的 0.3 倍
LIQUID_LIFE_SCALE = 3.0     # :148：液内泡的寿命 = 样式寿命 * 3
BUBBLE_LIFE = (0.6, 1.4)    # DiegesisParticles.java:46-47 的 BUBBLE 样式 life(0.6F, 1.4F)（秒）
BUBBLE_BUOYANCY = 6.0       # 同一处 gravity(-6.0F)：负的重力 = 向上 6 像素每二次方秒
BUBBLE_DRAG = 0.8           # 同一处 drag(0.8F)：每秒丢掉 80% 的速度（update :186 乘 (1 - drag) ^ dt）
POP_LIFE = (0.45, 0.85)     # :52 的 BUBBLE_POP 样式 life(0.45F, 0.85F)（秒）
_DRAG_RATE = -math.log(1.0 - BUBBLE_DRAG)                   # 每秒的衰减率：(1 - drag) ^ dt = e ^ (-rate * dt)
_TERMINAL = BUBBLE_BUOYANCY / _DRAG_RATE                    # 浮力和阻力平衡时的升速（像素每秒）


def standard():
    """一个标准正态的随机数（JE 的 random.nextGaussian()）。"""
    return random.gauss(0.0, 1.0)


def spawnPoint(at, spread, normal=standard):
    """一颗粒子的起点：每个轴 at + nextGaussian() * 0.5 * spread。normal 是取标准正态随机数的函数（测试里换成定值）。"""
    return tuple(at[axis] + normal() * GAUSS * spread for axis in range(3))


def jitterOf(velocity):
    """初速的抖动幅度：max(0.3, |velocity| * 0.25)。"""
    return max(JITTER_MIN, math.sqrt(sum(part * part for part in velocity)) * JITTER_PER_SPEED)


def spawnVelocity(velocity, normal=standard):
    """一颗粒子的初速：每个轴 velocity + nextGaussian() * 0.5 * jitter。"""
    jitter = jitterOf(velocity)
    return tuple(velocity[axis] + normal() * GAUSS * jitter for axis in range(3))


def liquidBubbleHeight(bottom, fill, roll):
    """液内的泡起点离站点地面多高（像素）：roll 是 [0, 1) 的随机数，高度 = lerp(roll * 0.6, bottom + 0.2, fill)，最高只到液面下的 60% 处。"""
    low = bottom + LIQUID_FLOOR_GAP
    return low + (fill - low) * (roll * LOWER_PART)


def liquidBubbleVelocity(velocity, normal=standard):
    """一个液内泡的初速（spawnInLiquid :146-147）：每个轴 velocity + gauss * jitter，左右两个轴的抖动只有 0.3 倍。"""
    jitter = jitterOf(velocity)
    side = jitter * LIQUID_SIDE_JITTER
    return (velocity[0] + normal() * GAUSS * side, velocity[1] + normal() * GAUSS * jitter, velocity[2] + normal() * GAUSS * side)


def _lerp(roll, span):
    return span[0] + (span[1] - span[0]) * roll


def liquidBubbleLife(roll):
    """一个液内泡的寿命（秒，:148）：roll 是 [0, 1) 的随机数，样式寿命 0.6 ~ 1.4 秒的 3 倍。"""
    return _lerp(roll, BUBBLE_LIFE) * LIQUID_LIFE_SCALE


def popLife(roll):
    """液面上破泡的寿命（秒）：它的寿命到了，液面才起那一圈水波。"""
    return _lerp(roll, POP_LIFE)


def _risen(speed, seconds):
    """初速 speed（像素每秒）的泡浮了 seconds 秒升了多少像素：浮力和阻力的解析解（update 每步先加浮力再乘阻力，步长小时就是它）。"""
    return _TERMINAL * seconds + (speed - _TERMINAL) * (1.0 - math.exp(-_DRAG_RATE * seconds)) / _DRAG_RATE


def riseTime(height, speed):
    """初速 speed 的泡浮过 height 像素要多久（秒）：update 里 pos.y 第一次到液面（ceiling）的时候；已经到了是 0。"""
    if height <= 0.0:
        return 0.0
    high = 1.0
    while _risen(speed, high) < height and high < 1.0e6:
        high *= 2.0
    low = 0.0
    for _ in range(48):
        middle = (low + high) / 2.0
        if _risen(speed, middle) < height:
            low = middle
        else:
            high = middle
    return high
