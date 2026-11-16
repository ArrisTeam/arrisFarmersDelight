# -*- coding: utf-8 -*-
# runner: both
"""厨锅徽章牌（Shared/Rules/HandsOn/PotBadge.py + PotBadgeGlyphs.py）：数值照 Hands-On Delight 的 PotBehavior（徽章常量 86-113、drawDial 1579-1660、
showGrade 926-950、tooltip 1113-1128）和 cooking_pot.json 的 badge / dial_track / dial / preview 节点。

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
    return [rect[:4] for rect in model["rects"] if rect[4] == argb]


def cellsOf(rects):
    """矩形列表 -> 铺开的格子集合 {(x, y)}（x 可以是 .5）。"""
    cells = set()
    for x, y, w, h in rects:
        for i in range(int(w)):
            for j in range(int(h)):
                cells.add((x + i, y + j))
    return cells


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
    assert Glyphs.plateRects() == [[-10, -16, 20, 28, PLATE], [-9, -17, 18, 1, PLATE], [-9, 12, 18, 1, PLATE]]
    model, _events = Badge.PotBadge().step(0.05, {"here": True, "dish": True, "meal": 2})
    assert model["rects"] == Glyphs.plateRects(), "出锅后锅里只剩成品、料格空了：只有底板和图标"
    assert model["itemRect"] == [-8, -8, 16, 16] and model["unit"] == 0.125
    assert model["hoverRect"] == [-12, -12, 24, 24], "preview 节点的碰撞盒 ±12"


def testStarsAreCentredOverTheIconAndTheMiddleOneStandsHigher():
    assert [Glyphs.starLeft(1, 0)] == [-2.5]
    assert [Glyphs.starLeft(2, star) for star in range(2)] == [-5.5, 0.5]
    assert [Glyphs.starLeft(3, star) for star in range(3)] == [-8.5, -2.5, 3.5]
    assert [Glyphs.starTop(3, star) for star in range(3)] == [-14, -15, -14], "三颗时中间那颗高一像素"
    assert [Glyphs.starTop(2, star) for star in range(2)] == [-14, -14] and Glyphs.starTop(1, 0) == -14


def testAFullStarMergesIntoSixRectangles():
    cells = Glyphs.starCells(1, 5)
    rects = Glyphs.merge(cells, DIAL)
    assert len(rects) == 6 and cellsOf([r[:4] for r in rects]) == cells
    assert [r[:4] for r in rects] == [[-0.5, -14, 1, 1], [-1.5, -13, 3, 1], [-2.5, -12, 5, 1], [-1.5, -11, 3, 1], [-1.5, -10, 1, 1], [0.5, -10, 1, 1]]
    assert all(isinstance(value, int) for rect in rects for value in rect[2:4]), "宽和高是整数，只有 x 带 .5"


def testMergingJoinsRunsAndTallColumns():
    assert Glyphs.merge(set([(0, 0), (1, 0), (2, 0), (4, 0)]), 1) == [[0, 0, 3, 1, 1], [4, 0, 1, 1, 1]], "一行里连着的并成一条，断开的分开"
    assert Glyphs.merge(set([(0, 0), (1, 0), (0, 1), (1, 1), (0, 2), (1, 2)]), 7) == [[0, 0, 2, 3, 7]], "上下横杠一样的并成高矩形"
    assert Glyphs.merge(set([(0, 0), (0, 2)]), 1) == [[0, 0, 1, 1, 1], [0, 2, 1, 1, 1]], "隔了一行不并"
    assert Glyphs.merge(set(), 1) == []


def testAColdPotShowsUnlitStarsAndAnEmptyFlameInsteadOfTheBar():
    model = exactly(heated=False, openStars=2, progress=1.0, stars=2.0)
    track = colored(model, TRACK)
    assert [-7, 10, 14, 1] not in track, "没火没有轨"
    flame = Glyphs.glyphCells(Glyphs.FLAME, -2, 8)
    assert flame <= cellsOf(track) and len(cellsOf(track)) == FLAME_CELLS + 2 * STAR_CELLS, "空火苗 + 两颗空星"
    assert [-2, 10, 5, 2] in track, "火苗中间两行一样，并成 5 x 2"
    assert [rect for rect in colored(model, DIAL) if rect[1] == 10] == [], "冷锅的条是 0：进度再满也不画（星照控制量画）"


def testAColdPotLightsNoBarEvenWithProgress():
    model = exactly(heated=False, progress=1.0, stars=0.0)
    assert colored(model, DIAL) == [], "冷锅条是 0，星没有，什么都不亮"


def testAHotPotShowsTheBarTrackAndTheProgressAsFarAsTheBatchIs():
    model = exactly(progress=0.5)
    assert [-7, 10, 14, 1] in colored(model, TRACK), "整条轨 14 像素"
    assert [-7, 10, 7, 1] in colored(model, DIAL), "进度 0.5 -> round(7) = 7 像素"
    assert [-7, 10, 4, 1] in colored(exactly(progress=0.25), DIAL), "3.5 进位成 4（Java 的 Math.round 是 floor(x + 0.5)）"
    assert [-7, 10, 3, 1] in colored(exactly(progress=0.24), DIAL)
    assert [-7, 10, 14, 1] in colored(exactly(progress=1.0), DIAL)
    assert colored(exactly(progress=0.0), DIAL) == [], "进度 0 又没有星：什么都不亮"


def testTheStarsFillFromTheBottomRow():
    one = exactly(stars=1.0)
    assert cellsOf(colored(one, DIAL)) == Glyphs.starCells(3, 5) and len(cellsOf(colored(one, DIAL))) == STAR_CELLS, "一颗星 = 5 行：第一颗全亮"
    part = exactly(stars=1.4)
    assert cellsOf(colored(part, DIAL)) == Glyphs.starCells(3, 7), "1.4 颗星 round(7) 行：第一颗全亮，第二颗从下往上两行（.###. 和 .#.#.）"
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
    assert waiting["rects"] == Glyphs.plateRects(), "等卷轴的菜不煮：没有条和星"
    assert len(badge.step(0.05, dict(HOT, waiting=True, meal=1))[0]["rects"]) > 3, "已经有成品了就不再等（waiting 只在没成品时算）"


def testAFinishedPotWithIngredientsStillShowsTheBar():
    assert len(Badge.PotBadge().step(0.05, dict(HOT, meal=2, ingredients=True))[0]["rects"]) > 3
    assert Badge.PotBadge().step(0.05, dict(HOT, meal=2, ingredients=False))[0]["rects"] == Glyphs.plateRects()


def testTheRectangleListIsTheSameObjectUntilSomethingChanges():
    badge = Badge.PotBadge()
    badge.shownProgress = 0.5
    first = badge.step(0.0, dict(HOT))[0]["rects"]
    assert badge.step(0.0, dict(HOT))[0]["rects"] is first
    badge.shownProgress = 0.75
    changed = badge.step(0.0, dict(HOT))[0]["rects"]
    assert changed is not first and [-7, 10, 11, 1] in [r[:4] for r in changed if r[4] == DIAL], "0.75 * 14 = 10.5 -> 11"


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
    assert [-7, 10, 14, 1] in colored(byAt[0.1], DIAL), "亮星期间条是满的"
    assert not Glyphs.countCells(3) & cellsOf(colored(byAt[0.5], DIAL)), "还没亮完不显示 +N"
    assert Glyphs.starCells(3, 5) <= cellsOf(colored(byAt[0.4], DIAL)), "0.4 秒第一颗全亮"
    assert not Glyphs.starCells(3, 10) <= cellsOf(colored(byAt[0.4], DIAL)), "第二颗还没亮"
    assert Glyphs.countCells(3) <= cellsOf(colored(byAt[1.0], DIAL)), "两颗都亮了又过了 0.3 + 2 * 0.18 = 0.66 秒：+3 出来"
    assert not badge.flashing and not Glyphs.countCells(3) & cellsOf(colored(sequence[-1][1], DIAL)), "2.8 秒后回到平常的样子"


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
        cells = Glyphs.countCells(added)
        assert max(x for x, _y in cells) == 8 and max(y for _x, y in cells) == 8 and min(y for _x, y in cells) == 4, added
    five = Glyphs.countCells(5)
    assert min(x for x, _y in five) == 2, "'+5'：右对齐 9 - 2 * 4 + 1 = 2，+ 号的横杠从 x = 2 起"
    assert min(x for x, _y in Glyphs.countCells(12)) == -2, "'+12'：9 - 3 * 4 + 1 = -2"
    assert (3, 5) in five and (2, 6) in five and (3, 6) in five and (4, 6) in five and (3, 7) in five, "+ 号"
    assert (6, 4) in five and (7, 4) in five and (8, 4) in five and (6, 5) in five and (7, 5) not in five, "5 的第一行 ### 和第二行 #.."
    capped = Badge.PotBadge()
    capped.flash()
    last = None
    for _ in range(30):
        last = capped.step(0.05, dict(HOT, grade=1, bonus=150))[0]
    drawn = cellsOf(colored(last, DIAL))
    assert Glyphs.countCells(99) <= drawn and not Glyphs.countCells(150) <= drawn, "最多显示 +99"


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
