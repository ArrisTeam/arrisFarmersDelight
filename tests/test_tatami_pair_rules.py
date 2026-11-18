# -*- coding: utf-8 -*-
# runner: both
"""榻榻米方块两两配对的规则（Shared/Rules/TatamiPair.py）对照 JE 的 TatamiBlock（FarmersDelight 1.20）。

JE：getStateForPlacement 的 FACING = 点的面的反方向；玩家没潜行、被点的方块是没配对的榻榻米时 PAIRED；
setPlacedBy 把被点的那块改成 FACING 指回新块、PAIRED；updateShape：FACING 那一格不再是榻榻米时 PAIRED 变假，FACING 不变。
"""
from __future__ import print_function

import fdtest

Pair = fdtest.load("Shared.Rules.TatamiPair")
Placement = fdtest.load("Shared.Rules.Placement")
T = Pair.TATAMI


def testDirectionsAreTheNeteaseFacingEnumOfThePlacementEvent():
    # 0 下 1 上 2 北 3 南 4 西 5 东：和 Placement._FACE_OFFSET（点哪一面、新方块放在哪）同一套编号
    offsets = Placement.placePositions(0, 0, 0)
    for facing in range(6):
        assert Pair.step((0, 0, 0), facing) == offsets[facing], facing
        assert Pair.step(Pair.step((3, 4, 5), facing), Pair.opposite(facing)) == (3, 4, 5), facing
    assert [Pair.opposite(f) for f in range(6)] == [Pair.UP, Pair.DOWN, Pair.SOUTH, Pair.NORTH, Pair.EAST, Pair.WEST]


def testFacingPointsBackAtTheClickedBlock():
    clicked = (8, 70, 2)
    for face in range(6):
        mine, partner = Pair.placement(face, True, False, "minecraft:stone", {})
        placed = Pair.step(clicked, face)                          # 新块在被点方块的 face 面外侧
        assert mine == {Pair.FACING: Pair.opposite(face), Pair.PAIRED: 0} and partner is None, face
        assert Pair.step(placed, mine[Pair.FACING]) == clicked, face


def testPlacingAgainstAnUnpairedTatamiPairsBothFacingEachOther():
    for face in range(6):
        mine, partner = Pair.placement(face, True, False, T, {Pair.FACING: 3, Pair.PAIRED: 0})
        assert mine == {Pair.FACING: Pair.opposite(face), Pair.PAIRED: 1}, face
        assert partner == {Pair.FACING: face, Pair.PAIRED: 1}, face   # 被点的那块指回新块（新块在它的 face 面外侧）


def testNoPairWhenSneakingOrNotAPlayerOrTheTatamiIsAlreadyPaired():
    unpaired, paired = {Pair.FACING: 0, Pair.PAIRED: 0}, {Pair.FACING: 2, Pair.PAIRED: 1}
    for byPlayer, sneaking, states in ((True, True, unpaired), (False, False, unpaired), (True, False, paired)):
        mine, partner = Pair.placement(Pair.EAST, byPlayer, sneaking, T, states)
        assert mine == {Pair.FACING: Pair.WEST, Pair.PAIRED: 0} and partner is None, (byPlayer, sneaking, states)
    # 别的方块（长榻榻米垫也不算）
    assert Pair.placement(Pair.UP, True, False, "arris:tatami_full_mat", unpaired)[1] is None


def testMissingOrStrangeStatesReadAsJavasDefaultDownAndUnpaired():
    for states in ({}, None, {Pair.FACING: 7, Pair.PAIRED: 3}, {Pair.FACING: "x"}):
        assert Pair.facingOf(states) == Pair.DOWN and not Pair.isPaired(states), states
    assert Pair.facingOf({Pair.FACING: 4}) == Pair.WEST and Pair.isPaired({Pair.PAIRED: 1})


def testAPairHoldsWhileTheCellItFacesIsATatami():
    assert Pair.keepsPairWith(T)
    for name in ("minecraft:air", "minecraft:stone", "arris:tatami_full_mat", "arris:tatami_half_mat"):
        assert not Pair.keepsPairWith(name), name
    assert Pair.keepsPairWith(Pair.MOVING_BLOCK)                      # 活塞推着走、还在路上
    assert Pair.keepsPairWith(None)                                    # 没加载的格子


def testOldTatamiBlocksReadAsUnpaired():
    """自定义方块态按名字降序从低位往高位排进 aux（arrisCreate BlockStateDecoder 的实测规则）：朝向（6 个值，3 位）的名字更大，
    占低 3 位，配对在第 4 位；改成方块态以前的榻榻米 aux 是 direction 0..3，按位读出来是朝向 0..3、没配对。"""
    layout, start = {}, 0
    for name, count in sorted(((Pair.FACING, 6), (Pair.PAIRED, 2)), reverse=True):
        bits = (count - 1).bit_length()
        layout[name] = (start, bits)
        start += bits
    assert layout == {Pair.FACING: (0, 3), Pair.PAIRED: (3, 1)}
    for aux in range(4):
        states = dict((name, (aux >> first) & ((1 << bits) - 1)) for name, (first, bits) in layout.items())
        assert states == {Pair.FACING: aux, Pair.PAIRED: 0}, aux


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
