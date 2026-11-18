# -*- coding: utf-8 -*-
# runner: both
"""榻榻米方块的样子（bp/netease_blocks/arris_tatami.json 的 permutations，tools/gen_tatami.py 生成）对照 JE。

JE 的 tatami：没配对的六面都是正方形的单块（tatami.png = 本包 tatami_mat_half）；配对的两块沿 FACING 拼成一张两格长的榻榻米——
四个侧面上两块的图合起来正好是 tatami_odd 在上、tatami_even 在下那一张（接缝处没有边框，席纹接得上），两头是单块。
这里不重算 JE 的转动，直接把两块在世界里同一面的图按基岩 full_block 的贴图坐标拼起来，逐像素比。
"""
from __future__ import print_function

import os
import re

import blockkit
import fdtest
import pngkit

Pair = fdtest.load("Shared.Rules.TatamiPair")
T = Pair.TATAMI
SINGLE, ODD, EVEN = "arris:tatami_mat_half", "arris:tatami_odd", "arris:tatami_even"
FACES = ("up", "down", "north", "south", "west", "east")
DIRS = {"down": (0, -1, 0), "up": (0, 1, 0), "north": (0, 0, -1), "south": (0, 0, 1), "west": (-1, 0, 0), "east": (1, 0, 0)}
# 基岩 full_block 每个面贴图的 (右, 上)：从外面正对着看。底面和 JE 差 180°（arrisCreate 机壳连接纹理真机标定）
FRAME = {"up": ("east", "north"), "down": ("west", "north"), "north": ("west", "up"), "south": ("east", "up"),
         "west": ("south", "up"), "east": ("north", "up")}
CONDITION = re.compile(r"^q\.block_state\('arris:tatami_facing'\) == (\d) && q\.block_state\('arris:paired'\) == (\d)$")


def _block():
    block = blockkit.readJson(os.path.join(blockkit.BLOCKS_DIR, "arris_tatami.json"))["minecraft:block"]
    return block["description"], block["components"], block["permutations"]


def _looks():
    """{(朝向, 配对): {面: 贴图名}}，从 permutations 的条件读出来。"""
    looks = {}
    for permutation in _block()[2]:
        match = CONDITION.match(permutation["condition"])
        assert match, permutation["condition"]
        key = (int(match.group(1)), int(match.group(2)))
        assert key not in looks, key
        instances = permutation["components"]["minecraft:material_instances"]
        assert instances["*"] == {"texture": SINGLE}
        looks[key] = dict((face, instances[face]["texture"]) for face in FACES)
    return looks


def _pixels(name):
    path = blockkit.terrainTextures()[name]
    width, height, rows = pngkit.read(os.path.join(blockkit.RP, path + ".png"))
    assert (width, height) == (16, 16), name
    return rows


def _clockwise(rows):
    height, width = len(rows), len(rows[0])
    return [[rows[height - 1 - x][y] for x in range(height)] for y in range(width)]


def _turns(rows):
    out = [rows]
    for _ in range(3):
        out.append(_clockwise(out[-1]))
    return out


def _isTurnOf(rows, source):
    return rows in _turns(source)


def _together(first, second, step, face):
    """世界里相邻的两块（second 在 first 沿 step 走一格的地方）在 face 面上合起来的图。"""
    right, up = (DIRS[name] for name in FRAME[face])
    negate = lambda v: tuple(-c for c in v)
    if step == right:
        return [a + b for a, b in zip(first, second)]
    if step == negate(right):
        return [b + a for a, b in zip(first, second)]
    if step == up:
        return second + first
    assert step == negate(up), (step, face)
    return first + second


def testStatesAndOnePermutationForEachOfTheTwelve():
    description, components, permutations = _block()
    assert description["identifier"] == T
    assert description["states"] == {Pair.FACING: [0, 1, 2, 3, 4, 5], Pair.PAIRED: [0, 1]}
    assert len(permutations) == 12 and sorted(_looks()) == [(f, p) for f in range(6) for p in (0, 1)]
    # 走新管线（几何 + 材质实例）才认 permutations 里的贴图；朝向由方块态管，不要 netease:face_directional
    assert components["minecraft:geometry"] == "minecraft:geometry.full_block"
    assert components["minecraft:material_instances"] == {"*": {"texture": SINGLE}}
    assert "netease:face_directional" not in components
    assert components["netease:neighborchanged_sendto_script"] == {"value": True}      # 另一半没了要收到邻格变化


def testBlocksJsonOnlyGivesTheSound():
    # 走新管线的自定义方块，blocks.json 里的 textures 引擎不认还报错（"trying to override the Geometry component"）
    assert blockkit.resourceBlocks()[T] == {"sound": "cloth"}


def testItDropsAPlainTatami():
    # 不写战利品表时引擎把方块的 aux（也就是方块态）带进掉落的物品（实机：拆配了对的一块掉 arris:tatami aux 8），
    # 和普通的榻榻米叠不到一起；JE 掉的就是一个榻榻米
    components = _block()[1]
    table = blockkit.readJson(os.path.join(fdtest.BP, components["minecraft:loot"]))
    [pool] = table["pools"]
    [entry] = pool["entries"]
    assert pool["rolls"] == 1 and entry["name"] == T and {"function": "set_data", "data": 0} in entry["functions"]


def testEveryTextureIsRegisteredAndIsATurnOfJavasThree():
    sources = dict((name, _pixels(name)) for name in (SINGLE, ODD, EVEN))
    for look in _looks().values():
        for face, name in look.items():
            assert blockkit.textureFileExists(blockkit.terrainTextures()[name]), name
            base = re.sub(r"_cw(90|180|270)$", "", name)
            turns = {"": 0, "_cw90": 1, "_cw180": 2, "_cw270": 3}[name[len(base):]]
            assert _pixels(name) == _turns(sources[base])[turns], name


def testLoneTatamiShowTheSquareOnAllSixFaces():
    single = _pixels(SINGLE)
    looks = _looks()
    for facing in range(6):
        for face, name in looks[(facing, 0)].items():
            assert _isTurnOf(_pixels(name), single), (facing, face, name)


def testAPairMakesOneLongMatWithNoSeamOnItsFourSides():
    whole = _pixels(ODD) + _pixels(EVEN)                          # JE：odd 上边有边框、even 下边有边框
    single = _pixels(SINGLE)
    looks = _looks()
    for first, second, axis in ((Pair.UP, Pair.DOWN, "up"), (Pair.SOUTH, Pair.NORTH, "south"), (Pair.EAST, Pair.WEST, "east")):
        step = DIRS[axis]                                          # second 在 first 沿 step 走一格的地方
        back = [face for face in FACES if DIRS[face] == tuple(-c for c in step)][0]
        a, b = looks[(first, 1)], looks[(second, 1)]
        for face in FACES:
            if face in (axis, back):
                continue
            together = _together(_pixels(a[face]), _pixels(b[face]), step, face)
            assert _isTurnOf(together, whole), (axis, face, a[face], b[face])
        # 两头（各自背对另一半的那一面）是单块
        assert _isTurnOf(_pixels(a[back]), single) and _isTurnOf(_pixels(b[axis]), single), axis


def testJavasOwnTurnsOnAFewFaces():
    """几处照 JE 模型手推的：facing=up 用 tatami_odd 不转（北面 odd 转 180、西面 even），facing=down 用 tatami_even 绕 X 转 180；
    没配对的 facing=up 是 cube_all 不转——只有底面差 180°（基岩 full_block 的底面和 JE 反着）。"""
    looks = _looks()
    assert looks[(Pair.UP, 1)]["north"] == ODD + "_cw180" and looks[(Pair.UP, 1)]["west"] == EVEN
    assert looks[(Pair.DOWN, 1)]["north"] == EVEN + "_cw180" and looks[(Pair.DOWN, 1)]["west"] == ODD
    lone = looks[(Pair.UP, 0)]
    assert lone["down"] == SINGLE + "_cw180" and all(lone[face] == SINGLE for face in FACES if face != "down")


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
