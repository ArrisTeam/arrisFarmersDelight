# -*- coding: utf-8 -*-
"""BoardDashes - 砧板刀口虚线和借来的工具的样子：每一段多长、多宽、多不透明、渐显多久（双端）

移植自 Hands-On Delight 的 client/BoardBehavior.java：drawMarks 画的那一条虚线（1142-1194）、fade（1206-1208）、借来的工具的半透明 OFFERED（178）
和 moveKnife / moveTool 里的 setTint（868、932）。长度单位是场景像素，时间是秒，不透明度是 0..1。
虚线是一段一段的小长方形，贴图是白混凝土（WHITE = block/white_concrete，满亮度），乘上 MARK_COLOR 0xA0FFFFFF：不透明度 0xA0 / 255，
新的一条从 0 起用 MARK_FADE 秒线性渐显（Math.round 取整到 1/255）。
"""
import math

MARK_WIDTH = 0.16        # BoardBehavior.java:81 一段的半宽，整宽 0.32
DASH = 0.6               # :82 一段多长
DASH_GAP = 0.45          # :83 段和段之间隔多远
MARK_ALPHA = 0xA0        # :85 MARK_COLOR = 0xA0FFFFFF 的 alpha 字节
MARK_FADE = 0.18         # :203 新的一条虚线用这么久显出来
OFFERED_ALPHA = 0x8C     # :178 OFFERED = 0x8CFFFFFF 的 alpha 字节：手空着、从背包里借来悬在食物上的工具


def dashes(length):
    """drawMarks（1181-1182）：一条长 length 的线上每一段的 (起, 止)（离线头多远）：每 DASH + DASH_GAP 一段，末尾那段截到线尾（不管多短都画）。"""
    out, start = [], 0.0
    while start < length:
        out.append((start, min(length, start + DASH)))
        start += DASH + DASH_GAP
    return out


def layout(a, b):
    """从 a 到 b（场景里的点 (x, z)）的一条虚线每一段放在哪：[((中点 x, 中点 z), 半长), ...]，从 a 往 b 的顺序（drawMarks 里一段的两端取平均）。"""
    dx, dz = b[0] - a[0], b[1] - a[1]
    length = math.hypot(dx, dz)
    return [((a[0] + dx * (first + last) / 2.0 / length, a[1] + dz * (first + last) / 2.0 / length), (last - first) / 2.0)
            for first, last in dashes(length)]


def markAlpha(age):
    """fade（1206-1208）：新的一条虚线出现 age 秒时的不透明度：MARK_ALPHA 按 age / MARK_FADE 线性长到全，Math.round 取整到字节。"""
    share = min(1.0, max(0.0, age / MARK_FADE))
    return int(math.floor(MARK_ALPHA * share + 0.5)) / 255.0


def offeredAlpha(striking):
    """借来的工具（手空着，背包里的）的不透明度：悬着只是提议，OFFERED_ALPHA（半透明）；落下去那一下（刀 chopAge、别的工具 strokeAge 在走）变实。"""
    return 1.0 if striking else OFFERED_ALPHA / 255.0
