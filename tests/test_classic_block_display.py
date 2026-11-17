# -*- coding: utf-8 -*-
# runner: both
"""没装前置包（或砧板站点关着）时砧板 / 煎锅 / 炉灶上东西的世界展示是 FD 自己的渲染器（Shared/Rules/BlockDisplay.py）：
CuttingBoardRenderer、SkilletRenderer、DefaultStoveRenderer 的 PoseStack 逐条照抄成这里的 Java 公式，和我们的摆法逐项对：位置、大小、高度、错开、朝向、一叠几张。
没有场景交互前置包的东西：不导入 dg* 小工具、不 import prereq，只用本仓库的联动小工具（linkkit）拨运行模式。

FD 的几条规矩（client/renderer/*.java）：
- 画的是 ItemDisplayContext.FIXED：贴图物品（item/generated）的 FIXED 变换是绕 Y 转 180 度、缩放 1，所以 scale(s) = s 格宽；方块物品（父模型 block/block）FIXED 缩放 0.5，
  所以 scale(s) = 0.5 * s 格棱长。掉落物缩放 1 时贴图 8 像素宽、方块立方体 4 像素，所以两种都是 Java 缩放的 2 倍。
- 一叠画 getModelCount = 1 + ceil(个数 / 最大叠数 * 4) 张（个数大于 1 时），每张抬高 0.03，x、z 错开 (nextFloat * 2 - 1) * 0.15 * 0.5（种子是物品编号 + 损伤值，
  同一种东西每次都一个样）；砧板上只有一张时不错开，煎锅一张也错开；
- 朝向：绕 Y 转 -dir.toYRot()，dir 是板 / 炉灶的 FACING.getOpposite()、煎锅的 FACING，都是放它的人面朝的方向（板和炉灶的 FACING 朝着人，煎锅的 FACING 是人看的方向）。
"""
from __future__ import print_function

import math

import fdtest
import linkkit

BD = fdtest.load("Shared.Rules.BlockDisplay")
Pose = fdtest.load("Shared.Rules.ItemPose")
Station = fdtest.load("Shared.Rules.BoardStation")
Mode = fdtest.load("Shared.Rules.HandsOnMode")
Table = fdtest.load("Shared.Data.HandsOnConfig")
Scene = fdtest.load("Shared.Rules.HandsOn.BoardScene")

# ---- FD 的 Java，照抄 ----
JAVA_YROT = {"SOUTH": 0.0, "WEST": 90.0, "NORTH": 180.0, "EAST": 270.0}                 # Direction.toYRot
JAVA_OPPOSITE = {"SOUTH": "NORTH", "NORTH": "SOUTH", "WEST": "EAST", "EAST": "WEST"}
FRONT_OF_YAW = {0: "NORTH", 90: "EAST", 180: "SOUTH", 270: "WEST"}                      # 我们的朝向（方块正面 / 锅柄那一侧）= 板、炉灶的 FACING


def _ry(deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return [[c, 0.0, s], [0.0, 1.0, 0.0], [-s, 0.0, c]]


def _rx(deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return [[1.0, 0.0, 0.0], [0.0, c, -s], [0.0, s, c]]


def _mul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def _apply(m, v):
    return tuple(sum(m[i][k] * v[k] for k in range(3)) for i in range(3))


def _javaCount(count, maxStack):
    """getModelCount：1，个数大于 1 时再加 ceil(个数 / 最大叠数 * 4)。"""
    return 1 + int(math.ceil(float(count) / maxStack * 4)) if count > 1 else 1


def _javaFlat(direction, scale):
    """renderItemLayingDown / SkilletRenderer / DefaultStoveRenderer 的转法：Ry(-dir.toYRot) · Rx(90)，贴图物品 FIXED 再转 Y 半圈。
    返回贴图的右方向、上方向（世界里）和边长（格）。"""
    m = _mul(_ry(-JAVA_YROT[direction]), _mul(_rx(90.0), _ry(180.0)))
    return _apply(m, (1.0, 0.0, 0.0)), _apply(m, (0.0, 1.0, 0.0)), scale


def _javaFront(direction, scale):
    """renderBlock：Ry(-dir.toYRot)，方块物品 FIXED 缩放 0.5。返回方块模型北面的朝向和棱长（格）。"""
    return _apply(_ry(-JAVA_YROT[direction]), (0.0, 0.0, -1.0)), scale * 0.5


def _ours(placement):
    """我们摆的这件平躺的东西：贴图的右方向（掉落物的 u 轴是贴图的左边：站在正面看，右边是它的反方向）、上方向、边长（格）。"""
    m = Pose.flatMatrix(placement.direction[0], placement.direction[1])
    return (-m[0][0], -m[1][0], -m[2][0]), (m[0][1], m[1][1], m[2][1]), placement.scale * Pose.ITEM_SPAN / 16.0


def _engineCubeCentre(placement):
    """引擎把方块物品的立方体画在哪：轴心上方 0.2 格（不跟缩放和旋转走），轴心 = 报的中心往下半个贴图边长。"""
    m = Pose.uprightMatrix(placement.direction[0], placement.direction[1], placement.roll)
    pivot = Pose.pivotFor(placement.center, m, placement.scale)
    return pivot[0], pivot[1] + Pose.BLOCK_LIFT / 16.0, pivot[2]


def _close(a, b, eps=1.0e-9):
    return len(a) == len(b) and all(abs(x - y) < eps for x, y in zip(a, b))


def _item(name, count=1, aux=0):
    return {"newItemName": name, "newAuxValue": aux, "count": count}


TOOLS = {"pickaxe": "pickaxe", "hoe": "hoe", "axe": "axe", "shovel": "shovel", "shears": "shears", "trident": "trident"}


def _typeOf(item):
    name = item["newItemName"]
    if name.endswith("_log") or name == "minecraft:poppy":
        return "block"
    if name.endswith("_knife") or name.endswith("_sword"):
        return "sword"
    return TOOLS.get(name.split(":")[-1].split("_")[-1], "food")


MAXES = {"minecraft:egg": 16, "minecraft:ender_pearl": 16}


def _maxStack(item):
    return MAXES.get(item["newItemName"], 64)


ENV = Station.Env(lambda name: name.endswith("_knife"), _typeOf)


def _board(items, yaw=0, **extra):
    return BD.layout(BD.KIND_BOARD, items, _typeOf, (1, 64, 1), yaw=yaw, carving=ENV.isCarving, isBlock=ENV.isBlock, maxStackOf=_maxStack, **extra)


def _skillet(item, yaw=0, pos=(3, 64, -7)):
    return BD.layout(BD.KIND_SKILLET, {"0": item}, _typeOf, pos, yaw=yaw, maxStackOf=_maxStack)


def _standalone():
    """没联动：前置包没装（还没判定当没联动）。"""
    linkkit.unlink()


# ---------------------------------------------------------------- 一叠几张

def testAStackIsDrawnAsManyLayersAsFarmersDelightsGetModelCount():
    assert [BD.modelCount(count, 64) for count in (1, 2, 16, 17, 32, 33, 48, 49, 64)] == [_javaCount(count, 64) for count in (1, 2, 16, 17, 32, 33, 48, 49, 64)]
    assert [BD.modelCount(count, 16) for count in (1, 2, 4, 5, 8, 9, 12, 13, 16)] == [_javaCount(count, 16) for count in (1, 2, 4, 5, 8, 9, 12, 13, 16)]
    assert BD.modelCount(1, 64) == 1 and BD.modelCount(64, 64) == 5 and BD.modelCount(16, 16) == 5 and BD.modelCount(1, 1) == 1
    _standalone()
    for count, maxStack, name in ((1, 64, "minecraft:beef"), (2, 64, "minecraft:beef"), (20, 64, "minecraft:beef"), (64, 64, "minecraft:beef"), (7, 16, "minecraft:egg")):
        assert len(_board({"0": _item(name, count)})) == _javaCount(count, maxStack) == len(_skillet(_item(name, count))), (name, count)


# ---------------------------------------------------------------- 砧板：躺着的东西

def testALyingThingOnTheBoardIsAtTheBlockCentreAtNinePointSixPixelsWhateverTheBoardsBase():
    """renderItemLayingDown：translate(0.5, 0.08 + 0.03 * (i + 1), 0.5)、scale(0.6)：方块正中心（不是 HoD 的板底座中间）、第一张 0.11 格高、9.6 像素宽。"""
    _standalone()
    for yaw in (0, 90, 180, 270):
        food, = _board({"0": _item("minecraft:beef", 1)}, yaw=yaw, offset=(-1.5 / 16.0, 0.0))        # offset 是 HoD 的板底座偏移：FD 的渲染器不看它
        assert food.flat and _close(food.center, (0.5, 0.08 + 0.03, 0.5)), (yaw, food.center)
        right, up, size = _ours(food)
        wantRight, wantUp, wantSize = _javaFlat(JAVA_OPPOSITE[FRONT_OF_YAW[yaw]], 0.6)
        assert _close(right, wantRight) and _close(up, wantUp) and abs(size - wantSize) < 1e-9, (yaw, right, wantRight, up, wantUp, size)


def testAPileOnTheBoardIsStackedThreeHundredthsHigherEachAndScatteredLikeTheRenderer():
    """一叠：每张抬高 0.03（0.11、0.14、0.17……）、x 和 z 各错开最多 0.075（nextFloat * 2 - 1，乘 0.15 * 0.5），朝向都和板一样（不像 HoD 的底下那张转 17 度）。"""
    _standalone()
    pile = _board({"0": _item("minecraft:beef", 20)}, yaw=90)
    assert len(pile) == 3
    for layer, placement in enumerate(pile):
        assert abs(placement.center[1] - (0.08 + 0.03 * (layer + 1))) < 1e-9, layer
        assert abs(placement.center[0] - 0.5) <= 0.075 + 1e-9 and abs(placement.center[2] - 0.5) <= 0.075 + 1e-9, layer
        assert placement.direction == pile[0].direction and placement.scale == pile[0].scale == 1.2 and placement.flat
    spots = [(p.center[0], p.center[2]) for p in pile]
    assert len(set(spots)) == 3 and any(abs(x - 0.5) > 0.005 or abs(z - 0.5) > 0.005 for x, z in spots), "每张各错开一点"
    again = _board({"0": _item("minecraft:beef", 20)}, yaw=90)
    assert [p.center for p in again] == [p.center for p in pile], "同一种东西每次画的一叠都一个样（FD 的种子是物品编号 + 损伤值）"
    elsewhere = BD.layout(BD.KIND_BOARD, {"0": _item("minecraft:beef", 20)}, _typeOf, (50, 70, -9), yaw=90, carving=ENV.isCarving, isBlock=ENV.isBlock, maxStackOf=_maxStack)
    assert [p.center for p in elsewhere] == [p.center for p in pile], "和板在哪个位置无关"
    other = _board({"0": _item("minecraft:cod", 20)}, yaw=90)
    assert [p.center for p in other] != [p.center for p in pile], "别的东西错开得不一样"


def testAFlowerOnTheBoardLiesLikeAnyFoodAndIsReportedWhereTheEngineDrawsItNotFloating():
    """花、野生作物：引擎照方块物品的规矩抬高 0.2 格、轴心在离底边 5/16 处（ItemPose.raisedShift）：报出去的中心反着挪过，引擎画出来的中心就是 FD 的 translate 的那个点
    （和食物一样：第一张 0.11 格高，一叠每张高 0.03，x、z 在 ±0.075 里），不会浮起 0.2 格。"""
    _standalone()
    for yaw in (0, 90, 180, 270):
        for count in (1, 5):
            flowers = _board({"0": _item("minecraft:poppy", count)}, yaw=yaw)
            assert len(flowers) == _javaCount(count, 64) and all(p.flat for p in flowers)
            for layer, flower in enumerate(flowers):
                matrix = Pose.flatMatrix(flower.direction[0], flower.direction[1])
                pivot = Pose.pivotFor(flower.center, matrix, flower.scale)
                reach = (Pose.ITEM_SPAN / 2.0 - Pose.RAISED_PIVOT) * flower.scale / 16.0         # 引擎：轴心到贴图中心，沿贴图自己的上方向
                drawn = (pivot[0] + matrix[0][1] * reach, pivot[1] + Pose.BLOCK_LIFT / 16.0 + matrix[1][1] * reach, pivot[2] + matrix[2][1] * reach)
                assert abs(drawn[1] - (0.08 + 0.03 * (layer + 1))) < 1e-9, (yaw, count, layer, drawn)
                spread = 1e-9 if count == 1 else 0.075 + 1e-9
                assert abs(drawn[0] - 0.5) <= spread and abs(drawn[2] - 0.5) <= spread, (yaw, count, layer, drawn)
                assert _close(_ours(flower)[1], _javaFlat(JAVA_OPPOSITE[FRONT_OF_YAW[yaw]], 0.6)[1]), "朝向和别的食物一样"


# ---------------------------------------------------------------- 砧板：方块类和插着的工具

def testABlockOnTheBoardIsFarmersDelightsPointEightBlockSitting0Point27High():
    """renderBlock：translate(0.5, 0.27 + 0.03 * (i + 1), 0.5)、scale(0.8)：方块 FIXED 缩放 0.5，立方体 0.4 格（6.4 像素）棱长，中心 0.30 格高（不是 HoD 的 5.2 像素）；
    正面朝板的 FACING 那一侧（Ry(-dir.toYRot) 转的）。"""
    _standalone()
    for yaw in (0, 90, 180, 270):
        block, = _board({"0": _item("minecraft:oak_log")}, yaw=yaw, offset=(-1.5 / 16.0, 0.0))
        assert not block.flat and abs(block.scale * 4.0 / 16.0 - 0.4) < 1e-9, yaw
        centre = _engineCubeCentre(block)
        assert _close(centre, (0.5, 0.27 + 0.03, 0.5)), (yaw, centre)
        front, edge = _javaFront(JAVA_OPPOSITE[FRONT_OF_YAW[yaw]], 0.8)
        assert _close(block.direction, (front[0], front[2])) and abs(block.scale * 4.0 / 16.0 - edge) < 1e-9, (yaw, block.direction, front)
    pile = _board({"0": _item("minecraft:oak_log", 20)})
    assert [round(_engineCubeCentre(p)[1], 6) for p in pile] == [0.30, 0.33, 0.36], "一叠的方块一张比一张高 0.03"


def testAStuckToolIsStillFarmersDelightsCarvedToolInBothModes():
    """renderItemCarved 两种模式本来就是同一个（砧板站点里、世界里都画它）：方块正中心、0.23 格高、0.6 倍、镐 / 锄 225、三叉戟 135、别的 180。"""
    for linked in (False, True):
        if linked:
            linkkit.link()
        else:
            _standalone()
        for yaw in (0, 90, 180, 270):
            tool, = _board({"0": _item("arris:iron_knife")}, yaw=yaw, offset=(-1.5 / 16.0, 0.0))
            assert not tool.flat and _close(tool.center, (0.5, 0.23, 0.5)) and abs(tool.scale * 8.0 / 16.0 - 0.6) < 1e-9, (linked, yaw)
            assert tool.roll == Scene.carvedRoll("sword") and tool.direction == BD.carvedFront(yaw)
    _standalone()


# ---------------------------------------------------------------- 站点在场时板上的东西照站点（开关站不跳）

def testWithTheBoardStationOnTheBoardKeepsTheStationsLayoutAndWithItOffFarmersDelightsOwn():
    food = {"0": _item("minecraft:beef", 5)}
    _standalone()
    fd = _board(food)
    assert len(fd) == _javaCount(5, 64) == 2 and abs(fd[0].scale - 1.2) < 1e-9, "FD：1 + ceil(5 / 64 * 4) = 2 张，9.6 像素宽"
    linkkit.link()
    try:
        hod = _board(food, offset=(-1.5 / 16.0, 0.0))
        assert len(hod) == 2 and hod[1].center[1] - hod[0].center[1] > 0.03, "站点里的一叠：底下垫一张转 17 度，上面那张抬 0.65 像素"
        assert abs(hod[0].scale - Scene.itemScale()) < 1e-9 and abs(hod[1].center[0] - (0.5 - 1.5 / 16.0)) < 1e-9, "10 像素宽、躺在板底座的中间"
        assert hod[0].direction != hod[1].direction
        original = dict(Table.CONFIG)
        Table.CONFIG["cutting_board"] = False
        try:
            off = _board(food)
            assert [p.center for p in off] == [p.center for p in fd], "联动着、配置里关了砧板站点：没有站点可对，一样是 FD 的渲染器"
        finally:
            Table.CONFIG.clear()
            Table.CONFIG.update(original)
    finally:
        _standalone()


# ---------------------------------------------------------------- 煎锅

def testTheSkilletDrawsFarmersDelightsPointFiveSizedThingsScatteredEvenWhenAlone():
    """SkilletRenderer：translate(0.5 + x, 0.1 + 0.03 * (i + 1), 0.5 + z)、scale(0.5)：8 像素宽、第一张 0.13 格高、一张也错开（和砧板不一样）、朝向跟着锅
    （FACING 是人看的方向，锅柄朝人：我们的朝向是锅柄那一侧）。"""
    _standalone()
    for yaw in (0, 90, 180, 270):
        lone, = _skillet(_item("minecraft:beef", 1), yaw=yaw)
        assert lone.flat and abs(lone.center[1] - 0.13) < 1e-9 and abs(lone.scale * 8.0 / 16.0 - 0.5) < 1e-9, yaw
        assert abs(lone.center[0] - 0.5) <= 0.075 + 1e-9 and abs(lone.center[2] - 0.5) <= 0.075 + 1e-9
        facing = JAVA_OPPOSITE[FRONT_OF_YAW[yaw]]                      # 锅的 FACING = 放它的人面朝的方向 = 锅柄那一侧的反方向
        right, up, size = _ours(lone)
        wantRight, wantUp, wantSize = _javaFlat(facing, 0.5)
        assert _close(right, wantRight) and _close(up, wantUp) and abs(size - wantSize) < 1e-9, (yaw, right, wantRight)
    assert abs(_skillet(_item("minecraft:beef", 1))[0].center[0] - 0.5) > 1e-6 or abs(_skillet(_item("minecraft:beef", 1))[0].center[2] - 0.5) > 1e-6, "错开不是 0"


def testASkilletPileGoesUpThreeHundredthsPerLayerAndIsTheSameEveryTime():
    _standalone()
    pile = _skillet(_item("minecraft:beef", 40))
    assert len(pile) == _javaCount(40, 64) == 4
    assert [round(p.center[1], 6) for p in pile] == [0.13, 0.16, 0.19, 0.22]
    assert all(p.direction == pile[0].direction and p.scale == 1.0 for p in pile), "只有错开，没有每张各转一点"
    assert [p.center for p in _skillet(_item("minecraft:beef", 40), pos=(9, 9, 9))] == [p.center for p in pile], "和锅在哪个位置无关，同一种东西每次一个样"
    assert _skillet(_item("minecraft:beef", 0)) == [] and _skillet({}) == [] and _skillet(None) == []


# ---------------------------------------------------------------- 炉灶

def testTheStoveIsFarmersDelightsDefaultStoveRendererAtOnePointZeroTwo():
    """DefaultStoveRenderer：translate(0.5, 1.02, 0.5)、转 -FACING.getOpposite().toYRot()、再 translate(offset)、scale(0.375)：6 像素宽、1.02 格高（原来 1.015）；
    位置和朝向的转法 test_stove_facing.py 已经和 Java 逐件对过，这里补上高度和贴图朝向。"""
    _standalone()
    for yaw in (0, 90, 180, 270):
        slots = dict((str(place), _item("minecraft:beef")) for place in range(6))
        for placement in BD.layout(BD.KIND_STOVE, slots, _typeOf, (0, 64, 0), yaw=yaw):
            assert abs(placement.center[1] - 1.02) < 1e-9 and abs(placement.scale * 8.0 / 16.0 - 0.375) < 1e-9, yaw
            right, up, size = _ours(placement)
            wantRight, wantUp, wantSize = _javaFlat(JAVA_OPPOSITE[FRONT_OF_YAW[yaw]], 0.375)
            assert _close(right, wantRight) and _close(up, wantUp) and abs(size - wantSize) < 1e-9, (yaw, right, wantRight)


def testTheSkilletAndTheStoveDoNotChangeWithTheRunModeBecauseTheSceneHidesThemWhenTheStationIsOn():
    """装了前置包又开着站点时，煎锅 / 炉灶的场景接管锅里、灶上的东西（Client/BlockItems.hide），这份展示收起来：不用按模式分两种，一份 FD 的就是对的。"""
    slots = dict((str(place), _item("minecraft:beef", 3)) for place in range(6))
    _standalone()
    plain = [(p.center, p.direction, p.scale) for p in _skillet(_item("minecraft:beef", 20))] + \
            [(p.center, p.direction, p.scale) for p in BD.layout(BD.KIND_STOVE, slots, _typeOf, (0, 64, 0), yaw=90)]
    linkkit.link()
    try:
        linked = [(p.center, p.direction, p.scale) for p in _skillet(_item("minecraft:beef", 20))] + \
                 [(p.center, p.direction, p.scale) for p in BD.layout(BD.KIND_STOVE, slots, _typeOf, (0, 64, 0), yaw=90)]
    finally:
        _standalone()
    assert linked == plain and len(plain) == 9


# ---------------------------------------------------------------- 经典厨锅

def testTheCookingPotHasNoItemDisplayAtAllBecauseFarmersDelightDrawsNone():
    """FD 注册的方块实体渲染器只有炉灶（DefaultStoveRenderer）、砧板、煎锅、两种告示牌（ClientSetupEvents.java:44-48），厨锅没有：厨锅里的东西只在界面里。"""
    assert BD.layout("cooking_pot", {"0": _item("minecraft:beef")}, _typeOf, (0, 0, 0)) == []


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
