# -*- coding: utf-8 -*-
"""BlockDisplay - 砧板 / 煎锅 / 炉灶上展示的物品摆在哪、什么姿态（双端，纯规则）

取代旧版的 arris:item_display 服务端实体：服务端只广播"这个方块上有什么"，各客户端按这里的摆法用客户端掉落物画
（与机械动力的置物台、传送带同一种做法）。坐标是方块内的格（原点在方块西北下角），方向是世界的 (dx, dz)。
- 砧板：一件。食物平躺在板的底座中间（FD 的板底座 x 1..12，柄在旁边：offset 是从方块中心挪过去的量，随方块朝向由调用方算）、一叠不止一个时底下
  再垫一张；方块类立在板上；插着的工具（BoardStation.Env.isCarving）画在方块正中心、贴图平行于板的正面、按类型转角度（镐 / 锄 225 度、三叉戟 135、
  别的 180，同 FD 的 renderItemCarved）。大小、层的偏转偏移都和砧板站点里本人看到的一样（HandsOn/BoardScene），开站、关站时板上的东西不跳。
- 煎锅：一叠按数量叠几层（1 个 1 层，2-16 两层，之后每 16 个加一层，最多 5 层），每层错开一点、转个角度。
- 炉灶：FD 的 DefaultStoveRenderer：六个烤位（3 x 2，位置就是 FD 的 getStoveItemOffset，也是 HoD 炉灶场景里的位置），每格一件 6 像素宽（SIZE 0.375）的平躺食物，
  每件朝向一样；位置和朝向跟着炉灶朝向转（StoveFacing：FD 按 FACING 转、HoD 的炉灶站点是 Orientation.BLOCK）。装了前置包又开着炉灶站点时，场景接管烤架上的东西
  （HoD 画 5 像素宽、每件各转一点），这里的展示在场景画出来之后就收起来了（Client/BlockItems.hide），所以这一份只有没装前置包、炉灶站点关了、场景还没画出来时看得到。
- 砧板摆盘（场景交互 · 前置在场时）：一层层叠起来；做好的菜平躺在中间。液体层（奶桶、蜂蜜瓶……）不画、蛋层画成打开的蛋：和站点里手倒完、磕完以后的样子
  一个样（HandsOn/BoardHands.lookOf），关站、开站时那几层不跳。
"""
import math

from . import ItemPose, StoveFacing
from .HandsOn import BoardHands, BoardScene, StoveLayout
from .Ticks import posHash

KIND_BOARD = "board"
KIND_SKILLET = "skillet"
KIND_STOVE = "stove"

BOARD_TOP = 1.0 / 16.0
SKILLET_FLOOR = 1.5 / 16.0
STOVE_TOP = 1.0
LAYER_STEP = 0.037
STOVE_SLOTS = StoveLayout.blockFractions()        # FD 的 getStoveItemOffset 的六个位置（HoD 炉灶场景里也是它们，炉灶朝北的那一份）；炉灶朝别处时 StoveFacing.turnFraction 转过去

FOOD_SCALE = 1.2
BLOCK_SCALE = BoardScene.itemScale(True)     # 方块类在板上是棱长 5.2 像素的立方体（HoD 的 BLOCK_SCALE 0.65：整块方块放在板上会挡住上面的东西）
BOARD_FOOD_SCALE = BoardScene.itemScale()    # 板上等着切的东西 10 像素
CARVED_SCALE = BoardScene.scaleOf(BoardScene.CARVED_SCALE * 16.0)
PILE_TURN = 17.0                              # 一叠的底下那张转的角度（scene 里 pile 节点的 rotation）
SKILLET_SCALE = 1.0
STOVE_SIZE = 0.375                           # FD 的 DefaultStoveRenderer.SIZE：一件 0.375 格 = 6 像素宽
STOVE_SCALE = STOVE_SIZE * 16.0 / 8.0        # 贴图缩放 1 时边长 8 像素


class Placement(object):
    """一件要画的物品：flat 时 direction 是贴图横向的方向；否则 direction 是正面朝向、roll 是平面内转角。"""

    __slots__ = ("item", "center", "flat", "direction", "roll", "scale")

    def __init__(self, item, center, flat=True, direction=(1.0, 0.0), roll=0.0, scale=1.0):
        self.item = item
        self.center = center
        self.flat = flat
        self.direction = direction
        self.roll = roll
        self.scale = scale

    def __repr__(self):
        return "Placement(%s, %r, flat=%s)" % (self.item.get("newItemName"), self.center, self.flat)


def skilletLayers(count):
    """煎锅上叠几层：1 个 1 层，2-16 两层，之后每 16 个加一层，最多 5 层。"""
    if count <= 0:
        return 0
    if count == 1:
        return 1
    return min(5, 2 + (count - 1) // 16)


def isItem(value):
    """是一件真的物品（客户端读方块实体数据时，空值可能是整数之类的占位，不是 None）。"""
    return isinstance(value, dict) and bool(value.get("newItemName")) and (value.get("count", 1) or 0) > 0


def _single(item):
    """展示用的一件（数量 1，只带名字和 aux）。"""
    return {"newItemName": item["newItemName"], "newAuxValue": item.get("newAuxValue", 0) or 0, "count": 1}


def _jitter(seed, index, span):
    """确定的小偏移：同一个方块每次画都一样，不会一刷新就跳。"""
    value = (seed * 2654435761 + index * 40503) & 0xFFFF
    return (value / 65535.0 * 2.0 - 1.0) * span


def carvedFront(yaw):
    """板上插着的工具的贴图正面朝哪（世界方向 dx, dz）：FD 的 renderItemCarved 比摆平的东西多转半圈，贴图正面朝板 FACING 的反方向（站在板正面的人看到的是背面），
    板的 FACING（模型的正面）在板自己的坐标里是 -z，所以正面是板自己坐标里的 +z。yaw 是板的朝向（度，StoveFacing.yawOfAux）。"""
    return StoveFacing.turnOffset(yaw, 0.0, 1.0)


def boardLayout(item, itemType, carving, isBlock, offset=(0.0, 0.0), yaw=0):
    """板上等着切的东西 / 做好的菜 / 插着的工具。carving(物品) 说是不是插着的工具、isBlock(物品) 说画成立着的方块还是平躺的图标
    （BoardStation.Env.isCarving / isBlock，站点里问的是同一个）；
    offset 是从方块中心挪到板底座中间的量（方块分数，x 往东 z 往南）；yaw 是板的朝向（度），插着的工具跟着它转。"""
    if not isItem(item):
        return []
    shown = _single(item)
    if carving(item):
        return [Placement(shown, (BoardScene.CARVED_X / 16.0, BoardScene.CARVED_HEIGHT / 16.0, BoardScene.CARVED_X / 16.0), False, carvedFront(yaw),
                          BoardScene.carvedRoll(itemType), CARVED_SCALE)]
    cx, cz = 0.5 + offset[0], 0.5 + offset[1]
    if isBlock(item):
        return [Placement(shown, (cx, BOARD_TOP + BoardScene.blockLift(BLOCK_SCALE) / 16.0, cz), False, (0.0, -1.0), 0.0, BLOCK_SCALE)]
    raised = itemType == "block"          # 走到这里的方块类是平躺着画的那几样（花、野生作物）：引擎照方块物品的规矩抬高着画
    flat = [_lying(shown, (cx, BOARD_TOP + 0.02 + BoardScene.pileLift(item.get("count", 1) or 1) / 16.0, cz), (1.0, 0.0), raised)]
    if (item.get("count", 1) or 1) > 1:
        angle = math.radians(PILE_TURN)
        flat.insert(0, _lying(shown, (cx, BOARD_TOP + 0.02, cz), (math.cos(angle), math.sin(angle)), raised))
    return flat


def _lying(shown, center, along, raised):
    """板上平躺的一件：center 是它该在的中心。raised（花、野生作物）：引擎把它整体抬高、轴心也不在底边，报出去的中心先反着挪（ItemPose.raisedShift），
    和方块那一支把立方体的抬高算进中心是同一个做法——摆的人（Client/BlockItems）只管照贴图物品的规矩摆。"""
    if raised:
        shift = ItemPose.raisedShift(ItemPose.flatMatrix(along[0], along[1]), BOARD_FOOD_SCALE)
        center = tuple(a + b / 16.0 for a, b in zip(center, shift))
    return Placement(shown, center, True, along, 0.0, BOARD_FOOD_SCALE)


DISH_LAYERS = 9                # 砧板摆盘最多几层（HandsOn/Assembly.MOST_LAYERS）
DISH_KEY = "D"                 # 做好的那叠在广播里的槽名；层是 "L0".."L8"


def layerKey(index):
    return "L%d" % index


def boardDishLayout(layers, dish, seed, offset=(0.0, 0.0)):
    """砧板摆盘：做好的菜平躺在中间；还在摆时一层层叠起来，每层的偏转偏移照 HoD（layer 号的固定函数，和站点里一样）。"""
    cx, cz = 0.5 + offset[0], 0.5 + offset[1]
    if isItem(dish):
        return [Placement(_single(dish), (cx, BOARD_TOP + 0.02, cz), True, (1.0, 0.0), 0.0, FOOD_SCALE)]
    placements = []
    for index, layer in enumerate(item for item in layers if isItem(item)):
        look = BoardHands.lookOf(index, layer)
        if look is None:
            continue                                  # 倒进去的液体：容器倒完就走了，这一层什么也不画（层的高度照留）
        pose = BoardScene.layerPose(index)
        angle = math.radians(pose["turn"])
        center = (cx + pose["x"] / 16.0, BOARD_TOP + 0.02 + pose["y"] / 16.0, cz + pose["z"] / 16.0)
        placements.append(Placement(_single(look), center, True, (math.cos(angle), math.sin(angle)), 0.0,
                                    BoardScene.scaleOf(BoardScene.layerSize(index))))
    return placements


def skilletLayout(item, seed):
    if not isItem(item):
        return []
    shown = _single(item)
    placements = []
    for layer in range(skilletLayers(item.get("count", 1) or 1)):
        dx, dz = _jitter(seed, layer * 2, 0.06), _jitter(seed, layer * 2 + 1, 0.06)
        turn = _jitter(seed, layer + 17, 1.0)
        placements.append(Placement(shown, (0.5 + dx, SKILLET_FLOOR + 0.02 + layer * LAYER_STEP, 0.5 + dz), True,
                                    (1.0, turn), 0.0, SKILLET_SCALE))
    return placements


def stoveLayout(slots, yaw=0):
    """slots：{"0": 物品或 None/{}, ...}。FD 的 DefaultStoveRenderer：每件一样大、朝向一样（不像 HoD 场景里每件各转一点）。
    yaw 是炉灶朝向（度，北 0 / 东 90 / 南 180 / 西 270，StoveFacing.yawOfAux）：六个烤位的位置和朝向都绕方块中心跟着转，炉灶朝哪都对得上场景里的位置。"""
    direction = StoveFacing.turnOffset(yaw, 1.0, 0.0)
    placements = []
    for index, (x, z) in enumerate(STOVE_SLOTS):
        item = slots.get(str(index))
        if isItem(item):
            cx, cz = StoveFacing.turnFraction(yaw, x, z)
            placements.append(Placement(_single(item), (cx, STOVE_TOP + 0.015, cz), True, direction, 0.0, STOVE_SCALE))
    return placements


def layout(kind, items, itemTypeOf, pos, offset=(0.0, 0.0), yaw=0, carving=None, isBlock=None):
    """kind 方块种类、items {"槽": 物品}、itemTypeOf(物品) -> 物品类型（客户端查 GetItemBasicInfo）、pos 方块坐标；
    offset 只有砧板用：板底座中间离方块中心的量（方块分数）；yaw 炉灶和砧板用：方块的朝向（度，StoveFacing.yawOfAux），炉灶转烤位、砧板转插着的工具；
    carving、isBlock 只有砧板用：carving(物品) 说是不是插着的工具、isBlock(物品) 说画成立着的方块还是平躺的图标（BoardStation.Env.isCarving / isBlock）。"""
    if kind == KIND_BOARD:
        layers = [items.get(layerKey(index)) for index in range(DISH_LAYERS)]
        if isItem(items.get(DISH_KEY)) or any(isItem(layer) for layer in layers):
            return boardDishLayout(layers, items.get(DISH_KEY), posHash(pos), offset)
        item = items.get("0")
        return boardLayout(item, itemTypeOf(item), carving, isBlock, offset, yaw) if isItem(item) else []
    if kind == KIND_SKILLET:
        return skilletLayout(items.get("0"), posHash(pos))
    if kind == KIND_STOVE:
        return stoveLayout(items, yaw)
    return []
