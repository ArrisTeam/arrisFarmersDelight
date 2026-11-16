# -*- coding: utf-8 -*-
# runner: both
"""汤里的碎料交给着色器的数（Shared/Rules/PotPiecesLook.py）：配料槽的打包、每块是哪个槽切的、钟、位置，
以及顶点着色器里抄的常量、汤面贴图和模型里的面片是不是和它对得上。"""
from __future__ import print_function

import io
import json
import math
import os
import re
import struct

import fdtest

Look = fdtest.load("Shared.Rules.PotPiecesLook")
Kinds = fdtest.load("Shared.Rules.HandsOn.PotPiecesKinds")
Piece = fdtest.load("Shared.Rules.HandsOn.PotPiecesPiece")
Pieces = fdtest.load("Shared.Rules.HandsOn.PotPieces")
RP = os.path.join(fdtest.ROOT, "rp")
TRAITS = {Look.EGG: ["egg"], Look.GRAIN: ["grain"], Look.PASTA: ["pasta"], Look.MEAT: ["meat"], Look.GREEN: [], Look.OTHER: []}
GREEN, ORANGE = 0x4C8A2E, 0xE0802A
PNG_MAGIC = bytearray([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A])


def _single(value):
    """value 存成单精度再读回来（uniform 是单精度）。"""
    return struct.unpack("f", struct.pack("f", value))[0]


def testEveryClassCutsTheWayJeDoes():
    for kind, traits in TRAITS.items():
        color = GREEN if kind == Look.GREEN else ORANGE
        assert Look.classOf(set(traits), color) == kind
        cut = [(floater[0], floater[2]) for floater in Kinds.cut(color, set(traits))]
        assert cut == list(Look.CUTS[kind]), (kind, cut)
    assert Look.classOf(set(["egg", "meat"]), GREEN) == Look.EGG, "蛋最先判"
    assert Look.KINDS.index(Kinds.DROP) == 5 and len(Look.KINDS) == 6


def testTraitsComeFromTheTables():
    assert Look.traitsOf("minecraft:egg") == set(["egg"]) and Look.traitsOf("arris:rice") == set(["grain"])
    assert Look.traitsOf("arris:raw_pasta") == set(["pasta"]) and Look.traitsOf("minecraft:cooked_beef") == set(["meat"])
    assert Look.traitsOf("minecraft:cooked_cod") == set(), "鱼不算肉"
    assert Look.traitsOf("minecraft:carrot") == set()


def testSlotPacksClassAndColour():
    for kind in range(1, 7):
        for color in (0x000000, 0xFFFFFF, 0xB84C28, 0x4C8A2E, 0x123456):
            slot = Look.packSlot(kind, color)
            assert slot == float(int(slot)) and slot < 2 ** 24 and _single(slot) == slot, "单精度装得下"
            back, shown = Look.unpackSlot(slot)
            assert back == kind
            for shift in (16, 8, 0):
                assert abs((shown >> shift & 0xFF) - (color >> shift & 0xFF)) <= 2, (hex(color), hex(shown))


def testDishSlotsFollowTheRecipe():
    stew = [Look.unpackSlot(slot)[0] for slot in Look.dishSlots("arris:cookbeef_stew")]
    assert stew == [Look.MEAT, Look.OTHER, Look.OTHER, Look.NONE], stew        # 熟牛肉、胡萝卜、烤土豆
    pasta = [Look.unpackSlot(slot)[0] for slot in Look.dishSlots("arris:pasta_with_meatballs")]
    assert pasta == [Look.MEAT, Look.PASTA, Look.NONE, Look.NONE], pasta        # 番茄酱是倒进去的，不留碎料
    rice = [Look.unpackSlot(slot)[0] for slot in Look.dishSlots("arris:fried_rice")]
    assert rice[0] == Look.GRAIN and rice[1] == Look.OTHER, "蛋进炉子是煎蛋：照 JE 切成币和小块"
    assert Look.dishSlots("arris:hot_cocoa") == Look.EMPTY, "只有牛奶、糖、可可：汤里不浮东西"
    assert Look.dishSlots("minecraft:not_a_dish") == Look.EMPTY
    assert len(Look.dishSlots("arris:vegetable_noodles")) == Look.SLOTS, "配料再多也只画前四种"
    broth = [Look.unpackSlot(slot)[0] for slot in Look.dishSlots("arris:bone_broth")]
    assert broth[0] != Look.NONE and broth[1] == Look.NONE, "骨头煮完拣出来：只剩发光浆果"


def _jeSources(classes):
    """JE 的碎料表（CookedPieces.of）：每块记成 (槽号, 第几块)，油滴是 (None, 0)。"""
    food = [(slot, part) for slot, kind in enumerate(classes) if kind for part in range(len(Look.CUTS[kind]))]
    for index in range(len(food) // Kinds.PIECES_PER_DROP):
        food.insert(index * (Kinds.PIECES_PER_DROP + 1) + Kinds.PIECES_PER_DROP, (None, 0))
    return food


def testSourceOfMatchesJesList():
    for classes in ([Look.MEAT, 0, 0, 0], [Look.GRAIN, 0, 0, 0], [Look.MEAT, Look.GRAIN, 0, 0], [Look.GRAIN, Look.GRAIN, Look.OTHER, 0],
                    [Look.OTHER, Look.GREEN, Look.PASTA, Look.EGG], [Look.GRAIN, Look.GRAIN, Look.GRAIN, Look.GRAIN]):
        sources = _jeSources(classes)
        for index in range(Look.MOST):
            assert Look.sourceOf(index, classes) == sources[index % len(sources)], (classes, index)
    assert Look.sourceOf(3, [0, 0, 0, 0]) == (None, 0)


def testPiecesSitWhereJesDo():
    """没人搅时，位置就是 LiquidPieces 的螺旋（JE 还互相挤开，差不出一块的宽度）；转起来之后和 JE 差在快慢分了档。"""
    pieces = Pieces.PotPieces(lambda: 0.5)
    pieces.set([Kinds.floater(Kinds.NUGGET, 0x808080, Look.MEAN_SIZE)], Look.MOST)
    drawn = []
    for _ in range(2000):
        drawn, _events = pieces.step(0.01, 6.0)
    assert len(drawn) == Look.MOST
    near = 0
    for piece in drawn:
        x, z = Look.wayOf(piece["id"], 0.0)
        far = math.hypot(piece["pos"][0] - 8.0 - x, piece["pos"][2] - 8.0 - z)
        assert far < 1.0, (piece["id"], far)
        near += far < 0.25
    assert near >= Look.MOST // 2, near
    for index in range(Look.MOST):
        x, z = Look.wayOf(index, 3.0)
        assert max(abs(x), abs(z)) <= Look.HALF * Piece.REACH + 1e-9
        rate = Look.turnRate(Look.reachOf(index))
        assert abs(rate - (0.45 + 0.75 * Look.reachOf(index))) <= 0.5 / Look.TURN_STEPS + 1e-9
        again = Look.wayOf(index, 3.0 + Look.TURN_WRAP)
        assert abs(again[0] - x) < 1e-6 and abs(again[1] - z) < 1e-6, "转角回卷，碎料不跳"


def _run(clock, seconds, wanted, key="a", slots=(1.0, 0.0, 0.0, 0.0), dt=0.01):
    born = []
    for _ in range(int(round(seconds / dt))):
        born += clock.step(dt, wanted, key, slots)
    return born


def testClockBringsPiecesUpOneByOne():
    clock = Look.PiecesClock()
    assert clock.packed() == 0.0 and clock.step(0.05, 0) == []
    born = _run(clock, 1.0, 19)
    assert born == list(range(len(born))) and 8 <= len(born) <= 12, born       # 一秒十二块，冒到面上晚 0.13 秒
    assert abs(clock.limit - 1.0 / Look.STEP) < 0.5 and abs(clock.clock - clock.limit) < 1e-6
    born += _run(clock, 4.0, 19)
    assert born == list(range(19)) and clock.limit == 19.0 and abs(clock.clock - (19.0 + Look.TAIL)) < 1e-6
    packed = clock.packed()
    assert math.floor(packed / Look.CLOCK_ROOM) / Look.LIMIT_STEPS == 19.0
    assert abs(packed - math.floor(packed / Look.CLOCK_ROOM) * Look.CLOCK_ROOM - clock.clock) < 1e-6
    assert abs(_single(packed) - packed) < 0.01, "单精度里钟还有百分之一块的精度"


def testClockShrinksAndRegrowsWithoutTouchingTheRest():
    clock = Look.PiecesClock()
    _run(clock, 6.0, 24)
    settled = clock.clock
    assert _run(clock, 0.1, 19) == [] and 19.0 < clock.limit < 24.0, "盛走一份：最后那几块很快缩没"
    _run(clock, 1.0, 19)
    assert clock.limit == 19.0 and clock.clock == settled, "剩下的不动"
    born = _run(clock, 2.0, 29)
    assert born == list(range(19, 29)) and clock.limit == 29.0 and clock.clock >= settled, "又煮了一批：新的一块块长出来"
    _run(clock, 3.0, 0)
    assert clock.limit == 0.0 and clock.clock == 0.0 and clock.packed() == 0.0


def testAnotherDishWaitsForTheOldPiecesToLeave():
    clock = Look.PiecesClock()
    _run(clock, 6.0, 19, "a", (1.0, 0.0, 0.0, 0.0))
    clock.step(0.01, 19, "b", (2.0, 0.0, 0.0, 0.0))
    assert clock.key == "a" and clock.slots == (1.0, 0.0, 0.0, 0.0) and clock.limit < 19.0
    born = _run(clock, 6.0, 19, "b", (2.0, 0.0, 0.0, 0.0))
    assert clock.key == "b" and clock.slots == (2.0, 0.0, 0.0, 0.0) and born == list(range(19))


def _constants(path):
    text = io.open(path, encoding="utf-8").read()
    return dict((name, float(value)) for name, value in re.findall(r"const float (\w+) = ([-0-9.]+);", text))


def testVertexShaderCarriesTheSameNumbers():
    glsl = _constants(os.path.join(RP, "shaders", "glsl", "arris_pot_broth_vertex.glsl"))
    wanted = {"PIECE_GOLDEN": Piece.GOLDEN_ANGLE, "PIECE_OUTWARD": Piece.OUTWARD_STEP, "PIECE_REACH": Piece.REACH,
              "PIECE_RATES": Look.TURN_STEPS, "PIECE_STEP": Look.STEP, "PIECE_GROW": Piece.APPEAR_HALF_LIFE,
              "PIECE_RISE_TIME": Piece.RISE_TIME, "PIECE_RISE_DEPTH": Piece.RISE_DEPTH, "PIECE_OVERSHOOT": Piece.OVERSHOOT,
              "PIECE_LIFT": Piece.LIFT, "LIMIT_STEPS": Look.LIMIT_STEPS, "CLOCK_ROOM": Look.CLOCK_ROOM, "CLASS_UNIT": Look.CLASS_UNIT,
              "PIECE_BIG": Kinds.BIG, "PIECE_SMALL": Kinds.SMALL, "PIECE_HERB": Kinds.HERB, "PIECE_FAT": Kinds.FAT,
              "PIECE_GRAIN": Kinds.GRAIN, "HALF": Look.HALF}
    for name, value in wanted.items():
        assert name in glsl and abs(glsl[name] - value) < 5e-4, (name, glsl.get(name), value)
    for name, kind in (("COIN", Kinds.COIN), ("CHUNK", Kinds.CHUNK), ("NUGGET", Kinds.NUGGET), ("SHRED", Kinds.SHRED),
                       ("LEAF", Kinds.LEAF), ("DROP", Kinds.DROP)):
        assert glsl[name] == Look.KINDS.index(kind), name
    assert Look.MOST + Look.TAIL < Look.CLOCK_ROOM


def testModelHasOneQuadPerPiece():
    """broth 骨骼：第一张是汤面（贴图坐标在左上 32 x 32），后面 MOST 张碎料面片各占右边的一格，缩在锅心、和汤面一样高
    （着色器从那一点把它撑开、挪到位）。"""
    path = os.path.join(RP, "models", "entity", "cooking_pot.geo.json")
    geometry = json.loads(io.open(path, encoding="utf-8").read())["minecraft:geometry"][0]
    assert geometry["description"]["texture_width"] == 64 and geometry["description"]["texture_height"] == 64
    cubes = [bone for bone in geometry["bones"] if bone["name"] == "broth"][0]["cubes"]
    assert len(cubes) == 1 + Look.MOST
    surface = cubes[0]["uv"]["up"]
    assert sorted([surface["uv"][0], surface["uv"][0] + surface["uv_size"][0]]) == [0, 32]
    seen = set()
    for index, cube in enumerate(cubes[1:]):
        face = cube["uv"]["up"]
        assert cube["origin"] == [-8.01, 2, 7.99] and cube["size"] == [0.02, 0, 0.02] and face["uv_size"] == [6, 6]
        assert face["uv"] == [32 + 8 * (index % 4) + 1, 8 * (index // 4) + 1], (index, face)
        seen.add(tuple(face["uv"]))
    assert len(seen) == Look.MOST


def testBrothSheetIsTheSizeTheShaderExpects():
    """汤面贴图 32 x 512：读 PNG 头就够了（内容由 tools/gen_pot_broth.py 从 Diegesis 的原图拼）。"""
    path = os.path.join(RP, "textures", "entity", "cooking_pot_broth.png")
    with open(path, "rb") as handle:
        head = bytearray(handle.read(24))
    assert head[:8] == PNG_MAGIC and struct.unpack(">II", bytes(head[16:24])) == (32, 512)


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
