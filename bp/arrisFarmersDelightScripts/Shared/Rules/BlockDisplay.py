# -*- coding: utf-8 -*-
"""BlockDisplay - 砧板 / 煎锅 / 炉灶上展示的物品摆在哪、什么姿态（双端，纯规则）

取代旧版的 arris:item_display 服务端实体：服务端只广播"这个方块上有什么"，各客户端按这里的摆法用客户端掉落物画
（与机械动力的置物台、传送带同一种做法）。坐标是方块内的格（原点在方块西北下角），方向是世界的 (dx, dz)。
- 砧板：一件。食物平躺在板面中央；方块类立在板上；工具竖着、刀尖朝下扎在板上（同 FD 原版）。
- 煎锅：一叠按数量叠几层（1 个 1 层，2-16 两层，之后每 16 个加一层，最多 5 层），每层错开一点、转个角度。
- 炉灶：六个烤位（3 x 2，位置照 HoD 的炉灶场景），每格一件小号的平躺食物。
- 砧板摆盘（场景交互 · 前置在场时）：一层层叠起来；做好的菜平躺在中间。
"""
import math

from .HandsOn import StoveLayout
from .Ticks import posHash

KIND_BOARD = "board"
KIND_SKILLET = "skillet"
KIND_STOVE = "stove"

BOARD_TOP = 1.0 / 16.0
SKILLET_FLOOR = 1.5 / 16.0
STOVE_TOP = 1.0
LAYER_STEP = 0.037
STOVE_SLOTS = StoveLayout.blockFractions()        # 照 HoD 炉灶场景里六个烤位的位置（炉灶朝北的那一份），开着站点时画面对得上
TOOL_TYPES = frozenset(("sword", "axe", "hoe", "shovel", "pickaxe"))

FOOD_SCALE = 1.2
BLOCK_SCALE = 1.0
TOOL_SCALE = 1.0
SKILLET_SCALE = 1.0
STOVE_SCALE = StoveLayout.SIZE / 8.0         # 一件 5 像素宽（贴图缩放 1 时边长 8 像素）
TOOL_ROLL = 135.0          # 竖立的工具在贴图平面内顺时针转 135 度：刀尖朝下（实机标定）
TOOL_DEPTH = 0.32          # 工具视觉中心离板面多高：刀尖略扎进板里


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


def boardLayout(item, itemType):
    if not isItem(item):
        return []
    shown = _single(item)
    if itemType == "block":
        return [Placement(shown, (0.5, BOARD_TOP + 0.125 * BLOCK_SCALE, 0.5), False, (0.0, -1.0), 0.0, BLOCK_SCALE)]
    if itemType in TOOL_TYPES:
        return [Placement(shown, (0.5, BOARD_TOP + TOOL_DEPTH * TOOL_SCALE, 0.5), False, (0.7071, -0.7071), TOOL_ROLL,
                          TOOL_SCALE)]
    return [Placement(shown, (0.5, BOARD_TOP + 0.02, 0.5), True, (1.0, 0.0), 0.0, FOOD_SCALE)]


DISH_LAYERS = 9                # 砧板摆盘最多几层（HandsOn/Assembly.MOST_LAYERS）
DISH_KEY = "D"                 # 做好的那叠在广播里的槽名；层是 "L0".."L8"


def layerKey(index):
    return "L%d" % index


def boardDishLayout(layers, dish, seed):
    """砧板摆盘：做好的菜平躺在中间；还在摆时一层层叠起来，每层略转一点、略偏一点，看得出是一摞。"""
    if isItem(dish):
        return [Placement(_single(dish), (0.5, BOARD_TOP + 0.02, 0.5), True, (1.0, 0.0), 0.0, FOOD_SCALE)]
    placements = []
    for index, layer in enumerate(item for item in layers if isItem(item)):
        angle = 0.5 * index + _jitter(seed, index, 0.25)
        center = (0.5 + _jitter(seed, index * 2 + 7, 0.04), BOARD_TOP + 0.02 + index * LAYER_STEP,
                  0.5 + _jitter(seed, index * 2 + 8, 0.04))
        placements.append(Placement(_single(layer), center, True, (math.cos(angle), math.sin(angle)), 0.0, FOOD_SCALE))
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


def stoveLayout(slots):
    """slots：{"0": 物品或 None/{}, ...}。每件各转一点（StoveLayout.yawOf，HoD 场景里"手放的、没有两件同向"），
    转的是世界里的方向，所以开着站点的人从哪一侧看，画面都和这里对得上。"""
    placements = []
    for index, (x, z) in enumerate(STOVE_SLOTS):
        item = slots.get(str(index))
        if isItem(item):
            turn = math.radians(StoveLayout.yawOf(index))
            placements.append(Placement(_single(item), (x, STOVE_TOP + 0.015, z), True, (math.cos(turn), -math.sin(turn)), 0.0,
                                        STOVE_SCALE))
    return placements


def layout(kind, items, itemTypeOf, pos):
    """kind 方块种类、items {"槽": 物品}、itemTypeOf(物品) -> 物品类型（客户端查 GetItemBasicInfo）、pos 方块坐标。"""
    if kind == KIND_BOARD:
        layers = [items.get(layerKey(index)) for index in range(DISH_LAYERS)]
        if isItem(items.get(DISH_KEY)) or any(isItem(layer) for layer in layers):
            return boardDishLayout(layers, items.get(DISH_KEY), posHash(pos))
        item = items.get("0")
        return boardLayout(item, itemTypeOf(item)) if isItem(item) else []
    if kind == KIND_SKILLET:
        return skilletLayout(items.get("0"), posHash(pos))
    if kind == KIND_STOVE:
        return stoveLayout(items)
    return []
