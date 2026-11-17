# -*- coding: utf-8 -*-
# runner: both
"""炉灶的朝向（Shared/Rules/StoveFacing.py）：JE 的炉灶站点是 Orientation.BLOCK（HoD 的 StoveStation），站点的北面永远是炉灶方块的正面，
场景按"炉灶朝北"写（stove.json）；FD 自己画烤架上的东西（DefaultStoveRenderer）、冒烟（StoveBlockEntity.addSmokeParticles）也按 FACING 转。
基岩版的炉灶是 netease:face_directional 的 direction 状态（方块的 aux）：0 南 1 西 2 北 3 东，写在 north 的贴图（点着的火口）出现在世界的
那一面（Strata 引擎知识库 BLOCK_LEGACY_ENGINE §10.2）。这里核对：aux 到朝向、六件的位置朝哪都和 FD 的 Java 一样（把 Java 的两段公式照抄成代码）、
和前置包的几何一样、世界里的展示是 FD 的渲染器（位置和场景里一样，每件 6 像素宽、朝向都一样）。"""
from __future__ import print_function

import math

import prereq  # noqa: F401 - 前置包不在这个仓库里：旁边没有它就跳过（tests/prereq.py）
import dgtest
import fdtest

StoveFacing = fdtest.load("Shared.Rules.StoveFacing")
Pot = fdtest.load("Shared.Rules.PotModelMath")
Layout = fdtest.load("Shared.Rules.HandsOn.StoveLayout")
Motion = fdtest.load("Shared.Rules.HandsOn.StoveMotion")
BD = fdtest.load("Shared.Rules.BlockDisplay")
Pose = fdtest.load("Shared.Rules.ItemPose")
Geometry = dgtest.load("Shared.Geometry")
Protocol = dgtest.load("Shared.Protocol")

# direction 状态 -> 炉灶的正面朝哪（世界的水平方向 (dx, dz)，+x 东、+z 南）：写在 north 的贴图出现在世界的哪一面
FRONT = {0: (0.0, 1.0), 1: (-1.0, 0.0), 2: (0.0, -1.0), 3: (1.0, 0.0)}
YAW_OF_AUX = {0: 180, 1: 270, 2: 0, 3: 90}              # 南 / 西 / 北 / 东 -> 站点朝向（度）
NAME_OF_AUX = {0: "SOUTH", 1: "WEST", 2: "NORTH", 3: "EAST"}

# ---- FD 的 Java，照抄 ----
# StoveBlockEntity.getStoveItemOffset：OFFSETS 六个 (x, y)，X_OFFSET 0.3、Y_OFFSET 0.2
JAVA_OFFSETS = ((0.3, 0.2), (0.0, 0.2), (-0.3, 0.2), (0.3, -0.2), (0.0, -0.2), (-0.3, -0.2))
JAVA_YROT = {"SOUTH": 0.0, "WEST": 90.0, "NORTH": 180.0, "EAST": 270.0}                 # Direction.toYRot
JAVA_OPPOSITE = {"SOUTH": "NORTH", "NORTH": "SOUTH", "WEST": "EAST", "EAST": "WEST"}
JAVA_DATA2D = {"SOUTH": 0, "WEST": 1, "NORTH": 2, "EAST": 3}                             # Direction.get2DDataValue
JAVA_STEP = {"SOUTH": (0, 1), "WEST": (-1, 0), "NORTH": (0, -1), "EAST": (1, 0)}         # (getStepX, getStepZ)
JAVA_CLOCKWISE = {"NORTH": "EAST", "EAST": "SOUTH", "SOUTH": "WEST", "WEST": "NORTH"}    # Direction.getClockWise


def javaRenderer(facing, index):
    """DefaultStoveRenderer.render：translate(0.5, 1.02, 0.5)、绕 Y 转 -FACING.getOpposite().toYRot()、再绕 X 转 90 度（贴图躺平，
    贴图的 y 变成 +z）、再 translate(offset.x, offset.y, 0)。第 index 件的中心在方块里的 (x, z)（比例）。"""
    ox, oy = JAVA_OFFSETS[index]
    f = math.radians(-JAVA_YROT[JAVA_OPPOSITE[facing]])
    # Ry(f) * (ox, 0, oy)：Axis.YP.rotationDegrees 的转法，x' = x cos f + z sin f，z' = -x sin f + z cos f
    return (0.5 + ox * math.cos(f) + oy * math.sin(f), 0.5 - ox * math.sin(f) + oy * math.cos(f))


def javaSmoke(facing, index):
    """StoveBlockEntity.addSmokeParticles 里算的粒子位置（方块里的 x, z 比例）：FACING 的 get2DDataValue 是奇数就把 offset 的 x、y 对调，
    x = 0.5 - stepX * ox + clockWise.stepX * ox，z = 0.5 - stepZ * oy + clockWise.stepZ * oy。"""
    ox, oy = JAVA_OFFSETS[index]
    if JAVA_DATA2D[facing] % 2 != 0:
        ox, oy = oy, ox
    (sx, sz), (cx, cz) = JAVA_STEP[facing], JAVA_STEP[JAVA_CLOCKWISE[facing]]
    return (0.5 - sx * ox + cx * ox, 0.5 - sz * oy + cz * oy)


# ---------------------------------------------------------------- aux 到朝向

def testTheStationFacesTheSideTheNorthTextureOfTheStoveGoesTo():
    assert dict((aux, StoveFacing.yawOfAux(aux)) for aux in range(4)) == YAW_OF_AUX
    assert all(StoveFacing.yawOfAux(aux) in Protocol.YAWS for aux in range(4)), "前置包的朝向钩子只认这四个值"


def testTheStationsNorthSideIsTheStovesFrontInTheKernelsGeometry():
    """前置包的几何（Geometry.stationPointToWorld）把站点的北面（-z）转到 yaw 那一侧：炉灶朝哪，站点的北边缘中点就在哪一面。"""
    for aux, front in sorted(FRONT.items()):
        x, _, z = Geometry.stationPointToWorld(StoveFacing.yawOfAux(aux), 8.0, 0.0, 0.0, 0, 0, 0)       # 站点北边缘的中点
        assert abs((x - 0.5) - front[0] * 0.5) < 1.0e-9 and abs((z - 0.5) - front[1] * 0.5) < 1.0e-9, (aux, x, z)


def testAnAuxTheEngineCannotGiveReadsAsTheEnginesDefaultStateLikeThePotAndPan():
    """读不到（None）、越界的值按 0：引擎的缺省状态朝南，和厨锅、煎锅同一个函数（Placement.directionOfAux；原来只取低两位，6 读成朝北）；
    假日创造者实验玩法下的 4 / 8 / 12 是 direction 1 / 2 / 3（完整的表在 test_facing_of_aux.py）。"""
    assert StoveFacing.yawOfAux(None) == StoveFacing.yawOfAux(0) == StoveFacing.yawOfAux(6) == 180
    assert StoveFacing.yawOfAux(3.0) == 90
    assert [StoveFacing.yawOfAux(aux) for aux in (4, 8, 12)] == [270, 0, 90]


# ---------------------------------------------------------------- 六件的位置和 FD 的 Java 对上号

def testTheSixPiecesOfANorthFacingStoveAreFarmersDelightsSixOffsets():
    """朝北的炉灶：FD 的 getStoveItemOffset 的六个 (x, y) 就是 HoD stove.json 里 piece_0 ~ piece_5 的 (x, z)（方块内的比例），序号一一对应
    （序号 0..5 是方块实体数据 "0".."5" 的格号，不能换序）。"""
    assert [javaRenderer("NORTH", index) for index in range(6)] == [(0.5 + x, 0.5 + y) for x, y in JAVA_OFFSETS]
    for index, (x, z) in enumerate(Layout.PIECE_AT):
        jx, jz = javaRenderer("NORTH", index)
        assert abs(jx - x / 16.0) < 1.0e-9 and abs(jz - z / 16.0) < 1.0e-9, (index, x, z, jx, jz)
    assert [(x, z) for x, z in BD.STOVE_SLOTS] == [(x / 16.0, z / 16.0) for x, z in Layout.PIECE_AT]


def testTheSixPiecesTurnWithTheStoveTheWayFarmersDelightsRendererAndSmokeDo():
    """炉灶朝哪，六件跟着转：我们的转法（StoveFacing.turnFraction，绕方块中心转到炉灶的正面那一侧）和 FD 的渲染器、冒烟两段公式都一样。"""
    for aux, name in sorted(NAME_OF_AUX.items()):
        yaw = StoveFacing.yawOfAux(aux)
        for index, (x, z) in enumerate(BD.STOVE_SLOTS):
            mine = StoveFacing.turnFraction(yaw, x, z)
            for theirs in (javaRenderer(name, index), javaSmoke(name, index)):
                assert abs(mine[0] - theirs[0]) < 1.0e-9 and abs(mine[1] - theirs[1]) < 1.0e-9, (name, index, mine, theirs)


def testTheJavaRendererAndTheJavaSmokeAgreeWithEachOther():
    """FD 自己的两段公式（画东西、冒烟）本来就是同一个转法：核对没抄错。"""
    for name in sorted(JAVA_YROT):
        for index in range(6):
            a, b = javaRenderer(name, index), javaSmoke(name, index)
            assert abs(a[0] - b[0]) < 1.0e-9 and abs(a[1] - b[1]) < 1.0e-9, (name, index)


# ---------------------------------------------------------------- 世界里的换算

def testPointsTurnAboutTheBlockCentreAndAgreeWithTheKernelsGeometryForEveryFacing():
    """炉灶自己的坐标换到世界：StoveFacing.worldPoint 和前置包站点的 stationPointToWorld（Geometry）是同一个转法，所以开着站点的人
    （view.toWorld）、谁都看得见的场景（StoveFacing）、世界里的展示放的是同一个位置。"""
    for yaw in Protocol.YAWS:
        for point in ((12.8, 16.3, 11.2), (3.2, 0.0, 4.8), (8.0, 16.0, 8.0), (0.0, 5.0, 16.0)):
            mine = StoveFacing.worldPoint(yaw, (10, 64, 10), *point)
            theirs = Geometry.stationPointToWorld(yaw, point[0], point[1], point[2], 10, 64, 10)
            assert max(abs(a - b) for a, b in zip(mine, theirs)) < 1.0e-9, (yaw, point, mine, theirs)
    assert StoveFacing.worldPoint(0, (10, 64, 10), 8.0, 16.0, 8.0) == (10.5, 65.0, 10.5), "烤架中心在哪都不动"
    assert StoveFacing.worldPoint(90, (10, 64, 10), 8.0, 16.0, 8.0) == (10.5, 65.0, 10.5)


def testAxesAreTheStoveFramesAxesInTheWorldAndFrameAPoseLikeThePointsTurn():
    for yaw in Protocol.YAWS:
        rows = StoveFacing.axes(yaw)
        origin = StoveFacing.worldPoint(yaw, (0, 0, 0), 0.0, 0.0, 0.0)
        for column, unit in enumerate(((16.0, 0.0, 0.0), (0.0, 16.0, 0.0), (0.0, 0.0, 16.0))):
            moved = StoveFacing.worldPoint(yaw, (0, 0, 0), *unit)
            assert max(abs(rows[row][column] - (moved[row] - origin[row])) for row in range(3)) < 1.0e-9, (yaw, column)
    assert StoveFacing.axes(0) == ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))


def testTheWorldDisplayIsFarmersDelightsRendererAtTheScenePositionsWhateverTheFacing():
    """没开站点 / 没装前置包时世界里的展示（BlockDisplay.stoveLayout）是 FD 的 DefaultStoveRenderer：位置和场景里一样（getStoveItemOffset 就是 piece_0 ~ 5，
    经 StoveFacing 转到世界），每件 0.375 格 = 6 像素宽（SIZE）、朝向都一样，那个朝向就是场景里不多转的那一件（poseRows 的转角 0）经 axes 换到世界的姿态；
    HoD 场景里每件各转一点、5 像素宽，是装了前置包时场景接管之后的样子（那时这里的展示收起来，Client/BlockItems.hide）。"""
    assert BD.STOVE_SIZE == 0.375 and BD.STOVE_SCALE == 0.75, "FD 的 SIZE 0.375 格 = 6 像素；贴图缩放 1 是 8 像素"
    for yaw in Protocol.YAWS:
        slots = dict((str(place), {"newItemName": "minecraft:beef", "newAuxValue": 0, "count": 1}) for place in range(6))
        placements = BD.layout(BD.KIND_STOVE, slots, lambda item: "", (0, 0, 0), yaw=yaw)
        assert len(placements) == 6
        straight = Pose.framed(StoveFacing.axes(yaw), Motion.poseRows(0.0, 0.0, 0.0))
        for place, placement in enumerate(placements):
            x, _, z = StoveFacing.worldPoint(yaw, (0, 0, 0), Layout.PIECE_AT[place][0], 0.0, Layout.PIECE_AT[place][1])
            assert abs(placement.center[0] - x) < 1.0e-9 and abs(placement.center[2] - z) < 1.0e-9, (yaw, place)
            shown = Pose.flatMatrix(placement.direction[0], placement.direction[1])
            assert all(abs(shown[i][j] - straight[i][j]) < 1.0e-9 for i in range(3) for j in range(3)), (yaw, place)
            assert placement.scale == BD.STOVE_SCALE and placement.direction == placements[0].direction, (yaw, place)


def testAnAngleThatIsNotOneOfTheFourTurnsAsNorth():
    assert StoveFacing.facingOfYaw(45) == Pot.NORTH and StoveFacing.axes(45) == StoveFacing.axes(0)
    assert StoveFacing.turnOffset(45, 1.0, 2.0) == (1.0, 2.0)


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
