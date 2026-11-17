# -*- coding: utf-8 -*-
# runner: py3
"""没有厚度的面片不能两面都贴图：两个包的实体几何（rp/models/entity、diegesisRp/models/entity）里，哪个方向的尺寸是 0 的方块，
垂直于那个方向的两个面最多只有一个有贴图。方块实体和纸娃娃用的材质（entity_alphatest、本包的几种）都不剔除背面，两面都贴的话两张画在
同一个深度上，来回闪（厨锅的吊把手刚加上时就是这样，用户在游戏里看出来的）。两面画一样的只贴一面（从两边都看得到）；两面画不一样的
（食谱书翻动的那张纸）给一点厚度把它们分开。"""
from __future__ import print_function

import glob
import io
import json
import os

import fdtest

PAIRS = {0: ("east", "west"), 1: ("up", "down"), 2: ("north", "south")}
ROOTS = (os.path.join(fdtest.ROOT, "rp", "models", "entity"), os.path.join(fdtest.ROOT, "diegesisRp", "models", "entity"))


def _drawn(face):
    """这个面画不画：写了、而且贴图区域不是空的（uv_size 有一边是 0 的不画）。"""
    if not isinstance(face, dict):
        return False
    size = face.get("uv_size")
    return size is None or (size[0] != 0 and size[1] != 0)


def _doubled(path):
    with io.open(path, encoding="utf-8-sig") as handle:
        doc = json.load(handle)
    found = []
    for geometry in doc.get("minecraft:geometry", []):
        for bone in geometry.get("bones", []):
            for cube in bone.get("cubes", []):
                size, uv = cube.get("size", [1, 1, 1]), cube.get("uv")
                for axis in range(3):
                    if size[axis] != 0:
                        continue
                    if not isinstance(uv, dict):
                        found.append((bone["name"], cube.get("origin"), "盒式贴图的方块没有厚度：六个面都会画"))
                    elif _drawn(uv.get(PAIRS[axis][0])) and _drawn(uv.get(PAIRS[axis][1])):
                        found.append((bone["name"], cube.get("origin"), "%s 和 %s 两面都贴了图" % PAIRS[axis]))
    return found


def testNoFlatCubeIsTexturedOnBothOfItsFaces():
    files = [path for root in ROOTS for path in sorted(glob.glob(os.path.join(root, "*.json")))]
    assert len(files) > 5, files
    wrong = dict((os.path.basename(path), _doubled(path)) for path in files)
    wrong = dict((name, found) for name, found in wrong.items() if found)
    assert not wrong, wrong


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
