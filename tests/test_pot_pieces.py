# -*- coding: utf-8 -*-
# runner: both
"""煮好的汤里浮着的碎料（Shared/Rules/HandsOn/PotPiecesKinds.py + PotPieces.py）：数值照 Hands-On Delight 的 CookedPieces / PotBehavior.pieces 和
Diegesis 的 LiquidPieces。

Java：块数 min(32, 14 + 5 * 份数)；蛋 -> 蛋白条 + 蛋黄块，谷物 -> 3 小粒，意面 -> 2 条丝，肉 -> 大块 + 小块，绿的 -> 叶 + 丝，其余 -> 币 + 小块，
每 2 块食材后一滴油；金角 2.3999631、向外步长 0.7548777、离壁 REACH 0.9；从面下 2.2 像素用 0.55 秒冒上来（过冲 2.6）；随汤转
流速 * (0.45 + 0.75 * reach)；躲勺子（半径 1.05）和整件的料（1.15）；走的时候缩没（半衰期 0.16 秒）；最多 48 块；每个新块一声 blub。
"""
from __future__ import print_function

import math

import fdtest

Kinds = fdtest.load("Shared.Rules.HandsOn.PotPiecesKinds")
Pieces = fdtest.load("Shared.Rules.HandsOn.PotPieces")
One = fdtest.load("Shared.Rules.HandsOn.PotPiecesPiece")
Colors = fdtest.load("Shared.Rules.HandsOn.PotColors")
DT = 0.01
ORANGE = 0xFF8600
GREEN = 0x30CC11
BROTH = 0xB87917


def nuggets(count):
    return [Kinds.floater(Kinds.NUGGET, 0x808080 + index, 1.2) for index in range(count)]


def traitsFor(table):
    return lambda item: table.get(item, ())


def sequence(values):
    """按次序给定值的"随机数"。"""
    left = list(values)
    return lambda: left.pop(0)


def colorsFor(table):
    return lambda item: table[item]


def run(pieces, seconds, dt=DT, surface=0.0, height=None):
    """推进 seconds 秒；返回 [(时刻, drawn, events)]。"""
    out = []
    for index in range(int(round(seconds / dt))):
        drawn, events = pieces.step(dt, surface, height)
        out.append((round((index + 1) * dt, 6), drawn, events))
    return out


def testPieceCountFollowsTheServings():
    count = Kinds.piecesCount
    assert [count(n) for n in (0, 1, 2, 3, 4, 5, 20)] == [0, 19, 24, 29, 32, 32, 32], "min(32, 14 + 5 * 份数)"
    assert (Kinds.PIECES_BASE, Kinds.PIECES_PER_SERVING, Kinds.PIECES_MOST) == (14, 5, 32)
    assert count(-3) == 0


def testWhichIngredientsLeavePieces():
    remainders = set(["milk_bucket", "milk_bottle"])
    dissolves = set(["sugar", "bone"])
    cookedAs = {"beef": "steak", "egg": "fried_egg"}
    found = Kinds.ingredientsOf(["beef", "milk_bucket", "carrot", "sugar", "egg", "beef", "bone", "carrot", "milk_bottle"],
                                lambda item: item in remainders, lambda item: item in dissolves, lambda item: cookedAs.get(item, item))
    assert found == ["steak", "carrot", "fried_egg"], "奶桶剩桶不是食材，糖溶掉、骨头拣出来，重复的只算一次，按熟食算，先后不变"
    assert Kinds.ingredientsOf(["a", "b"], lambda item: False, lambda item: False) == ["a", "b"], "不给 cooked 就是原样"


def testCutByWhatItIs():
    cut = Kinds.cut
    assert cut(0, ["egg"]) == [("shred", 0xF4F1E6, 1.3, True), ("nugget", 0xF2C230, 1.2, True)], "蛋：蛋白条 + 蛋黄块（固定颜色）"
    assert cut(ORANGE, ["grain"]) == [("nugget", ORANGE, 0.75, True)] * 3, "谷物：三小粒"
    assert cut(ORANGE, ["pasta"]) == [("shred", ORANGE, 1.3, True)] * 2, "意面：两条丝"
    assert cut(ORANGE, ["meat"]) == [("chunk", ORANGE, 1.65, True), ("nugget", ORANGE, 1.2, True)], "肉：大块 + 小块"
    assert cut(GREEN, []) == [("leaf", GREEN, 1.3, True), ("shred", GREEN, 1.3, True)], "绿的：叶 + 丝"
    coin = cut(ORANGE, [])
    assert coin[0][:2] == ("coin", ORANGE) and abs(coin[0][2] - 1.65 * 0.9) < 1e-9 and coin[1] == ("nugget", ORANGE, 1.2, True), "其余：币（大小 * 0.9）+ 小块"


def testTheCutOrderOfPrecedence():
    cut = Kinds.cut
    assert cut(GREEN, ["egg", "meat"])[0][0] == "shred" and cut(GREEN, ["egg", "meat"])[0][1] == Kinds.EGG_WHITE, "蛋最先"
    assert cut(GREEN, ["grain", "pasta", "meat"])[0][0] == "nugget", "再是谷物"
    assert cut(GREEN, ["pasta", "meat"])[0][0] == "shred" and cut(GREEN, ["meat"])[0][0] == "chunk", "再是意面、肉；然后才看绿不绿"


def testFatDropsAfterEveryTwoPieces():
    traits = traitsFor({"egg": ["egg"], "rice": ["grain"]})
    colors = colorsFor({"rice": ORANGE, "carrot": ORANGE, "steak": ORANGE})
    pieces = Kinds.cookedPieces(["rice", "egg"], BROTH, traits, colors)
    # 米 3 粒 + 蛋 2 块 = 5 块食材：5 // 2 = 2 滴，插在下标 2 和 5
    assert [piece[0] for piece in pieces] == ["nugget", "nugget", "drop", "nugget", "shred", "drop", "nugget"]
    four = Kinds.cookedPieces(["carrot", "steak"], BROTH, lambda item: ["meat"] if item == "steak" else [], colors)
    assert [piece[0] for piece in four] == ["coin", "nugget", "drop", "chunk", "nugget", "drop"], "四块食材：每两块一滴油"
    six = Kinds.cookedPieces(["carrot", "steak", "rice"], BROTH, lambda item: ["meat"] if item == "steak" else [], colors)
    assert [piece[0] for piece in six] == ["coin", "nugget", "drop", "chunk", "nugget", "drop", "coin", "nugget", "drop"], "六块：三滴，最后一滴接在末尾"
    drop = four[2]
    assert drop == ("drop", Colors.lighter(BROTH, 0.55), 0.75, False), "油滴：比汤色亮 0.55、大小 0.75、不是实心的"
    assert Kinds.cookedPieces([], BROTH, traits, colors) == []


def testTheColourOfAnEggIsNeverAskedFor():
    asked = []
    Kinds.cookedPieces(["egg"], BROTH, lambda item: ["egg"], lambda item: asked.append(item) or 0)
    assert asked == [], "Java 的 cut 对蛋直接用固定的白和黄"


def testFirstPieceTakesTheFirstSpotOnTheGoldenSpiral():
    piece = One.Piece(Kinds.floater("coin", 1, 1.0), 3, lambda: 0.5)
    assert abs(piece.angle - 3 * 2.3999631) < 1e-12
    assert abs(piece.reach - math.sqrt(0.06 + 0.94 * ((3 * 0.7548777) % 1.0))) < 1e-12
    assert abs(One.Piece(Kinds.floater("coin", 1, 1.0), 0, lambda: 0.5).reach - math.sqrt(0.06)) < 1e-12
    assert One.GOLDEN_ANGLE == 2.3999631 and One.OUTWARD_STEP == 0.7548777 and Pieces.REACH == 0.9
    # 随机数的次序：wander、yaw、shade、mirrored
    made = One.Piece(Kinds.floater("coin", 1, 1.0), 1, sequence([0.25, 0.5, 0.75, 0.1]))
    assert made.wander == -0.5 and abs(made.yaw - math.pi) < 1e-12 and abs(made.shade - 0.975) < 1e-12 and made.mirrored
    film = One.Piece(Kinds.floater("drop", 1, 0.75, False), 1, sequence([0.0, 1.0, 0.5, 0.9]))
    assert abs(film.yaw - 0.45) < 1e-12 and film.wander == -1.0, "油滴的朝向在 -0.45..0.45 里（只是膜）：(rand - 0.5) * 0.9"


def testPiecesComeUpOneAtATimeOnceTheLastIsGrown():
    pieces = Pieces.PotPieces(lambda: 0.5)
    pieces.set(nuggets(3), 10)
    timeline = run(pieces, 0.5)
    counts = dict((at, len(drawn)) for at, drawn, _events in timeline)
    assert counts[0.01] == 1 and counts[0.05] == 1, "先长出一块"
    # 第一块长到 grown > 0.3 才长第二块：1 - 0.5 ** (t / 0.16) > 0.3 -> t > 0.0823 秒，第 9 步（0.09 秒）才到，下一步的开头才看到
    assert counts[0.09] == 1 and counts[0.1] == 2
    assert counts[0.5] == 6, "每 0.1 秒一块（0.01 秒一步）"
    assert pieces.made == len(pieces.pieces) == 6


def testAtMostFortyEightFloatAtOnce():
    pieces = Pieces.PotPieces(lambda: 0.5)
    pieces.set(nuggets(5), 100)
    run(pieces, 12.0, dt=0.05)
    assert len(pieces.pieces) == 48 == Pieces.MAX
    assert pieces.wanted == 48


def testAPieceRisesFromBelowWithAnOvershootAndRingsTheSurfaceOnce():
    assert One.overshot(0.0) == 0.0 and abs(One.overshot(1.0) - 1.0) < 1e-12
    peak = max(One.overshot(index / 1000.0) for index in range(1001))
    assert abs(peak - 1.2009) < 1e-3, "过冲：冲到 1.2 左右再落回 1"
    pieces = Pieces.PotPieces(lambda: 0.5)
    pieces.set(nuggets(1), 1)
    timeline = run(pieces, 1.0, surface=5.0)
    first = timeline[0][1][0]
    assert abs(first["pos"][1] - (5.0 + 0.16 + 1.2 * 0.1 - 2.2 * (1.0 - One.overshot(DT / 0.55)))) < 1e-9, "起头在面下 2.2 像素"
    rings = [(at, e) for at, _d, events in timeline for e in events if e["type"] == "ripple"]
    assert len(rings) == 1 and rings[0][1]["strength"] == 0.14, "冒到面上（过冲曲线到 0.9）时敲一圈涟漪，只一圈"
    assert 0.12 <= rings[0][0] <= 0.14, "0.55 秒的冒起里 t = 0.229 的地方：0.126 秒"
    settled = timeline[-1][1][0]
    assert abs(settled["pos"][1] - (5.0 + 0.16 + 0.12)) < 0.01, "冒完了浮在面上 LIFT + 0.1 * 大小"
    assert settled["grow"] > 0.98, "1 秒后 1 - 0.5 ** (1 / 0.16) = 0.987"


def testTheYHeightFollowsTheWavesAndGrowsWithTheSurface():
    pieces = Pieces.PotPieces(lambda: 0.5)
    pieces.set(nuggets(1), 1)
    run(pieces, 1.0)
    flat = pieces.step(DT, 0.0)[0][0]["pos"][1]
    pieces2 = Pieces.PotPieces(lambda: 0.5)
    pieces2.set(nuggets(1), 1)
    run(pieces2, 1.0)
    waved = pieces2.step(DT, 2.0, lambda u, v: 0.3)[0][0]["pos"][1]
    assert abs((waved - flat) - (2.0 - 0.3)) < 1e-6, "y = 面高 + ... - 波高"


def testPiecesTurnWithTheCurrentAtAnAngularRateByReach():
    pieces = Pieces.PotPieces(lambda: 0.5)
    pieces.set(nuggets(1), 1)
    pieces.setCurrent(1.0)
    run(pieces, 0.01)
    piece = pieces.pieces[0]
    start = piece.angle
    run(pieces, 2.0)
    assert abs((piece.angle - start) - 2.0 * (0.45 + 0.75 * piece.reach)) < 1e-9, "角速度 = 流速 * (0.45 + 0.75 * reach)（wander 为 0）"
    pieces.setCurrent(-0.5)
    before = piece.angle
    run(pieces, 1.0)
    assert piece.angle < before, "反向转"


def testLeavingShrinksAwayWithAHalfLifeOfSixteenHundredths():
    pieces = Pieces.PotPieces(lambda: 0.5)
    pieces.set(nuggets(2), 2)
    run(pieces, 2.0)
    assert len(pieces.pieces) == 2
    pieces.set(nuggets(2), 0)
    timeline = run(pieces, 0.16)
    assert abs(timeline[-1][1][0]["grow"] - 0.5) < 0.02, "半衰期 0.16 秒"
    assert all(piece["leaving"] for piece in timeline[-1][1])
    run(pieces, 1.0)
    assert pieces.pieces == [], "缩到 0.02 以下就拿掉：1 -> 0.02 要 0.9 秒"


def testANewKindOfPieceReplacesTheOldOnes():
    pieces = Pieces.PotPieces(lambda: 0.5)
    pieces.set(nuggets(2), 3)
    run(pieces, 1.5)
    assert len(pieces.pieces) == 3 and not any(piece.leaving for piece in pieces.pieces)
    other = [Kinds.floater(Kinds.LEAF, GREEN, 1.3)]
    pieces.set(other, 3)
    assert all(piece.leaving for piece in pieces.pieces), "换了一批东西，原来的都走"
    run(pieces, 2.0)
    assert [piece.floater for piece in pieces.pieces] == other * 3, "新的一块块冒上来"
    pieces.set(list(other), 3)
    assert not any(piece.leaving for piece in pieces.pieces), "同一批东西（值相等）不折腾"


def testPiecesStayOutOfTheSpoonAndBetweenTheWalls():
    pieces = Pieces.PotPieces(lambda: 0.5)
    pieces.set(nuggets(3), 12)
    pieces.setObstacles(One.obstaclesOf((0.5, 0.0), [(-1.0, 1.0)]))
    assert pieces.obstacles == [8.5, 8.0, 1.05, 7.0, 9.0, 1.15]
    run(pieces, 3.0, dt=0.02)
    for piece in pieces.pieces:
        assert abs(piece.x - 8.0) <= 4.0 - piece.radius * 0.8 + 1e-9 and abs(piece.z - 8.0) <= 4.0 - piece.radius * 0.8 + 1e-9, "不出壁"
    lone = Pieces.PotPieces(lambda: 0.5)
    lone.set(nuggets(1), 1)
    lone.setObstacles([8.0, 8.0, 1.05])
    run(lone, 2.0, dt=0.02)
    piece = lone.pieces[0]
    assert math.hypot(piece.x - 8.0, piece.z - 8.0) >= 1.05 + piece.radius - 1e-6, "绕开勺子：离勺子至少 1.05 + 自己的半径"


def testTwoPiecesOnTopOfEachOtherAreMovedApart():
    pieces = Pieces.PotPieces(lambda: 0.5)
    first = One.Piece(Kinds.floater("coin", 1, 1.0), 0, lambda: 0.5)
    second = One.Piece(Kinds.floater("coin", 1, 1.0), 1, lambda: 0.5)
    for piece in (first, second):
        piece.x, piece.z, piece.radius = 8.0, 8.0, 1.0
    first.x = 7.9
    pieces.pieces = [first, second]
    pieces._separate()
    assert math.hypot(first.x - second.x, first.z - second.z) >= 2.0 - 1e-9 and first.touching and second.touching


def testSolidPiecesTumbleInAFastCurrentAndFilmsNeverDo():
    pieces = Pieces.PotPieces(lambda: 0.0)
    pieces.set([Kinds.floater("coin", 1, 1.0), Kinds.floater("drop", 1, 0.75, False)], 2)
    pieces.setCurrent(1.0)
    timeline = run(pieces, 0.5)
    last = dict((piece["id"], piece) for piece in timeline[-1][1])
    assert last[0]["flip"] > 1.0, "实心的在流速 1 时翻身（rand 0 一定翻）"
    assert abs(last[1]["flip"]) < 0.1, "油滴是一层膜，不翻"
    slow = Pieces.PotPieces(lambda: 0.0)
    slow.set([Kinds.floater("coin", 1, 1.0)], 1)
    slow.setCurrent(0.3)
    assert abs(run(slow, 0.5)[-1][1][0]["flip"]) < 0.1, "流速不到 0.35 不翻"


def testBlubsAreOnePerNewlyWantedPiece():
    pieces = Pieces.PotPieces(lambda: 0.5)
    pieces.setMeal(nuggets(2), 3)
    events = pieces.step(DT)[1]
    assert len([e for e in events if e["type"] == "blub"]) == 29, "3 份 = 29 块，每块一声"
    pieces.setMeal(nuggets(2), 3)
    assert not [e for e in pieces.step(DT)[1] if e["type"] == "blub"], "没变就不再响"
    pieces.setMeal(nuggets(2), 4)
    assert len([e for e in pieces.step(DT)[1] if e["type"] == "blub"]) == 3, "29 -> 32"
    pieces.setMeal(nuggets(2), 0)
    assert not [e for e in pieces.step(DT)[1] if e["type"] == "blub"] and pieces.wanted == 0
    pieces.setMeal(nuggets(2), 1)
    assert len([e for e in pieces.step(DT)[1] if e["type"] == "blub"]) == 19, "汤空了再有汤，重新数"


def testEmptyFloaterListFloatsNothing():
    pieces = Pieces.PotPieces(lambda: 0.5)
    pieces.set([], 30)
    assert run(pieces, 0.5)[-1][1] == [] and pieces.wanted == 0


def testShadedColourMultipliesEachChannel():
    assert One.shaded(0xFF8040, 1.0) == 0xFF8040
    assert One.shaded(0xFF8040, 0.9) == 0xE6733A
    pieces = Pieces.PotPieces(lambda: 0.5)
    pieces.set([Kinds.floater("coin", 0xFF8040, 1.0)], 1)
    drawn = run(pieces, 0.1)[-1][1][0]
    assert drawn["baseColor"] == 0xFF8040 and drawn["color"] == One.shaded(0xFF8040, 0.95)


def testApproachHalvesTheDistanceEveryHalfLife():
    assert abs(One.approach(0.0, 1.0, 0.16, 0.16) - 0.5) < 1e-12
    assert One.approach(0.3, 1.0, 0.0, 0.1) == 1.0


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
