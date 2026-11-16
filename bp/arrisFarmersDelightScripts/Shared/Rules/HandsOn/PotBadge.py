# -*- coding: utf-8 -*-
"""PotBadge - 厨锅上方的徽章牌：评星、进度条、火苗、出锅后星星一颗颗亮起并显示 "+N"、悬停提示（双端）

移植自 Hands-On Delight 的 client/PotBehavior.java：徽章可见性 badge（873-881 行）、graded / grade / bonus / openStars（897-915 行）、
showGrade（926-950 行）、frame 里的平滑（1172-1173 行）、tooltip（1113-1128 行）、drawDial（1579-1601 行）。像素本身在 PotBadgeGlyphs。
时间一律是秒（Java 的刻 = 1/20 秒；这里 COOK_LEFT 已经是秒）。

每帧用当前状态调 step(dt, state)，得到 (model, events)：model 是给内核的"像素牌"（view.plate(...) 的 rects / itemRect，坐标是图标像素，
原点在菜的图标中心、+y 向下，见 PotBadgeGlyphs），不该显示时是 None；events 是出锅后星星亮起的闪光和叮的一声。

state 的键（缺省都是假 / 0）：
    here 厨师在锅边（镜头在锅那儿）；dish 有一道菜可显示（成品，或锅里的料能做出的）；meal 锅里煮好的份数（0 = 没有）；ingredients 料格里有料；
    heated 烧着；progress 进度 0..1；stars 评星的控制量 0..3；grade 这一批的整星数；bonus 这一批多送的份数；openStars 厨师开了几颗星 1..3；
    waiting 这道菜在等法术卷轴，不煮（炼金锅用；本锅没有就别给）。
"""
import math

from .Mth import EPS, clamp, lerp, roundInt
from .PotBadgeGlyphs import (BAR_LENGTH, HOVER_RECT, ITEM_RECT, MOST_ADDED, PIXEL, STAR, STAR_SIZE, STARS, dialRects, plateRects, starLeft,
                             starTop, trackRects)
from .PotSounds import ONE_SHOTS, shotOf

GRADE_WAIT = 0.3          # 一批出锅后，第一颗星等这么久才亮
GRADE_STAGGER = 0.18      # 星一颗接一颗亮，间隔
GRADE_SHOWN = 2.8         # 亮着这么久之后牌子回到平常的样子
GRADE_PITCH = ONE_SHOTS["chime"]["pitches"]      # 叮的音高，按第几颗星：1.0 / 1.26 / 1.5
SMOOTH = 6.0              # 进度和星的平滑：每秒朝目标走 min(1, SMOOTH * dt)
PUFF_UP = (0.0, 4.0, 0.0)
GLINT_COLOR = 0xFFFFE9A0
GLINT_COUNT = 3
GLINT_SPREAD = 0.4
TIP_READY = "handson_delight.pot.ready"        # "%s x %s"：份数、菜名
TIP_COOKING = "handson_delight.pot.cooking"    # "%s in %s s"：菜名、剩几秒
TIP_NAME = "name"                              # 只显示菜名
TIP_FORMATS = {TIP_READY: "%s x %s", TIP_COOKING: "%s in %s s"}
_MEMO = 400               # 记着多少种已经拼好的矩形


def tooltipOf(servings, mealName, dishName, heated, stirring, cookLeft):
    """悬停提示的选择（PB 1113-1128）：返回 (键, 参数元组)，调用方自己格式化（TIP_FORMATS 是英文原文）；没有菜是 None。

    锅里有煮好的 -> (TIP_READY, (份数, 菜名))；没烧着或没人搅 -> (TIP_NAME, (菜名,))；在煮 -> (TIP_COOKING, (菜名, 剩几秒))，
    剩的秒数进位（Mth.ceil）。"""
    if servings > 0:
        return TIP_READY, (servings, mealName)
    if dishName is None:
        return None
    if not heated or not stirring:
        return TIP_NAME, (dishName,)
    return TIP_COOKING, (dishName, int(math.ceil(max(0.0, cookLeft) - EPS)))


class PotBadge(object):
    """一口锅的徽章：平滑的进度 / 星、出锅后的亮星序列、拼好的矩形（没变就是同一个列表对象，内核不用重新摆）。"""

    def __init__(self):
        self.shownProgress = 0.0
        self.shownStars = 0.0
        self.gradeAge = None             # 出锅后星星亮起的计时；None = 没在亮
        self._plate = plateRects()
        self._tracks = {}
        self._dials = {}
        self._key = None
        self._rects = None

    @property
    def flashing(self):
        """出锅后的亮星序列在不在放（PB 的 !isNaN(gradeAge)）。"""
        return self.gradeAge is not None

    def flash(self, focused=True):
        """一批出锅了（PB 的 graded()）：开始亮星序列；这位玩家不在锅边（focused 为 False）就不演。"""
        self.gradeAge = 0.0 if focused else None

    def tooltip(self, state):
        """悬停提示：state 另外要 servings、mealName、dishName、stirring、cookLeft（秒）；见 tooltipOf。"""
        return tooltipOf(int(state.get("servings", 0)), state.get("mealName"), state.get("dishName") if state.get("dish") else None,
                         bool(state.get("heated")), bool(state.get("stirring")), float(state.get("cookLeft", 0.0)))

    def step(self, dt, state):
        """推进 dt 秒，返回 (model, events)。model：{"rects": [[x, y, w, h, argb], ...], "itemRect": [x, y, w, h], "hoverRect": [...], "unit": PIXEL}
        或 None（徽章不显示）；events：{"type": "glint", ...} 和 {"type": "sound", ...}（叮，只在这批多送了份数时响）。"""
        smooth = min(1.0, dt * SMOOTH)
        self.shownProgress = lerp(smooth, self.shownProgress, float(state.get("progress", 0.0)))
        self.shownStars = lerp(smooth, self.shownStars, float(state.get("stars", 0.0)))
        events = self._flash(dt, state)
        return self._model(state), events

    def _flash(self, dt, state):
        """showGrade：每颗得到的星在 GRADE_WAIT + 序号 * GRADE_STAGGER 秒那一刻闪一下（图标像素里星的中心），有多送的份数才叮。"""
        if self.gradeAge is None:
            return []
        before = self.gradeAge
        self.gradeAge += dt
        grade = clamp(int(state.get("grade", 0)), 0, STARS)
        open_ = clamp(int(state.get("openStars", 1)), 1, STARS)
        events = []
        for star in range(grade):
            at = GRADE_WAIT + star * GRADE_STAGGER
            if before <= at < self.gradeAge:
                events.append({"type": "glint", "x": starLeft(open_, star) + STAR_SIZE / 2.0, "y": starTop(open_, star) + STAR_SIZE / 2.0,
                               "count": GLINT_COUNT, "size": GLINT_SPREAD, "rise": PUFF_UP, "color": GLINT_COLOR})
                if int(state.get("bonus", 0)) > 0:
                    events.append(shotOf("chime", star))
        if self.gradeAge >= GRADE_SHOWN:
            self.gradeAge = None
        return events

    def _model(self, state):
        """徽章此刻的样子（PB 的 badge() 可见性 + drawDial）。"""
        if not (state.get("here") and state.get("dish")):
            return None
        meal = bool(state.get("meal"))
        holding = self.gradeAge is not None
        # 星和条只在煮 / 出锅亮星的时候有；锅里只剩成品、料格都空了就只剩底板和图标；等卷轴的菜不煮
        running = not meal or bool(state.get("ingredients")) or holding
        waiting = bool(state.get("waiting")) and not meal
        model = {"itemRect": list(ITEM_RECT), "hoverRect": list(HOVER_RECT), "unit": PIXEL}
        if not running or waiting:
            model["rects"] = self._rectsFor(("plate",), lambda: list(self._plate))
            return model
        cold = not state.get("heated")
        grade = clamp(int(state.get("grade", 0)), 0, STARS)
        open_ = clamp(int(state.get("openStars", 1)), 1, STARS)
        bar = BAR_LENGTH if holding else (0 if cold else roundInt(self.shownProgress * BAR_LENGTH))
        lit = clamp(int(math.floor((self.gradeAge - GRADE_WAIT) / GRADE_STAGGER)) + 1, 0, grade) if holding else 0
        rows = min(open_ * len(STAR), lit * len(STAR) if holding else roundInt(self.shownStars * len(STAR)))
        # 多送的份数在最后一颗星亮起之后才显示
        shows = holding and lit == grade and self.gradeAge > GRADE_WAIT + grade * GRADE_STAGGER
        added = min(max(0, int(state.get("bonus", 0))), MOST_ADDED) if shows else 0
        model["rects"] = self._rectsFor((open_, cold, bar, rows, added), lambda: self._plate + self._track(open_, cold) + self._dial(open_, bar, rows, added))
        return model

    def _rectsFor(self, key, build):
        """矩形列表：key（徽章此刻的样子）没变就还是上一个列表对象，内核不用重新摆。"""
        if key != self._key:
            self._key, self._rects = key, build()
        return self._rects

    def _track(self, open_, cold):
        key = (open_, cold)
        if key not in self._tracks:
            self._tracks[key] = trackRects(open_, cold)
        return self._tracks[key]

    def _dial(self, open_, bar, rows, added):
        key = (open_, bar, rows, added)
        if key not in self._dials:
            if len(self._dials) > _MEMO:
                self._dials.clear()
            self._dials[key] = dialRects(open_, bar, rows, added)
        return self._dials[key]
