# -*- coding: utf-8 -*-
# runner: both
"""厨锅徽章牌（Shared/Rules/HandsOn/PotBadge.py + PotBadgeGlyphs.py）：数值照 Hands-On Delight 的 PotBehavior（徽章常量 86-113、drawDial 1579-1660、
showGrade 926-950、tooltip 1113-1128）和 cooking_pot.json 的 badge / dial_track / dial / preview 节点。
JE 把每个像素画成小方块；这里每样东西是一张贴图、没亮满的靠裁切（见 PotBadgeGlyphs），下面按"实际画出来的格子"对照 Java 的像素。

Java：底板 20 x 28 图标像素 + 上下各一条 18 x 1，颜色 0x8C1E140C；5 x 5 的星，间隔 1，顶在 -14（三颗全开时中间高一像素），没亮 0x50FFF2DC、亮 0xFFFFCB6B 从最底下一行往上亮，
rows = min(open * 5, round(shownStars * 5))；条左 -7、顶 10、14 x 1，长 round(shownProgress * 14)；没火：没有条，一朵 5 x 5 的空火苗在 (-2, 8)；
出锅后星按 0.3 秒 + 0.18 秒 * 序号亮起（闪光 x3，有多送的份数才叮：1.0 / 1.26 / 1.5），整个 2.8 秒；"+N" 3 x 5 的数字右对齐到 x = 9、顶 4。
"""
from __future__ import print_function

import fdtest

Badge = fdtest.load("Shared.Rules.HandsOn.PotBadge")
Glyphs = fdtest.load("Shared.Rules.HandsOn.PotBadgeGlyphs")
PLATE, TRACK, DIAL = 0x8C1E140C, 0x50FFF2DC, 0xFFFFCB6B
HOT = {"here": True, "dish": True, "heated": True, "progress": 0.0, "stars": 0.0, "openStars": 3, "ingredients": True}
STAR_CELLS = 14       # 星 5 行：1 + 3 + 5 + 3 + 2
FLAME_CELLS = 17      # 火苗 5 行：1 + 3 + 5 + 5 + 3
TICK = 0.05


def settle(badge, state, seconds=3.0, dt=TICK):
    """推进到平滑的进度 / 星到位，返回最后一次的 (model, events)。"""
    last = None
    for _ in range(int(round(seconds / dt))):
        last = badge.step(dt, state)
    return last


def colored(model, argb):
    """model 里染成 argb 的那几张图。"""
    return [sprite for sprite in model["sprites"] if sprite is not None and sprite["color"] == argb]


def cellsOf(sprites):
    """几张图实际画出来的格子 {(x, y)}（x 可以是 .5）：贴图的字符画按各自的裁切。"""
    cells = set()
    for sprite in sprites:
        cells |= Glyphs.cellsOf(sprite)
    return cells


def starCells(open_, rows):
    """Java 的 dial() 画的星：开着 open_ 颗、点亮 rows 行（从第一颗最底下一行算起）的像素。"""
    cells = set()
    for star in range(open_):
        lit = max(0, min(5, rows - star * 5))
        for row in range(5 - lit, 5):
            cells |= Glyphs.glyphCells((Glyphs.STAR[row],), Glyphs.starLeft(open_, star), Glyphs.starTop(open_, star) + row)
    return cells


def countCells(added):
    """Java 的 count() 画的 "+N" 的像素。"""
    text = "+" + str(added)
    left = Glyphs.COUNT_RIGHT - len(text) * 4 + 1
    cells = set()
    for char in text:
        cells |= Glyphs.glyphCells(Glyphs.PLUS if char == "+" else Glyphs.DIGITS[int(char)], left, Glyphs.COUNT_TOP)
        left += 4
    return cells


def barCells(length):
    return set((Glyphs.BAR_LEFT + index, Glyphs.BAR_TOP) for index in range(length))


def exactly(progress=None, stars=None, **state):
    """平滑量正好是给定值的徽章（直接设 shown*，dt = 0 不再滑）和它此刻的 model。"""
    badge = Badge.PotBadge()
    badge.shownProgress = progress or 0.0
    badge.shownStars = stars or 0.0
    return badge.step(0.0, dict(HOT, **state))[0]


def testTheConstantsAreJavas():
    assert Glyphs.PIXEL == 0.125 and Glyphs.STAR_SIZE == 5 and Glyphs.STARS == 3 and Glyphs.STAR_GAP == 1 and Glyphs.STAR_TOP == -14
    assert (Glyphs.BAR_LEFT, Glyphs.BAR_TOP, Glyphs.BAR_LENGTH) == (-7, 10, 14)
    assert (Glyphs.COUNT_RIGHT, Glyphs.COUNT_TOP, Glyphs.FLAME_LEFT, Glyphs.FLAME_TOP) == (9, 4, -2, 8)
    assert (Glyphs.PLATE_COLOR, Glyphs.TRACK_COLOR, Glyphs.DIAL_COLOR) == (0x8C1E140C, 0x50FFF2DC, 0xFFFFCB6B)
    assert Glyphs.STAR == ("..#..", ".###.", "#####", ".###.", ".#.#.")
    assert Glyphs.FLAME == ("..#..", ".##.#", "#####", "#####", ".###.") and Glyphs.PLUS == ("...", ".#.", "###", ".#.", "...")
    assert Glyphs.DIGITS[0] == ("###", "#.#", "#.#", "#.#", "###") and Glyphs.DIGITS[7] == ("###", "..#", ".#.", ".#.", ".#.") and len(Glyphs.DIGITS) == 10
    assert (Badge.GRADE_WAIT, Badge.GRADE_STAGGER, Badge.GRADE_SHOWN) == (0.3, 0.18, 2.8) and tuple(Badge.GRADE_PITCH) == (1.0, 1.26, 1.5)
    assert len(Glyphs.glyphCells(Glyphs.STAR, 0, 0)) == STAR_CELLS and len(Glyphs.glyphCells(Glyphs.FLAME, 0, 0)) == FLAME_CELLS


def testThePlateIsTwentyByTwentyEightWithCutCorners():
    plate = Glyphs.sprites(1, False, 0, 0, 0, running=False)
    assert plate[0]["rect"] == [-10, -17, 20, 30] and plate[0]["color"] == PLATE and plate[1:] == [None] * (Glyphs.SLOTS - 1)
    javas = set()
    for x, y, w, h in ((-10, -16, 20, 28), (-9, -17, 18, 1), (-9, 12, 18, 1)):
        javas |= set((x + i, y + j) for i in range(w) for j in range(h))
    assert Glyphs.cellsOf(plate[0]) == javas, "一张 20 x 30 的图，四个角是空的：就是 Java 的三块"
    model, _events = Badge.PotBadge().step(0.05, {"here": True, "dish": True, "meal": 2})
    assert model["sprites"] == plate, "出锅后锅里只剩成品、料格空了：只有底板和图标"
    assert model["itemRect"] == [-8, -8, 16, 16] and model["unit"] == 0.125
    assert model["hoverRect"] == [-12, -12, 24, 24], "preview 节点的碰撞盒 ±12"


def testStarsAreCentredOverTheIconAndTheMiddleOneStandsHigher():
    assert [Glyphs.starLeft(1, 0)] == [-2.5]
    assert [Glyphs.starLeft(2, star) for star in range(2)] == [-5.5, 0.5]
    assert [Glyphs.starLeft(3, star) for star in range(3)] == [-8.5, -2.5, 3.5]
    assert [Glyphs.starTop(3, star) for star in range(3)] == [-14, -15, -14], "三颗时中间那颗高一像素"
    assert [Glyphs.starTop(2, star) for star in range(2)] == [-14, -14] and Glyphs.starTop(1, 0) == -14


def testEveryThingKeepsItsOwnSlotAndPartFilledOnesAreClipped():
    """一样东西一张图、一直占同一格（不画的是 None）；没亮满的星只露出下面几行，没走完的条只露出左边几格。"""
    made = Glyphs.sprites(3, False, 7, 7, 12, pops=(1, 0, 0), countPop=2)
    assert len(made) == Glyphs.SLOTS == 12
    assert made[Glyphs.SLOT_PLATE]["texture"] == "textures/ui/pot_badge/plate"
    stars = made[Glyphs.SLOT_STARS:Glyphs.SLOT_STARS + 6]
    assert [star and star["color"] for star in stars] == [TRACK, DIAL, TRACK, DIAL, TRACK, None], "每颗星：没亮的一张、亮的一张；第三颗还没亮"
    assert stars[1]["clip"] == ["bottom", 1.0] and stars[1]["pop"] == 1 and stars[1]["rect"] == [-8.5, -14, 5, 5]
    assert stars[3]["clip"] == ["bottom", 0.4] and "pop" not in stars[3], "第二颗亮了最底下两行"
    assert made[Glyphs.SLOT_TRACK]["texture"].endswith("bar") and "clip" not in made[Glyphs.SLOT_TRACK]
    assert made[Glyphs.SLOT_BAR]["clip"] == ["left", 0.5] and made[Glyphs.SLOT_BAR]["rect"] == [-7, 10, 14, 1]
    count = made[Glyphs.SLOT_COUNT:]
    assert [part["texture"].rsplit("/", 1)[1] for part in count] == ["plus", "digit_1", "digit_2"]
    assert [part["rect"][0] for part in count] == [-2, 2, 6] and all(part["pop"] == 2 and part["rect"][1:] == [4, 3, 5] for part in count)
    assert Glyphs.SLOT_COUNT >= 9, "数字那几格在内核里画在物品图标上面（PlateLayout.OVER_ITEM）"
    cold = Glyphs.sprites(1, True, 9, 0, 0)
    assert cold[Glyphs.SLOT_TRACK]["texture"].endswith("flame") and cold[Glyphs.SLOT_BAR]["clip"] == ["left", 9 / 14.0]
    assert sorted(Glyphs.PATTERNS) == sorted(["plate", "star", "flame", "bar", "plus"] + ["digit_%d" % digit for digit in range(10)])


def testClippingShowsExactlyJavasPixels():
    for rows in range(0, 16):
        made = Glyphs.sprites(3, False, 0, rows, 0)
        lit = [sprite for sprite in made if sprite is not None and sprite["color"] == DIAL]
        assert cellsOf(lit) == starCells(3, rows), rows
    for bar in range(0, 15):
        made = Glyphs.sprites(1, False, bar, 0, 0)
        assert cellsOf([made[Glyphs.SLOT_BAR]]) == barCells(bar), bar
    assert Glyphs.cellsOf(None) == set()


def testAColdPotShowsUnlitStarsAndAnEmptyFlameInsteadOfTheBar():
    model = exactly(heated=False, openStars=2, progress=1.0, stars=2.0)
    track = colored(model, TRACK)
    flame = Glyphs.glyphCells(Glyphs.FLAME, -2, 8)
    assert flame <= cellsOf(track) and len(cellsOf(track)) == FLAME_CELLS + 2 * STAR_CELLS, "空火苗 + 两颗空星，没有条的轨"
    assert model["sprites"][Glyphs.SLOT_TRACK]["rect"] == [-2, 8, 5, 5], "火苗在条该在的那一格"
    assert model["sprites"][Glyphs.SLOT_BAR] is None, "冷锅的条是 0：进度再满也不画（星照控制量画）"


def testAColdPotLightsNoBarEvenWithProgress():
    model = exactly(heated=False, progress=1.0, stars=0.0)
    assert colored(model, DIAL) == [], "冷锅条是 0，星没有，什么都不亮"


def testAHotPotShowsTheBarTrackAndTheProgressAsFarAsTheBatchIs():
    model = exactly(progress=0.5)
    assert barCells(14) <= cellsOf(colored(model, TRACK)), "整条轨 14 像素"
    assert cellsOf(colored(model, DIAL)) == barCells(7), "进度 0.5 -> round(7) = 7 像素"
    assert cellsOf(colored(exactly(progress=0.25), DIAL)) == barCells(4), "3.5 进位成 4（Java 的 Math.round 是 floor(x + 0.5)）"
    assert cellsOf(colored(exactly(progress=0.24), DIAL)) == barCells(3)
    assert cellsOf(colored(exactly(progress=1.0), DIAL)) == barCells(14)
    assert colored(exactly(progress=0.0), DIAL) == [], "进度 0 又没有星：什么都不亮"


def testTheStarsFillFromTheBottomRow():
    one = exactly(stars=1.0)
    assert cellsOf(colored(one, DIAL)) == starCells(3, 5) and len(cellsOf(colored(one, DIAL))) == STAR_CELLS, "一颗星 = 5 行：第一颗全亮"
    part = exactly(stars=1.4)
    assert cellsOf(colored(part, DIAL)) == starCells(3, 7), "1.4 颗星 round(7) 行：第一颗全亮，第二颗从下往上两行（.###. 和 .#.#.）"
    second = [cell for cell in cellsOf(colored(part, DIAL)) if cell[0] > -3]
    assert sorted(set(y for _x, y in second)) == [-12, -11], "第二颗的顶是 -15，最底下两行是 -12 和 -11"
    assert len(cellsOf(colored(exactly(stars=3.0), DIAL))) == 3 * STAR_CELLS
    assert len(cellsOf(colored(exactly(stars=3.0, openStars=1), DIAL))) == STAR_CELLS, "只开了一颗星：最多点亮 open * 5 行"


def testHalfAStarLightsItsBottomThreeRows():
    rows = sorted(set(y for _x, y in cellsOf(colored(exactly(stars=0.5, openStars=1), DIAL))))
    assert rows == [-12, -11, -10], "0.5 颗 = round(2.5) = 3 行：最底下三行"


def testOnlyTheOpenStarsAreDrawn():
    for opened in (1, 2, 3):
        model = exactly(openStars=opened, stars=3.0)
        assert len(cellsOf(colored(model, TRACK))) == opened * STAR_CELLS + Glyphs.BAR_LENGTH, opened
    assert exactly(openStars=9, stars=3.0) == exactly(openStars=3, stars=3.0), "夹进 1..3"
    assert exactly(openStars=0, stars=3.0) == exactly(openStars=1, stars=3.0)


def testProgressAndStarsGlideWithTheSmoothingOfSixPerSecond():
    badge = Badge.PotBadge()
    badge.step(0.05, dict(HOT, progress=1.0, stars=3.0))
    assert abs(badge.shownProgress - 0.3) < 1e-12 and abs(badge.shownStars - 0.9) < 1e-12, "lerp(min(1, 6 * dt)) = 0.3"
    badge.step(1.0, dict(HOT, progress=1.0, stars=3.0))
    assert badge.shownProgress == 1.0 and badge.shownStars == 3.0, "dt 够长就一步到位"


def testTheBadgeShowsOnlyForTheCookAtADish():
    badge = Badge.PotBadge()
    assert badge.step(0.05, {"dish": True, "heated": True})[0] is None
    assert badge.step(0.05, {"here": True, "heated": True})[0] is None
    assert badge.step(0.05, dict(HOT))[0] is not None
    waiting = badge.step(0.05, dict(HOT, waiting=True))[0]
    assert colored(waiting, TRACK) == [] and colored(waiting, DIAL) == [] and len(colored(waiting, PLATE)) == 1, "等卷轴的菜不煮：没有条和星"
    assert colored(badge.step(0.05, dict(HOT, waiting=True, meal=1))[0], TRACK), "已经有成品了就不再等（waiting 只在没成品时算）"


def testAFinishedPotWithIngredientsStillShowsTheBar():
    assert colored(Badge.PotBadge().step(0.05, dict(HOT, meal=2, ingredients=True))[0], TRACK)
    assert Badge.PotBadge().step(0.05, dict(HOT, meal=2, ingredients=False))[0]["sprites"] == Glyphs.sprites(1, False, 0, 0, 0, running=False)


def testTheSpriteListIsTheSameObjectUntilSomethingChanges():
    badge = Badge.PotBadge()
    badge.shownProgress = 0.5
    first = badge.step(0.0, dict(HOT))[0]["sprites"]
    assert badge.step(0.0, dict(HOT))[0]["sprites"] is first
    badge.shownProgress = 0.75
    changed = badge.step(0.0, dict(HOT))[0]["sprites"]
    assert changed is not first and changed[Glyphs.SLOT_BAR]["clip"] == ["left", 11 / 14.0], "0.75 * 14 = 10.5 -> 11"


def flashRun(state, steps=70, dt=TICK):
    badge = Badge.PotBadge()
    badge.flash()
    out = []
    for index in range(steps):
        model, events = badge.step(dt, state)
        out.append((round((index + 1) * dt, 6), model, events))
    return badge, out


def testGradingFlashesTheStarsOneAfterTheOtherAndSaysThePlusWhenTheLastIsLit():
    state = dict(HOT, grade=2, bonus=3, openStars=3)
    badge, sequence = flashRun(state)
    glints = [(at, e) for at, _m, events in sequence for e in events if e["type"] == "glint"]
    assert len(glints) == 2
    assert 0.3 < glints[0][0] <= 0.3 + TICK + 1e-9 and 0.48 < glints[1][0] <= 0.48 + TICK + 1e-9, "0.3 + 0.18 * 序号 之后的第一步"
    assert (glints[0][1]["x"], glints[0][1]["y"]) == (-8.5 + 2.5, -14 + 2.5), "第一颗星的中心"
    assert (glints[1][1]["x"], glints[1][1]["y"]) == (-2.5 + 2.5, -15 + 2.5), "中间那颗高一像素"
    assert glints[0][1]["count"] == 3 and glints[0][1]["color"] == 0xFFFFE9A0 and glints[0][1]["rise"] == (0.0, 4.0, 0.0)
    chimes = [e for _at, _m, events in sequence for e in events if e["type"] == "sound"]
    assert [e["pitch"] for e in chimes] == [1.0, 1.26] and all(e["name"] == "chime" and e["volume"] == 0.35 for e in chimes)
    byAt = dict((at, model) for at, model, _e in sequence)
    assert barCells(14) <= cellsOf(colored(byAt[0.1], DIAL)), "亮星期间条是满的"
    assert not countCells(3) & cellsOf(colored(byAt[0.5], DIAL)), "还没亮完不显示 +N"
    assert starCells(3, 5) <= cellsOf(colored(byAt[0.4], DIAL)), "0.4 秒第一颗全亮"
    assert not starCells(3, 10) <= cellsOf(colored(byAt[0.4], DIAL)), "第二颗还没亮"
    assert countCells(3) <= cellsOf(colored(byAt[1.0], DIAL)), "两颗都亮了又过了 0.3 + 2 * 0.18 = 0.66 秒：+3 出来"
    assert not badge.flashing and not countCells(3) & cellsOf(colored(sequence[-1][1], DIAL)), "2.8 秒后回到平常的样子"
    stars = Glyphs.SLOT_STARS
    assert byAt[0.4]["sprites"][stars + 1]["pop"] == 1 and byAt[0.4]["sprites"][stars + 3] is None, "亮起的那颗弹一下（pop 加一）"
    assert byAt[1.0]["sprites"][stars + 3]["pop"] == 1 and byAt[1.0]["sprites"][stars + 1]["pop"] == 1, "先亮的那颗不再弹"
    assert all(part["pop"] == 1 for part in byAt[1.0]["sprites"][Glyphs.SLOT_COUNT:Glyphs.SLOT_COUNT + 2]), "+3 出来时弹一下"
    badge.flash()
    again = [badge.step(TICK, state)[0] for _ in range(30)][-1]
    assert again["sprites"][stars + 1]["pop"] == 2 and again["sprites"][Glyphs.SLOT_COUNT]["pop"] == 2, "再出一锅再弹一回"


def testTheFlashLastsTwoPointEightSeconds():
    badge = Badge.PotBadge()
    badge.flash()
    seen = []
    for _ in range(60):
        badge.step(0.05, dict(HOT, grade=1, bonus=1))
        seen.append(badge.flashing)
    assert all(seen[:55]) and not any(seen[57:]), "56 步 = 2.8 秒（浮点累加差一步以内）：之前一直在亮，之后回到平常"


def testNoChimeWhenTheStarsPayNothing():
    badge = Badge.PotBadge()
    badge.flash()
    events = []
    for _ in range(40):
        events += badge.step(0.05, dict(HOT, grade=3, bonus=0))[1]
    assert len([e for e in events if e["type"] == "glint"]) == 3, "三颗星各闪一下"
    assert not [e for e in events if e["type"] == "sound"], "一颗星不奖励份数时不叮，先让第一批教会玩家星是干什么的"


def testTheFlashDoesNotPlayForSomeoneWhoIsNotAtThePot():
    badge = Badge.PotBadge()
    badge.flash(focused=False)
    assert not badge.flashing
    assert not badge.step(0.05, dict(HOT, grade=3, bonus=1))[1]


def testThePlusSignAndDigitsAreRightAlignedAtNine():
    for added in (5, 12, 99):
        cells = cellsOf(Glyphs.sprites(1, False, 0, 0, added)[Glyphs.SLOT_COUNT:])
        assert cells == countCells(added)
        assert max(x for x, _y in cells) == 8 and max(y for _x, y in cells) == 8 and min(y for _x, y in cells) == 4, added
    five = countCells(5)
    assert min(x for x, _y in five) == 2, "'+5'：右对齐 9 - 2 * 4 + 1 = 2，+ 号的横杠从 x = 2 起"
    assert min(x for x, _y in countCells(12)) == -2, "'+12'：9 - 3 * 4 + 1 = -2"
    assert Glyphs.countChars(12) == [("plus", -2), ("digit_1", 2), ("digit_2", 6)]
    assert (3, 5) in five and (2, 6) in five and (3, 6) in five and (4, 6) in five and (3, 7) in five, "+ 号"
    assert (6, 4) in five and (7, 4) in five and (8, 4) in five and (6, 5) in five and (7, 5) not in five, "5 的第一行 ### 和第二行 #.."
    capped = Badge.PotBadge()
    capped.flash()
    last = None
    for _ in range(30):
        last = capped.step(0.05, dict(HOT, grade=1, bonus=150))[0]
    drawn = cellsOf(colored(last, DIAL))
    assert countCells(99) <= drawn and not countCells(150) <= drawn, "最多显示 +99"


def testTheTooltipChoice():
    tip = Badge.tooltipOf
    assert tip(3, "Beef Stew", "Beef Stew", True, True, 7.0) == ("handson_delight.pot.ready", (3, "Beef Stew"))
    assert tip(0, None, "Beef Stew", False, True, 7.0) == ("name", ("Beef Stew",)), "没烧着：只显示名字"
    assert tip(0, None, "Beef Stew", True, False, 7.0) == ("name", ("Beef Stew",)), "没人搅：只显示名字"
    assert tip(0, None, "Beef Stew", True, True, 7.0) == ("handson_delight.pot.cooking", ("Beef Stew", 7))
    assert tip(0, None, "Beef Stew", True, True, 4.1)[1][1] == 5 and tip(0, None, "Beef Stew", True, True, 4.0)[1][1] == 4, "剩的秒数进位"
    assert tip(0, None, "Beef Stew", True, True, 0.05)[1][1] == 1 and tip(0, None, "Beef Stew", True, True, 0.0)[1][1] == 0
    assert tip(0, None, None, True, True, 3.0) is None, "没有菜没有提示"
    key, args = tip(2, "A", "A", True, True, 1.0)
    assert Badge.TIP_FORMATS[key] % args == "2 x A"
    key, args = tip(0, None, "A", True, True, 1.0)
    assert Badge.TIP_FORMATS[key] % args == "A in 1 s"
    state = {"dish": True, "dishName": "Stew", "servings": 0, "heated": True, "stirring": True, "cookLeft": 2.5}
    assert Badge.PotBadge().tooltip(state) == ("handson_delight.pot.cooking", ("Stew", 3))


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
