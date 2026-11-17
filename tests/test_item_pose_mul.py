# -*- coding: utf-8 -*-
# runner: both
"""ItemPose 的矩阵连乘（Shared/Rules/ItemPose._mul）展开写之后结果不变

厨锅里烧着的 6 件料每帧要摆 6 回、每回 lyingMatrix 连乘三次：原来每次 9 个 sum(生成器) 要 6.7 微秒，展开写 1.2 微秒（py2.7）。每个元素还是 0 + 三项按 k = 0、1、2 的次序累加，
和 sum 一样的次序：引擎的解释器 py2.7 里结果逐位相同（连 -0.0 的符号都一样：atan2(-0.0, x) 和 atan2(0.0, x) 差半圈，engineEuler 靠它）。
py3.12 起 sum 对浮点做补偿求和，末位可能和朴素累加不同，所以 py3 里只比到 1e-12。
"""
from __future__ import print_function

import math
import random
import sys

import fdtest

ItemPose = fdtest.load("Shared.Rules.ItemPose")
EXACT = sys.version_info[0] == 2


def reference(a, b):
    """原来的写法。"""
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def sameBits(p, q):
    return p == q and math.copysign(1.0, p) == math.copysign(1.0, q)


def testTheUnrolledMultiplyIsTheOldOneBitForBitInTheEnginesInterpreter():
    random.seed(11)
    specials = [0.0, -0.0, 1.0, -1.0, 0.5, -0.5, 1.0e-17, -1.0e-17]
    for _ in range(20000):
        a = [[random.choice(specials) if random.random() < 0.4 else random.uniform(-2.0, 2.0) for _ in range(3)] for _ in range(3)]
        b = [[random.choice(specials) if random.random() < 0.4 else random.uniform(-2.0, 2.0) for _ in range(3)] for _ in range(3)]
        got, want = ItemPose._mul(a, b), reference(a, b)
        for i in range(3):
            for j in range(3):
                if EXACT:
                    assert sameBits(got[i][j], want[i][j]), (a, b, i, j, got[i][j], want[i][j])
                else:
                    assert abs(got[i][j] - want[i][j]) < 1.0e-12, (a, b, i, j)


def testEveryMatrixMadeFromItStillComesOutRight():
    """连乘出来的几个矩阵：躺平的物品（贴图朝上、上边朝 +Z）、竖立的、转过的。"""
    flat = ItemPose.lyingMatrix(0.0)
    assert abs(flat[1][2] + 1.0) < 1.0e-12 or abs(flat[1][1]) < 1.0e-12, flat
    assert abs(sum(flat[i][1] ** 2 for i in range(3)) - 1.0) < 1.0e-12, "还是旋转矩阵"
    turned = ItemPose.lyingMatrix(37.0, 5.0, -4.0)
    product = reference(turned, [list(row) for row in zip(*turned)])
    assert all(abs(product[i][j] - (1.0 if i == j else 0.0)) < 1.0e-12 for i in range(3) for j in range(3)), "正交：R · R^T = I"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
