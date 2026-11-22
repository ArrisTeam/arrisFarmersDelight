# -*- coding: utf-8 -*-
"""PotRecipes - 厨锅经典界面左边的食谱格：算出的内容（按这位查看者的搜索词）与点选的手势（双端）

食谱格是库的 Choice（原版切石机的配方按钮）：一格一道菜的成品，点一格发 pick(格号) 选中，选中的那格换底格，悬停写成品的悬停文本。
- 内容由部件 RecipeGrid 算：这位查看者的搜索词过滤后每道食谱的成品，一份，照表的顺序（CookingPotBook.gridCells，按搜索词记着）；
  显示几格随搜索变；
- 手势：键鼠、手柄照 Choice（按下就选中）；触屏改成抬起才选中。食谱多到放不下时要用手指拖着滚，按下就选会把开始滚动时按到的
  那道选上（旧界面的配方按钮也是抬起才算）：手指拖动过、这一下被滚动视图接走、松开在别的格子上都不算。
"""
from ...dolorContainer.Common import Rules
from ...dolorContainer.Std.Slots import Choice, ChoiceInteraction
from ..Rules import CookingPotBook as Book

# 食谱格的底格：没选中、选中（旧界面配方按钮平时与按下的两张；这里选中的那格一直是第二张）
CELLS = ("textures/ui/recipe_book_item_bg", "textures/ui/recipe_book_touch_cell_selected")


def searchOf(viewer):
    """这位查看者的搜索词（没有时是空串）。"""
    return (viewer or {}).get("search") or ""


class RecipeGrid(object):
    """食谱格的内容（算出的格子的部件）：搜索过滤后每道食谱的成品，一份；显示几格随搜索变。"""

    def derive(self, name, reader, viewer=None):
        return Book.gridCells(searchOf(viewer))

    def shown(self, name, reader, viewer=None):
        return Book.shownCount(searchOf(viewer))


class TapToPick(ChoiceInteraction):
    """食谱格的手势：触屏按下先接管这一下，松开在同一格、手指没拖动过才选中；别的输入照 Choice。"""

    def touchPress(self, g, ref, now, position):
        g.forgetDoubleClick()
        g.hold(ref, Rules.PRIMARY, now, position, self)
        return True

    def holdTick(self, g, press, now, pointer):
        g.trackMove(press, pointer)

    def holdRelease(self, g, press, ref, now):
        if ref is not None and ref == press.ref and not press.data.get("moved"):
            self._select(g, ref)


class RecipeChoice(Choice):
    """食谱格的格子类型：Choice 换上触屏抬起才选中的手势，底格是 CELLS。"""

    interaction = TapToPick()

    def __init__(self, select, selected):
        Choice.__init__(self, select, selected, cells=CELLS)
