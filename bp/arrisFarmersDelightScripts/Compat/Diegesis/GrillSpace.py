# -*- coding: utf-8 -*-
"""GrillSpace - 炉灶站点里的坐标：六个烤位落在哪、命中盒、烤架中心、粒子声音的世界坐标、光标落在烤架面的哪一点、放进来的东西从屏幕哪里飞来（客户端）

件在方块里的位置是固定的（世界里的展示 Shared/Rules/BlockDisplay.STOVE_SLOTS，照 HoD 炉灶场景里"炉灶朝北"的那一份），不随炉灶朝向转；
站点的坐标按玩家所在的一侧转（前置包的 view.toStation / toWorld），所以这里把方块里的点按玩家这一侧换过来：从哪边开站，
件都落在世界里它们躺的地方。HoD 场景里的像素坐标（命中盒、粒子的偏移）都按方块里的像素给，经 block() 换。
"""
from ...Client.Engine import compFactory, levelId
from ...Shared.Rules import GrillStation as Rules
from ...Shared.Rules.HandsOn import FromPlayer, StoveLayout, StoveMotion

TOP_Y = 16.3                         # 平躺的物品贴图的中心离方块底多高：躺在烤架面（16）上略高一点（实机标定，和原来一样）
LIFT = TOP_Y - StoveLayout.TOP       # 道具的中心比 JE 里件的原点（16.02）高这么多：粒子照 JE 的高度放，要减回去


class Space(object):
    def __init__(self, view):
        self.view = view
        self._centers = None

    def block(self, x, y, z):
        """方块里的点（像素，原点在方块西北下角、炉灶朝北那一份）-> 站点像素。"""
        px, py, pz = self.view.pos
        return self.view.toStation(px + x / 16.0, py + y / 16.0, pz + z / 16.0)

    def centers(self):
        """六件落点的站点坐标 (x, y, z)，y 是道具中心的高度。"""
        if self._centers is None:
            self._centers = []
            for place in range(StoveLayout.PLACES):
                fx, fz = Rules.slotCenter(place)
                x, _, z = self.block(fx * 16.0, 16.0, fz * 16.0)
                self._centers.append((x, TOP_Y, z))
        return self._centers

    def middle(self):
        """烤架中心的站点坐标（被拒绝的虚影从这里弹）。"""
        x, _, z = self.block(8.0, 16.0, 8.0)
        return (x, TOP_Y, z)

    def world(self, place, offset):
        """某一件（None = 烤架中心）加上偏移（站点像素）的世界坐标：粒子和声音用。"""
        base = self.centers()[place] if place is not None else self.middle()
        return self.view.toWorld(base[0] + offset[0], base[1] - LIFT + offset[1], base[2] + offset[2])

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

    def _plane(self, size, fx, fy, height):
        ray = self.view.rayAt((size[0] * fx, size[1] * fy))
        return FromPlayer.planeAt(ray, height) if ray is not None else None
