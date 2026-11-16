# -*- coding: utf-8 -*-
"""PotBadgeGlyphs - 厨锅徽章上画的东西：底板、星、进度条、火苗、"+N" 数字，各是哪张图、摆在哪（双端）

移植自 Hands-On Delight 的 client/PotBehavior.java：徽章常量（86-113 行）、onSceneReady 里的底板（403-410 行）、
starLeft / starTop（917-924 行）、drawDial / flame / glyph / count / dial / pixels（1579-1672 行）。场景里 badge / dial_track / dial / preview 四个节点
（HODRES/assets/handson_delight/diegesis/scenes/cooking_pot.json）叠在同一个位置。

JE 是把每个像素画成一个小方块；基岩版的界面有现成的图片裁切，所以这里每样东西是一张小贴图（PATTERNS 里的字符画，
tools/gen_pot_badge.py 照它生成 rp/textures/ui/pot_badge/*.png，白色，颜色由牌的 color 染）：没亮满的星 = 星的贴图只露出下面几行，
没走完的进度条 = 条的贴图只露出左边几格（内核的牌，diegesisBp 的 Shared/PlateLayout.py）。

坐标是"图标像素"（icon px）：原点是菜的图标的中心，+x 向右，+y 向下；图标 16 x 16（[-8, 8) 两个方向）。
一个图标像素 = PIXEL 个场景像素。星的左边是 x.5（"五像素宽的星坐在图标的像素之间"）。
每样东西在牌里占固定的一格（SLOT_*）：暂时不画的那格是 None，界面上的图片控件不会串。
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
# 底板：20 x 28 的矩形加上下各一条 18 x 1 的边，四个角是切掉的（PB 406-408）：合起来是 (-10, -17) 起的 20 x 30
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


TEXTURES = "textures/ui/pot_badge/"     # 本包资源包里的贴图目录
BAR = ("#" * BAR_LENGTH,)                # 进度条：14 x 1
PLATE_ROWS = ((".##################.",) + ("####################",) * 28 + (".##################.",))      # 底板 20 x 30，四个角切掉
PATTERNS = {"plate": PLATE_ROWS, "star": STAR, "flame": FLAME, "bar": BAR, "plus": PLUS}
PATTERNS.update(("digit_%d" % digit, rows) for digit, rows in enumerate(DIGITS))
# 牌里的格子：底板、三颗星各两张（没亮的、亮的）、进度条的轨（没火时是火苗）、进度、"+N" 至多三个字（这三格画在图标上面）
SLOT_PLATE, SLOT_STARS, SLOT_TRACK, SLOT_BAR, SLOT_COUNT, SLOTS = 0, 1, 7, 8, 9, 12


def sprite(name, x, y, color, clip=None, pop=0):
    """一张图：PATTERNS 里叫 name 的那张摆在 (x, y)，染 color；clip = [留哪一边, 露出多少]；pop 变大一次界面上弹一下。"""
    rows = PATTERNS[name]
    made = {"texture": TEXTURES + name, "rect": [x, y, len(rows[0]), len(rows)], "color": color}
    if clip is not None:
        made["clip"] = list(clip)
    if pop:
        made["pop"] = pop
    return made


def cellsOf(made):
    """这张图实际画出来的格子 {(x, y)}：字符画里的 #，再按 clip 裁（测试和文档用，和界面上看到的是同一回事）。"""
    if made is None:
        return set()
    rows = PATTERNS[made["texture"][len(TEXTURES):]]
    x, y = made["rect"][0], made["rect"][1]
    side, shown = (made.get("clip") or [None, 1.0])[:2]
    keepRows = int(round(len(rows) * shown)) if side in ("top", "bottom") else len(rows)
    keepColumns = int(round(len(rows[0]) * shown)) if side in ("left", "right") else len(rows[0])
    cells = set()
    for row, line in enumerate(rows):
        if (side == "bottom" and row < len(rows) - keepRows) or (side == "top" and row >= keepRows):
            continue
        for column, char in enumerate(line):
            if (side == "left" and column >= keepColumns) or (side == "right" and column < len(line) - keepColumns):
                continue
            if char == "#":
                cells.add((x + column, y + row))
    return cells


def starRows(open_, rows, star):
    """点亮 rows 行（从第一颗星最底下一行算起，满一颗再到下一颗）时第 star 颗亮几行（dial() 里的星，PB 1649-1657）。"""
    return max(0, min(STAR_SIZE, rows - star * len(STAR))) if star < open_ else 0


def countChars(added):
    """"+N" 的每个字：[(贴图名, 左边)]，右对齐到 COUNT_RIGHT，每个字 3 宽、间隔 1（PB 1624-1638）。"""
    text = "+" + str(added)
    left = COUNT_RIGHT - len(text) * 4 + 1
    return [("plus" if char == "+" else "digit_" + char, left + index * 4) for index, char in enumerate(text)]


def sprites(open_, cold, bar, rows, added, running=True, pops=(0, 0, 0), countPop=0):
    """徽章此刻的全部图，一格一样（SLOTS 格，不画的是 None）。

    底板总在；running 为假（锅里只剩成品、或在等卷轴）时只有底板。没点亮的一层（JE 的 dial_track，TRACK_COLOR）：开着的星、
    热着是整条进度条的轨、没火是一朵空火苗（PB 1592-1596、1604-1611）。点亮的一层（dial，DIAL_COLOR）：亮了几行的星、
    bar 像素的进度、added > 0 时的 "+N"（PB 1641-1659）。pops 是每颗星亮起过几回，countPop 是 "+N" 出现过几回。"""
    made = [None] * SLOTS
    made[SLOT_PLATE] = sprite("plate", -10, -17, PLATE_COLOR)
    if not running:
        return made
    for star in range(open_):
        left, top = starLeft(open_, star), starTop(open_, star)
        made[SLOT_STARS + star * 2] = sprite("star", left, top, TRACK_COLOR)
        lit = starRows(open_, rows, star)
        if lit > 0:
            made[SLOT_STARS + star * 2 + 1] = sprite("star", left, top, DIAL_COLOR, ["bottom", lit / float(STAR_SIZE)], pops[star])
    made[SLOT_TRACK] = sprite("flame", FLAME_LEFT, FLAME_TOP, TRACK_COLOR) if cold else sprite("bar", BAR_LEFT, BAR_TOP, TRACK_COLOR)
    lit = max(0, min(BAR_LENGTH, bar))
    if lit > 0:
        made[SLOT_BAR] = sprite("bar", BAR_LEFT, BAR_TOP, DIAL_COLOR, ["left", lit / float(BAR_LENGTH)])
    if added > 0:
        for index, (name, left) in enumerate(countChars(added)):
            made[SLOT_COUNT + index] = sprite(name, left, COUNT_TOP, DIAL_COLOR, None, countPop)
    return made
