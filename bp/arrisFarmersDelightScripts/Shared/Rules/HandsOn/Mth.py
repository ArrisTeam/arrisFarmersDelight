# -*- coding: utf-8 -*-
"""Mth - 数学与取整小工具（双端）

对应 Java 的 net.minecraft.util.Mth / Math 里规则用到的那几个。Java 与 Python 的取整、取余语义不同
（Math.round 是 floor(x + 0.5)，整数除法向零取整，浮点 % 是 fmod），统一收在这里，规则模块不再各写一份。

时间一律是秒。原版以刻计（20 刻/秒）：凡是原版"按整刻取整"的地方，这里用 roundToTick 取整到 0.05 秒的倍数，
数值与原版一致；调用方不想要刻的量化时，各模块的相应函数有 quantize 开关。
"""
import math

TICKS_PER_SECOND = 20.0
TICK = 0.05              # 一刻 = 1/20 秒
EPS = 1.0e-6             # 时间比较的容差（秒），远小于一刻：只吃浮点误差，让"刚好 N 刻"的边界和原版一致
FULL_EPS = 1.0e-9        # "满了"(>= 1.0)的容差：逐步累加 1/N 之后可能停在 0.9999999999
NEVER = -1.0e12          # "从没发生过"的时间戳，对应 Java 的 Long.MIN_VALUE / 2
INFINITY = float("inf")
TWO_PI = 2.0 * math.pi


def clamp(value, low, high):
    """Mth.clamp：整数、浮点通用。"""
    if value < low:
        return low
    return high if value > high else value


def sign(value):
    """Math.signum：-1 / 0 / 1（整数；NaN 按 0）。"""
    return (value > 0) - (value < 0)


def lerp(delta, start, end):
    """Mth.lerp(delta, start, end) = start + delta * (end - start)。"""
    return start + delta * (end - start)


def isFinite(value):
    return not (math.isnan(value) or math.isinf(value))


def floorInt(value):
    """Mth.floor：向负无穷取整。"""
    return int(math.floor(value))


def roundInt(value):
    """Math.round：floor(x + 0.5)（半数向正无穷进位，和 Python 的 round 不同）。"""
    return int(math.floor(value + 0.5))


def truncDiv(numerator, denominator):
    """Java 的整数除法：向零取整（Python 的 // 向负无穷取整，负数时不同）。"""
    quotient = abs(numerator) // abs(denominator)
    return quotient if (numerator >= 0) == (denominator > 0) else -quotient


def wrapRadians(angle):
    """把弧度折进 [-pi, pi)；对应 Mth.wrapDegrees（浮点 % 是 fmod）。"""
    wrapped = math.fmod(angle, TWO_PI)
    if wrapped >= math.pi:
        wrapped -= TWO_PI
    if wrapped < -math.pi:
        wrapped += TWO_PI
    return wrapped


def roundToTick(seconds):
    """取整到整刻，且至少一刻：对应原版 Math.max(1, Math.round(刻数))，结果仍以秒计。"""
    return max(TICK, roundInt(seconds * TICKS_PER_SECOND) / TICKS_PER_SECOND)


def reached(value, goal=1.0):
    """value 是否达到 goal（容忍累加误差）。"""
    return value >= goal - FULL_EPS
