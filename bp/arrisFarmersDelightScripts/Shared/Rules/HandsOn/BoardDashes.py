# -*- coding: utf-8 -*-
"""BoardDashes - 砧板刀口虚线的样子：每一段多长、多宽、多不透明、渐显多久（双端）

移植自 Hands-On Delight 的 client/BoardBehavior.java：drawMarks 画的那一条虚线（1142-1194）和 fade（1206-1208）。长度单位是场景像素，时间是秒，不透明度是 0..1。
虚线是一段一段的小长方形，贴图是白混凝土（WHITE = block/white_concrete，满亮度），乘上 MARK_COLOR 0xA0FFFFFF：不透明度 0xA0 / 255，
新的一条从 0 起用 MARK_FADE 秒线性渐显（Math.round 取整到 1/255）。
"""
import math

MARK_WIDTH = 0.16        # BoardBehavior.java:81 一段的半宽，整宽 0.32
DASH = 0.6               # :82 一段多长
DASH_GAP = 0.45          # :83 段和段之间隔多远
MARK_ALPHA = 0xA0        # :85 MARK_COLOR = 0xA0FFFFFF 的 alpha 字节
MARK_FADE = 0.18         # :203 新的一条虚线用这么久显出来


def dashes(length):
    """drawMarks（1181-1182）：一条长 length 的线上每一段的 (起, 止)（离线头多远）：每 DASH + DASH_GAP 一段，末尾那段截到线尾（不管多短都画）。"""
    out, start = [], 0.0
    while start < length:
        out.append((start, min(length, start + DASH)))
        start += DASH + DASH_GAP
    return out


def markAlpha(age):
    """fade（1206-1208）：新的一条虚线出现 age 秒时的不透明度：MARK_ALPHA 按 age / MARK_FADE 线性长到全，Math.round 取整到字节。"""
    share = min(1.0, max(0.0, age / MARK_FADE))
    return int(math.floor(MARK_ALPHA * share + 0.5)) / 255.0
