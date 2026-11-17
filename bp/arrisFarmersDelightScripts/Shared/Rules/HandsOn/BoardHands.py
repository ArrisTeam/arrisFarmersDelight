# -*- coding: utf-8 -*-
"""BoardHands - 砧板摆盘时手怎么放液体层和蛋层：哪些层走手、倒在哪、磕在哪、要多久、层最后画成什么（双端，纯规则）

移植自 Hands-On Delight：client/BoardBehavior.java 的常量（148-157）、dress（1963-1984）、arrives（1986-2027）、handFrom 的高度（2044-2055）、
arrive 里每层要多久（1583-1617）、pourUntil（250、1526）；client/KitchenLooks.java 的 isPoured / isCracked / opened / liquidColor（32-55）；
标签 data/handson_delight/tags/items/poured.json / cracked.json（名单照搬：Shared/Data/PotSunk.py，厨锅用同一份，只留本包有的物品）。
手的动作本身（端过来、仰一下、倾倒、磕、落）是 KitchenMotions 的 Pour（93-283）、Crack（394-571），厨锅也用它，在 PotServePour / PotServeHands 里；
这里只给板上的参数：

- 液体层（poured 标签的东西，第 1 层起；第 0 层是底座，照旧画容器）：一只手端着装满的容器从光标（书里点的菜从屏幕底边）来，在这一层的落点上方倾倒
  （容器画 POUR_SIZE 像素，往屏幕左边倾，落点比层底高 POUR_LIFT），倒空了换成空容器端走。HoD 在倒的时候在下面那层的轮廓上长出一层薄薄的、
  取液体颜色的淋面（dress、ItemVoxels.film）；掉落物染不了色也画不出贴着轮廓的膜，所以这一层倒完什么也不画（lookOf 是 None）。
- 蛋层（cracked 标签的东西，哪一层都磕）：手端着蛋在板上、食物右侧 KNOCK_ASIDE 像素的地方磕一下（碎壳和脆响），再到这一层的落点上方打开，蛋液落到食物上，
  落稳了才露出这一层；这一层画成打开的蛋（煎蛋的图标，HoD 染 RAW_EGG，这里用 EggLook 烤进图标的第 0 档）。
坐标是站点像素（16 = 1 格，+x 往屏幕左边、+z 往远处，和 JE 的场景同一个坐标系），高度离站点地面；"板面中心"是 (cx, cz)。
"""
from .BoardMotion import LAYER_STEP, PLAYER_LAND_TIME, SETTLE_TIME
from .BoardScene import TOP, layerSize
from .PotServeHands import CRACK_ARRIVE, KNOCK_DOWN, Crack
from .PotServePour import ARRIVE, TIP, Pour
from ...Data import PotSunk, Remainders
from ...Data.BrothColors import FALLBACK, MainColors, PouredColors
from ..EggLook import itemOf as eggLookOf

POUR, CRACK = "pour", "crack"
POUR_SIZE = 5.0              # BoardBehavior:152 倒的时候手里的容器画多大（像素）
POUR_HEIGHT = 4.0            # :153 手从层顶上方这么高来（光标所在的那一层平面、或屏幕底边投到的那一层）
EGG_SIZE = 3.6               # :154 手里的蛋画多大
KNOCK_ASIDE = 5.5            # :155 蛋磕在食物的屏幕右侧这么远（x 减去它：+x 是屏幕左边）
FILM_SHARE, FILM_THICK = 0.85, 0.12     # :156-157 HoD 的淋面占图标几成、多厚：这边画不了淋面，不用
POUR_LIFT = 0.3              # :1998 倒的落点比这一层的底高这么多（蛋直接落在层的底上）
POUR_SIDE = -1.0             # :2001 容器往屏幕左边倾
HAND_YAW = 0.0               # :2001 / :2020 手的动作在场景坐标里算，镜头朝哪由前置包的站点空间管，这里不转
EGG_LOOK = eggLookOf(0.0)    # KitchenLooks:42-49 打开的蛋：煎蛋的图标按 RAW_EGG 着色 = 刚打进来的蛋清（EggLook 第 0 档，arris:egg_look_0）

POURED = frozenset(name for name, _aux in PotSunk.POURED)
CRACKED = frozenset(name for name, _aux in PotSunk.CRACKED)
_BUCKET = "minecraft:bucket"


def kindOf(index, name):
    """这一层（第 index 层、物品 name）怎么放下去：POUR 倒（液体；第 0 层是底座，照旧落下：BoardBehavior:1993 的 index > 0）、
    CRACK 磕（蛋；哪一层都磕：:2011）、None 照旧从光标 / 玩家那边落下。"""
    if name in POURED and index > 0:
        return POUR
    return CRACK if name in CRACKED else None


def isBucket(name):
    """装它的容器是不是桶（Pour.isBucket：合成剩余物是原版的桶）：桶慢而粗（倾 105 度、流 0.8 秒），瓶和碗快而细（125 度、0.55 秒）。"""
    return Remainders.craftRemainderOf(name) == _BUCKET


def containerOf(name):
    """倒空之后留在手里的容器（KitchenMotions.containerOf：物品的合成剩余物，奶桶 -> 桶、蜂蜜瓶 -> 玻璃瓶、番茄酱 -> 碗），没有是 None。"""
    return Remainders.craftRemainderOf(name)


def liquidColor(name):
    """倒出来的液体什么颜色，ARGB（KitchenLooks.liquidColor：满的图标和空容器的图标不一样的那些像素；厨锅同一张表 PouredColors）。"""
    return 0xFF000000 | (PouredColors.get(name) or MainColors.get(name) or FALLBACK)


def lookOf(index, item):
    """这一层躺在板上画成什么（dress）：液体层不画（None）；蛋画成打开的蛋（EGG_LOOK）；别的原样。item 是引擎的物品字典。"""
    kind = kindOf(index, item["newItemName"])
    if kind == POUR:
        return None
    if kind == CRACK:
        return {"newItemName": EGG_LOOK, "newAuxValue": 0, "count": item.get("count", 1)}
    return item


def layerTop(index, kind):
    """手要对准的高度：这一层的底（TOP + 层号 * LAYER_STEP），倒液体的落点再高 POUR_LIFT（arrives:1998、:2015）。"""
    return TOP + index * LAYER_STEP + (POUR_LIFT if kind == POUR else 0.0)


def handHeight(index, kind):
    """手从哪一层平面来：落点上方 POUR_HEIGHT（arrives:1999、:2016 传给 handFrom 的高度，光标和屏幕底边都投到这个面上）。"""
    return layerTop(index, kind) + POUR_HEIGHT


def pourFor(index, name, x, z, center, start):
    """第 index 层倒下去的手（arrives:2000-2001）：x、z 是这一层的偏移（layerJitter），center 是板面中心 (cx, cz)，start 是手从哪来（站点像素 (x, y, z)）。
    返回 PotServePour.Pour：厨锅倒液体用的同一个动作，落点是这一层的中心、液面高度是 layerTop。"""
    top = layerTop(index, POUR)
    return Pour(isBucket(name), start, (center[0] + x, top, center[1] + z), top, POUR_SIZE, POUR_SIDE, HAND_YAW, liquidColor(name), "pour", None)


def crackFor(index, x, z, center, start, turn):
    """第 index 层磕下去的手（arrives:2017-2020）：蛋在板上 (cx - KNOCK_ASIDE, TOP, cz + z) 磕，蛋液落在这一层的中心，蛋液躺着转 turn 度、
    画这一层的大小（layerSize）。返回 PotServeHands.Crack：sinks 假（落了就由这一层接手）、liquid 假（落在食物上，没有涟漪和水花）。"""
    top = layerTop(index, CRACK)
    return Crack(start, (center[0] - KNOCK_ASIDE, TOP, center[1] + z), (center[0] + x, 0.0, center[1] + z), top, EGG_SIZE, layerSize(index),
                 False, HAND_YAW, turn, False)


def flowAt():
    """液体从瓶口开始流的时刻（秒，从手出发算起）：端过来 + 仰一下。出声就在这一刻（Pour:229）。"""
    return ARRIVE + TIP


def knockAt():
    """蛋磕在板沿上的时刻：端过来 + 磕下去（Crack:491-494，碎壳和脆响）。"""
    return CRACK_ARRIVE + KNOCK_DOWN


def landsBy():
    """蛋液落到食物上的时刻（Crack.landsBy，0.9 秒）。"""
    return Crack.landsBy()


def pouredBy(name):
    """液体全倒出来的时刻（Pour.pouredBy：桶 1.3 秒、瓶 1.05 秒）。"""
    return Pour.pouredBy(isBucket(name))


def lasts(index, name):
    """手把这一层放好要多久（秒）：液体倒完、蛋落下。做成菜要等它（pourUntil，250 / 1526；JE 只等倒液体，蛋这边也等：蛋没落下时这一层还没露出来）。"""
    kind = kindOf(index, name)
    if kind == POUR:
        return pouredBy(name)
    return landsBy() if kind == CRACK else 0.0


def takes(index, name):
    """书里一次放的几层，这一层从出发到落稳要多久（arrive:1594-1595）：倒液体 pouredBy、磕蛋 landsBy + SETTLE_TIME、别的 PLAYER_LAND_TIME + SETTLE_TIME。"""
    kind = kindOf(index, name)
    if kind == POUR:
        return pouredBy(name)
    return landsBy() + SETTLE_TIME if kind == CRACK else PLAYER_LAND_TIME + SETTLE_TIME
