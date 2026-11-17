# -*- coding: utf-8 -*-
# runner: both
"""炉灶的朝向（Shared/Rules/StoveFacing.py）：JE 的炉灶站点是 Orientation.BLOCK（HoD 的 StoveStation），站点的北面永远是炉灶方块的正面，
场景按"炉灶朝北"写（stove.json）。基岩版的炉灶是 netease:face_directional 的 direction 状态（方块的 aux）：0 南 1 西 2 北 3 东，
写在 north 的贴图（点着的火口）出现在世界的那一面（Strata 引擎知识库 BLOCK_LEGACY_ENGINE §10.2）。"""
from __future__ import print_function

import dgtest
import fdtest

StoveFacing = fdtest.load("Shared.Rules.StoveFacing")
Geometry = dgtest.load("Shared.Geometry")
Protocol = dgtest.load("Shared.Protocol")

# direction 状态 -> 炉灶的正面朝哪（世界的水平方向 (dx, dz)，+x 东、+z 南）：写在 north 的贴图出现在世界的哪一面
FRONT = {0: (0.0, 1.0), 1: (-1.0, 0.0), 2: (0.0, -1.0), 3: (1.0, 0.0)}
YAW_OF_AUX = {0: 180, 1: 270, 2: 0, 3: 90}              # 南 / 西 / 北 / 东 -> 站点朝向（度）


def testTheStationFacesTheSideTheNorthTextureOfTheStoveGoesTo():
    assert dict((aux, StoveFacing.yawOfAux(aux)) for aux in range(4)) == YAW_OF_AUX
    assert all(StoveFacing.yawOfAux(aux) in Protocol.YAWS for aux in range(4)), "前置包的朝向钩子只认这四个值"


def testTheStationsNorthSideIsTheStovesFrontInTheKernelsGeometry():
    """前置包的几何（Geometry.stationPointToWorld）把站点的北面（-z）转到 yaw 那一侧：炉灶朝哪，站点的北边缘中点就在哪一面。"""
    for aux, front in sorted(FRONT.items()):
        x, _, z = Geometry.stationPointToWorld(StoveFacing.yawOfAux(aux), 8.0, 0.0, 0.0, 0, 0, 0)       # 站点北边缘的中点
        assert abs((x - 0.5) - front[0] * 0.5) < 1.0e-9 and abs((z - 0.5) - front[1] * 0.5) < 1.0e-9, (aux, x, z)


def testAnAuxTheEngineCannotGiveReadsAsTheEnginesDefaultStateLikeThePotAndPan():
    """读不到（None）按 0：引擎的缺省状态朝南；越界的位和厨锅、煎锅一样只看低两位。"""
    assert StoveFacing.yawOfAux(None) == StoveFacing.yawOfAux(0) == 180
    assert StoveFacing.yawOfAux(6) == StoveFacing.yawOfAux(2) == 0 and StoveFacing.yawOfAux(3.0) == 90


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
