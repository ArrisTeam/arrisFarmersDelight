# -*- coding: utf-8 -*-
"""
界面数据的字段类型（docs/ARCHITECTURE.md 第 3.8 节）：服务端算出的值怎么上线、客户端怎么读回来。纯逻辑，两端共用。

界面模型用 data = {名字: 字段类型} 声明界面数据；服务端的 dataValues(实例) 给出原始值，会话按类型编码（encode），
跟上次发的比，变了才发（会动的数每次都发，见 again）；客户端按类型解码（decode），控件读值时由类型给出"现在"的值
（current：会动的数按时间往前算）。

这里有布尔、整数、长整数、浮点、枚举、文字、可本地化的文字（客户端按玩家的语言拼）、物品、资源（流体、化学品、能量：名字、
数量、容量）、会动的数、列表与映射（整份或增量发送）、每格数据（集合里格子的值，给格子的装饰用）。字段的范围：SHARED（同一实例的查看者看到同一份，界面模型的
dataValues 算）、VIEWER（每位查看者各一份，viewerValues 按查看者算）、PANEL（属于一个面板，dataValues 算，面板对这位查看者
开着才发，关了再开时整份补发）。
发法：服务端每次把原始值编码（encode），跟上次发的线上值比，变了才发；发的写法由字段类型的 message 给（缺省就是线上值，
增量的列表与映射只发改动），客户端用 receive 把它变成值（增量的接在现在的值上）。
界面模型声明的每位查看者的状态（Menu.viewerState）也用这些类型编解码（整份发送）。
"""
import re

from . import Items

SHARED = "shared"
VIEWER = "viewer"
PANEL = "panel"
TICKS_PER_SECOND = 20
MISSING = object()   # 服务端还没发过这个字段（第一次、面板关了再开）：message 的 previous

try:
    _TEXT = (str, unicode)  # noqa: F821
    _NUMBERS = (int, long, float)  # noqa: F821
except NameError:
    _TEXT = (str,)
    _NUMBERS = (int, float)


def _str(value):
    """py2 下 unicode 编成 utf-8 的 str（引擎的文本接口只收 str）。"""
    return value if isinstance(value, str) else value.encode("utf-8")


class Field(object):
    """
    字段类型的基类。empty 是客户端还没收到值时读到的；scope 是范围（SHARED、VIEWER 或 PANEL）。
    子类改写 encode / decode，需要时改写 again（同样的线上值也要再发）与 current（客户端读到的"现在"的值）。
    """

    empty = None

    def __init__(self, scope=SHARED):
        if scope not in (SHARED, VIEWER, PANEL):
            raise ValueError("data field scope must be SHARED, VIEWER or PANEL: %r" % (scope,))
        self.scope = scope

    def encode(self, value):
        """服务端：原始值 -> 线上的值（只有简单值）。"""
        return value

    def decode(self, wire):
        """客户端：线上的值 -> 值。不合格时抛 TypeError / ValueError（客户端丢掉这一项）。"""
        return wire

    def again(self, wire):
        """线上的值和上次发的一样时还要不要再发。"""
        return False

    def message(self, previous, wire):
        """服务端：这次发给客户端的写法。previous 是上次发的线上值（没发过时为 MISSING）；缺省整份发。"""
        return wire

    def receive(self, current, message):
        """客户端：收到的写法 -> 值。current 是现在的值（还没收到过时为 None）；缺省整份解码。"""
        return self.decode(message)

    def forPart(self, rename):
        """部件声明的字段并进界面模型时：字段里引用的名字（集合名）按部件的前缀改（rename(本地名) -> 名字）；缺省不变。"""
        return self

    def current(self, value, received, now):
        """客户端：received 时刻收到的值在 now 时刻是多少。"""
        return value


class Bool(Field):
    empty = False

    def encode(self, value):
        return bool(value)

    def decode(self, wire):
        return bool(wire)


class Int(Field):
    empty = 0

    def encode(self, value):
        return int(value)

    def decode(self, wire):
        if isinstance(wire, bool) or not isinstance(wire, _NUMBERS):
            raise TypeError("not a number: %r" % (wire,))
        return int(wire)


class Long(Int):
    """长整数（能量这类可能超过 32 位的）：上线的写法同整数。"""


class Float(Field):
    empty = 0.0

    def __init__(self, digits=6, scope=SHARED):
        Field.__init__(self, scope)
        self.digits = digits

    def encode(self, value):
        return round(float(value), self.digits)

    def decode(self, wire):
        return float(wire)


class Enum(Field):
    """几个取值之一（数或文字）；客户端收到不认识的值时当作第一个。"""

    def __init__(self, values, scope=SHARED):
        Field.__init__(self, scope)
        if not values:
            raise ValueError("an enum needs values")
        self.values = tuple(_str(value) if isinstance(value, _TEXT) else value for value in values)
        self.empty = self.values[0]

    def encode(self, value):
        value = _str(value) if isinstance(value, _TEXT) else value
        if value not in self.values:
            raise ValueError("%r is not one of %r" % (value, self.values))
        return value

    def decode(self, wire):
        wire = _str(wire) if isinstance(wire, _TEXT) else wire
        return wire if wire in self.values else self.values[0]


class Text(Field):
    empty = ""

    def encode(self, value):
        return _str(value if isinstance(value, _TEXT) else str(value))

    def decode(self, wire):
        if not isinstance(wire, _TEXT):
            raise TypeError("not text: %r" % (wire,))
        return _str(wire)


_PRINTF = re.compile(r"%(?:(\d+)\$)?([sdif%])")


def printf(pattern, args):
    """语言文件里的格式（%s、%d、%1$s 这类，%% 是百分号）按顺序或按编号填进 args（都已是字）；缺的填空。"""
    position = [0]

    def replace(match):
        number, kind = match.group(1), match.group(2)
        if kind == "%":
            return "%"
        if number:
            index = int(number) - 1
        else:
            index = position[0]
            position[0] += 1
        return args[index] if 0 <= index < len(args) else ""
    return _PRINTF.sub(replace, pattern)


def renderLang(value, text):
    """
    可本地化的文字按语言拼成字：字原样，整数照写，列表一段段接起来，{"t": 语言文件的键, "w": [参数, ...]} 是那一条按参数
    填好（参数也是可本地化的文字）。text(键) 是这一端按玩家的语言查语言文件（找不到时给键本身）。
    """
    if isinstance(value, _TEXT):
        return _str(value)
    if isinstance(value, list):
        return "".join(renderLang(part, text) for part in value)
    if isinstance(value, dict):
        return printf(_str(text(value.get("t", ""))), [renderLang(arg, text) for arg in value.get("w", ())])
    if _isNumber(value):
        return str(value)
    return ""


def renderTitle(title, text):
    """
    开屏消息里的标题按语言写成字（容器类型的 titleFor）：字符串是语言文件的键或文字（text 查不到时给它本身），列表、字典是
    可本地化的文字（renderLang）。
    """
    if isinstance(title, (list, dict)):
        return renderLang(title, text)
    return _str(text(title or ""))


def _langWire(value, depth=0):
    """可本地化的文字的线上写法：只有字、整数、列表与 {"t": 键, "w": 参数列表}；别的东西报错。"""
    if depth > 16:
        raise ValueError("lang text nested too deep")
    if isinstance(value, _TEXT):
        return _str(value)
    if _isNumber(value) and not isinstance(value, float):
        return int(value)
    if isinstance(value, (list, tuple)):
        return [_langWire(part, depth + 1) for part in value]
    if isinstance(value, dict) and isinstance(value.get("t"), _TEXT) and set(value) <= {"t", "w"}:
        out = {"t": _str(value["t"])}
        if value.get("w"):
            out["w"] = [_langWire(arg, depth + 1) for arg in value["w"]]
        return out
    raise TypeError("not lang text: %r" % (value,))


class LangText(object):
    """可本地化的文字（Lang 字段读到的值）：render(text) 按语言拼成字。比较按内容。"""

    __slots__ = ("value",)

    def __init__(self, value):
        self.value = value

    def render(self, text):
        return renderLang(self.value, text)

    def __eq__(self, other):
        return isinstance(other, LangText) and other.value == self.value

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(repr(self.value))

    def __repr__(self):
        return "LangText(%r)" % (self.value,)


class Lang(Field):
    """
    可本地化的文字：照基岩版 rawtext 的写法，字、整数、列表（接起来）、{"t": 语言文件的键, "w": [参数, ...]}（那一条按参数
    填好，参数也是可本地化的文字），可以带 § 颜色。服务端给出写法，客户端按玩家的语言拼（文字控件、按钮与提示区域的格式串里
    照常写 {名字}）。读到的值是 LangText。
    """

    empty = LangText("")

    def encode(self, value):
        return _langWire(value.value if isinstance(value, LangText) else value)

    def decode(self, wire):
        return LangText(_langWire(wire))


class Item(Field):
    """一个物品堆（物品字典的四个键）或 None。"""

    def encode(self, value):
        return Items.normalize(value)

    def decode(self, wire):
        return Items.normalize(wire)


def _isNumber(value):
    return not isinstance(value, bool) and isinstance(value, _NUMBERS)


class ResourceValue(object):
    """
    资源的值：名字（流体、化学品、能量的名字，空为没有）、数量、容量。fraction 是数量占容量的比例（0–1）。
    格式串里（Std/TextFormat）：{名字} 写成"数量 / 容量"；{名字:amount}、{名字:capacity}、{名字:name} 写那一项；
    百分数格式（{名字:.0%}）写比例；别的格式同时用在数量与容量上（{名字:,} 写成"1,000 / 4,000"）。
    """

    __slots__ = ("name", "amount", "capacity")
    PARTS = ("name", "amount", "capacity")

    def __init__(self, name="", amount=0, capacity=0):
        self.name, self.amount, self.capacity = name, amount, capacity

    @property
    def fraction(self):
        if self.capacity <= 0:
            return 0.0
        return max(0.0, min(1.0, float(self.amount) / self.capacity))

    def _key(self):
        return (self.name, self.amount, self.capacity)

    def __eq__(self, other):
        return isinstance(other, ResourceValue) and self._key() == other._key()

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self._key())

    def __repr__(self):
        return "ResourceValue(%r, %r, %r)" % self._key()

    def __format__(self, spec):
        if spec in self.PARTS:
            return format(getattr(self, spec), "")
        if spec.endswith("%"):
            return format(self.fraction, spec)
        return "%s / %s" % (format(self.amount, spec), format(self.capacity, spec))


class Resource(Field):
    """
    资源（流体、化学品、能量）：名字、数量、容量。服务端的原始值是 (名字, 数量, 容量)、有这三个键的字典或 ResourceValue，
    None 为没有；线上写成 [名字, 数量, 容量]（数量与容量是整数时照发，不是时留 digits 位小数）；客户端读到 ResourceValue
    （还没收到时名字为空、数量与容量为 0）。
    """

    def __init__(self, digits=3, scope=SHARED):
        Field.__init__(self, scope)
        self.digits = digits
        self.empty = ResourceValue()

    def _number(self, value):
        if not _isNumber(value):
            raise TypeError("not a number: %r" % (value,))
        return value if isinstance(value, int) else round(float(value), self.digits)

    def encode(self, value):
        if value is None:
            return ["", 0, 0]
        if isinstance(value, ResourceValue):
            name, amount, capacity = value.name, value.amount, value.capacity
        elif isinstance(value, dict):
            name, amount, capacity = value.get("name"), value.get("amount", 0), value.get("capacity", 0)
        else:
            name, amount, capacity = value
        return [_str(name or ""), self._number(amount), self._number(capacity)]

    def decode(self, wire):
        name, amount, capacity = wire
        if not isinstance(name, _TEXT) or not _isNumber(amount) or not _isNumber(capacity):
            raise TypeError("not a resource: %r" % (wire,))
        return ResourceValue(_str(name), amount, capacity)


class Moving(Field):
    """
    会动的数（熔炉的火焰与箭头）：原始值是数，或 (值, 每刻变化)；上线写成 [值, 每秒变化]，只在变化的那一刻推一次起点
    与速度，客户端自己往前算，并夹在 [low, high] 里（缺省 0–1，给裁剪贴图用）。速度不为 0 时每次都发：值是"现在"的起点，
    同样的起点与速度也可能是新的一段（熔好一个，箭头又从 0 走起）。
    """

    def __init__(self, low=0.0, high=1.0, scope=SHARED):
        Field.__init__(self, scope)
        self.low, self.high = float(low), float(high)
        self.empty = self.low

    def encode(self, value):
        if isinstance(value, (tuple, list)):
            return [round(float(value[0]), 6), round(float(value[1]) * TICKS_PER_SECOND, 6)]
        return [round(float(value), 6), 0.0]

    def decode(self, wire):
        return (float(wire[0]), float(wire[1]))

    def again(self, wire):
        return bool(wire[1])

    def current(self, value, received, now):
        start, rate = value
        return max(self.low, min(self.high, start + rate * max(0.0, now - received)))


FULL, CHANGE = 0, 1   # 增量发送的列表与映射的两种写法：[FULL, 整份]，[CHANGE, 改动]


def splice(old, new):
    """
    old 改成 new 的一段改动：(起点, 删几个, 插进的那些)；起点之前与改动之后的部分两边一样（只在中间改了一段时最省：
    插进、删掉、改了连续的几项）。
    """
    size = min(len(old), len(new))
    start = 0
    while start < size and old[start] == new[start]:
        start += 1
    end = 0
    while end < size - start and old[len(old) - 1 - end] == new[len(new) - 1 - end]:
        end += 1
    return start, len(old) - start - end, new[start:len(new) - end]


class List(Field):
    """
    元素同一种类型的列表。delta 为假时整份发送；为真时增量发送：第一次（与面板关了再开时）整份 [FULL, 列表]，之后只发一段改动
    [CHANGE, 起点, 删几个, 插进的那些]（改动不比整份省时照样整份发）。客户端读到列表。
    """

    empty = ()

    def __init__(self, element, scope=SHARED, delta=False):
        Field.__init__(self, scope)
        self.element = element
        self.delta = delta

    def encode(self, value):
        return [self.element.encode(item) for item in value]

    def decode(self, wire):
        return [self.element.decode(item) for item in wire]

    def message(self, previous, wire):
        if not self.delta:
            return wire
        if previous is MISSING or not isinstance(previous, list):
            return [FULL, wire]
        start, removed, inserted = splice(previous, wire)
        if removed + len(inserted) >= len(wire):
            return [FULL, wire]
        return [CHANGE, start, removed, inserted]

    def receive(self, current, message):
        if not self.delta:
            return self.decode(message)
        if message[0] == FULL:
            return self.decode(message[1])
        if current is None:
            raise ValueError("a list change came before the whole list")
        start, removed, inserted = message[1], message[2], message[3]
        values = list(current)
        if not 0 <= start <= len(values) or removed < 0 or start + removed > len(values):
            raise ValueError("a list change out of range: %r" % (message,))
        values[start:start + removed] = [self.element.decode(item) for item in inserted]
        return values


class Map(Field):
    """
    键是文字、值同一种类型的映射。delta 为假时整份发送；为真时增量发送：第一次（与面板关了再开时）整份 [FULL, 映射]，之后
    只发改动 [CHANGE, {改了与新加的键: 值}, [删掉的键]]（改动不比整份省时照样整份发）。客户端读到映射。
    """

    def __init__(self, value, scope=SHARED, delta=False):
        Field.__init__(self, scope)
        self.value = value
        self.delta = delta
        self.empty = {}

    def key(self, wire):
        """线上的键 -> 键。"""
        return _str(wire)

    def encode(self, value):
        return dict((_str(key), self.value.encode(item)) for key, item in value.items())

    def decode(self, wire):
        return dict((self.key(key), self.value.decode(item)) for key, item in wire.items())

    def message(self, previous, wire):
        if not self.delta:
            return wire
        if previous is MISSING or not isinstance(previous, dict):
            return [FULL, wire]
        changed = dict((key, item) for key, item in wire.items() if key not in previous or previous[key] != item)
        removed = [key for key in previous if key not in wire]
        if len(changed) + len(removed) >= len(wire):
            return [FULL, wire]
        return [CHANGE, changed, removed]

    def receive(self, current, message):
        if not self.delta:
            return self.decode(message)
        if message[0] == FULL:
            return self.decode(message[1])
        if current is None:
            raise ValueError("a map change came before the whole map")
        values = dict(current)
        values.update(self.decode(message[1]))
        for key in message[2]:
            values.pop(self.key(key), None)
        return values


class SlotValues(Map):
    """
    每格数据：集合 collection 里格子的值（格号 -> 值，没有值的格不写），给格子的装饰用（进度、热量、电量，ROADMAP P4.10）。
    增量发送（同 Map）。服务端的原始值是 {格号: 值} 或列表（第几项就是第几格，None 为没有）；客户端读到 {格号: 值}。
    部件声明的每格数据并进界面模型时，集合名按部件的前缀改。
    """

    def __init__(self, element, collection, scope=SHARED):
        Map.__init__(self, element, scope, delta=True)
        self.collection = collection

    def key(self, wire):
        return int(wire)

    def encode(self, value):
        items = enumerate(value) if isinstance(value, (list, tuple)) else value.items()
        return dict((str(int(index)), self.value.encode(item)) for index, item in items if item is not None)

    def forPart(self, rename):
        return SlotValues(self.value, rename(self.collection), self.scope)
