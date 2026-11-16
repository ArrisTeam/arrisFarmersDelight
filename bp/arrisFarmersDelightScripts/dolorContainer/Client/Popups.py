# -*- coding: utf-8 -*-
"""
界面上的弹出部件，都照原版容器界面：
- 物品详情（selected_item_details）：触屏按下有物品的格子时在底部显示它的完整悬停文本，2 秒内淡出；
- 锁定提示（item_lock_notification）：锁定的物品动不了时在上方提示，2 秒内淡出；
- 选数量条（stack_splitting_overlay）：触屏长按时盖在格子旁的带箭头数量条，方向按格子在网格里的位置
  （快捷栏朝上；第一列朝右、最后一列朝左；第一行朝下；其余朝上），填充按比例裁剪，文字"已选/总数"；
- 手柄提示条：A / X / Y / B 的说明问手势识别（悬停那一格的交互的 helpers，没给时照标准交互：随手上有没有东西、悬停的格子
  有没有东西变化，文案键与原版相同）；显示与否由原版绑定决定。
淡出动画由引擎播放（gen_ui.py 定义的动画，参数照原版）。控件都在第一次用到时才向引擎要（见 Views.Lazy）。
"""
from . import Paths
from .Views import Fade, Lazy, Placed


def _label(control):
    return control.asLabel()


def _image(control):
    return control.asImage()


class Popups(object):

    def __init__(self, screen):
        self.screen = screen
        self.details = Placed(screen, Paths.ITEM_DETAILS, visible=False)
        self.detailsText = Lazy(screen, Paths.ITEM_DETAILS_TEXT, _label)
        self.detailsFade = Fade(Lazy(screen, Paths.ITEM_DETAILS_IMAGE), Paths.DETAILS_ANIMATION)
        self.lock = Placed(screen, Paths.LOCK_NOTIFICATION, visible=False)
        self.lockText = Lazy(screen, Paths.LOCK_NOTIFICATION_TEXT, _label)
        self.lockFades = (Fade(Lazy(screen, Paths.LOCK_NOTIFICATION_IMAGE), Paths.LOCK_BACKGROUND_ANIMATION),
                          Fade(Lazy(screen, Paths.LOCK_NOTIFICATION_TEXT), Paths.LOCK_TEXT_ANIMATION))
        self.split = Placed(screen, Paths.SPLIT_BAR, visible=False)
        self.splitSides = {}
        for side, name in Paths.SPLIT_BAR_SIDES.items():
            path = Paths.SPLIT_BAR + "/" + name
            self.splitSides[side] = (Placed(screen, path, visible=False),
                                     Lazy(screen, path + Paths.SPLIT_BAR_FILL, _image),
                                     Lazy(screen, path + Paths.SPLIT_BAR_TEXT, _label))
        self.helperTexts = dict((key, Lazy(screen, Paths.HELPER_TEXT % key, _label)) for key in Paths.HELPER_KEYS)
        self._split = None
        self._helpers = None

    # ---------------------------------------------------------------- 一次性的提示

    def showDetails(self, text, offsetY):
        label = self.detailsText.get()
        if label is None:
            return
        label.SetText(text)
        self.details.place(0, offsetY)
        self.details.setVisible(True)
        self.detailsFade.restart()

    def hideDetails(self):
        self.details.setVisible(False)

    def showLock(self, text):
        label = self.lockText.get()
        if label is None:
            return
        label.SetText(text)
        self.lock.setVisible(True)
        for fade in self.lockFades:
            fade.restart()

    # ---------------------------------------------------------------- 每次重画

    def renderSplit(self, slider, view, side, origin):
        """
        slider：(格, 数量, 总数) 或 None；view：那一格的控件；side：数量条在哪一侧；origin：界面根的坐标。面板盖住那一格
        （位置与大小照那一格现在的样子：整屏按比例缩放的布局里格子缩了，数量条照样贴着它的边）。
        """
        if slider is None or view is None or view.control is None:
            self.split.setVisible(False)
            self._split = None
            return
        _, amount, total = slider
        x, y = view.control.GetGlobalPosition()
        self.split.place(x - origin[0], y - origin[1])
        self.split.resize(*view.control.GetSize())
        state = (side, amount, total)
        if state != self._split:
            self._split = state
            for name, (placed, _, _) in self.splitSides.items():
                placed.setVisible(name == side)
            _, fill, text = self.splitSides[side]
            image = fill.get()
            if image is not None:
                image.SetSpriteClipRatio((total - amount) / float(total) if total else 0.0)
            label = text.get()
            if label is not None:
                label.SetText("%d/%d" % (amount, total))
        self.split.setVisible(True)

    def renderHelpers(self, gestures, session):
        """手柄说明：x、a、y、b 四个键的文案键由手势识别给（悬停那一格的交互，没给时照标准交互）。"""
        state = gestures.helpers()
        if state == self._helpers:
            return
        self._helpers = state
        for key, text in zip(Paths.HELPER_KEYS, state):
            label = self.helperTexts[key].get()
            if label is not None:
                label.SetText(session.text(text))

    def controls(self):
        """所有控件（测试用：逐个向引擎要一遍，核对路径都在）。"""
        out = [self.details, self.detailsText, self.detailsFade.control, self.lock, self.lockText, self.split]
        out += [fade.control for fade in self.lockFades]
        for placed, fill, text in self.splitSides.values():
            out += [placed, fill, text]
        return out + list(self.helperTexts.values())
