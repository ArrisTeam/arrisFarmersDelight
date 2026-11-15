# -*- coding: utf-8 -*-
"""Cutting - 切菜板的切法规划、刀口布局、落刀校验与工具判定（双端）

移植自 Hands-On Delight 的 station/Cutting.java（Plan / Style）、station/BoardLogic.java（chop / restart /
crossOnTheItem）与 client/ToolStroke.java（of）。

一件食材按切出的件数得到若干刀口(marks)，刀口按顺序一刀一刀落：服务端只认"下一个刀口"，且两刀之间有最小间隔；
最后一刀落下时，整叠食材（最多 BATCH 件，受工具耐久限制）一起切开。刀口的位置/角度由服务端随机布局后同步给客户端，
客户端只照着画。布局是纯函数 + 注入的随机数，方便离线测试。

时间一律是秒（原版以刻计，20 刻/秒）。
"""
import math
import random

from .Mth import EPS, clamp

MOST_MARKS = 3           # 一件食材最多几个刀口：蛋糕切 7 块也只落 3 刀
STRIP_MARKS = 3          # 原 Cutting.STRIPS：意面条固定 3 刀
BATCH = 16               # 最后一刀一次切开的最大件数
CHOP_GAP = 0.15          # 原 CHOP_GAP = 3 刻：服务端接受的两刀之间的最小间隔
SPOT_FROM = 0.2          # 刀口落在食材全长（从远端算）的 20%..80% 之间，不贴两头
SPOT_TO = 0.8
SPOT_JITTER = 0.2        # 刀口偏离匀称位置的幅度（占相邻刀口间距的比例）
MOST_LEAN = math.radians(35.0)   # 斜切刀口最大偏离"垂直切"的角度
MAX_REROLL = 30          # 斜切的刀口相交时，最多重掷几次角度

STYLE_ACROSS = "across"      # 沿长度横切、每刀略斜：肉、鱼、卷心菜
STYLE_STRAIGHT = "straight"  # 垂直切成等宽片：卷
STYLE_WEDGES = "wedges"      # 过圆心、彼此相交：派、蛋糕
STYLE_STRIPS = "strips"      # 垂直切、紧挨：面团切面条

TOOL_CUT = "cut"             # 刀：由刀口动画自己处理
TOOL_CHOP = "chop"           # 斧：劈木头以外的木制品
TOOL_STRIP = "strip"         # 斧：削去树皮（产物里有 stripped_ 开头的）
TOOL_SMASH = "smash"         # 镐
TOOL_DIG = "dig"             # 锹
TOOL_PRY = "pry"             # 锄
TOOL_SNIP = "snip"           # 剪刀

# 各工具一次动作的 (落点时刻, 总时长)，秒：落点就是发出这一刀的时刻（ToolStroke 枚举里本来就以秒计）
STROKES = {
    TOOL_CUT: (0.0, 0.0),
    TOOL_CHOP: (0.19, 0.42),
    TOOL_STRIP: (0.27, 0.42),
    TOOL_SMASH: (0.19, 0.40),
    TOOL_DIG: (0.17, 0.38),
    TOOL_PRY: (0.20, 0.40),
    TOOL_SNIP: (0.36, 0.46),
}
SNIPS = 3                # 剪刀沿刀口剪几下
SNIP_START = 0.06        # 剪刀先用这么久移到刀口起点，然后才开始剪
SNIP_TIME = 0.1          # 每一下多长；0.06 + 3 * 0.1 = 0.36 正好是剪刀的落点时刻

_KIND_BY_LAST_WORD = {"axe": "axe", "pickaxe": "pickaxe", "shovel": "shovel", "hoe": "hoe",
                      "shears": "shears", "knife": "knife"}


class CutPlan(object):
    """一件食材怎么切：几个刀口、什么布局。"""

    def __init__(self, marks, style):
        self.marks = marks
        self.style = style

    def __repr__(self):
        return "CutPlan(marks=%d, style=%s)" % (self.marks, self.style)


def pieces(counts):
    """切成几件：主产物的数量，加上其余每种产物各算一件（火腿的骨头）；没有产物算 2。"""
    if not counts:
        return 2
    return counts[0] + len(counts) - 1


def chooseStyle(wedges=False, strips=False, straight=False):
    """布局：派/蛋糕等圆形（调用方判断）或带楔形标记 > 面团条 > 卷 > 默认横切。"""
    if wedges:
        return STYLE_WEDGES
    if strips:
        return STYLE_STRIPS
    return STYLE_STRAIGHT if straight else STYLE_ACROSS


def planCut(counts, style):
    """按产物件数 counts（配方里每种产物的数量，主产物在前）定刀口数。

    横切 n 刀切成 n+1 件；过圆心 n 刀切成 2n 个楔形；面条固定 3 刀；都夹进 1..MOST_MARKS。
    """
    if style == STYLE_STRIPS:
        return CutPlan(STRIP_MARKS, style)
    total = pieces(counts)
    marks = (total + 1) // 2 if style == STYLE_WEDGES else total - 1
    return CutPlan(clamp(marks, 1, MOST_MARKS), style)


def countsOf(itemList):
    """从 [{"itemName":..,"count":..}] 这种产物表里取出各产物数量（缺省 1）。"""
    return [entry.get("count", 1) for entry in itemList]


def crossOnTheItem(spotA, angleA, spotB, angleB):
    """两刀会不会在食材上相交。食材当作一个正方形（长度 0..1 从远端到近端），每刀过宽度的中点，
    角度是偏离垂直切的弧度。"""
    ax, az = math.cos(angleA), math.sin(angleA)
    bx, bz = math.cos(angleB), math.sin(angleB)
    across = ax * bz - az * bx
    if abs(across) < 1.0e-4:
        return False
    t = (0.0 * bz - (spotB - spotA) * bx) / across
    x = 0.5 + t * ax
    z = spotA + t * az
    return 0.0 <= x <= 1.0 and 0.0 <= z <= 1.0


def _crosses(spots, angles):
    for a in range(len(spots)):
        for b in range(a + 1, len(spots)):
            if crossOnTheItem(spots[a], angles[a] * MOST_LEAN, spots[b], angles[b] * MOST_LEAN):
                return True
    return False


def _uniform(rng, low, high):
    return low if low >= high else rng.random() * (high - low) + low


def layoutMarks(plan, rng=random):
    """给一件新食材布刀口，返回 (spots, angles)。spot 是离远端的比例；angle 的含义随布局：
    横切是 -1..1（占最大斜度的比例），楔形是绕圆心的转角（弧度），垂直切是 0。"""
    count = plan.marks
    room = (SPOT_TO - SPOT_FROM) / count
    turn = rng.random() * math.pi
    spots = [0.0] * count
    angles = [0.0] * count
    for mark in range(count):
        if plan.style == STYLE_WEDGES:
            spots[mark] = 0.5
            angles[mark] = turn + mark * math.pi / count
        elif plan.style in (STYLE_STRAIGHT, STYLE_STRIPS):
            span = 0.5 if plan.style == STYLE_STRIPS else 1.0
            spots[mark] = 0.5 + ((mark + 1.0) / (count + 1.0) - 0.5) * span
        else:
            even = SPOT_FROM + (mark + 0.5) * room
            stray = 0.15 if count == 1 else room * SPOT_JITTER
            spots[mark] = even + _uniform(rng, -stray, stray)
            angles[mark] = _uniform(rng, -1.0, 1.0)
    if plan.style == STYLE_ACROSS:
        _untangle(spots, angles, rng)
    return spots, angles


def _untangle(spots, angles, rng):
    """横切的刀口不按固定顺序落：重掷角度直到互不相交，实在不行就全平行；最后洗牌，落刀顺序就随机了。"""
    for _ in range(MAX_REROLL):
        if not _crosses(spots, angles):
            break
        for mark in range(len(angles)):
            angles[mark] = _uniform(rng, -1.0, 1.0)
    if _crosses(spots, angles):
        for mark in range(len(angles)):
            angles[mark] = angles[0]
    for mark in range(len(spots) - 1, 0, -1):
        other = rng.randint(0, mark)
        spots[mark], spots[other] = spots[other], spots[mark]
        angles[mark], angles[other] = angles[other], angles[mark]


class BoardCut(object):
    """一块菜板上当前这件食材的刀口进度。服务端权威，客户端只读。"""

    def __init__(self):
        self.marks = 0                       # 已经落下的刀口数（按顺序）
        self.plan = CutPlan(1, STYLE_ACROSS)
        self.spots = []
        self.angles = []
        self.lastChop = -CHOP_GAP

    def restart(self, plan, rng=random):
        """新的一件食材（或最后一个人离开板子）：刀口清零、重新布局。"""
        self.marks = 0
        self.plan = plan
        self.spots, self.angles = layoutMarks(plan, rng)

    def accept(self, now, mark, hasItem=True):
        """校验一次落刀：板上有食材、刀口序号正好是下一个、离上一刀够久。通过则记下时刻并返回 True。

        随后调用方再检查工具；工具不对时刀口不落（Java 里这时间隔已经记了，所以这里也先记）。
        """
        if not hasItem or mark != self.marks or now - self.lastChop < CHOP_GAP - EPS:
            return False
        self.lastChop = now
        return True

    def strike(self):
        """这一刀落实：刀口数加一。返回 True 表示这是最后一刀，该整批切开了。"""
        self.marks += 1
        return self.marks >= self.plan.marks


def batchSize(stackCount, toolLeft=None):
    """最后一刀一次切开几件：整叠最多 BATCH 件，每件磨损工具 1 点，所以不超过工具剩余耐久（None = 不磨损）。"""
    done = min(BATCH, stackCount)
    return done if toolLeft is None else max(0, min(done, toolLeft))


def toolKindOf(name):
    """物品名或类别名 -> axe / pickaxe / shovel / hoe / shears / knife；认不出是 None。
    只看名字最后一个下划线词，"iron_pickaxe" 不会被当成斧。"""
    return _KIND_BY_LAST_WORD.get(name.split(":")[-1].split("_")[-1])


def strokeKind(toolNames, resultNames=()):
    """一个配方该用哪种动作（ToolStroke.of）：没写工具或刀在内 -> 刀；斧 -> 削皮(产物是 stripped_*)或劈；
    镐/锹/锄/剪刀各一种；认不出按刀。按配方列出的工具顺序，第一个认得的说了算。"""
    kinds = [toolKindOf(name) for name in toolNames]
    if not kinds or "knife" in kinds:
        return TOOL_CUT
    for kind in kinds:
        if kind == "axe":
            stripped = any(name.split(":")[-1].startswith("stripped_") for name in resultNames)
            return TOOL_STRIP if stripped else TOOL_CHOP
        if kind in _SIMPLE_TOOLS:
            return _SIMPLE_TOOLS[kind]
    return TOOL_CUT


_SIMPLE_TOOLS = {"pickaxe": TOOL_SMASH, "shovel": TOOL_DIG, "hoe": TOOL_PRY, "shears": TOOL_SNIP}


def snipTimes():
    """剪刀每一下开始的时刻（秒，从动作起点算）。"""
    return [SNIP_START + SNIP_TIME * index for index in range(SNIPS)]
