# -*- coding: utf-8 -*-
"""PotBadgeGlyphs - 厨锅徽章的像素：底板、星、进度条、火苗、"+N" 数字，合并成少量矩形（双端）

移植自 Hands-On Delight 的 client/PotBehavior.java：徽章常量（86-113 行）、onSceneReady 里的底板（403-410 行）、
starLeft / starTop（917-924 行）、drawDial / flame / glyph / count / dial / pixels（1579-1672 行）。场景里 badge / dial_track / dial / preview 四个节点
（HODRES/assets/handson_delight/diegesis/scenes/cooking_pot.json）叠在同一个位置，这里把它们画的东西都落成矩形。

坐标是"图标像素"（icon px）：原点是菜的图标的中心（四个节点的原点），+x 向右，+y 向下；图标 16 x 16（[-8, 8) 两个方向）。
一个图标像素 = PIXEL 个场景像素。矩形 [x, y, w, h]，颜色 ARGB；星的左边是 x.5（"五像素宽的星坐在图标的像素之间"，所以有半像素）。
合并：一行里连着的像素合成一条横杠，上下几行横杠一样的再合成一个高矩形，这样一整套徽章只有几十个矩形。
"""
PIXEL = 0.125                  # 一个图标像素 = 0.125 个场景像素（PB 86）
STAR = ("..#..", ".###.", "#####", ".###.", ".#.#.")     # 5 x 5 的星（PB 87）
STAR_SIZE = 5
STARS = 3                      # 最多三颗星
STAR_GAP = 1                   # 两颗星之间隔一像素
STAR_TOP = -14                 # 星顶的行；三颗时中间那颗高一像素
BAR_LEFT = -7
BAR_TOP = 10
BAR_LENGTH = 14                # 进度条满了是 14 像素长、1 像素高
PLUS = ("...", ".#.", "###", ".#.", "...")                # "+N" 的 + 号，3 x 5（PB 102）
DIGITS = (("###", "#.#", "#.#", "#.#", "###"), (".#.", "##.", ".#.", ".#.", "###"), ("###", "..#", "###", "#..", "###"),
          ("###", "..#", ".##", "..#", "###"), ("#.#", "#.#", "###", "..#", "..#"), ("###", "#..", "###", "..#", "###"),
          ("###", "#..", "###", "#.#", "###"), ("###", "..#", ".#.", ".#.", ".#."), ("###", "#.#", "###", "#.#", "###"),
          ("###", "#.#", "###", "..#", "###"))
COUNT_RIGHT = 9                # "+N" 右对齐到 x = 9（图标右下角，叠在数量该在的地方）
COUNT_TOP = 4
MOST_ADDED = 99                # "+N" 最多显示到 99
FLAME = ("..#..", ".##.#", "#####", "#####", ".###.")    # 没火时代替进度条的火苗（PB 110）
FLAME_LEFT = -2
FLAME_TOP = 8
PLATE_COLOR = 0x8C1E140C       # 底板：深色半透明
TRACK_COLOR = 0x50FFF2DC       # 没点亮的星、进度条的轨、火苗
DIAL_COLOR = 0xFFFFCB6B        # 点亮的星、进度、"+N"
# 底板：20 x 28 的矩形加上下各一条 18 x 1 的边，四个角是切掉的（PB 406-408）
PLATE = ((-10, -16, 20, 28), (-9, -17, 18, 1), (-9, 12, 18, 1))
ITEM_RECT = (-8, -8, 16, 16)           # 菜的图标：16 x 16，中心在原点
HOVER_RECT = (-12, -12, 24, 24)        # 鼠标放上去显示提示的范围：scene 里 preview 节点的碰撞盒 ±12（PB 之外，cooking_pot.json）


def starLeft(open_, star):
    """第 star 颗星的左边（图标像素）：开着的星居中排在图标上方，五像素宽，之间隔一像素（PB 918-920）。"""
    return -(open_ * (STAR_SIZE + STAR_GAP) - STAR_GAP) / 2.0 + star * (STAR_SIZE + STAR_GAP)


def starTop(open_, star):
    """第 star 颗星的顶（图标像素）：三颗全开时中间一颗高一像素（PB 922-924）。"""
    return STAR_TOP - 1 if open_ == STARS and star == 1 else STAR_TOP


def glyphCells(rows, left, top):
    """字符画里 # 的格子 -> {(x, y)}，左上角在 (left, top)。"""
    return set((left + column, top + row) for row, line in enumerate(rows) for column, char in enumerate(line) if char == "#")


def merge(cells, color):
    """一堆 1 x 1 的格子 -> 矩形 [x, y, w, h, color]：先把一行里连着的并成横杠，再把上下相邻、横杠一样的并成高矩形；按 (y, x) 排好。"""
    runs = {}                                  # (x, w) -> [y, ...]
    byRow = {}
    for x, y in cells:
        byRow.setdefault(y, []).append(x)
    for y, xs in byRow.items():
        xs.sort()
        start = previous = xs[0]
        for x in xs[1:] + [None]:
            if x is not None and x == previous + 1:
                previous = x
                continue
            runs.setdefault((start, int(previous - start) + 1), []).append(y)
            if x is not None:
                start = previous = x
    rects = []
    for (x, width), ys in runs.items():
        ys.sort()
        top = last = ys[0]
        for y in ys[1:] + [None]:
            if y is not None and y == last + 1:
                last = y
                continue
            rects.append([x, top, width, int(last - top) + 1, color])
            if y is not None:
                top = last = y
    rects.sort(key=lambda rect: (rect[1], rect[0]))
    return rects


def plateRects():
    """底板的矩形（PLATE_COLOR）。"""
    return [list(part) + [PLATE_COLOR] for part in PLATE]


def starCells(open_, rows):
    """开着 open_ 颗星、点亮 rows 行（从第一颗星的最底下一行开始算，满一颗再往下一颗）的格子（dial() 里的星，PB 1649-1657）。"""
    cells = set()
    for star in range(open_):
        lit = max(0, min(STAR_SIZE, rows - star * len(STAR)))
        for row in range(len(STAR) - lit, len(STAR)):
            cells |= glyphCells((STAR[row],), starLeft(open_, star), starTop(open_, star) + row)
    return cells


def countCells(added):
    """"+N" 的格子：右对齐到 COUNT_RIGHT，每个字符 3 宽、间隔 1（PB 1624-1638）。"""
    digits = "+" + str(added)
    left = COUNT_RIGHT - len(digits) * 4 + 1
    cells = set()
    for char in digits:
        cells |= glyphCells(PLUS if char == "+" else DIGITS[int(char)], left, COUNT_TOP)
        left += 4
    return cells


def trackRects(open_, cold):
    """没点亮的那一层（dial_track 节点，TRACK_COLOR）：开着的星全是空星；热着是一整条进度条的轨，没火是一朵空火苗（PB 1592-1596，1604-1611）。"""
    cells = starCells(open_, open_ * len(STAR))
    if cold:
        cells |= glyphCells(FLAME, FLAME_LEFT, FLAME_TOP)
    else:
        cells |= set((BAR_LEFT + index, BAR_TOP) for index in range(BAR_LENGTH))
    return merge(cells, TRACK_COLOR)


def dialRects(open_, bar, rows, added):
    """点亮的那一层（dial 节点，DIAL_COLOR）：bar 像素的进度条、点亮 rows 行的星、added > 0 时的 "+N"（PB 1641-1659）。"""
    cells = starCells(open_, rows)
    if added > 0:
        cells |= countCells(added)
    cells |= set((BAR_LEFT + index, BAR_TOP) for index in range(max(0, min(BAR_LENGTH, bar))))
    return merge(cells, DIAL_COLOR)
