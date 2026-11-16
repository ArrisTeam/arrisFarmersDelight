# -*- coding: utf-8 -*-
"""
布局表（docs/LAYOUTS.md）。tools/layouts.py 把使用方的布局源文件编译成界面文件与绑定表，绑定表是脚本根下的
dolorLayouts.py：布局名 -> 界面模型、两套界面（经典版 classic、携带版 pocket）的屏幕定义名、运行时控件
（控件名、参数与路径，Client/Widgets.py）、写文字的控件与具名控件（布局里 $dc_name 标的）的路径、用到的控件不在
标准控件模块里时登记它们的库模块（imports：第一次取这个布局时载入，Common/Modules.py）。
界面模型的 layout 指明用哪个布局。绑定表带格式版本：旧版编译工具生成的表不认（重新编译），这时没有布局可用。

界面扩展（docs/ARCHITECTURE.md 第 3.11 节）是只属于某个布局的客户端行为（例如面板随格数长高、滚动条侧栏）：
一个继承 ScreenExtension 的类，按布局名登记（registerExtension，客户端导入登记它的模块时登记）。它跟着界面的视图对象
一起建、一起被引擎的界面缓存复用；界面打开、每帧、关闭时被调用。它按名字拿控件（parts.path(名字)），不需要知道库内部的路径。
别的模块往这个布局里加东西时（C66，编译时加控件见 Common/Components.extendLayout）用 addExtension 叠加界面扩展：
布局自己的与叠加的串起来调用（Stacked）。

按布局换类（客户端导入登记它们的模块时登记，界面初始化之前）：registerScreenClass(布局名, 类的全名) 换界面类（派生
Client/Screen.ContainerScreen，加自己的输入绑定）；registerGestures(布局名, 类) 换手势识别（派生 Client/Gestures.Gestures）；
registerDisplay(布局名, 类) 换物品显示（派生 Client/Display.Context：数量字、耐久条、容量条、图标的附加参数）。
"""
import collections
import re

from ..Common import Modules

PROFILES = ("classic", "pocket")
QUIET = "_quiet"
TABLE_VERSION = 3   # 认的绑定表格式（tools/layouts.py 的 TABLE_VERSION）
_cache = [None]
_problem = [None]
_extensions = {}   # 布局名 -> 界面扩展类（布局自己的）
_added = {}        # 布局名 -> {类的全名: 类}：别的模块叠加的界面扩展，按登记的先后
_screenClasses = {}    # 布局名 -> 界面类的全名
_gestureClasses = {}   # 布局名 -> 手势识别类
_displayClasses = {}   # 布局名 -> 物品显示类


def _table():
    if _cache[0] is None:
        try:
            from ... import dolorLayouts
        except ImportError:
            _cache[0] = {}
            return _cache[0]
        version = getattr(dolorLayouts, "VERSION", 1)
        if version != TABLE_VERSION:
            _problem[0] = "layout table format %r is not %r: run tools/layouts.py again" % (version, TABLE_VERSION)
            _cache[0] = {}
        else:
            _cache[0] = dict(dolorLayouts.LAYOUTS)
    return _cache[0]


def problem():
    """绑定表用不了的原因（格式不对）；没有问题时为 None。"""
    _table()
    return _problem[0]


def get(name):
    """布局名对应的布局（没有编译进来时为 None）；先载入它用到的控件模块（imports，只载入一次）。"""
    layout = _table().get(name) if name else None
    if layout is not None:
        Modules.loadAll(layout.get("imports"))
    return layout


def screenKey(name, profile):
    """登记界面用的键（只用字母、数字与下划线）。"""
    return "%s_%s" % (re.sub(r"[^0-9A-Za-z]", "_", name), profile)


def screens():
    """
    全部要登记的屏幕：[(登记键, 屏幕定义名)]。每个屏幕还有一份不带进入动画的孪生屏幕（切换到别的布局时推它），
    登记键是界面档后面接 _quiet。
    """
    return [entry for name in names() for entry in screensOf(name)]


def names():
    """编译进来的布局名。"""
    return sorted(_table())


def screensOf(name):
    """布局 name 要登记的屏幕：[(登记键, 屏幕定义名)]（两套界面档，各带不带进入动画的孪生屏幕）。"""
    layout = _table().get(name)
    out = []
    for profile in PROFILES:
        screen = layout["screens"].get(profile) if layout else None
        if screen is not None:
            out.append((screenKey(name, profile), screen["screen"]))
            if screen.get("quiet"):
                out.append((screenKey(name, profile + QUIET), screen["quiet"]))
    return out


def registerScreenClass(layoutName, classPath):
    """
    给布局换界面类（类的全名，引擎按它建屏幕；要派生 Client/Screen.ContainerScreen）：加自己的输入绑定（ViewBinder 的
    按钮名、引擎的按键映射）。界面初始化（登记屏幕）之前登记。
    """
    _screenClasses[layoutName] = classPath
    return classPath


def screenClass(layoutName):
    """布局换过的界面类的全名（没换过为 None）。"""
    return _screenClasses.get(layoutName)


def registerGestures(layoutName, gesturesClass):
    """给布局换手势识别类（派生 Client/Gestures.Gestures；打开这种界面时建它）。返回类。"""
    _gestureClasses[layoutName] = gesturesClass
    return gesturesClass


def gesturesClass(layoutName):
    return _gestureClasses.get(layoutName)


def registerDisplay(layoutName, displayClass):
    """给布局换物品显示类（派生 Client/Display.Context：数量字、耐久条、容量条的写法）。返回类。"""
    _displayClasses[layoutName] = displayClass
    return displayClass


def displayClass(layoutName):
    return _displayClasses.get(layoutName)


def widgetNames(layout):
    """布局的两套界面用到的控件名。"""
    return set(spec["widget"] for screen in layout["screens"].values() for spec in screen["widgets"])


def registerExtension(layoutName, extensionClass):
    """给布局登记界面扩展（同名的新登记替换旧的：重新载入时）。返回扩展类，可以当类装饰器的内层用。"""
    _extensions[layoutName] = extensionClass
    return extensionClass


def addExtension(layoutName, extensionClass):
    """
    给布局叠加一个界面扩展（C66：别的模块往别人的布局里加东西时用；布局自己的用 registerExtension）。叠加的与布局自己的
    一起调用：布局自己的在前，叠加的按登记的先后。同一个类（模块与类名相同）再登记一次替换前一次（重新载入时）。返回扩展类。
    """
    added = _added.setdefault(layoutName, collections.OrderedDict())
    added["%s.%s" % (extensionClass.__module__, extensionClass.__name__)] = extensionClass
    return extensionClass


def extensionClass(layoutName):
    """
    布局的界面扩展类：只有布局自己的就是它；有叠加的就是把它们串起来的组合（parts -> Stacked）；都没有时为 None。
    """
    own = _extensions.get(layoutName)
    added = list((_added.get(layoutName) or {}).values())
    if not added:
        return own
    classes = [own or ScreenExtension] + added
    return lambda parts: Stacked(parts, classes)


class ScreenExtension(object):
    """
    界面扩展。parts 是这一套界面的视图对象（Screen._Parts）：parts.path(名字) 给出布局里 $dc_name 标的控件路径，
    parts.panes 是各个格子区。下面的方法都可以不写。
    """

    def __init__(self, parts):
        self.parts = parts

    def open(self, screen, counts):
        """界面打开（第一次重画之前）。counts 是各个格子区现在显示的格数。"""

    def frame(self, screen, now, counts):
        """每个渲染帧，在格子区同步之前。"""

    def contentLimit(self, paneName):
        """格子区内容高度的上限（None 为不限）。"""
        return None

    def detailsOffset(self, screen):
        """触屏物品详情离底边的距离（原版：只有大箱子贴底，其余界面都在 16 处）。"""
        return -16

    def effect(self, screen, kind, value):
        """手势识别（格子的交互）留下的一次性效果里界面不认识的（自定义的种类）：接了返回 True。"""
        return False

    def close(self, screen):
        """界面关闭。"""



class Stacked(ScreenExtension):
    """
    几个界面扩展串起来（布局自己的在前，addExtension 叠加的在后）：open、frame、close 依次调用；内容高度上限取最小的；
    物品详情的位置听布局自己的。members 是各个扩展对象。
    """

    def __init__(self, parts, classes):
        ScreenExtension.__init__(self, parts)
        self.members = [cls(parts) for cls in classes]

    def open(self, screen, counts):
        for member in self.members:
            member.open(screen, counts)

    def frame(self, screen, now, counts):
        for member in self.members:
            member.frame(screen, now, counts)

    def contentLimit(self, paneName):
        found = None
        for member in self.members:
            limit = member.contentLimit(paneName)
            if limit is not None and (found is None or limit < found):
                found = limit
        return found

    def detailsOffset(self, screen):
        return self.members[0].detailsOffset(screen)

    def effect(self, screen, kind, value):
        return any(member.effect(screen, kind, value) for member in self.members)

    def close(self, screen):
        for member in self.members:
            member.close(screen)
