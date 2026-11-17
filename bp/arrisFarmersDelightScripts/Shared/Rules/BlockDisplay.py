# -*- coding: utf-8 -*-
"""BlockDisplay - 砧板 / 煎锅 / 炉灶上展示的物品摆在哪、什么姿态（双端，纯规则）

取代旧版的 arris:item_display 服务端实体：服务端只广播"这个方块上有什么"，各客户端按这里的摆法用客户端掉落物画
（与机械动力的置物台、传送带同一种做法）。坐标是方块内的格（原点在方块西北下角），方向是世界的 (dx, dz)。
没装前置包（或站点关着）时看到的是 FD 自己的渲染器：CuttingBoardRenderer、SkilletRenderer、DefaultStoveRenderer 的位置、高度、大小、错开、朝向都照它们
（tests/test_classic_block_display.py 把它们的 PoseStack 照抄成 Java 公式逐项对）；砧板站点在场时板上的东西摆成站点里的样子，开站、关站不跳。
- 砧板：FD：食物平躺在方块正中心，一叠画 1 + ceil(个数 / 最大叠数 * 4) 张、每张抬高 0.03、错开一点、朝向跟着板；方块类立着（缩放 0.8）；插着的工具画在方块正中心、
  贴图平行于板的正面、按类型转角度（镐 / 锄 225 度、三叉戟 135、别的 180，FD 的 renderItemCarved，两种模式同一个）。砧板站点在场（HandsOnOptions.cuttingBoard）时是站点里的
  摆法（HandsOn/BoardScene）：食物在板底座中间（FD 的板底座 x 1..12，柄在旁边，offset 是从方块中心挪过去的量，随方块朝向由调用方算）、一叠不止一个时底下再垫一张。
- 煎锅：FD：一叠画 1 + ceil(个数 / 最大叠数 * 4) 张，每张抬高 0.03、错开一点（一张也错开）、朝向跟着锅。装了前置包又开着煎锅站点时场景接管锅里的东西
  （Client/BlockItems.hide），这一份只有没装、站点关了、场景还没画出来时看得到（和炉灶同一个做法）。
- 炉灶：FD：六个烤位（3 x 2，位置就是 FD 的 getStoveItemOffset，也是 HoD 炉灶场景里的位置），每格一件 6 像素宽的平躺食物，每件朝向一样；位置和朝向跟着炉灶朝向转
  （StoveFacing：FD 按 FACING 转、HoD 的炉灶站点是 Orientation.BLOCK）。场景接管同煎锅（HoD 画 5 像素宽、每件各转一点）。
- 砧板摆盘（场景交互 · 前置在场时）：一层层叠起来；做好的菜平躺在中间。液体层（奶桶、蜂蜜瓶……）不画、蛋层画成打开的蛋：和站点里手倒完、磕完以后的样子
  一个样（HandsOn/BoardHands.lookOf），关站、开站时那几层不跳。
"""
import math

from . import HandsOnOptions as Options
from . import ItemPose, StoveFacing
from .HandsOn import BoardHands, BoardScene, StoveLayout
from .Ticks import posHash

KIND_BOARD = "board"
KIND_SKILLET = "skillet"
KIND_STOVE = "stove"

BOARD_TOP = 1.0 / 16.0
STOVE_SLOTS = StoveLayout.blockFractions()        # FD 的 getStoveItemOffset 的六个位置（HoD 炉灶场景里也是它们，炉灶朝北的那一份）；炉灶朝别处时 StoveFacing.turnFraction 转过去

# ---- FD 的渲染器（client/renderer/*.java）。贴图物品的 FIXED 变换缩放 1、方块物品缩放 0.5，掉落物缩放 1 时贴图 8 像素宽、立方体 4 像素：Java 的 scale(s) 都是掉落物缩放 2 * s
FD_SCALE = 2.0
FD_LAYER_RISE = 0.03                          # 一叠每张比前一张高这么多：translate(…, base + 0.03 * (i + 1), …)
FD_SPREAD = 0.15 * 0.5                        # x、z 错开 (nextFloat * 2 - 1) * 0.15 * 0.5
FD_BOARD_LYING = (0.08, 0.6)                  # CuttingBoardRenderer.renderItemLayingDown（java:64-77）：(高度底数, scale)
FD_BOARD_BLOCK = (0.27, 0.8)                  # renderBlock（:79-89）
FD_SKILLET = (0.1, 0.5)                       # SkilletRenderer（:45、:55）
FD_STOVE_HEIGHT = 1.02                        # DefaultStoveRenderer.render：translate(0.5, 1.02, 0.5)
STOVE_SIZE = 0.375                            # DefaultStoveRenderer.SIZE：一件 0.375 格 = 6 像素宽
STOVE_SCALE = STOVE_SIZE * FD_SCALE

# ---- 站点里的摆法（HoD，BoardScene）
BLOCK_SCALE = BoardScene.itemScale(True)     # 方块类在板上是棱长 5.2 像素的立方体（HoD 的 BLOCK_SCALE 0.65：整块方块放在板上会挡住上面的东西）
BOARD_FOOD_SCALE = BoardScene.itemScale()    # 板上等着切的东西 10 像素
CARVED_SCALE = BoardScene.scaleOf(BoardScene.CARVED_SCALE * 16.0)
PILE_TURN = 17.0                              # 一叠的底下那张转的角度（scene 里 pile 节点的 rotation）
FOOD_SCALE = 1.2                              # 做好的菜 9.6 像素


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


def modelCount(count, maxStack=64):
    """FD 的渲染器一叠画几张（getModelCount，砧板和煎锅同一个）：1 个 1 张，多个是 1 + ceil(个数 / 最大叠数 * 4)。"""
    if count <= 1:
        return 1
    return 1 + int(math.ceil(float(count) / max(1, maxStack) * 4))


def isItem(value):
    """是一件真的物品（客户端读方块实体数据时，空值可能是整数之类的占位，不是 None）。"""
    return isinstance(value, dict) and bool(value.get("newItemName")) and (value.get("count", 1) or 0) > 0


def _single(item):
    """展示用的一件（数量 1，只带名字和 aux）。"""
    return {"newItemName": item["newItemName"], "newAuxValue": item.get("newAuxValue", 0) or 0, "count": 1}


def _jitter(seed, index, span):
    """确定的小偏移（-span 到 span）：同样的种子每次画都一样，不会一刷新就跳。要混匀：只取低 16 位的话 x 和 z 的偏移差是个常数，一叠的几张排成一条斜线。"""
    value = (seed * 2654435761 + index * 40503) & 0xFFFFFFFF
    value = ((value ^ (value >> 15)) * 2246822519) & 0xFFFFFFFF
    value = ((value ^ (value >> 13)) * 3266489917) & 0xFFFFFFFF
    value ^= value >> 16
    return ((value & 0xFFFF) / 65535.0 * 2.0 - 1.0) * span


def _seedOf(item):
    """FD 的渲染器拿物品编号 + 损伤值当随机数的种子（同一种东西每次画的一叠都一个样，和方块在哪无关）；客户端不知道 JE 的物品编号，用名字和 aux 算一个固定的数。"""
    seed = item.get("newAuxValue", 0) or 0
    for char in item["newItemName"]:
        seed = (seed * 31 + ord(char)) & 0x7FFFFFFF
    return seed


def _scatter(seed, layer):
    """这一张的 (x, z) 错开量（格）。"""
    return _jitter(seed, layer * 2, FD_SPREAD), _jitter(seed, layer * 2 + 1, FD_SPREAD)


def _cubeCenter(height, scale):
    """立着的方块物品（掉落物是个小立方体，中心固定在轴心上方 CUBE_LIFT）：立方体的中心要在 height 格高，报出去的"中心"（道具按贴图物品算轴心）要在哪。"""
    return height + (scale * BoardScene.SPRITE_SPAN / 2.0 - BoardScene.CUBE_LIFT) / 16.0


def carvedFront(yaw):
    """板上插着的工具的贴图正面朝哪（世界方向 dx, dz）：renderItemCarved 比摆平的东西多转半圈，正面朝板 FACING 的反方向，即板自己坐标里的 +z（模型的正面是 -z）。yaw 是板的朝向（度，StoveFacing.yawOfAux）。"""
    return StoveFacing.turnOffset(yaw, 0.0, 1.0)


def _carved(shown, itemType, yaw):
    """插着的工具（FD 的 renderItemCarved，站点里和没开站时是同一个）：方块正中心、0.23 格高。"""
    return Placement(shown, (BoardScene.CARVED_X / 16.0, BoardScene.CARVED_HEIGHT / 16.0, BoardScene.CARVED_X / 16.0), False, carvedFront(yaw),
                     BoardScene.carvedRoll(itemType), CARVED_SCALE)


def _lying(shown, center, along, raised, scale):
    """板上平躺的一件：center 是它该在的中心。raised（花、野生作物）：引擎把它整体抬高、轴心也不在底边，报出去的中心先反着挪（ItemPose.raisedShift），
    和方块那一支把立方体的抬高算进中心是同一个做法——摆的人（Client/BlockItems）只管照贴图物品的规矩摆。"""
    if raised:
        shift = ItemPose.raisedShift(ItemPose.flatMatrix(along[0], along[1]), scale)
        center = tuple(a + b / 16.0 for a, b in zip(center, shift))
    return Placement(shown, center, True, along, 0.0, scale)


def fdBoardLayout(item, itemType, carving, isBlock, yaw=0, maxStack=64):
    """砧板站点不在场时板上的东西：FD 的 CuttingBoardRenderer.render。一叠画 modelCount 张，每张抬高 FD_LAYER_RISE、x z 各错开一点（只有一张时不错开），
    朝向跟着板（-FACING.getOpposite().toYRot()，和炉灶同一个转法：StoveFacing.turnOffset）；方块类立着、正面朝板 FACING 那一侧。"""
    if not isItem(item):
        return []
    shown, seed = _single(item), _seedOf(item)
    if carving(item):
        return [_carved(shown, itemType, yaw)]
    layers, block = modelCount(item.get("count", 1) or 1, maxStack), isBlock(item)
    placements = []
    for layer in range(layers):
        dx, dz = _scatter(seed, layer) if layers > 1 else (0.0, 0.0)
        if block:
            base, javaScale = FD_BOARD_BLOCK
            scale = javaScale * FD_SCALE
            center = (0.5 + dx, _cubeCenter(base + FD_LAYER_RISE * (layer + 1), scale), 0.5 + dz)
            placements.append(Placement(shown, center, False, StoveFacing.turnOffset(yaw, 0.0, -1.0), 0.0, scale))
        else:
            base, javaScale = FD_BOARD_LYING
            center = (0.5 + dx, base + FD_LAYER_RISE * (layer + 1), 0.5 + dz)
            placements.append(_lying(shown, center, StoveFacing.turnOffset(yaw, 1.0, 0.0), itemType == "block", javaScale * FD_SCALE))
    return placements


def boardLayout(item, itemType, carving, isBlock, offset=(0.0, 0.0), yaw=0):
    """砧板站点在场时板上等着切的东西 / 插着的工具：站点里摆的（HoD 的 BoardScene），关站、开站不跳。carving / isBlock 同 layout 的（站点里问的是同一个）；
    offset 是从方块中心挪到板底座中间的量（方块分数，x 往东 z 往南）；yaw 是板的朝向（度），插着的工具跟着它转。"""
    if not isItem(item):
        return []
    shown = _single(item)
    if carving(item):
        return [_carved(shown, itemType, yaw)]
    cx, cz = 0.5 + offset[0], 0.5 + offset[1]
    if isBlock(item):
        return [Placement(shown, (cx, BOARD_TOP + BoardScene.blockLift(BLOCK_SCALE) / 16.0, cz), False, (0.0, -1.0), 0.0, BLOCK_SCALE)]
    raised = itemType == "block"          # 走到这里的方块类是平躺着画的那几样（花、野生作物）：引擎照方块物品的规矩抬高着画
    flat = [_lying(shown, (cx, BOARD_TOP + 0.02 + BoardScene.pileLift(item.get("count", 1) or 1) / 16.0, cz), (1.0, 0.0), raised, BOARD_FOOD_SCALE)]
    if (item.get("count", 1) or 1) > 1:
        angle = math.radians(PILE_TURN)
        flat.insert(0, _lying(shown, (cx, BOARD_TOP + 0.02, cz), (math.cos(angle), math.sin(angle)), raised, BOARD_FOOD_SCALE))
    return flat


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


def skilletLayout(item, yaw=0, maxStack=64):
    """FD 的 SkilletRenderer.render：一叠画 modelCount 张，每张抬高 FD_LAYER_RISE、x z 各错开一点（一张也错开）、朝向跟着锅（和炉灶同一个转法：我们的朝向是锅柄那一侧，
    FD 的 FACING 是人看的方向，两边都是 -放它的人面朝的方向.toYRot()）。"""
    if not isItem(item):
        return []
    shown, seed = _single(item), _seedOf(item)
    base, javaScale = FD_SKILLET
    along = StoveFacing.turnOffset(yaw, 1.0, 0.0)
    placements = []
    for layer in range(modelCount(item.get("count", 1) or 1, maxStack)):
        dx, dz = _scatter(seed, layer)
        placements.append(Placement(shown, (0.5 + dx, base + FD_LAYER_RISE * (layer + 1), 0.5 + dz), True, along, 0.0, javaScale * FD_SCALE))
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
            placements.append(Placement(_single(item), (cx, FD_STOVE_HEIGHT, cz), True, direction, 0.0, STOVE_SCALE))
    return placements


def layout(kind, items, itemTypeOf, pos, offset=(0.0, 0.0), yaw=0, carving=None, isBlock=None, maxStackOf=None):
    """kind 方块种类、items {"槽": 物品}、itemTypeOf(物品) -> 物品类型（客户端查 GetItemBasicInfo）、pos 方块坐标、maxStackOf(物品) -> 一叠最多几个（不给按 64）；
    yaw 是方块的朝向（度，StoveFacing.yawOfAux）：炉灶转烤位、煎锅和砧板转食物（砧板还转插着的工具）；offset 只有砧板站点在场时用：板底座中间离方块中心的量（方块分数）；
    carving、isBlock 只有砧板用：carving(物品) 说是不是插着的工具、isBlock(物品) 说画成立着的方块还是平躺的图标（BoardStation.Env.isCarving / isBlock）。"""
    maxStack = maxStackOf or (lambda item: 64)
    if kind == KIND_BOARD:
        layers = [items.get(layerKey(index)) for index in range(DISH_LAYERS)]
        if isItem(items.get(DISH_KEY)) or any(isItem(layer) for layer in layers):
            return boardDishLayout(layers, items.get(DISH_KEY), posHash(pos), offset)
        item = items.get("0")
        if not isItem(item):
            return []
        if Options.cuttingBoard():                    # 站点在场：开站的人看到的是站点里的摆法，关着站点时也摆成那样
            return boardLayout(item, itemTypeOf(item), carving, isBlock, offset, yaw)
        return fdBoardLayout(item, itemTypeOf(item), carving, isBlock, yaw, maxStack(item))
    if kind == KIND_SKILLET:
        item = items.get("0")
        return skilletLayout(item, yaw, maxStack(item)) if isItem(item) else []
    if kind == KIND_STOVE:
        return stoveLayout(items, yaw)
    return []
