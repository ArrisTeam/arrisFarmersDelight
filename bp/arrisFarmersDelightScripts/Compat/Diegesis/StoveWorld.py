# -*- coding: utf-8 -*-
"""StoveWorld - 炉灶场景里的客户端道具：把"炉灶自己的像素"摆成客户端掉落物（客户端）

烤架上的画面（GrillPieces 的 Pieces、GrillGhosts 的 Ghosts）原来画在前置包的站点空间里（view.props），只有开着站点的人看得见。
炉灶的场景谁都看得见、不靠站点，所以这里给它们一个同样接口的替身 WorldView：
- 炉灶朝向的站点空间：站点像素 = 炉灶自己的像素（原点在方块西北下角，按"炉灶朝北"写），炉灶朝哪就绕方块中心转到哪（Shared/Rules/StoveFacing），
  和开着站点的人用的坐标是同一套（站点的北面就是炉灶的正面）；
- props：客户端掉落物（Client/Engine.addDropItem，影子关掉）。位置、姿态、缩放的换算和前置包 Client/Props.ItemProp 是同一套
  （Shared/Rules/ItemPose 的 pivotFor / engineEuler；炉灶坐标里的姿态矩阵经 ItemPose.framed 换到世界）；
- state / data：Pieces 读的"每个烤位是什么、两面烤到哪、是不是手放的"，来自服务端广播解出来的 Look（Shared/Rules/StoveLookState）。
"""
from ...Client.Engine import addDropItem, compFactory, levelId
from ...Shared.Rules import ItemPose, StoveFacing
from ...Shared.Rules.StoveLookState import Look


class WorldProp(object):
    """一件摆在世界里的客户端掉落物。center 是炉灶自己的像素（视觉中心），matrix 是炉灶坐标里的 3x3 行表姿态，scale 同 ItemProp；yaw 是炉灶朝向。"""

    def __init__(self, dimensionId, origin, yaw, item, center, scale, matrix):
        self.origin, self.yaw = origin, yaw
        self.center, self.scale, self.matrix = center, scale, matrix
        self.drawn = None                     # 上一次送给引擎的姿态（世界里的）：下一次接着它，翻面换向时轴心不跳（ItemPose.steadied）
        # 一出生就在轴心该在的地方：引擎按游戏刻插值掉落物的位置，建在别处再挪，头一两帧画在半路上
        self.entityId = addDropItem(item, dimensionId, self._placed()[0])
        self.move()

    @property
    def alive(self):
        return self.entityId is not None

    def _world(self, point):
        return StoveFacing.worldPoint(self.yaw, self.origin, point[0], point[1], point[2])

    def worldCenter(self):
        """视觉中心在世界里的位置（格）：叠在它朝上那面的熟色粒子（FryTints）跟着它和 drawn（世界里的姿态）摆。"""
        return self._world(self.center)

    def move(self, center=None, matrix=None, scale=None):
        """改位置 / 姿态 / 缩放（不给的不变）。"""
        if self.entityId is None:
            return False
        self.center = center if center is not None else self.center
        self.matrix = matrix if matrix is not None else self.matrix
        self.scale = scale if scale is not None else self.scale
        pivot, self.drawn = self._placed()
        return compFactory.CreateItem(levelId).SetDropItemTransform(self.entityId, pivot, ItemPose.engineEuler(self.drawn), float(self.scale))

    def _placed(self):
        """(轴心在世界里的位置, 世界里的姿态)，姿态接着上一次画的。"""
        world = ItemPose.steadied(ItemPose.framed(StoveFacing.axes(self.yaw), self.matrix), self.drawn)
        return ItemPose.pivotFor(self._world(self.center), world, self.scale), world

    def remove(self):
        if self.entityId is not None:
            compFactory.CreateItem(levelId).DeleteClientDropItemEntity(self.entityId)
            self.entityId = None


class WorldProps(object):
    """一座炉灶的全部道具；场景收掉时统一清理。yaw 是炉灶朝向（炉灶方块转了，StoveScene.turn 改它，已有的道具先收掉再画）。"""

    def __init__(self, dimensionId, origin, yaw):
        self.dimensionId, self.origin, self.yaw = dimensionId, origin, yaw
        self._props = []

    def item(self, item, center, scale=1.0, matrix=None):
        prop = WorldProp(self.dimensionId, self.origin, self.yaw, item, center, scale, matrix)
        if prop.alive:
            self._props.append(prop)
        return prop

    def remove(self, prop):
        prop.remove()
        if prop in self._props:
            self._props.remove(prop)

    def clear(self):
        for prop in self._props:
            prop.remove()
        del self._props[:]

    def __len__(self):
        return len(self._props)


class WorldView(object):
    """Pieces / Ghosts 当作站点视图用的东西：炉灶朝向的站点空间、道具、当前的样子（state.getItem 和 data）。"""

    def __init__(self, dimensionId, pos, yaw):
        self.pos = (int(pos[0]), int(pos[1]), int(pos[2]))
        self.yaw = yaw
        self.props = WorldProps(dimensionId, self.pos, yaw)
        self.show(Look())

    def turn(self, yaw):
        """炉灶转了：往后摆的道具按新朝向（已有的道具由调用方先收掉）。"""
        self.yaw = self.props.yaw = yaw

    def show(self, look):
        """换一份样子：下一次 Pieces.refresh 就照它画。"""
        self.state = look
        self.data = look.data()
