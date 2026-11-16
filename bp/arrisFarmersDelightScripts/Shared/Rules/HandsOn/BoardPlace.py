# -*- coding: utf-8 -*-
"""BoardPlace - 把一叠东西放上砧板、拿回去、插工具：板怎么收（双端，纯规划）

移植自 Hands-On Delight 的 station/BoardLogic.java：place（172-239）、isDone / clear / startDish（241-297）、carve（260-280）、
take（525-541）、refuse（613-630）。只算"板和层变成什么样、手上少几个、给厨师什么、发什么事"，不碰引擎、不改入参；
服务端（Compat/Diegesis/BoardLogic.py）按结果去动方块实体、光标栈和背包。

放的判定树（place）：
  1. 手上是板上的工具 -> 什么也不放（客户端敲一声）；
  2. 板上有东西、没有层、和手上不是同一种：板上的 + 手上这件能接成某道菜 -> 板上的成为第 0 层（至多一批 16 个，多的还给厨师）；
     板上的是"没活干的"（插着的工具、做好的菜）而手上是能切的或能打底的 -> 板上的整个还给厨师；
  3. 有层了，或者板空着、手上的不能切、能打底：新一层要还是某道菜的前缀、层数 <= 9，否则弹回；一层放几个：第 0 层最多 16、
     以后的层最多和第 0 层一样多（最薄的一层定份数），右键只放一个；
  4. 别的：板空着时能切的整叠放上去，板上是同种的接着叠（都不超过物品的最大堆叠和 BOARD_MAX），否则弹回。
手上这一叠是光标栈或背包里的一格（Shift 点托盘），差别只在服务端从哪里扣。byUse（右键开站那一下手里拿着的）板不收就一声不吭。
板上、层里的东西是整件的（附魔、染色、改名、耐久这些数据一起，取回原样还，ItemData.py）；数据存不进方块实体数据的（storable 说否）板不收，
同名同 aux 但数据不一样的不叠在一起（JE 的 isSameItemSameTags）。
"""
from . import ItemData
from .Assembly import BATCH, MOST_LAYERS
from .Items import keyOf

BOARD_MAX = 64               # 板上一种东西放多少（HoD 取物品的最大堆叠，gametest 放 20 个卷心菜）

PLACED = "placed"
REFUSED = "refused"
TAKEN = "taken"
CARVED = "carved"


def stackOf(item, count):
    """拷一份、改个数：名字、aux、数量和全部数据（附魔、耐久、改名……）。"""
    return ItemData.copyOf(item, count)


def eventStack(item, count):
    """事件里给客户端看的一份（弹回 / 拿走的动画）：只有名字、aux、数量（和工具的耐久）。"""
    return ItemData.light(item, count)


class Placed(object):
    """一步的结果。board / layers 是新的板和层；moved 是手上那叠少了几个；give 是还给厨师的整叠；events 是 [(名字, 数据)]；
    restart 为真板上换了东西、刀口要重布；finish 为真放的是一层、该看看做成没有；ignored 为真是工具，什么也没发生。"""

    __slots__ = ("board", "layers", "moved", "give", "events", "restart", "finish", "ignored")

    def __init__(self, board, layers):
        self.board = board
        self.layers = list(layers)
        self.moved = 0
        self.give = []
        self.events = []
        self.restart = False
        self.finish = False
        self.ignored = False

    def refuse(self, carried, quiet):
        """板不收：手上这叠弹回去（带一个当样子）；quiet（开站时手里的）一声不吭。"""
        if not quiet:
            self.events.append((REFUSED, {"stack": eventStack(carried, 1)} if keyOf(carried) is not None else {}))
        return self

    def clear(self, env):
        """板上的整个还给厨师（clear，251-258）：事件 taken（-1 = 板上的，插着的工具带 carved）。"""
        self.events.append((TAKEN, {"stack": eventStack(self.board, self.board["count"]), "at": -1, "carved": env.isCarving(self.board)}))
        self.give.append(self.board)
        self.board = None
        self.restart = True


def place(carried, board, layers, one, byUse, env):
    """手上一叠 carried 放上板（board 是板上的、layers 是摆盘的层）。one：右键只放一个。返回 Placed。"""
    result = Placed(board, layers)
    if keyOf(carried) is None:
        result.ignored = True
        return result
    if env.isTool(carried, board):
        result.ignored = True
        return result
    if not env.canHold(carried):
        return result.refuse(carried, byUse)             # 数据存不进方块实体数据的东西：板不收，绝不悄悄丢数据
    cuttable = env.cuttable(carried)
    same = keyOf(board) == keyOf(carried) and ItemData.same(board, carried)
    if not result.layers and keyOf(board) is not None and not same and env.fits([board], carried):
        # 等着切的东西成为第 0 层：先躺下等切，下一层放上来时才开始做菜（startDish，286-297）
        base = stackOf(board, min(board["count"], BATCH))
        if board["count"] > base["count"]:
            result.give.append(stackOf(board, board["count"] - base["count"]))
        result.board, result.layers, result.restart = None, [base], True
    elif not result.layers and keyOf(board) is not None and not same and env.isDone(board) and (cuttable or env.isBase(carried)):
        result.clear(env)
    if result.layers or (keyOf(result.board) is None and not cuttable and env.isBase(carried)):
        if len(result.layers) >= MOST_LAYERS or not env.fits(result.layers, carried):
            return result.refuse(carried, byUse)
        batch = BATCH if not result.layers else result.layers[0]["count"]
        count = 1 if one else min(carried["count"], batch)
        result.events.append((PLACED, {"at": len(result.layers)}))
        result.layers.append(stackOf(carried, count))
        result.moved, result.finish = count, True
        return result
    onBoard = result.board
    fits = cuttable if keyOf(onBoard) is None else (same and not env.isCarving(onBoard))
    room = min(env.maxStack(carried), BOARD_MAX) - (onBoard["count"] if keyOf(onBoard) is not None else 0)
    moved = min(1 if one else carried["count"], room)
    if not fits or moved <= 0:
        return result.refuse(carried, byUse)
    result.board = stackOf(carried, (onBoard["count"] if keyOf(onBoard) is not None else 0) + moved)
    result.moved = moved
    result.restart = result.restart or keyOf(onBoard) is None
    result.events.append((PLACED, {}))
    return result


def take(board, layers, env):
    """点一下取回（take，525-541）：有层拿走最上一层，没有层就把板上的整个还给厨师。"""
    result = Placed(board, layers)
    if result.layers:
        top = result.layers.pop()
        result.events.append((TAKEN, {"stack": eventStack(top, top["count"]), "at": len(result.layers), "carved": False}))
        result.give.append(top)
    elif keyOf(board) is not None:
        result.clear(env)
    return result


def carve(carried, board, layers, env):
    """工具插进空板（carve，264-280）：手上是能插的工具、没有层、板是空的才行，插一件。"""
    result = Placed(board, layers)
    if keyOf(carried) is None or not env.canStick(carried) or layers or keyOf(board) is not None:
        return result.refuse(carried, False)
    result.board = stackOf(carried, 1)
    result.moved, result.restart = 1, True
    result.events.append((CARVED, {}))
    return result
