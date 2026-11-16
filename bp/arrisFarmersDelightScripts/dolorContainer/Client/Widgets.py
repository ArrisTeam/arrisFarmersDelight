# -*- coding: utf-8 -*-
"""
运行时控件（docs/ARCHITECTURE.md 第 3.10 节）：界面按布局绑定表（Client/Layouts.py）里的每一项建一个控件对象，
按绑定里的控件名找控件类。控件类按名字登记；库带的在 Std/Client/Widgets.py（按行回收的格子区在 Std/Windowed/Client.py），
使用方的名字带命名空间，客户端导入登记它们的模块。布局里怎么写、编译时记下什么见 Common/Components.py。

界面对控件的调用（Client/Screen.py）：
- 建：cls(screen, path, spec)。screen 是向引擎要控件用的界面（Views.ScreenHandle），path 是控件的完整路径，spec 是绑定。
  控件对象跟着引擎的界面缓存复用（同一个屏幕定义一套），所以建的时候不碰会话；
- open(model)：界面打开（每次推入），model 是这次的客户端会话（Client/Service.ClientSession），控件只用它的公开部分：
  值：value(名字, 时间)（界面数据、每位查看者的状态、客户端界面状态依次找）、dataValue、viewerValue、clientValue、
  setClientValue、setEditing / clearEditing；格子：displayed(格)（算上预测与手势的预览）、size(集合)（现在显示几格）、
  contents(容器) / predictedSlots(容器)
  （容器显示的格子与还没应答的预测）、syncOf(容器)（容器的同步方式）、heldRef()（手上那一格）、hovered()（悬停的格）；
  界面模型与结构：menu、structure、rules（物品规则）；输入：device()（输入方式）、pointer()（这一帧的指针）、
  do(操作)（发格子操作）、call(动作名, 参数)（发动作）、memory(主人)（跨手势记的东西）；文字与物品：text(键)、
  itemName(物品)、plainItemName、hoverText(物品)、idAuxOf；声音：playSound(名字, 音量)；时间：now()；修订号：revision()
  （显示内容、界面数据、客户端界面状态哪样变了哪个加一，控件按它判断这一帧要不要重算）；界面：display（这个布局的物品显示）、
  pushScreen(命名空间, 名字, 参数)（在交互回调里调时等这一下抬起再推）、requestClose()、showDetails(字)（在屏幕底部的物品详情处弹一段字）、log(字)、refusedWords / noteRefusedWords()（文本框的字含敏感词的次数）、
  uiScale()（整屏按比例缩放的布局缩到了几倍）；
  frame(now)：每个渲染帧（只调改写了它的控件；所在的面板关着时不调，开了接着调）；
  onScale(scale)：整屏按比例缩放的布局缩放的比例变了（界面已经按比例给布局里的标签设好了字号、把经 Placed 摆过的位置与
  尺寸重新下发了；只调改写了它的控件）；
  remember()：会话写回客户端界面状态之前（关界面、被关掉、换会话）：控件把自己要记的写进客户端界面状态（滚动的控件记
  滚动位置），列进 savedClientState 的跟着写进配置；
  close()：界面关闭，把会影响下次推入的部分摆回 JSON 初始的样子；
- onInput(event)：控件下面映射到 #dc.widget 的按钮按下或抬起，控件里的按钮照原版"交互"时机被按下，控件里的文本框改了
  文字、输入结束，滑块动了（见 onInput）；后三种按名字接上：控件里有哪些由 presses、textBoxes、sliders 给出（按钮的
  $pressed_button_name、文本框的 text_box_name、滑块的 slider_name），界面打开时接上；
- bind(binder)：每个引擎屏幕一次（推入时），控件向引擎登记按名字的绑定与原版下拉（见 bind）。
控件发动作（Common/Actions）用 call(动作名, 参数)；按钮类控件的动作名与参数写在布局里，编译时核对（Common/Components）。
显示格子的控件继承 SlotArea：界面经它的接口把悬停、焦点、按钮事件换成格子引用，画格子与收纳袋张开的样子；画格子用
redrawSlot（与上一次画的一样的不动），挪动格子控件、改显隐之后 forgetDrawn。
"""
from ..Common import Items
from . import Views

_registry = {}


def register(name, widgetClass):
    """登记控件类（同名的新登记替换旧的：重新载入时）。返回它，可以当类装饰器的内层用。"""
    _registry[name] = widgetClass
    return widgetClass


def get(name):
    return _registry.get(name)


def missing(names):
    """names 里还没有登记的控件名（排好序）。"""
    return sorted(set(name for name in names if name not in _registry))


class Widget(object):
    """运行时控件的基类：下面的方法都可以不写。"""

    def __init__(self, screen, path, spec):
        self.screen = screen
        self.path = path
        self.spec = spec
        self.name = spec.get("name")
        self.model = None

    def open(self, model):
        """界面打开（第一次重画之前）：记下这次的会话。"""
        self.model = model

    def frame(self, now):
        """每个渲染帧（格子区同步之后）。"""

    def remember(self):
        """会话写回客户端界面状态之前：把控件自己要记的（滚动位置这类）写进客户端界面状态（setClientValue）。"""

    def close(self):
        """界面关闭。"""

    def onInput(self, event):
        """
        输入，处理完界面当场重画。event["kind"] 是哪一种：
        - "button"：控件下面映射到 #dc.widget 的按钮，{"down": 按下还是抬起, "path": 按钮相对控件的路径,
          "position": 触点位置（不是触屏为 None）}；
        - "press"：控件里的按钮（presses 给的名字）照原版"交互"时机报一次（键鼠与手柄在按下时、触屏在抬起且没拖动时），
          {"name": 按钮名}；
        - "text"：控件里的文本框（textBoxes 给的名字），{"box": 名字, "text": 框里现在的字（str）,
          "finished": 输入结束（点到别处、回车或 ESC 让文本框失去选中、触屏键盘收起）, "enter": 按了回车（还没结束）}。
          要提交到服务端的文本框（textBoxes 里标了 submit）输入结束时，含敏感词的字已经被引擎换成 ***；
        - "slider"：控件里的滑块（sliders 给的名字），{"name": 名字, "value": 滑块现在的值（分格的滑块是格序号，0 起）,
          "finished": 这一下动完了（松手、点了轨道、手柄左右键的一步；拖动中的为假）}；
        - "clear"：点了控件里原版文本框的清空按钮（$text_clear_button_enabled，按下时报一次）。
        """

    def presses(self):
        """
        控件里照原版"交互"时机报的按钮：[名字, ...]，名字是按钮的 $pressed_button_name（同一个屏幕里不重名；引擎的交互事件
        里没有按钮路径，按名字分）。没有的控件不写。
        """
        return ()

    def textBoxes(self):
        """
        控件里的文本框：[(名字, submit), ...]。名字是 JSON 里文本框的 text_box_name（同一个屏幕里不重名）；
        submit 为真的文本框的字要发给服务端（输入结束时由引擎按敏感词换掉）。没有文本框的控件不写。
        """
        return ()

    def sliders(self):
        """控件里的滑块：[名字, ...]，名字是 JSON 里滑块的 slider_name（同一个屏幕里不重名）。没有的控件不写。"""
        return ()

    def onEffect(self, kind, value):
        """
        格子的交互留下的一次性效果里界面与界面扩展都不认识的（自定义的种类，g.effects.append((种类, 值))）：控件要就处理并
        返回真（依次问，第一个接了的为准）。
        """
        return False

    def onScale(self, scale):
        """
        整屏按比例缩放的布局（$dc_fit）缩放的比例变了（scale 是框的实际高 / 设计高）：界面已经按比例给布局里的标签设好了
        字号（原有的字号倍数乘上它），经 Views.Placed 摆过的位置与尺寸（按设计像素写）也按新的比例重新下发了。自己另调字号的
        标签、用 SetPosition 这类直接摆的控件在这里重设。从引擎读的尺寸与位置是界面像素，除以 self.screen.scale 才是设计像素。
        只调改写了它的控件。
        """

    def onWheel(self, up, pointer):
        """
        滚轮（经典版的界面才有；up 为真是向上），pointer 是指针的界面坐标（取不到时为 None）。控件要这一下（例如指针在
        分页的列表上）就处理并返回真；都不要时交给手势（悬停收纳袋时在提示里选上一项、下一项）。
        """
        return False

    def bind(self, binder):
        """
        向引擎登记按名字的绑定（引擎每次更新控件时向这边要值）与原版下拉（开合与单选由引擎做）。每个引擎屏幕调一次
        （推入时；登记随引擎的屏幕弹出失效，不用撤）。binder 的方法（Client/Screen.py 的 _Binder）：
        - string(绑定名, 取值函数)、boolean(绑定名, 取值函数)：JSON 里按这个名字绑定的控件属性（文字、#visible 等）；
        - dropdown(下拉名, 单选项名的列表, selected, picked)：原版下拉（$dropdown_name 是下拉名，第 k 项单选项的开关状态
          绑定名是列表里第 k 个）；selected() 给出选中第几项（没有为 -1），玩家选了第 k 项时调 picked(k)。
        取值函数在引擎更新控件时调用，不该抛出异常（抛了记一行日志、按缺省值）。用不着的控件不写。
        """

    def call(self, name, args=(), done=None):
        """
        发动作：args 是线上写法的参数，done(成没成, 返回值) 在应答到了时调用（没成时第二个参数是错误码）。界面没开着时不发。
        返回发了没有。
        """
        model = self.model
        return model is not None and model.call(name, args, done)


def indexAfter(path, prefix):
    """path 里紧跟在 prefix 后面的数字（prefix 不在 path 里时为 None）。"""
    position = path.find(prefix)
    if position < 0:
        return None
    digits = ""
    for char in path[position + len(prefix):]:
        if not char.isdigit():
            break
        digits += char
    return int(digits) if digits else None


def showSlot(view, stack, selection, context, showLocks, releaseBar):
    """在格子控件上画一格：物品，触屏选中时的框与选好的数量。总是画；按上一次画的比对着画用 redrawSlot。"""
    view.fresh, view.drawn = True, None
    view.show(stack, context, showLocks)
    if selection is not None:
        view.setSelected(True, selection["amount"] if releaseBar else None, Items.count(stack))
    else:
        view.setSelected(False)


def redrawSlot(view, ref, stack, selection, context, showLocks, releaseBar):
    """
    在格子控件上画格子 ref（显示 stack）；与这个控件上一次画的一样（同一格、同样的物品堆、选中与显示设置都一样）时不动。
    返回这次画了没有，也记在控件的 fresh 上（界面只给画了的格子重算格子装饰）。物品堆按值比：镜像里的物品堆不就地改，
    没变的是同一个对象，一比就过。格子装饰还依赖界面数据：数据变了时界面先用 forgetDrawn 让整片重画。
    """
    state = (ref, stack, selection, context, showLocks, releaseBar)
    if state == getattr(view, "drawn", None):
        view.fresh = False
        return False
    showSlot(view, stack, selection, context, showLocks, releaseBar)
    view.drawn = state
    return True


def forgetDrawn(views):
    """这些格子控件下一次都重画（挪了位置、显隐变了，或格子装饰依赖的界面数据变了）。"""
    for view in views:
        view.drawn = None


def selectionFor(selection, ref):
    return selection if selection and selection["ref"] == ref else None


class SlotArea(Widget):
    """
    格子区：显示集合 collection 的格子。绑定里有 collection、slot（格子边长）、split（触屏选数量条的方向，可以没有）、
    columns（列数，可以没有）、placeholder（格子装饰的占位图标换成这张贴图，可以没有）。属性 views 是格子控件（viewClass 建的，
    缺省 Views.SlotView：自己写了格子模板的格子区派生 SlotView 改子路径，viewClass 写它），revision 在格子区的样子变了时加一
    （要重画），bundleOpen 是收纳袋张开的覆盖层（没有时为 None）。
    """

    viewClass = Views.SlotView

    def __init__(self, screen, path, spec):
        Widget.__init__(self, screen, path, spec)
        self.collection = spec["collection"]
        self.split = spec.get("split")
        self.slot = spec["slot"]
        self.columns = spec.get("columns")
        self.placeholder = spec.get("placeholder")
        self.revision = 0
        self.views = []
        self.bundleOpen = None

    def onScale(self, scale):
        """格子的数量字按比例设字号（四个字的短写法另改小，见 Views.ItemView.scaleFont）。"""
        for view in self.views:
            view.scaleFont(scale)

    def covers(self, ref):
        """格子 ref 在不在这个格子区里。"""
        raise NotImplementedError

    def indexIn(self, ref):
        """格子在格子区网格里排第几（按列数从左上数）。"""
        raise NotImplementedError

    def positionOf(self, ref):
        """格子在覆盖层所在的那个父控件里的位置（此刻不显示它时为 None）。"""
        raise NotImplementedError

    def indexOf(self, path):
        """按钮路径 path 是第几个格子控件的（不是这个格子区的为 None）。"""
        raise NotImplementedError

    def refAt(self, index):
        """第 index 个格子控件此刻显示的格子（没有时为 None）。"""
        raise NotImplementedError

    def sync(self, count, limit=None):
        """每帧：集合现在显示 count 格，limit 是内容高度的上限（None 为不限）。返回有没有要重画的变化。"""
        return False

    def wanted(self):
        """要显示集合的哪一段：(集合, 起, 止)；格子都在界面上的不用报。"""
        return None

    def render(self, displayed, selection, context, showLocks, releaseBar):
        """画格子：displayed(ref) 给出显示的物品堆，selection 是触屏选中。返回 {格子引用: 格子控件}。"""
        raise NotImplementedError

    def setHoverVisible(self, visible):
        """原版触屏下不显示悬停高亮。"""
        for view in self.views:
            view.setHoverVisible(visible)
