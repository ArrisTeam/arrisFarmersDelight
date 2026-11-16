# -*- coding: utf-8 -*-
# runner: both
"""tools/je_model_to_netease.py（JE 方块模型 -> 网易方块模型）：用两边各自的规则逐顶点、逐 UV 对照。

JE 一侧是 FaceBakery 的烘焙：FaceInfo 给每个面四个顶点的次序，BlockFaceUV 按面旋转挑 UV，元素旋转绕 origin 右手转 angle。
网易一侧照 Strata 知识库 kb/engine/rp/16_netease_block_model（引擎反汇编核实）：立方体 x 取反（x0 = -origin.x - size.x），
面表给每个面四个顶点的次序，四个 UV 角按 rot 向左循环移位，矩阵 [R | q - R·q]，R = Rz(rz)·Ry(-ry)·Rx(-rx)，q = (-px, py, pz)。
每个顶点的位置和它拿到的 UV 两边必须一致（顶点次序两边不同，所以按位置配对）。
"""
from __future__ import print_function

import itertools
import math
import os
import sys

import fdtest

sys.path.insert(0, os.path.join(fdtest.ROOT, "tools"))
import je_model_to_netease as Tool  # noqa: E402

# ---- JE 一侧（FaceInfo：每个顶点取 from / to 的哪一边） ----
JE_VERTICES = {
    "down": [("min", "min", "max"), ("min", "min", "min"), ("max", "min", "min"), ("max", "min", "max")],
    "up": [("min", "max", "min"), ("min", "max", "max"), ("max", "max", "max"), ("max", "max", "min")],
    "north": [("max", "max", "min"), ("max", "min", "min"), ("min", "min", "min"), ("min", "max", "min")],
    "south": [("min", "max", "max"), ("min", "min", "max"), ("max", "min", "max"), ("max", "max", "max")],
    "west": [("min", "max", "min"), ("min", "min", "min"), ("min", "min", "max"), ("min", "max", "max")],
    "east": [("max", "max", "max"), ("max", "min", "max"), ("max", "min", "min"), ("max", "max", "min")],
}

# ---- 网易一侧（P 空间：x0 / x1 是 x 的小 / 大边，下标 0 / 1） ----
ENGINE_VERTICES = {
    "down": [(0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)],
    "up": [(0, 1, 1), (1, 1, 1), (1, 1, 0), (0, 1, 0)],
    "north": [(1, 0, 0), (0, 0, 0), (0, 1, 0), (1, 1, 0)],
    "south": [(0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)],
    "west": [(0, 0, 0), (0, 0, 1), (0, 1, 1), (0, 1, 0)],
    "east": [(1, 0, 1), (1, 0, 0), (1, 1, 0), (1, 1, 1)],
}


def rotate(point, axis, degrees):
    """右手旋转：绕 x：(y, z) -> (y·c - z·s, y·s + z·c)，其余轴依次轮换。"""
    c, s = math.cos(math.radians(degrees)), math.sin(math.radians(degrees))
    x, y, z = point
    if axis == "x":
        return (x, y * c - z * s, y * s + z * c)
    if axis == "y":
        return (x * c + z * s, y, -x * s + z * c)
    return (x * c - y * s, x * s + y * c, z)


def jeFace(element, direction):
    """[(位置, UV)]：JE 烘焙这个面得到的四个顶点。"""
    low, high = element["from"], element["to"]
    face = element["faces"][direction]
    u0, v0, u1, v1 = face["uv"]
    shift = int(face.get("rotation", 0)) // 90
    found = []
    for index, picks in enumerate(JE_VERTICES[direction]):
        point = tuple((low if pick == "min" else high)[axis] for axis, pick in enumerate(picks))
        rotation = element.get("rotation")
        if rotation:
            origin = rotation["origin"]
            local = tuple(point[axis] - origin[axis] for axis in range(3))
            local = rotate(local, rotation["axis"], rotation["angle"])
            point = tuple(local[axis] + origin[axis] for axis in range(3))
        j = (index + shift) % 4
        found.append((point, (u0 if j in (0, 1) else u1, v0 if j in (0, 3) else v1)))
    return found


def matrix(rotation, pivot):
    """立方体矩阵 [R | q - R·q]，返回一个把点变过去的函数。R = Rz(rz)·Ry(-ry)·Rx(-rx)，先转 x 再 y 再 z。"""
    rx, ry, rz = rotation
    q = (-pivot[0], pivot[1], pivot[2])

    def apply(point):
        local = tuple(point[axis] - q[axis] for axis in range(3))
        local = rotate(rotate(rotate(local, "x", -rx), "y", -ry), "z", rz)
        return tuple(local[axis] + q[axis] for axis in range(3))
    return apply


def engineFace(cube, direction):
    """[(位置, UV)]：引擎出这个面得到的四个顶点（P 空间像素）。"""
    origin, size = cube["origin"], cube["size"]
    low = (-origin[0] - size[0], origin[1], origin[2])
    high = tuple(low[axis] + size[axis] for axis in range(3))
    face = cube["uv"][direction]
    u, v = face["uv"]
    w, h = face["uv_size"]
    if direction == "up":
        corners = [(u + w, v), (u, v), (u, v + h), (u + w, v + h)]
    else:
        corners = [(u, v + h), (u + w, v + h), (u + w, v), (u, v)]
    shift = {0: 0, 90: 1, 180: 2}.get(face.get("rot", 0), 3)
    transform = matrix(cube.get("rotation", (0, 0, 0)), cube.get("pivot", (0, 0, 0)))
    found = []
    for k, picks in enumerate(ENGINE_VERTICES[direction]):
        point = tuple((low, high)[pick][axis] for axis, pick in enumerate(picks))
        found.append((transform(point), corners[(k + shift) % 4]))
    return found


def canonical(vertices):
    return sorted((tuple(round(x, 6) + 0.0 for x in point), tuple(round(x, 6) + 0.0 for x in uv)) for point, uv in vertices)


def _element(rotation=None, flipU=False, flipV=False, faceRotation=0):
    u = (13, 2) if flipU else (2, 13)
    v = (14, 3) if flipV else (3, 14)
    element = {"from": [2, 3, 5], "to": [11, 9, 14],
               "faces": dict((name, {"uv": [u[0], v[0], u[1], v[1]], "texture": "#t", "rotation": faceRotation}) for name in Tool.FACES)}
    if rotation:
        element["rotation"] = rotation
    return element


def _check(element):
    cube = Tool.convert({"elements": [element]}, "arris:t", "", {"t": "arris:t"})["netease:block_geometry"]["bones"][0]["cubes"][0]
    for direction in Tool.FACES:
        assert canonical(jeFace(element, direction)) == canonical(engineFace(cube, direction)), \
            "%s 面不一致：element=%r\nJE=%r\n网易=%r" % (direction, element, canonical(jeFace(element, direction)), canonical(engineFace(cube, direction)))


def testEveryFaceKeepsItsPositionsAndUvs():
    # 六个面 × 面旋转 0 / 90 / 180 / 270 × 水平 / 竖直翻转
    for faceRotation, flipU, flipV in itertools.product((0, 90, 180, 270), (False, True), (False, True)):
        _check(_element(None, flipU, flipV, faceRotation))


def testElementRotationsAboutEachAxisMatch():
    # 三根轴 × JE 允许的角度（±22.5、±45），元素旋转的 origin 不在元素里也行
    for axis, angle, origin in itertools.product("xyz", (-45, -22.5, 22.5, 45), ([8, 6, 3], [3.5, 12, 10], [16, 0, 0])):
        for faceRotation in (0, 90, 270):
            _check(_element({"angle": angle, "axis": axis, "origin": origin}, faceRotation=faceRotation))


def testFlatPlanesAndTheTopFaceUseNegativeSizes():
    # JE 的顶面区域 [u0, v0, u1, v1] 写进网易是 uv = [u1, v1]、uv_size = [u0 - u1, v0 - v1]（引擎顶面的角另排，见知识库 §5.1）
    model = {"elements": [{"from": [3, 5, 3], "to": [13, 5, 13], "faces": {"up": {"uv": [3, 3, 13, 13], "texture": "#t", "rotation": 180}}}]}
    cube = Tool.convert(model, "arris:t", "", {"t": "arris:t"})["netease:block_geometry"]["bones"][0]["cubes"][0]
    assert cube["origin"] == [-13, 5, 3] and cube["size"] == [10, 0, 10], cube
    assert cube["uv"] == {"up": {"texture": 0, "uv": [13, 13], "uv_size": [-10, -10], "rot": 180}}, cube["uv"]


def testRotationSignsFollowTheEngineConvention():
    # 引擎读 rotation = (-rx, -ry, +rz)、pivot.x 取反：x、y 轴写 -angle，z 轴写 +angle
    assert Tool.rotationOf({"angle": 22.5, "axis": "x", "origin": [8, 6, 3]}) == ([-22.5, 0, 0], [-8, 6, 3])
    assert Tool.rotationOf({"angle": 22.5, "axis": "y", "origin": [8, 6, 3]}) == ([0, -22.5, 0], [-8, 6, 3])
    assert Tool.rotationOf({"angle": -22.5, "axis": "z", "origin": [13, 6, 8]}) == ([0, 0, -22.5], [-13, 6, 8])


def testTexturesAreIndexedInOrderOfFirstUse():
    # 先后按元素、再按引擎的面键顺序（down, up, north, south, west, east），和 JSON 里键怎么排无关（py2 的字典没有顺序）
    model = {"elements": [{"from": [0, 0, 0], "to": [1, 1, 1], "faces": {
        "north": {"uv": [0, 0, 1, 1], "texture": "#b"}, "down": {"uv": [0, 0, 1, 1], "texture": "#a"},
        "up": {"uv": [0, 0, 1, 1], "texture": "#b"}}}]}
    result = Tool.convert(model, "arris:t", "arris:t_icon", {"a": "arris:ta", "b": "arris:tb"})["netease:block_geometry"]
    assert result["description"]["textures"] == ["arris:ta", "arris:tb"], result["description"]["textures"]
    assert result["description"]["item_texture"] == "arris:t_icon"
    assert result["description"]["textures_descriptions"] == [{"width": 16, "length": 16}] * 2
    uv = result["bones"][0]["cubes"][0]["uv"]
    assert (uv["north"]["texture"], uv["down"]["texture"], uv["up"]["texture"]) == (1, 0, 1)


def testUnsupportedInputIsRejected():
    for model in ({"elements": [{"from": [0, 0, 0], "to": [1, 1, 1], "faces": {"up": {"texture": "#t"}}}]},
                  {"elements": [{"from": [0, 0, 0], "to": [1, 1, 1], "rotation": {"angle": 45, "axis": "y", "origin": [8, 8, 8], "rescale": True},
                                 "faces": {"up": {"uv": [0, 0, 1, 1], "texture": "#t"}}}]}):
        try:
            Tool.convert(model, "arris:t", "", {"t": "arris:t"})
        except ValueError:
            continue
        raise AssertionError("应该报错: %r" % model)


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
