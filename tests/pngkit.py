# -*- coding: utf-8 -*-
"""pngkit - 读 PNG 的小工具（不是测试本身，跑器只收 test_*.py）：贴图的像素在两种 Python 里都要能读（8 位、RGB / RGBA、不隔行），
测试拿它核对资源里的颜色；写图是开发机上 py -3 的 tools/ 脚本（要 Pillow）的事。"""
from __future__ import print_function

import struct
import zlib


def _unfilter(kind, line, prior, bpp):
    out = bytearray(len(line))
    for i in range(len(line)):
        left = out[i - bpp] if i >= bpp else 0
        up = prior[i]
        upLeft = prior[i - bpp] if i >= bpp else 0
        if kind == 0:
            value = line[i]
        elif kind == 1:
            value = line[i] + left
        elif kind == 2:
            value = line[i] + up
        elif kind == 3:
            value = line[i] + (left + up) // 2
        else:
            guess = left + up - upLeft
            near = min((abs(guess - left), left), (abs(guess - up), up), (abs(guess - upLeft), upLeft))[1]
            value = line[i] + near
        out[i] = value & 0xFF
    return out


def read(path):
    """-> (宽, 高, 行表)：每行是 (r, g, b, a) 的列表（RGB 的图 a 取 255）。"""
    with open(path, "rb") as handle:
        data = handle.read()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", "不是 PNG：%s" % path
    position, idat, header = 8, b"", None
    while position < len(data):
        length, kind = struct.unpack(">I4s", data[position:position + 8])
        body = data[position + 8:position + 8 + length]
        position += 12 + length
        if kind == b"IHDR":
            header = struct.unpack(">IIBBBBB", body)
        elif kind == b"IDAT":
            idat += body
    width, height, depth, colour, _, _, interlace = header
    assert depth == 8 and colour in (2, 6) and interlace == 0, "只读 8 位 RGB / RGBA 不隔行的图：%s" % (header,)
    bpp = 3 if colour == 2 else 4
    raw = zlib.decompress(idat)
    stride, rows, prior = width * bpp, [], bytearray(width * bpp)
    for y in range(height):
        start = y * (stride + 1)
        line = _unfilter(ord(raw[start:start + 1]), bytearray(raw[start + 1:start + 1 + stride]), prior, bpp)
        prior = line
        rows.append([tuple(line[x * bpp:(x + 1) * bpp]) + ((255,) if bpp == 3 else ()) for x in range(width)])
    return width, height, rows
