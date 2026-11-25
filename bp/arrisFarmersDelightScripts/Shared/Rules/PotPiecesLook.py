# -*- coding: utf-8 -*-
"""PotPiecesLook - 汤里的碎料交给着色器的几个数：配料槽、出现 / 缩走的钟，和一块碎料此刻在哪（双端，纯计算）

JE（Diegesis 的 LiquidPieces，移植在 HandsOn/PotPieces.py）每帧在 CPU 上算每一块的位置、逐块画。基岩版把这件事交给厨锅模型的
顶点着色器（rp/shaders/glsl/arris_pot_broth_vertex.glsl）：模型的 broth 骨骼里有 MOST 张小面片，着色器按同一套公式（金角螺旋、
随汤转、一块块从面下冒上来）把它们摆到位、挑图案和颜色，脚本每帧只给这几个数：
- 配料槽（至多 SLOTS 个，dishSlots）：这道菜的配方里会留下碎料的配料各是哪一类、什么颜色，一槽一个数 = 类 * 262144 + 18 位颜色
  （每通道 6 位）。每一类切成哪几块见 CUTS（就是 PotPiecesKinds.cut），每两块食材之后一滴油（sourceOf）；
- 钟（PiecesClock）：limit = 汤里有几块（带小数：最上面那块长到多大），clock = 按出生先后走的钟（第 i 块的年龄 = (clock - i) * STEP 秒），
  打包成一个数 = round(limit * LIMIT_STEPS) * 128 + clock。
和 JE 不一样的地方（着色器里每块只知道自己）：块和块不互相挤开、不绕开勺子和整件的料、不翻身；随汤转的快慢按离心的远近分
TURN_STEPS 档（转角才能回卷）；缩走是从最后一块起一块接一块（每秒 LEAVE 块），不是一起缩；汤里已经有碎料时再添的那几块是直接长出来的。
"""
import math

from . import CookingPot, ItemTags
from .HandsOn import PotPiecesKinds as Kinds
from .HandsOn.PotColors import FALLBACK, isGreen
from .HandsOn.PotPiecesPiece import APPEAR_HALF_LIFE, GOLDEN_ANGLE, OUTWARD_STEP, REACH, RISE_TIME
from ..Data import PotPieceTraits, PotSunk, Remainders
from ..Data.BrothColors import CookedForms, MainColors

MOST = Kinds.PIECES_MOST            # 模型里的面片数
SLOTS = 4                           # 一道菜至多几种配料有碎料（着色器的一组 uniform 是四个数）
EMPTY = (0.0,) * SLOTS
KINDS = (Kinds.COIN, Kinds.CHUNK, Kinds.NUGGET, Kinds.SHRED, Kinds.LEAF, Kinds.DROP)   # 图案号：贴图里从上到下的次序
NONE, EGG, GRAIN, PASTA, MEAT, GREEN, OTHER = range(7)                                  # 配料的类
CUTS = {                            # 每一类切成哪几块：(图案, 多宽)；和 PotPiecesKinds.cut 一样（测试对着它查）
    EGG: ((Kinds.SHRED, Kinds.HERB), (Kinds.NUGGET, Kinds.SMALL)),
    GRAIN: ((Kinds.NUGGET, Kinds.GRAIN),) * Kinds.GRAINS,
    PASTA: ((Kinds.SHRED, Kinds.HERB), (Kinds.SHRED, Kinds.HERB)),
    MEAT: ((Kinds.CHUNK, Kinds.BIG), (Kinds.NUGGET, Kinds.SMALL)),
    GREEN: ((Kinds.LEAF, Kinds.HERB), (Kinds.SHRED, Kinds.HERB)),
    OTHER: ((Kinds.COIN, Kinds.BIG * 0.9), (Kinds.NUGGET, Kinds.SMALL)),
}
CLASS_UNIT = 262144                 # 槽里类的那一位：2 ** 18
STEP = APPEAR_HALF_LIFE * math.log(1.0 / 0.7, 2.0)     # 上一块长到三成下一块才出发（LiquidPieces.update）：0.0823 秒一块
TAIL = 14.0                         # 最后一块出发之后钟再走这么多块，它才长满、冒到面上
LEAVE = 30.0                        # 缩走：每秒这么多块
LIMIT_STEPS = 8.0                   # limit 的小数分几档
CLOCK_ROOM = 128.0                  # 打包时钟占的位置（MOST + TAIL 比它小）
RING_AFTER = 0.235 * RISE_TIME / STEP   # 出发之后过这么多块，它冒到了面上九成：敲一圈涟漪（LiquidPieces 的 risen >= 0.9）
TURN_STEPS = 20.0                   # 随汤转的快慢分这么多档
TURN_WRAP = 2.0 * math.pi * TURN_STEPS      # 汤转过的角度到这儿回卷：各档都正好是整圈，碎料不跳
HALF = 4.0                          # 汤的内壁离锅心（像素）
MEAN_SIZE = 1.2                     # 算涟漪落点时碎料按这么大算（差不到 0.2 像素）
_dishes = {}


def traitsOf(name):
    """这件配料的特征（PotPiecesKinds.cut 用的那几样）。"""
    traits = set()
    if any(name == cracked for cracked, _ in PotSunk.CRACKED):
        traits.add("egg")
    for trait, names in (("grain", PotPieceTraits.GRAINS), ("pasta", PotPieceTraits.PASTA), ("meat", PotPieceTraits.MEAT)):
        if name in names:
            traits.add(trait)
    return traits


def classOf(traits, color):
    """配料的类：蛋最先判，然后谷物、意面、肉，再看颜色是不是绿的（CookedPieces.cut 的次序）。"""
    for trait, found in (("egg", EGG), ("grain", GRAIN), ("pasta", PASTA), ("meat", MEAT)):
        if trait in traits:
            return found
    return GREEN if isGreen(color) else OTHER


def packSlot(kind, color):
    """一个配料槽：类 * 262144 + 颜色（每通道四舍五入到 6 位）。"""
    red, green, blue = [int((color >> shift & 0xFF) / 255.0 * 63.0 + 0.5) for shift in (16, 8, 0)]
    return float(kind * CLASS_UNIT + red * 4096 + green * 64 + blue)


def unpackSlot(slot):
    """packSlot 的反过来：(类, 0xRRGGBB)，着色器里是同一套算术。"""
    kind = int(slot // CLASS_UNIT)
    rest = int(slot) - kind * CLASS_UNIT
    red, green, blue = [int(part / 63.0 * 255.0 + 0.5) for part in (rest // 4096, rest // 64 % 64, rest % 64)]
    return kind, red << 16 | green << 8 | blue


def slotsOf(items, colorOf=None):
    """items（煮熟之后的配料名，按配方的先后）-> SLOTS 个槽；多出来的配料不画。"""
    colorOf = colorOf or (lambda name: MainColors.get(name, FALLBACK))
    slots = [packSlot(classOf(traitsOf(name), colorOf(name)), colorOf(name)) for name in items[:SLOTS]]
    return tuple(slots + [0.0] * (SLOTS - len(slots)))


def dishSlots(mealName):
    """这道菜的配料槽：配方（第一种做法：每格的第一个选项，没有格子的是第一种写法，CookingPot.framesOf）里会留下碎料的配料——
    用掉会留下容器的、倒进去的、化掉的、煮完拣出来的不算，生的换成它烧熟的样子（CookedPieces.ingredients）。
    没有配方、写法是空的（新接口登记的配方标签格还没有成员）或没有这样的配料是 EMPTY：汤里不浮东西。"""
    stamp = (CookingPot.revision(), ItemTags.generation())       # 配方表改了、标签的答案变了：重新看第一种做法
    if _dishes.get(None) != stamp:
        _dishes.clear()
        _dishes[None] = stamp
    if mealName not in _dishes:
        recipe = CookingPot.findRecipeByResult(mealName)
        frames = CookingPot.framesOf(recipe) if recipe else []
        names = [entry[0] for entry in frames[0]] if frames else []
        gone = set(name for name, _ in PotSunk.POURED + PotSunk.DISSOLVES) | PotPieceTraits.STRAINED
        items = Kinds.ingredientsOf(names, lambda name: Remainders.potRemainderOf(name) is not None, lambda name: name in gone,
                                    lambda name: CookedForms.get(name, name))
        _dishes[mealName] = slotsOf(items)
    return _dishes[mealName]


def sourceOf(index, classes):
    """第 index 块是哪个槽切出来的第几块：(槽号, 第几块)，一滴油是 (None, 0)；classes 是各槽的类。着色器里是同一套算术。"""
    counts = [len(CUTS[kind]) if kind else 0 for kind in classes]
    food = sum(counts)
    if not food:
        return None, 0
    drops = food // Kinds.PIECES_PER_DROP
    order = index % (food + drops)
    third = order // (Kinds.PIECES_PER_DROP + 1)
    if order % (Kinds.PIECES_PER_DROP + 1) == Kinds.PIECES_PER_DROP and third < drops:
        return None, 0
    piece = order - min(drops, third)
    for slot, count in enumerate(counts):
        if piece < count:
            return slot, piece
        piece -= count
    return None, 0


def reachOf(index):
    """第 index 块离锅心多远（0..1，LiquidPieces.Piece 的 reach）。"""
    return math.sqrt(0.06 + 0.94 * (index * OUTWARD_STEP % 1.0))


def turnRate(reach):
    """这一块随汤转得多快（汤的流速的几倍）：JE 是 0.45 + 0.75 * reach，这里取到最近的 1 / TURN_STEPS。"""
    return math.floor((0.45 + 0.75 * reach) * TURN_STEPS + 0.5) / TURN_STEPS


def wayOf(index, turned, size=MEAN_SIZE):
    """第 index 块此刻在哪：相对锅心的 (x, z)，锅自己的坐标（像素）。turned 是汤转过的角度（弧度，回卷过也一样）。"""
    reach = reachOf(index)
    angle = index * GOLDEN_ANGLE + turned * turnRate(reach)
    cos, sin = math.cos(angle), math.sin(angle)
    stretch = reach * REACH / max(abs(cos), abs(sin))        # 圆被推到方壁的角上：按方形的汤填满
    room = HALF - size * 0.3
    return cos * stretch * room, sin * stretch * room


class PiecesClock(object):
    """一口锅的碎料此刻有几块、各多大。每帧 step，把 packed() 和 slots 推给模型。"""

    def __init__(self):
        self.limit = self.clock = 0.0
        self.key, self.slots = None, EMPTY
        self.rung = 0                   # 已经冒到面上的块数（敲过涟漪的）

    def step(self, dt, wanted, key=None, slots=EMPTY):
        """推进 dt 秒：这锅要浮 wanted 块 key 这道菜的碎料（slots 是它的配料槽）。返回这一帧冒到面上的块的序号。"""
        if self.limit > 0.0 and key != self.key:
            wanted = 0                                          # 换了一道菜：原来的先缩走
        if self.limit <= 0.0:
            self.key, self.slots = key, slots
            self.clock, self.rung = 0.0, 0
        if wanted > self.limit:
            self.limit = min(float(wanted), self.limit + dt / STEP)
        elif wanted < self.limit:
            self.limit = max(float(wanted), self.limit - dt * LEAVE)
        if self.limit <= 0.0:
            self.clock = 0.0
        else:
            self.clock = min(self.clock + dt / STEP, max(self.clock, self.limit + TAIL))
        up = min(int(math.floor(self.clock - RING_AFTER)) + 1, int(math.ceil(self.limit))) if self.clock >= RING_AFTER else 0
        born = list(range(self.rung, up))
        self.rung = up
        return born

    def packed(self):
        """给着色器的那一个数。"""
        return float(int(self.limit * LIMIT_STEPS + 0.5)) * CLOCK_ROOM + min(self.clock, CLOCK_ROOM - 1.0)
