# -*- coding: utf-8 -*-
"""
格子与跟随指针控件的引擎封装。

开销集中在两处，都在这里挡掉：
- 按路径向引擎要控件（GetBaseUIControl）：界面里格子上千个子控件，打开时大多不用动。控件在第一次真要改它时才去要；
- 改控件：每个对象记着控件现在的状态，初始值就是界面 JSON 里写的值（显隐、位置、文字），与之相同的设置不调用引擎。
格子显示同一个物品堆对象时整段跳过（镜像里的物品堆从不原地修改，换了内容就是换了对象）。

位置与尺寸都用 SetFullPosition / SetFullSize（经过布局，不会像 SetPosition 那样把位置锁死）。整屏按比例缩放的布局
（$dc_fit）里，布局内容中的位置与尺寸按设计像素写，下发时乘上缩放的比例，比例变了重新下发（见 ScreenHandle）。
进度条（耐久、收纳袋容量、渐进拿取、选好的数量）用引擎原版的进度条渲染器，数值写进它的属性包，画法与原版一致。

界面会被引擎缓存复用（cache_screen），视图对象也跟着复用（见 Screen 的 _Parts）：视图对象经 ScreenHandle 向当前的
界面节点要控件。引擎留着树、这边的缓存却没了的时候，在 UnknownState 里建视图对象：不假定控件是 JSON 初始的样子，
第一次设置都下发给引擎。
"""
from ..Common import Items
from . import Display, Paths

_UNRESOLVED = object()
_STALE = object()      # 状态未知（复用来路不明的界面树时）
_KNOWN = [True]        # 现在建的视图对象能不能假定控件是 JSON 初始的样子


class UnknownState(object):
    """with 块里建的视图对象不假定控件的状态，第一次设置都下发给引擎。"""

    def __enter__(self):
        _KNOWN[0] = False
        return self

    def __exit__(self, *args):
        _KNOWN[0] = True


def defaultsKnown():
    return _KNOWN[0]


_POSITION, _WIDTH, _HEIGHT = 1, 2, 4   # 控件下发过的几样：位置、宽、高


class ScreenHandle(object):
    """
    视图对象向引擎要控件时用的界面。缓存复用的界面每次打开都是一个新的 ScreenNode，换节点时只改 node；
    已经要到的控件按界面名与路径操作，换了节点照样能用。
    整屏按比例缩放的布局（$dc_fit）：scaledPrefix 是缩放的那一块（布局的内容）的路径前缀，scale 是它现在的比例（界面像素 /
    设计像素，不缩放的布局为 1）。那一块里经 Placed 摆的位置与尺寸按设计像素写，下发时乘上比例；比例变了按新的比例重新下发。
    """

    __slots__ = ("node", "scale", "scaledPrefix", "_scaled")

    def __init__(self, node):
        self.node = node
        self.scale = 1.0
        self.scaledPrefix = None
        self._scaled = {}   # 缩放的那一块里下发过位置、尺寸的控件 -> 下发过哪几样（_POSITION、_WIDTH、_HEIGHT）

    def factor(self, placed, kinds):
        """控件 placed 这次下发 kinds 要乘的比例：在缩放的那一块里的记下来（比例变了重新下发），别处的为 1。"""
        prefix = self.scaledPrefix
        if prefix is None or not placed.path.startswith(prefix):
            return 1.0
        self._scaled[placed] = self._scaled.get(placed, 0) | kinds
        return self.scale

    def setScale(self, scale):
        """缩放的那一块的比例变了：下发过的位置与尺寸按新的比例重新下发。"""
        if scale == self.scale:
            return
        self.scale = scale
        for placed, kinds in self._scaled.items():
            placed.resend(kinds, scale)

    def GetBaseUIControl(self, path):
        return self.node.GetBaseUIControl(path)

    def CreateChildControl(self, defName, childName, parentControl=None, forceUpdate=True):
        return self.node.CreateChildControl(defName, childName, parentControl, forceUpdate)

    def UpdateScreen(self, syncRefresh=True):
        return self.node.UpdateScreen(syncRefresh)

    def SetSelectControl(self, path, enable):
        """选中（文本框：开始打字）或取消选中控件；引擎在按钮事件结束时清掉选中，界面节点延后一点再设。"""
        return self.node.SetSelectControl(path, enable)

    def pointer(self, device):
        """指针的界面坐标（手柄是虚拟光标，触屏是最后一次的触点），取不到时为 None。"""
        return self.node.pointer(device)


def _absolute(value):
    return {"followType": "none", "absoluteValue": float(value)}


class Lazy(object):
    """按路径向引擎要的控件，第一次用到时才要；convert 把基础控件转成具体类型（asLabel 等）。"""

    __slots__ = ("_screen", "path", "_convert", "_value")

    def __init__(self, screen, path, convert=None):
        self._screen = screen
        self.path = path
        self._convert = convert
        self._value = _UNRESOLVED

    def get(self):
        value = self._value
        if value is _UNRESOLVED:
            value = self._screen.GetBaseUIControl(self.path)
            if value is not None and self._convert is not None:
                value = self._convert(value)
            self._value = value
        return value


def _label(control):
    return control.asLabel()


def ensureItemLayers(screen, control, path, mayExist=False):
    """
    在图标控件（路径 path）下建网易物品叠加贴图的 5 层（原版每个图标控件下都有，SetUiItem 按名字找到它们写贴图）。
    带叠加贴图的物品很少，所以第一次显示这种物品时才建，不让每个格子都多 5 个控件。
    界面建好以后才建的子控件，要等父控件的显隐变一次才进绘制列表（刷新界面只重排布局，不够）：
    图标控件此刻显示着就藏一下再显示；藏着的等它显示出来时自然进去。
    mayExist：界面树来路不明（可能已经建过），先看有没有。返回建好了没有。
    """
    if control is None:
        return False
    if mayExist and screen.GetBaseUIControl(path + "/" + Paths.ITEM_LAYERS[0]) is not None:
        return True
    for name in Paths.ITEM_LAYERS:
        if screen.CreateChildControl(Paths.ITEM_LAYER_TEMPLATE % name, name, control, False) is None:
            return False
    if control.GetVisible():
        control.SetVisible(False, False)
        control.SetVisible(True, False)
    screen.UpdateScreen(False)
    return True


SMALL_COUNT_LENGTH = 4    # 数量字这么长起改小字号（超堆叠的短写法：1.2k）
SMALL_COUNT_SCALE = 0.75


class Fade(object):
    """一个控件上的淡出动画（库组件文件里的动画）：第一次挂上并播放，之后每次从头再播。control 是 Lazy。"""

    def __init__(self, control, animation):
        self.control = control
        self.animation = animation
        self.attached = False

    def restart(self):
        control = self.control.get()
        if control is None:
            return
        if self.attached:
            control.StopAnimation("alpha")
            control.PlayAnimation("alpha")
        else:
            self.attached = bool(control.SetAnimation("alpha", Paths.NAMESPACE, self.animation, True))


class Placed(object):
    """
    一个能显隐、能摆位置、能改尺寸的控件。visible / position 传界面 JSON 里的初始值（不知道就传 None）。
    这类对象打开界面时一次建两千来个，用 __slots__ 省掉各自的属性字典（建得快，也少给垃圾回收添对象）。
    """

    __slots__ = ("_screen", "path", "_control", "_visible", "_position", "_size")

    def __init__(self, screen, path, visible=None, position=None):
        self._screen = screen
        self.path = path
        self._control = _UNRESOLVED
        known = _KNOWN[0]
        self._visible = visible if known else None
        self._position = position if known else None
        self._size = None

    @property
    def control(self):
        control = self._control
        if control is _UNRESOLVED:
            control = self._control = self._screen.GetBaseUIControl(self.path)
        return control

    def valid(self):
        return self.control is not None

    def position(self):
        """现在的位置（JSON 里的初始位置或最后一次 place 的位置；都不知道时为 None）。"""
        return self._position

    def shown(self):
        """现在是否显示（JSON 里的初始显隐或最后一次 setVisible；都不知道时为 None）。"""
        return self._visible

    def setVisible(self, visible):
        if visible != self._visible:
            control = self.control
            if control is not None:
                self._visible = visible
                control.SetVisible(visible, False)

    def place(self, x, y):
        position = (round(x, 2), round(y, 2))
        if position != self._position:
            control = self.control
            if control is not None:
                self._position = position
                scale = self._screen.factor(self, _POSITION)
                control.SetFullPosition("x", _absolute(position[0] * scale))
                control.SetFullPosition("y", _absolute(position[1] * scale))

    def resize(self, width, height):
        size = (round(width, 2), round(height, 2))
        if size != self._size:
            control = self.control
            if control is not None:
                self._size = size
                scale = self._screen.factor(self, _WIDTH | _HEIGHT)
                control.SetFullSize("x", _absolute(size[0] * scale))
                control.SetFullSize("y", _absolute(size[1] * scale))

    def setWidth(self, width):
        """只改宽度，高度保持 JSON 里的写法（比如随父控件的 100% - 112px）或之前设的。"""
        width = round(width, 2)
        if self._size is None or self._size[0] != width:
            control = self.control
            if control is not None:
                self._size = (width, self._size[1] if self._size else None)
                control.SetFullSize("x", _absolute(width * self._screen.factor(self, _WIDTH)))

    def setHeight(self, height):
        """只改高度，宽度保持 JSON 里的写法（比如随父控件的 100%）或之前设的。"""
        height = round(height, 2)
        if self._size is None or self._size[1] != height:
            control = self.control
            if control is not None:
                self._size = (self._size[0] if self._size else None, height)
                control.SetFullSize("y", _absolute(height * self._screen.factor(self, _HEIGHT)))

    def resend(self, kinds, scale):
        """整屏缩放的比例变了：下发过的几样（kinds）按新的比例重新下发。"""
        control = self.control
        if control is None:
            return
        if kinds & _POSITION and self._position is not None:
            control.SetFullPosition("x", _absolute(self._position[0] * scale))
            control.SetFullPosition("y", _absolute(self._position[1] * scale))
        size = self._size or (None, None)
        if kinds & _WIDTH and size[0] is not None:
            control.SetFullSize("x", _absolute(size[0] * scale))
        if kinds & _HEIGHT and size[1] is not None:
            control.SetFullSize("y", _absolute(size[1] * scale))


class ProgressBar(object):
    """
    引擎的进度条渲染器：总量与当前值写进它的属性包。渲染器的显示开关在 JSON 里写死为真
    （从 Python 写的布尔值会变成整数，渲染器不认），显隐用控件可见性（JSON 里默认藏着）。
    """

    __slots__ = ("placed", "_amounts")

    def __init__(self, screen, path):
        self.placed = Placed(screen, path, visible=False)
        self._amounts = None

    def show(self, total, current):
        amounts = (float(total), float(current))
        if amounts != self._amounts:
            control = self.placed.control
            if control is not None:
                self._amounts = amounts
                control.SetPropertyBag({"#progress_bar_total_amount": amounts[0],
                                        "#progress_bar_current_amount": amounts[1]})
        self.placed.setVisible(True)

    def hide(self):
        self.placed.setVisible(False)


class ItemView(object):
    """
    图标、数量、耐久条、收纳袋容量条、锁图标：格子、手持物、收纳袋提示里的格子共用的部分。
    rendererVisible 是图标控件在 JSON 里的初始显隐；没有锁图标的（收纳袋提示）lockPath 为 None。
    图标控件没设过物品时什么都不画，所以只有设过物品的才要在空了时藏起来（格子的图标控件在 JSON 里默认显示，
    与原版一样，打开界面时不用逐格去开）。
    """

    def __init__(self, screen, rendererPath, countPath, durabilityPath, storagePath, lockPath=None,
                 rendererVisible=False):
        self.renderer = Placed(screen, rendererPath, visible=rendererVisible)
        self._itemRenderer = _UNRESOLVED
        self._countLabel = Lazy(screen, countPath, _label)
        self.durability = ProgressBar(screen, durabilityPath)
        self.storage = ProgressBar(screen, storagePath)
        self.lockYellow = Placed(screen, lockPath + Paths.LOCK_YELLOW, visible=False) if lockPath else None
        self.lockRed = Placed(screen, lockPath + Paths.LOCK_RED, visible=False) if lockPath else None
        known = _KNOWN[0]
        self.hasItem = False
        self._layered = False      # 图标控件下建好了物品叠加贴图的 5 层
        self._layersMayExist = not known
        self._icon = None if known else _STALE   # 图标控件上的物品 (物品名, aux, userData)；没设过为 None
        self._count = "" if known else None      # JSON 里数量标签的初始文字
        self._shown = _UNRESOLVED  # 上次显示的物品堆对象与锁图标开关
        self._mode = Items.LOCK_NONE
        self.fontScale = 1.0       # 数量字的字号倍数：整屏按比例缩放的布局里是缩放的比例（scaleFont）

    def showItem(self, stack, context, showLocks):
        """stack 为空时清空；context 是 Display.Context。返回物品的锁定方式（showLocks 为假时恒为不锁）。"""
        shown = (stack, showLocks)
        if self._shown is not _UNRESOLVED and shown[0] is self._shown[0] and showLocks == self._shown[1]:
            return self._mode
        self._shown = shown
        self.hasItem = not Items.isEmpty(stack)
        if not self.hasItem:
            if self._icon is not None:
                self.renderer.setVisible(False)
            self._setCount("")
            self.durability.hide()
            self.storage.hide()
            self._setLock(Items.LOCK_NONE)
            self._mode = Items.LOCK_NONE
            return self._mode
        # 物品堆从不原地修改；附加数据直接比较（相同内容的不同对象也算相同），不必先规整成文本
        icon = (stack.get("newItemName"), stack.get("newAuxValue", 0), stack.get("userData"))
        if icon != self._icon:
            itemRenderer = self._getItemRenderer()
            if itemRenderer is not None:
                name, aux, enchanted, userData = Display.iconArgs(stack)
                if not self._layered and Display.hasItemLayers(userData):
                    self._layered = ensureItemLayers(self.renderer._screen, self.renderer.control, self.renderer.path,
                                                     self._layersMayExist)
                if itemRenderer.SetUiItem(name, aux, enchanted, userData):
                    self._icon = icon
                    extras = context.iconExtras(stack)
                    if extras:
                        itemRenderer.SetPropertyBag(extras)
        self.renderer.setVisible(True)
        self._setCount(context.countText(stack))
        bar = context.durability(stack)
        if bar is None:
            self.durability.hide()
        else:
            self.durability.show(*bar)
        bar = context.storage(stack)
        if bar is None:
            self.storage.hide()
        else:
            self.storage.show(*bar)
        self._mode = Items.lockMode(stack) if showLocks else Items.LOCK_NONE
        self._setLock(self._mode)
        return self._mode

    def _getItemRenderer(self):
        """图标控件的物品渲染器接口（由同一个控件转换，不再按路径另要一次）。"""
        value = self._itemRenderer
        if value is _UNRESOLVED:
            control = self.renderer.control
            value = self._itemRenderer = control.asItemRenderer() if control is not None else None
        return value

    def _setCount(self, text):
        if text != self._count:
            label = self._countLabel.get()
            if label is not None:
                small = len(text) >= SMALL_COUNT_LENGTH
                if small != (len(self._count or "") >= SMALL_COUNT_LENGTH):
                    # 1.2k 这类四个字的放进 18 宽的格子
                    label.SetTextFontSize((SMALL_COUNT_SCALE if small else 1.0) * self.fontScale)
                self._count = text
                label.SetText(text)

    def scaleFont(self, scale):
        """
        整屏按比例缩放的布局：数量字的字号乘上比例（四个字的短写法照样改小）。界面先按比例给布局里的标签设过字号，这里在它
        之后设，比例变了就设。
        """
        self.fontScale = scale
        label = self._countLabel.get()
        if label is not None:
            small = len(self._count or "") >= SMALL_COUNT_LENGTH
            label.SetTextFontSize((SMALL_COUNT_SCALE if small else 1.0) * scale)

    def _setLock(self, mode):
        if self.lockYellow is not None:
            self.lockYellow.setVisible(mode == Items.LOCK_IN_INVENTORY)
            self.lockRed.setVisible(mode == Items.LOCK_IN_SLOT)


class _Image(Placed):
    """一张能换贴图、颜色、裁剪比例的图（格子装饰用），没变时不调用引擎。"""

    __slots__ = ("_sprite", "_color", "_clip", "_uv")

    def __init__(self, screen, path):
        Placed.__init__(self, screen, path, visible=False)
        self._sprite = self._color = self._clip = self._uv = None

    def _image(self):
        control = self.control
        return control.asImage() if control is not None else None

    def sprite(self, texture):
        if texture != self._sprite:
            image = self._image()
            if image is not None:
                self._sprite = texture
                image.SetSprite(texture)

    def color(self, rgb):
        if rgb != self._color:
            image = self._image()
            if image is not None:
                self._color = rgb
                image.SetSpriteColor(rgb)

    def clip(self, ratio):
        ratio = round(ratio, 3)
        if ratio != self._clip:
            image = self._image()
            if image is not None:
                self._clip = ratio
                image.SetSpriteClipRatio(ratio)

    def uv(self, origin, size):
        """只画贴图里的一块（贴图像素）：左上角 origin、大小 size。"""
        if (origin, size) != self._uv:
            image = self._image()
            if image is not None:
                self._uv = (origin, size)
                image.SetSpriteUVSize(size)
                image.SetSpriteUV(origin)


class _DecorViews(object):
    """
    一格的装饰控件（Std/Decor）：底色、占位图标、从下往上的一层、底边的横条、锁住的样子、右下角的小图标。第一次画装饰时才建。
    占位图标有帧时（Decoration.frames）从显示它那一刻起按时间轮流显示各帧：界面每帧调 animate。
    """

    __slots__ = ("tint", "placeholder", "fill", "line", "lock", "badge", "_frames", "_since")

    def __init__(self, screen, view):
        path = view.path
        self.tint = _Image(screen, path + view.DECOR_TINT)
        self.placeholder = _Image(screen, path + view.DECOR_PLACEHOLDER)
        self.fill = _Image(screen, path + view.DECOR_FILL)
        self.line = _Image(screen, path + view.DECOR_LINE)
        self.lock = Placed(screen, path + view.DECOR_LOCK, visible=False)
        self.badge = _Image(screen, path + view.DECOR_BADGE)
        self._frames = None   # (贴图, 帧) 正在轮流显示的占位图标
        self._since = 0.0

    def show(self, decoration, now):
        self.tint.setVisible(decoration.tint is not None)
        if decoration.tint is not None:
            self.tint.color(decoration.tint)
        self.placeholder.setVisible(decoration.placeholder is not None)
        if decoration.placeholder is not None:
            self.placeholder.sprite(decoration.placeholder)
        frames = (decoration.placeholder, decoration.frames) if decoration.placeholder and decoration.frames else None
        if frames != self._frames:
            self._frames, self._since = frames, now
            self.animate(now)
        bar = decoration.bar
        for style, image in (("fill", self.fill), ("line", self.line)):
            shown = bar is not None and bar[0] == style
            image.setVisible(shown)
            if shown:
                image.clip(1.0 - bar[1])   # 裁掉没满的那一截（fill 从下往上、line 从左往右留）
                image.color(bar[2])
        self.lock.setVisible(decoration.locked)
        if decoration.badge is not None:
            self.badge.setVisible(bool(decoration.badge))
            if decoration.badge:
                self.badge.sprite(decoration.badge)

    def animated(self):
        return self._frames is not None

    def animate(self, now):
        """占位图标有帧时显示现在该显示的那一帧。"""
        if self._frames is not None:
            count, size, fps = self._frames[1]
            index = int((now - self._since) * fps) % count if count > 1 else 0
            self.placeholder.uv((index * size, 0), (size, size))

    def hide(self):
        self._frames = None
        for view in self.controls():
            view.setVisible(False)

    def controls(self):
        return [self.tint, self.placeholder, self.fill, self.line, self.lock, self.badge]


class SlotView(Placed, ItemView):
    """
    一个格子：图标、数量、耐久条、锁图标与锁定底格、触屏选中（底格与框、选好数量的进度条）、悬停高亮与悬停文本、
    停用底格。position 是格子在 JSON 里的初始位置。各部分在格子模板里的子路径是类属性（库的格子模板的写法，见 Client/Paths；
    DECOR_ 开头的是格子装饰用的几样）：自己写格子模板时派生它改这几项，格子区的 viewClass 写派生的类；各部分的初始显隐照库的
    格子模板（控件按它省掉没变的显隐）。界面经这些方法画格子：show、setSelected、setDisabled、
    decorate / animated / animate、setTip、setHoverVisible，记 drawn、fresh（Client/Widgets.redrawSlot）。
    """

    RENDERER = Paths.SLOT_RENDERER
    COUNT = Paths.SLOT_COUNT
    DURABILITY = Paths.SLOT_DURABILITY
    STORAGE_BAR = Paths.SLOT_STORAGE
    LOCK = Paths.SLOT_LOCK
    CELL = Paths.SLOT_CELL
    CELL_SELECTED = Paths.SLOT_CELL_SELECTED
    SELECTED = Paths.SLOT_SELECTED
    SELECTED_PROGRESS = Paths.SLOT_SELECTED_PROGRESS
    LOCK_CELL = Paths.SLOT_LOCK_CELL
    DISABLED = Paths.SLOT_DISABLED
    HOVER = Paths.SLOT_HOVER
    HOVER_PARTS = Paths.SLOT_HOVER_PARTS
    TIP = Paths.SLOT_TIP
    DECOR_TINT = Paths.SLOT_DECOR_TINT
    DECOR_PLACEHOLDER = Paths.SLOT_DECOR_PLACEHOLDER
    DECOR_FILL = Paths.SLOT_DECOR_FILL
    DECOR_LINE = Paths.SLOT_DECOR_LINE
    DECOR_LOCK = Paths.SLOT_DECOR_LOCK
    DECOR_BADGE = Paths.SLOT_DECOR_BADGE
    DECOR_RENDERER = Paths.SLOT_DECOR_RENDERER

    def __init__(self, screen, path, position=None):
        Placed.__init__(self, screen, path, visible=True, position=position)
        ItemView.__init__(self, screen, path + self.RENDERER, path + self.COUNT,
                          path + self.DURABILITY, path + self.STORAGE_BAR, path + self.LOCK,
                          rendererVisible=True)
        self.cell = Placed(screen, path + self.CELL, visible=True)
        self.cellSelected = Placed(screen, path + self.CELL_SELECTED, visible=False)
        self.selectedFrame = Placed(screen, path + self.SELECTED, visible=False)
        self.selectedProgress = ProgressBar(screen, path + self.SELECTED_PROGRESS)
        self.lockCell = Placed(screen, path + self.LOCK_CELL, visible=False)
        self.disabledCell = Placed(screen, path + self.DISABLED, visible=False)
        self.home = position   # 格子区给的位置（装饰的布局挪走过、又不在布局里时摆回来）
        self._decor = None     # 装饰控件（_DecorViews），第一次画装饰时才建
        self._cellImage = None   # 底格的贴图（装饰第一次换底格时才建）
        self._renderer = None    # 布局加的自定义渲染器（装饰第一次写属性包时才要）与写过的属性包
        self._bag = None
        self.dimmed = False      # 图标画暗（格子装饰的 dim）：格子组件写了 $dc_dim_icon 时，格子区按它答引擎的绑定
        self.drawn = None        # 上一次画的（格子、物品堆、选中、显示设置；Widgets.redrawSlot 比对它），None 为下次要画
        self.fresh = True        # 这一次重画画了它（界面只给画了的格子重算格子装饰）
        self.hoverParts = [Placed(screen, path + self.HOVER + part, visible=True) for part in self.HOVER_PARTS]
        self._tipControl = Lazy(screen, path + self.TIP)
        known = _KNOWN[0]
        self._tip = "" if known else None                        # JSON 里悬停文本的初始值
        self._selected = (False, None, None) if known else None

    def show(self, stack, context, showLocks=True):
        mode = self.showItem(stack, context, showLocks)
        self.lockCell.setVisible(mode != Items.LOCK_NONE)

    def setSelected(self, selected, amount=None, total=None):
        """触屏选中：底格换成选中底格、套上选中框；选好了数量时框上显示数量占整堆的比例。"""
        state = (selected, amount, total)
        if state == self._selected:
            return
        self._selected = state
        self.cell.setVisible(not selected)
        self.cellSelected.setVisible(selected)
        self.selectedFrame.setVisible(selected)
        if selected and amount:
            self.selectedProgress.show(total, amount)
        else:
            self.selectedProgress.hide()

    def setDisabled(self, disabled):
        """停用的格子（格子类型的 isActive 为假）盖一层停用底格。"""
        self.disabledCell.setVisible(disabled)

    def decorate(self, decoration, now=0.0):
        """
        格子装饰（Std/Decor 的 Decoration，在 show 之后调用；None 为没有装饰）：底色、占位图标、覆盖条、锁住的样子、
        数量的写法、按布局摆的位置与显隐（只对固定的格子区）。now 是界面的时间（有帧的占位图标从这时起轮流显示）。
        """
        views = self._decor
        if decoration is None:
            if views is not None:
                views.hide()
            self.dimmed = False
            return
        if views is None:
            views = self._decor = _DecorViews(self._screen, self)
        views.show(decoration, now)
        if decoration.count is not None:
            self._setCount(decoration.count)
        if decoration.position is not None:
            self.place(*decoration.position)
        elif self.home is not None and decoration.visible is not None:
            self.place(*self.home)
        if decoration.visible is not None:
            self.setVisible(decoration.visible)
        if decoration.cell is not None:
            if self._cellImage is None:
                self._cellImage = _Image(self._screen, self.path + self.CELL)
            self._cellImage.sprite(decoration.cell)
        if decoration.dim is not None:
            self.dimmed = bool(decoration.dim)
        if decoration.renderer is not None and decoration.renderer != self._bag:
            if self._renderer is None:
                self._renderer = Lazy(self._screen, self.path + self.DECOR_RENDERER)
            control = self._renderer.get()
            if control is not None:
                control.SetPropertyBag(decoration.renderer)
                self._bag = dict(decoration.renderer)

    def animated(self):
        """装饰里有轮流显示的占位图标（界面每帧调 animate）。"""
        return self._decor is not None and self._decor.animated()

    def animate(self, now):
        if self._decor is not None:
            self._decor.animate(now)

    def setHoverVisible(self, visible):
        """原版触屏下不显示悬停高亮（连同挂在高亮下的悬停文本）。"""
        for part in self.hoverParts:
            part.setVisible(visible)

    def setTip(self, text):
        """悬停文本：只在按钮处于悬停态（指针在上面或手柄焦点在这里）时由引擎画出来。"""
        if text != self._tip:
            control = self._tipControl.get()
            if control is not None:
                self._tip = text
                control.SetPropertyBag({"#hover_text": text})

    def controls(self):
        """所有子控件（测试用：逐个向引擎要一遍，核对路径都在）。"""
        return [self, self.renderer, self.durability.placed, self.storage.placed, self.lockYellow, self.lockRed,
                self.cell, self.cellSelected, self.selectedFrame, self.selectedProgress.placed, self.lockCell,
                self.disabledCell] + _DecorViews(self._screen, self).controls() \
            + self.hoverParts + [self._countLabel, self._tipControl]


class CursorView(ItemView):
    """
    跟随指针的部分：手持物（图标、数量、锁图标、耐久条、收纳袋容量条）、渐进拿取进度条。子控件按这块的边长写比例：整屏按
    比例缩放的布局里按比例改这块的边长（scale），手上的东西与格子里的一样大。
    """

    SIZE = 16.0   # 这块在界面文件里的边长（tools/gen_ui.py 的 CURSOR_SIZE）

    def __init__(self, screen):
        ItemView.__init__(self, screen, Paths.CURSOR_RENDERER, Paths.CURSOR_COUNT, Paths.CURSOR_DURABILITY,
                          Paths.CURSOR_STORAGE, Paths.CURSOR_LOCK, rendererVisible=True)
        self.icon = Placed(screen, Paths.CURSOR_ICON, visible=False)
        self.hold = ProgressBar(screen, Paths.CURSOR_HOLD)
        self._follower = Lazy(screen, Paths.CURSOR)
        self._half = None   # (跟随控件, 半宽, 半高)：量到一次就记着，按比例改边长时跟着换
        self._scale = 1.0   # 这块的边长是界面文件里的几倍

    def scale(self, scale):
        """按比例改这块的边长（子控件跟着缩），数量字的字号跟着；按指针算中心用的半宽、半高跟着换。"""
        if scale == self._scale:
            return
        follower = self._follower.get()
        if follower is None:
            return
        size = self.SIZE * scale
        follower.SetFullSize("x", _absolute(size))
        follower.SetFullSize("y", _absolute(size))
        self.scaleFont(scale)
        self._half = (follower, size / 2.0, size / 2.0)
        self._scale = scale

    def show(self, stack, context, showLocks=True):
        self.icon.setVisible(not Items.isEmpty(stack))
        self.showItem(stack, context, showLocks)

    def showProgress(self, progress):
        """渐进拿取：(格, 数量, 总数)；没有时为 None。"""
        if progress is None:
            self.hold.hide()
        else:
            self.hold.show(progress[2], progress[1])

    def position(self):
        """指针的界面坐标：跟随控件居中在指针上，取它的中心（手柄虚拟光标也会带着它走）。"""
        follower = self._follower.get()
        if follower is None:
            return None
        x, y = follower.GetGlobalPosition()
        half = self._half
        if half is None or half[0] is not follower:
            width, height = follower.GetSize()
            half = (follower, width / 2.0, height / 2.0)
            if width > 0 and height > 0:
                self._half = half
        return (x + half[1], y + half[2])
