# -*- coding: utf-8 -*-
"""StoveWorld - 炉灶场景里的客户端道具：把"方块里的像素"摆成客户端掉落物（客户端）

烤架上的画面（GrillPieces 的 Pieces、GrillGhosts 的 Ghosts）原来画在前置包的站点空间里（view.props），只有开着站点的人看得见。
炉灶的场景谁都看得见、不靠站点，所以这里给它们一个同样接口的替身 WorldView：
- 朝向 0 的站点空间：站点像素 = 方块里的像素（原点在方块西北下角，轴和世界同向）；
- props：客户端掉落物（Client/Engine.addDropItem，影子关掉）。位置、姿态、缩放的换算和前置包 Client/Props.ItemProp 是同一套
  （Shared/Rules/ItemPose 的 pivotFor / engineEuler，朝向 0 时站点的姿态矩阵就是世界的）；
- state / data：Pieces 读的"每个烤位是什么、两面烤到哪、是不是手放的"，来自服务端广播解出来的 Look（Shared/Rules/StoveLookState）。
"""
from ...Client.Engine import addDropItem, compFactory, levelId
from ...Shared.Rules import ItemPose
from ...Shared.Rules.StoveLookState import Look


class WorldProp(object):
    """一件摆在世界里的客户端掉落物。center 是方块里的像素（视觉中心），matrix 是 3x3 行表的姿态，scale 同 ItemProp。"""

    def __init__(self, dimensionId, origin, item, center, scale, matrix):
        self.origin = origin
        self.center, self.scale, self.matrix = center, scale, matrix
        self.entityId = addDropItem(item, dimensionId, self._world(center))
        self.move()

    @property
    def alive(self):
        return self.entityId is not None

    def _world(self, point):
        return (self.origin[0] + point[0] / 16.0, self.origin[1] + point[1] / 16.0, self.origin[2] + point[2] / 16.0)

    def move(self, center=None, matrix=None, scale=None):
        """改位置 / 姿态 / 缩放（不给的不变）。"""
        if self.entityId is None:
            return False
        self.center = center if center is not None else self.center
        self.matrix = matrix if matrix is not None else self.matrix
        self.scale = scale if scale is not None else self.scale
        pivot = ItemPose.pivotFor(self._world(self.center), self.matrix, self.scale)
        return compFactory.CreateItem(levelId).SetDropItemTransform(self.entityId, pivot, ItemPose.engineEuler(self.matrix), float(self.scale))

    def remove(self):
        if self.entityId is not None:
            compFactory.CreateItem(levelId).DeleteClientDropItemEntity(self.entityId)
            self.entityId = None


class WorldProps(object):
    """一座炉灶的全部道具；场景收掉时统一清理。"""

    def __init__(self, dimensionId, origin):
        self.dimensionId, self.origin = dimensionId, origin
        self._props = []

    def item(self, item, center, scale=1.0, matrix=None):
        prop = WorldProp(self.dimensionId, self.origin, item, center, scale, matrix)
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
    """Pieces / Ghosts 当作站点视图用的东西：朝向 0、道具、当前的样子（state.getItem 和 data）。"""

    yaw = 0.0

    def __init__(self, dimensionId, pos):
        self.pos = (int(pos[0]), int(pos[1]), int(pos[2]))
        self.props = WorldProps(dimensionId, self.pos)
        self.show(Look())

    def show(self, look):
        """换一份样子：下一次 Pieces.refresh 就照它画。"""
        self.state = look
        self.data = look.data()
