# -*- coding: utf-8 -*-
"""GrillSpace - 炉灶的坐标：六个烤位落在哪、烤架中心、粒子声音的世界坐标；站点里还有光标落在烤架面的哪一点、放进来的东西从屏幕哪里飞来（客户端）

站点空间就是炉灶朝向的空间（前置包的朝向钩子，GrillView 登记；JE 的 Orientation.BLOCK）：HoD 的 stove.json 写在"炉灶朝北"的像素坐标里
（原点在方块西北下角，+x 在画面左边，+z 朝远处，烤架面 y = 16），站点的北面就是炉灶的正面，所以场景文件里的像素坐标（六件的位置、命中盒、
粒子的偏移、镜头）直接用，不用再换；炉灶朝哪，站点、场景、世界里的展示（Shared/Rules/BlockDisplay）都跟着转，是同一套（Shared/Rules/StoveFacing）。
两个空间只差"站点像素怎么换成世界"：
- Space：本人开着站点时的站点像素，换到世界用前置包的 view.toWorld（站点的朝向就是炉灶的）。命中盒、光标射线、从屏幕下沿飞来的起点只有它有（要相机和屏幕）；
- WorldSpace：谁都看得见的场景（StoveScene.py）用的：不开站点也要有，所以不借前置包的视图，自己按炉灶的朝向把站点像素转到世界（StoveFacing.worldPoint）。
  本人开着站点时，站点把"从屏幕哪里飞来"交进来（focus），旁观的人没有。
"""
from ...Shared.Rules import StoveFacing
from ...Shared.Rules.HandsOn import FromPlayer, StoveLayout, StoveMotion

TOP_Y = 16.3                         # 平躺的物品贴图的中心离方块底多高：躺在烤架面（16）上略高一点（实机标定，和原来一样）
LIFT = TOP_Y - StoveLayout.TOP       # 道具的中心比 JE 里件的原点（16.02）高这么多：粒子照 JE 的高度放，要减回去


class Layout(object):
    """六件落点、烤架中心、某一件加偏移的世界坐标，都在站点像素里（炉灶朝向的空间）。子类给 toWorld（站点像素 -> 世界）。"""

    def __init__(self):
        self._centers = None

    def toWorld(self, x, y, z):
        raise NotImplementedError

    def fromPlayer(self, index, count):
        """一次放好几件时第 index 件从哪出发：相对它落点的 (x, z)，站点像素；没有屏幕（旁观的人）是 None。"""
        return None

    def centers(self):
        """六件落点的位置 (x, y, z)，站点像素，y 是道具中心的高度。"""
        if self._centers is None:
            self._centers = [(x, TOP_Y, z) for x, _, z in (StoveLayout.placeOf(place) for place in range(StoveLayout.PLACES))]
        return self._centers

    def middle(self):
        """烤架中心的位置（被拒绝的虚影从这里弹）。"""
        return (8.0, TOP_Y, 8.0)

    def world(self, place, offset):
        """某一件（None = 烤架中心）加上偏移（站点像素）的世界坐标：粒子和声音用。"""
        base = self.centers()[place] if place is not None else self.middle()
        return self.toWorld(base[0] + offset[0], base[1] - LIFT + offset[1], base[2] + offset[2])


class Space(Layout):
    """开着的站点的坐标。"""

    def __init__(self, view):
        Layout.__init__(self)
        self.view = view

    def toWorld(self, x, y, z):
        return self.view.toWorld(x, y, z)

    def cursor(self, ray):
        """光标射线落在烤架面上的点 (x, z)（站点像素）；射线碰不到返回 None。"""
        point = FromPlayer.planeAt(ray, StoveLayout.TOP) if ray is not None else None
        return None if point is None else (point[0], point[2])

    def fromPlayer(self, index, count):
        """一次放好几件时第 index 件（共 count 件）从哪出发：相对它落点的 (x, z)，站点像素（FromPlayer.offset）。
        屏幕下沿的一点投到 LAND_FROM 高的水平面上，减去屏幕正中投到同一个面上的点；拿不到屏幕或相机返回 None。
        屏幕大小问前置包的端口（view.ports.uiSize）：和 view.rayAt 换算界面点用的是同一个数。"""
        size = self.view.ports.uiSize()
        if not size:
            return None
        fx, fy = FromPlayer.startAt(index, count)
        height = StoveMotion.LAND_FROM
        start, middle = (self._plane(size, x, y, height) for x, y in ((fx, fy), FromPlayer.MIDDLE))
        return FromPlayer.offsetOf(start, middle) if start is not None and middle is not None else None

    def _plane(self, size, fx, fy, height):
        ray = self.view.rayAt((size[0] * fx, size[1] * fy))
        return FromPlayer.planeAt(ray, height) if ray is not None else None


class WorldSpace(Layout):
    """场景的坐标：站点像素，按炉灶的朝向 yaw（度）转到世界。"""

    def __init__(self, pos, yaw):
        Layout.__init__(self)
        self.pos = (int(pos[0]), int(pos[1]), int(pos[2]))
        self.yaw = yaw
        self.starts = None            # 本人开着站点时：fromPlayer(index, count) -> (x, z) 或 None（Space.fromPlayer）

    def focus(self, starts):
        """本人开了站点：交进来飞入的起点；关站时 focus(None)。"""
        self.starts = starts

    def toWorld(self, x, y, z):
        return StoveFacing.worldPoint(self.yaw, self.pos, x, y, z)

    def fromPlayer(self, index, count):
        return self.starts(index, count) if self.starts is not None else None
