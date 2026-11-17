# -*- coding: utf-8 -*-
"""GrillSpace - 炉灶的坐标：六个烤位落在哪、烤架中心、粒子声音的世界坐标；站点里还有命中盒、光标落在烤架面的哪一点、放进来的东西从屏幕哪里飞来（客户端）

件在方块里的位置是固定的（世界里的展示 Shared/Rules/BlockDisplay.STOVE_SLOTS，照 HoD 炉灶场景里"炉灶朝北"的那一份），不随炉灶朝向转。
两套坐标用同一套算法（Layout），只差"方块里的点"怎么换成本坐标系和世界：
- Space：本人开着站点时的站点像素。站点的坐标按站点的朝向转（前置包的 view.toStation / toWorld：炉灶登记了 facing 钩子，朝炉灶的正面；
  没有钩子的老版本前置包朝着玩家所在的一侧），所以把方块里的点按站点朝向换过来：不管朝哪，件都落在世界里它们躺的地方。
  命中盒、光标射线、从屏幕下沿飞来的起点只有它有（要相机和屏幕）。HoD 场景里的像素坐标（命中盒、粒子的偏移）都按方块里的像素给，经 block() 换；
- WorldSpace：谁都看得见的场景（StoveScene.py）用的：朝向 0 的站点空间，站点像素就是方块里的像素，换到世界是方块坐标加上像素 / 16。
  本人开着站点时，站点把"从屏幕哪里飞来"和"站点的方向怎么换成世界的方向"交进来（focus），旁观的人这两样都没有。
"""
from ...Client.Engine import compFactory, levelId
from ...Shared.Rules import GrillStation as Rules
from ...Shared.Rules.HandsOn import FromPlayer, StoveLayout, StoveMotion

TOP_Y = 16.3                         # 平躺的物品贴图的中心离方块底多高：躺在烤架面（16）上略高一点（实机标定，和原来一样）
LIFT = TOP_Y - StoveLayout.TOP       # 道具的中心比 JE 里件的原点（16.02）高这么多：粒子照 JE 的高度放，要减回去


class Layout(object):
    """六件落点、烤架中心、某一件加偏移的世界坐标。子类给：block（方块里的点 -> 本坐标系的点）和 toWorld（本坐标系的点 -> 世界）。"""

    def __init__(self):
        self._centers = None

    def block(self, x, y, z):
        raise NotImplementedError

    def toWorld(self, x, y, z):
        raise NotImplementedError

    def fromPlayer(self, index, count):
        """一次放好几件时第 index 件从哪出发：相对它落点的 (x, z)，本坐标系的像素；没有屏幕（旁观的人）是 None。"""
        return None

    def centers(self):
        """六件落点在本坐标系里的位置 (x, y, z)，y 是道具中心的高度。"""
        if self._centers is None:
            self._centers = []
            for place in range(StoveLayout.PLACES):
                fx, fz = Rules.slotCenter(place)
                x, _, z = self.block(fx * 16.0, 16.0, fz * 16.0)
                self._centers.append((x, TOP_Y, z))
        return self._centers

    def middle(self):
        """烤架中心在本坐标系里的位置（被拒绝的虚影从这里弹）。"""
        x, _, z = self.block(8.0, 16.0, 8.0)
        return (x, TOP_Y, z)

    def world(self, place, offset):
        """某一件（None = 烤架中心）加上偏移（本坐标系的像素）的世界坐标：粒子和声音用。"""
        base = self.centers()[place] if place is not None else self.middle()
        return self.toWorld(base[0] + offset[0], base[1] - LIFT + offset[1], base[2] + offset[2])

    def turn(self, dx, dz):
        """本坐标系里的一个水平方向换成场景的方向（场景是朝向 0 的站点空间）；场景自己的坐标系就是它。"""
        return (dx, dz)


class Space(Layout):
    """开着的站点的坐标。"""

    def __init__(self, view):
        Layout.__init__(self)
        self.view = view

    def block(self, x, y, z):
        """方块里的点（像素，原点在方块西北下角、炉灶朝北那一份）-> 站点像素。"""
        px, py, pz = self.view.pos
        return self.view.toStation(px + x / 16.0, py + y / 16.0, pz + z / 16.0)

    def toWorld(self, x, y, z):
        return self.view.toWorld(x, y, z)

    def turn(self, dx, dz):
        """站点里的一个水平方向（像素）换成方块里的（朝向 0 的）方向：两点做差，和站点的转法无关。"""
        a, b = self.view.toWorld(0.0, 0.0, 0.0), self.view.toWorld(dx, 0.0, dz)
        return ((b[0] - a[0]) * 16.0, (b[2] - a[2]) * 16.0)

    def box(self, api, key, lo, hi, payload=None):
        """方块里的一个盒子（像素）-> 站点里的命中盒。"""
        a, b = self.block(*lo), self.block(*hi)
        return api.box(key, tuple(min(a[i], b[i]) for i in range(3)), tuple(max(a[i], b[i]) for i in range(3)), payload=payload)

    def cursor(self, ray):
        """光标射线落在烤架面上的点 (x, z)（站点像素）；射线碰不到返回 None。"""
        point = FromPlayer.planeAt(ray, StoveLayout.TOP) if ray is not None else None
        return None if point is None else (point[0], point[2])

    def fromPlayer(self, index, count):
        """一次放好几件时第 index 件（共 count 件）从哪出发：相对它落点的 (x, z)，站点像素（FromPlayer.offset）。
        屏幕下沿的一点投到 LAND_FROM 高的水平面上，减去屏幕正中投到同一个面上的点；拿不到屏幕或相机（旁观的人）是 None。"""
        size = compFactory.CreateGame(levelId).GetScreenSize()
        if not size:
            return None
        fx, fy = FromPlayer.startAt(index, count)
        height = StoveMotion.LAND_FROM
        start, middle = (self._plane(size, x, y, height) for x, y in ((fx, fy), FromPlayer.MIDDLE))
        return FromPlayer.offsetOf(start, middle) if start is not None and middle is not None else None

    def fromPlayerInWorld(self, index, count):
        """同 fromPlayer，只是换成场景的方向（场景里的件是朝向 0 的坐标）：StoveScene 的飞入用它。"""
        offset = self.fromPlayer(index, count)
        return None if offset is None else self.turn(offset[0], offset[1])

    def _plane(self, size, fx, fy, height):
        ray = self.view.rayAt((size[0] * fx, size[1] * fy))
        return FromPlayer.planeAt(ray, height) if ray is not None else None


class WorldSpace(Layout):
    """场景的坐标：站点像素 = 方块里的像素（朝向 0）。"""

    def __init__(self, pos):
        Layout.__init__(self)
        self.pos = (int(pos[0]), int(pos[1]), int(pos[2]))
        self.starts = None            # 本人开着站点时：fromPlayer(index, count) -> (x, z) 或 None（Space.fromPlayerInWorld）
        self.turner = None            # 本人开着站点时：turn(dx, dz) -> (dx, dz)（Space.turn）

    def focus(self, starts, turner):
        """本人开了站点：交进来飞入的起点和方向的换法；关站时 focus(None, None)。"""
        self.starts, self.turner = starts, turner

    def block(self, x, y, z):
        return (x, y, z)

    def toWorld(self, x, y, z):
        return (self.pos[0] + x / 16.0, self.pos[1] + y / 16.0, self.pos[2] + z / 16.0)

    def fromPlayer(self, index, count):
        return self.starts(index, count) if self.starts is not None else None

    def turn(self, dx, dz):
        return self.turner(dx, dz) if self.turner is not None else (dx, dz)
