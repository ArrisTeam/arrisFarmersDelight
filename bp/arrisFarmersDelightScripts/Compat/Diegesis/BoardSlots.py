# -*- coding: utf-8 -*-
"""BoardSlots - 砧板站点的两个槽组直接绑在方块实体数据上：board（板上的东西）、layers（摆盘的层）（服务端）

对应 Hands-On Delight：station/BoardLogic.java 构造里的 bindSlots（58-93）。站点只是交互层，存档不变：
    board   1 格 = 方块实体数据 cuttingDict（带数量的物品字典，经典玩法也读写它；做好的菜、插着的工具也躺在这里）
    layers  9 格 = dishLayers（物品字典的列表，底座在前；Server/Helpers/BoardDish.py 经典玩法读它）
前置包的 StationState 经 get / set 读写这里，别处（经典玩法、漏斗）改了它们由 Manager 的 pollStorages 发现并同步。
每次写完照最后的样子广播给各客户端画（Helpers/BlockItems）：有层时画层，否则画板上的东西。
"""
from ...Server.Helpers import BoardDish as Store
from ...Server.Helpers.BlockItems import PublishBoard, PublishBoardDish
from ...Server.Helpers.Engine import GetBlockEntityData
from ...Shared.Rules.BoardStation import MOST_LAYERS, keyOf


_TEXT = type(u"")      # py2 的 unicode；py3 里就是 str


def stack(item):
    """存档用的一叠：名字、aux、数量（带耐久的工具再加耐久）；空是 None。名字转成 str：py2 的 unicode 写进方块实体数据引擎只打日志、不存。"""
    if keyOf(item) is None:
        return None
    out = Store.stack(item)
    if _TEXT is not str and isinstance(out["newItemName"], _TEXT):
        out["newItemName"] = out["newItemName"].encode("utf-8")
    if item.get("durability"):
        out["durability"] = item["durability"]
    return out


def boardOf(data):
    """方块实体数据里板上的东西（只读用，空是 None）。"""
    item = data["cuttingDict"] if data else None
    return stack(item) if item else None


def layersOf(data):
    return Store.layersOf(data) if data else []


def publish(dimensionId, pos, data):
    """按现在的样子广播：有层画层，没有层画板上的东西。"""
    layers = layersOf(data)
    if layers:
        PublishBoardDish(dimensionId, pos, layers, None)
    else:
        PublishBoard(dimensionId, pos, boardOf(data))


def writeBoard(dimensionId, pos, item):
    """板上的东西整个换成 item（None = 清空），广播。改了之后站点状态由 Manager 每次动作 / tick 后的 pollStorages 发现并同步给使用者。"""
    data = GetBlockEntityData(dimensionId, pos)
    if data is not None:
        data["cuttingDict"] = stack(item)
        publish(dimensionId, pos, data)


def writeLayers(dimensionId, pos, layers):
    """摆盘的层整排换成 layers（底座在前，至多 9 层），广播。"""
    data = GetBlockEntityData(dimensionId, pos)
    if data is not None:
        kept = [stack(layer) for layer in layers[:MOST_LAYERS] if keyOf(layer) is not None]
        data[Store.LAYERS_KEY] = kept or None            # 整体回写：改了嵌套列表只有赋值才存档
        publish(dimensionId, pos, data)


class BoardSlot(object):
    """board 槽组：一格，读写 cuttingDict。"""

    def __init__(self, dimensionId, pos):
        self.dimensionId, self.pos = dimensionId, pos

    def size(self):
        return 1

    def get(self, index):
        return boardOf(GetBlockEntityData(self.dimensionId, self.pos))

    def set(self, index, item):
        writeBoard(self.dimensionId, self.pos, item)


class LayerSlots(object):
    """layers 槽组：九格，读写 dishLayers。放的和拿走的都是最上面一层或整排，空格紧跟在最后一层后面（写回时压紧）。"""

    def __init__(self, dimensionId, pos):
        self.dimensionId, self.pos = dimensionId, pos

    def size(self):
        return MOST_LAYERS

    def get(self, index):
        layers = layersOf(GetBlockEntityData(self.dimensionId, self.pos))
        return layers[index] if index < len(layers) else None

    def set(self, index, item):
        slots = (layersOf(GetBlockEntityData(self.dimensionId, self.pos)) + [None] * MOST_LAYERS)[:MOST_LAYERS]
        slots[index] = item
        writeLayers(self.dimensionId, self.pos, slots)
