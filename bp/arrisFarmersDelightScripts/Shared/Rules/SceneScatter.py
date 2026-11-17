# -*- coding: utf-8 -*-
"""SceneScatter - Diegesis 的 SceneParticles.spawn 的散布：起点 at + gauss * spread、初速 velocity + gauss * max(0.3, |velocity| * 0.25)（双端，纯规则）

JE：DGJ/impl/client/fx/SceneParticles.java 的 spawn（:68-70）和 gauss()（:158-160，nextGaussian() * 0.5F：标准差是一半）；spawnInLiquid（:131-156）里液内泡
的起点高度只取池底上 0.2 到液面之间的下 60%（:143 lerp(random * 0.6F, bottom + 0.2F, fill)）。
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
