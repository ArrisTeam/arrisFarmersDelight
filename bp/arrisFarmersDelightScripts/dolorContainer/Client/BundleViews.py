# -*- coding: utf-8 -*-
"""
收纳袋的界面部件，照原版：悬停提示（gameplay.bundle_tooltip）与格子上张开的样子（bundle_slot_panel）。
控件结构由 tools/gen_ui.py 生成；原版靠数据绑定驱动的部分在这里按状态设值，没变的设置由各控件对象挡掉。
"""
from ..Common import Bundles, Items
from . import Display, Paths
from .Views import ItemView, Lazy, Placed, ProgressBar, UnknownState, defaultsKnown, ensureItemLayers

_STALE = object()   # 状态未知（复用来路不明的界面树时）

CELL_SIZE = {False: 20, True: 30}     # 提示网格一格的边长：经典版 20、携带版 30（原版 bundle_tooltip_slot_*）


def _label(control):
    return control.asLabel()


def _image(control):
    return control.asImage()


class _Text(object):
    """一个文字控件；文字没变时不调用引擎。"""

    def __init__(self, screen, path):
        self._label = Lazy(screen, path, _label)
        self._text = "" if defaultsKnown() else None

    def set(self, text):
        if text != self._text:
            label = self._label.get()
            if label is not None:
                self._text = text
                label.SetText(text)


class _Cell(object):
    """提示网格的一格：物品（图标、数量、耐久条、容量条）、选中高亮（键鼠绿底白框、触屏蓝底）、"+N"。"""

    def __init__(self, screen, path):
        self.placed = Placed(screen, path, visible=True, position=(0, 0))
        self.slot = Placed(screen, path + Paths.BC_SLOT, visible=False)
        self.item = ItemView(screen, path + Paths.BC_RENDERER, path + Paths.BC_COUNT, path + Paths.BC_DURABILITY,
                             path + Paths.BC_STORAGE, rendererVisible=True)
        self.highlight = Placed(screen, path + Paths.BC_HIGHLIGHT, visible=False)
        self.mouse = Placed(screen, path + Paths.BC_HIGHLIGHT_MOUSE, visible=True)
        self.touch = Placed(screen, path + Paths.BC_HIGHLIGHT_TOUCH, visible=False)
        self.more = Placed(screen, path + Paths.BC_MORE, visible=False)
        self.moreText = _Text(screen, path + Paths.BC_MORE)

    def showItem(self, stack, context, selected, touch):
        self.more.setVisible(False)
        self.slot.setVisible(True)
        self.item.showItem(stack, context, False)
        self.highlight.setVisible(selected)
        if selected:
            self.mouse.setVisible(not touch)
            self.touch.setVisible(touch)

    def showMore(self, text):
        self.slot.setVisible(False)
        self.moreText.set(text)
        self.more.setVisible(True)

    def hide(self):
        self.slot.setVisible(False)
        self.more.setVisible(False)

    def controls(self):
        return [self.placed, self.slot, self.item.renderer, self.item.durability.placed, self.item.storage.placed,
                self.highlight, self.mouse, self.touch, self.more]


class BundleTooltip(object):
    """
    收纳袋的悬停提示：标题是收纳袋的名字；网格照 Bundles.TooltipLayout 排，选中的一格加高亮；空袋时写说明；
    重量条按剩余重量裁剪（满了换红条写"满"，空袋写"空"）；选中一项时提示上方显示它的名字。
    path 是提示本身：键鼠与手柄是跟着指针的那一份里面的提示，触屏是贴底边的那一份。
    网格的格子照原版按需长：要显示几格就建到几格（按 Paths.BUNDLE_CELL_TEMPLATE），建好的留着下次用。
    """

    def __init__(self, screen, path, pocket, touch=False):
        self.screen = screen
        self.path = path
        self.placed = Placed(screen, path, visible=False)
        self.cellSize = CELL_SIZE[bool(pocket)]
        self.cellTemplate = Paths.BUNDLE_CELL_TEMPLATE % (("pocket" if pocket else "classic") + ("_touch" if touch else ""))
        self.label = _Text(screen, path + Paths.BT_LABEL)
        self.grid = Placed(screen, path + Paths.BT_GRID)
        self.cells = []
        self.info = Placed(screen, path + Paths.BT_INFO, visible=False)
        self.empty = Placed(screen, path + Paths.BT_BAR_EMPTY, visible=False)
        self.fill = Placed(screen, path + Paths.BT_BAR_FILL, visible=True)
        self.fillImage = Lazy(screen, path + Paths.BT_BAR_FILL, _image)
        self.full = Placed(screen, path + Paths.BT_BAR_FULL, visible=False)
        self.selectedName = Placed(screen, path + Paths.BT_SELECTED_NAME, visible=False)
        self.selectedText = _Text(screen, path + Paths.BT_SELECTED_TEXT)
        self._ratio = None
        self._shown = None
        self._cellsMayExist = not defaultsKnown()   # 界面树来路不明：格子可能已经建过

    def show(self, bundle, name, selectedCell, selectedName, context, touch):
        """bundle：收纳袋；name：它的名字；selectedCell：选中的网格格（没有为 None）；selectedName：选中那一项的名字。"""
        state = (name, selectedCell, selectedName, touch)
        if self._shown is None or self._shown[0] is not bundle or self._shown[1] != state:
            self._shown = (bundle, state)
            self._render(bundle, name, selectedCell, selectedName, context, touch)
        self.placed.setVisible(True)

    def _ensureCells(self, count):
        """网格里至少有 count 格（不够的按模板建）；建了新格子时返回真（设完状态后要刷新界面，新格子才画出来）。"""
        if len(self.cells) >= count:
            return False
        grid = self.grid.control
        if grid is None:
            return False
        created = False
        while len(self.cells) < count:
            index = len(self.cells)
            path = self.path + Paths.BT_CELL % index
            if self._cellsMayExist and self.screen.GetBaseUIControl(path) is not None:
                with UnknownState():
                    self.cells.append(_Cell(self.screen, path))
                continue
            self._cellsMayExist = False
            if self.screen.CreateChildControl(self.cellTemplate, "c%d" % index, grid, False) is None:
                break
            self.cells.append(_Cell(self.screen, path))
            created = True
        return created

    def _render(self, bundle, name, selectedCell, selectedName, context, touch):
        layout = Bundles.TooltipLayout(bundle)
        self.label.set(name)
        size = self.cellSize
        created = self._ensureCells(layout.cells())
        self.grid.resize(layout.columns * size, layout.rows * size)
        more = layout.moreCell()
        for index, cell in enumerate(self.cells):
            if index >= layout.cells():
                cell.hide()
                continue
            cell.placed.place(index % layout.columns * size, index // layout.columns * size)
            entry = layout.entryIndexAt(index)
            if entry is not None:
                cell.showItem(Bundles.entryItem(layout.items[entry]), context, index == selectedCell, touch)
            elif index == more:
                cell.showMore("+%d" % layout.hiddenCount)
            else:
                cell.hide()
        capacity = Bundles.specOf(bundle).weightLimit
        weight = Bundles.contentsWeight(bundle, context.rules)
        empty, full = weight <= 0, weight >= capacity
        self.info.setVisible(empty)
        self.empty.setVisible(empty)
        self.full.setVisible(full)
        self.fill.setVisible(not full)
        # 裁掉剩余重量那一段；超重的收纳袋（命令造的）按满算
        ratio = round(min(1.0, max(0.0, float(capacity - weight) / capacity)), 4) if capacity else 1.0
        if ratio != self._ratio:
            image = self.fillImage.get()
            if image is not None:
                self._ratio = ratio
                image.SetSpriteClipRatio(ratio)
        self.selectedName.setVisible(selectedCell is not None)
        if selectedCell is not None:
            self.selectedText.set(selectedName)
        if created:
            # 界面建好以后才建的格子要刷新一次界面才画出来（网格藏一下再显示是早先的做法，留着无妨）
            grid = self.grid.control
            grid.SetVisible(False, False)
            grid.SetVisible(True, False)
            self.screen.UpdateScreen(False)

    def hide(self):
        self.placed.setVisible(False)

    def controls(self):
        out = [self.placed, self.grid, self.info, self.empty, self.fill, self.full, self.selectedName, self.fillImage]
        for cell in self.cells:
            out += cell.controls()
        return out


class BundleOpen(object):
    """
    收纳袋张开的样子：盖在那一格上，底色（键鼠绿、触屏蓝加选中框）、袋子后片、选中的物品、袋子前片、容量条。
    袋子前后片是收纳袋本身的图标，开口的开关写死在界面 JSON 里，这里只往属性包写它的物品编号。每个格子区一个。
    """

    def __init__(self, screen, path):
        self.screen = screen
        self.placed = Placed(screen, path, visible=False, position=(0, 0))
        self.mouse = Placed(screen, path + Paths.BO_MOUSE, visible=True)
        self.touchCell = Placed(screen, path + Paths.BO_TOUCH_CELL, visible=False)
        self.touchFrame = Placed(screen, path + Paths.BO_TOUCH_FRAME, visible=False)
        self.halves = (Lazy(screen, path + Paths.BO_BACK), Lazy(screen, path + Paths.BO_FRONT))
        self.item = Placed(screen, path + Paths.BO_ITEM, visible=False)
        self.itemRenderer = Lazy(screen, path + Paths.BO_ITEM, lambda control: control.asItemRenderer())
        self.storage = ProgressBar(screen, path + Paths.BO_STORAGE)
        self._idAux = None
        self._item = None if defaultsKnown() else _STALE
        self._layered = False
        self._layersMayExist = not defaultsKnown()

    def show(self, position, idAux, selected, storage, touch, context):
        """
        position：那一格的位置；idAux：收纳袋图标的物品编号；selected：选中的物品（没有为 None）；storage：容量条数值；
        context：Display.Context。
        """
        self.placed.place(*position)
        self.mouse.setVisible(not touch)
        self.touchCell.setVisible(touch)
        self.touchFrame.setVisible(touch)
        if idAux is not None and idAux != self._idAux:
            for half in self.halves:
                control = half.get()
                if control is not None:
                    control.SetPropertyBag({"#item_id_aux": int(idAux)})
            self._idAux = idAux
        if selected is not self._item:
            self._item = selected
            if Items.isEmpty(selected):
                self.item.setVisible(False)
            else:
                renderer = self.itemRenderer.get()
                args = Display.iconArgs(selected)
                if renderer is not None and not self._layered and Display.hasItemLayers(args[3]):
                    self._layered = ensureItemLayers(self.screen, self.item.control, self.item.path,
                                                     self._layersMayExist)
                if renderer is not None and renderer.SetUiItem(*args):
                    extras = context.iconExtras(selected)
                    if extras:
                        self.item.control.SetPropertyBag(extras)
                self.item.setVisible(True)
        if storage is None:
            self.storage.hide()
        else:
            self.storage.show(*storage)
        self.placed.setVisible(True)

    def hide(self):
        self.placed.setVisible(False)

    def controls(self):
        return [self.placed, self.mouse, self.touchCell, self.touchFrame, self.item, self.storage.placed] \
            + list(self.halves) + [self.itemRenderer]
