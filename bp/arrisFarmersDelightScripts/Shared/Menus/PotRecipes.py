# -*- coding: utf-8 -*-
"""PotRecipes - 厨锅经典界面左边的食谱格：算出的内容（在看界面的那一端按搜索词算）、选中的底格与点选的手势（双端）

食谱格是库的 Choice（原版切石机的配方按钮）：一格一道菜的成品，点一格选中，选中的那格换底格，悬停写成品的悬停文本。
- 内容由部件 RecipeGrid 算：这一端按这位查看者的搜索词过滤后每道食谱的成品，一份，照表的顺序（Shared/Rules/PotSearch：用这一端
  自己问到的显示名，按搜索词记着）；显示几格随搜索变。服务端那一份给空：联机时两端问到的名字可以不一样，它不知道客户端过滤出了什么，
  也用不到（客户端的食谱格是客户端自己算的，点它发的是动作、不是格子操作）；
- 选中按配方的身份：点一格发的是这一格在本端过滤结果里是表里的哪一行（pick(行号)），服务端只认行号；选中的那格的底格按
  "这一格的行是不是选中的那一行"画（每位查看者状态 picked 记的是行号），那一行被搜索词过滤掉时哪格都不亮；
- 手势：键鼠、手柄照 Choice（按下就选中）；触屏改成抬起才选中。食谱多到放不下时要用手指拖着滚，按下就选会把开始滚动时按到的
  那道选上（旧界面的配方按钮也是抬起才算）：手指拖动过、这一下被滚动视图接走、松开在别的格子上都不算。
"""
from ...dolorContainer.Common import Menus as Libs
from ...dolorContainer.Common import Rules
from ...dolorContainer.Common.Slots import Decoration
from ...dolorContainer.Std.Slots import Choice, ChoiceInteraction
from ..Rules import PotSearch
from ..Rules.TableWire import isInt

# 食谱格的底格：没选中、选中（旧界面配方按钮平时与按下的两张；这里选中的那格一直是第二张）
CELLS = ("textures/ui/recipe_book_item_bg", "textures/ui/recipe_book_touch_cell_selected")


def searchOf(viewer):
    """这位查看者的搜索词（没有时是空串）。"""
    return (viewer or {}).get("search") or ""


def rowOf(viewer, cell):
    """这位查看者在这一端看到的食谱格第 cell 格是表里的哪一行；没有这一格是 None。"""
    return PotSearch.rowAt(searchOf(viewer), cell)


class RecipeGrid(object):
    """食谱格的内容（算出的格子的部件）：这一端按搜索词过滤后每道食谱的成品，一份；显示几格随搜索变。side 是结构建在哪一端
    （Structure.side）：服务端给空（见模块说明）。"""

    def __init__(self, side=None):
        self.side = side

    def derive(self, name, reader, viewer=None):
        return {} if self.side == Libs.SERVER else PotSearch.cells(searchOf(viewer))

    def shown(self, name, reader, viewer=None):
        return 0 if self.side == Libs.SERVER else PotSearch.count(searchOf(viewer))


class TapToPick(ChoiceInteraction):
    """食谱格的手势：选中时发行号（见模块说明）；触屏按下先接管这一下，松开在同一格、手指没拖动过才选中；别的输入照 Choice。"""

    def _select(self, g, ref):
        """选中一格（键鼠、手柄按下，Shift、Q，触屏抬起都走这里）：发这一格在本端过滤结果里是哪一行；这一格没有东西时什么都不发。"""
        g.forgetDoubleClick()
        g.lastActionRef = ref
        row = rowOf(g.workspace().viewer, ref[1])
        slot = g.slotType(ref)
        if row is not None and g.call(slot.select, [row]) and slot.sound:
            g.sound(slot.sound)
        return True

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
    """食谱格的格子类型：Choice 换上发行号、触屏抬起才选中的手势，底格是 CELLS，选中的那格按行号画。"""

    interaction = TapToPick()

    def __init__(self, select, selected):
        Choice.__init__(self, select, selected, cells=CELLS)

    def decorate(self, ws, ref, stack):
        out = Decoration()
        viewer = ws.viewer or {}
        picked = viewer.get(self.selected)
        chosen = isInt(picked) and picked >= 0 and rowOf(viewer, ref[1]) == picked
        out.cell = self.cells[1] if chosen else self.cells[0]
        return out
