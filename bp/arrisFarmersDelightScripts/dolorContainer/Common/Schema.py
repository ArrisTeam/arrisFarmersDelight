# -*- coding: utf-8 -*-
"""
参数格式（docs/ARCHITECTURE.md 第 3.5、3.7 节）：操作与动作（Common/Actions）的参数在线上怎么写、怎么校验。
纯逻辑，两端共用。

客户端发来的东西一律不信：类型、范围、条数都由格式查，不合格抛 BadRequest（带错误码），整条请求被拒。
格式的 parse(值, 结构) 把线上的值变成 Python 值（格子引用变成 (集合名, 下标)），encode(值, 结构) 反过来。
线上的字典里缺了这个键时，parse 收到的值是 MISSING：给了 default 的用缺省值，否则按 None 处理。
"""
from . import Items
from .Collections import CURSOR_ITEMS, MAX_COLLECTIONS  # noqa: F401  线上的集合编号以它为界

MAX_CONTAINER_INDEX = 1 << 24   # 不设上限的集合，下标以它为界

MISSING = object()

try:
    _INTS = (int, long)  # noqa: F821
    _STRS = (str, unicode)  # noqa: F821
except NameError:
    _INTS = (int,)
    _STRS = (str,)


class BadRequest(Exception):

    def __init__(self, code):
        Exception.__init__(self, code)
        self.code = code


def text(value):
    """线上来的字符串一律转成 str（py2 下 unicode 编成 utf-8）。"""
    if isinstance(value, str):
        return value
    return value.encode("utf-8")


def isText(value):
    return isinstance(value, _STRS)


def integer(value, low, high, code):
    """value 是 [low, high] 里的整数（布尔不算），否则抛 BadRequest(code)。"""
    if isinstance(value, bool) or not isinstance(value, _INTS) or not low <= value <= high:
        raise BadRequest(code)
    return int(value)


def ref(value, structure, cursor=True):
    """
    [集合编号, 下标] -> (集合名, 下标)：集合要在结构里有，下标在集合的格数内（不设上限的集合以 MAX_CONTAINER_INDEX 为界）。
    cursor 为假时不许是手持物。
    """
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise BadRequest("bad_ref")
    name = structure.collectionName(integer(value[0], 0, MAX_COLLECTIONS - 1, "bad_ref"))
    if name is None or (not cursor and name == CURSOR_ITEMS):
        raise BadRequest("bad_ref")
    collection = structure.get(name)
    limit = (collection.size if collection.size is not None else MAX_CONTAINER_INDEX + 1) - 1
    return (name, integer(value[1], 0, limit, "bad_ref"))


def wireRef(value, structure):
    """(集合名, 下标) -> [集合编号, 下标]。"""
    return [structure.collectionId(value[0]), value[1]]


class Field(object):
    """一个参数的格式。"""

    def parse(self, value, structure):
        raise NotImplementedError

    def encode(self, value, structure):
        return value


class Int(Field):
    """[low, high] 里的整数（布尔不算）；optional 时可以是 None；缺了这个键时用 default（没给 default 就按 None）。"""

    def __init__(self, low, high, code="bad_arg", optional=False, default=MISSING):
        self.low, self.high, self.code = low, high, code
        self.optional, self.default = optional, default

    def parse(self, value, structure):
        if value is MISSING:
            value = None if self.default is MISSING else self.default
        if value is None and self.optional:
            return None
        return integer(value, self.low, self.high, self.code)


class Bool(Field):
    """真或假（线上只收布尔，0 与 1 不算）；缺了这个键时用 default（没给 default 就不收）。"""

    def __init__(self, code="bad_arg", default=MISSING):
        self.code, self.default = code, default

    def parse(self, value, structure):
        if value is MISSING:
            value = self.default
        if not isinstance(value, bool):
            raise BadRequest(self.code)
        return value


class Enum(Field):
    """几个取值之一（整数或文字）；缺了这个键时用 default（没给 default 就不收）。"""

    def __init__(self, values, code="bad_arg", default=MISSING):
        if not values:
            raise ValueError("an enum needs values")
        self.values = tuple(text(value) if isText(value) else value for value in values)
        self.code, self.default = code, default

    def parse(self, value, structure):
        if value is MISSING:
            value = self.default
        if isText(value):
            value = text(value)
        elif isinstance(value, bool) or not isinstance(value, _INTS):
            raise BadRequest(self.code)
        if value not in self.values:
            raise BadRequest(self.code)
        return value


NAMES = "names"   # Text 的 words 写它：按名字查敏感词（给东西起的名字；比按语句查的严）
_wordCheck = [None, None]   # 敏感词检查（按语句、按名字）：服务端的缺省登记装上引擎的检查（Std/Server/Words.py），客户端没有


def setWordCheck(check, names=None):
    """装上敏感词检查：check(文字) 按语句查、names(文字) 按名字查，真为可以、假为含敏感词（文字是 str）；names 不给时用 check。"""
    _wordCheck[0] = check
    _wordCheck[1] = names


def _chars(value):
    """文字 -> unicode（按字处理）；py2 的 str 按 utf-8 解，解不开时抛 UnicodeDecodeError。"""
    return value.decode("utf-8") if isinstance(value, bytes) else value


class Text(Field):
    """
    文字，最多 limit 个字（按字数，不按字节）；值是 str（py2 下编成 utf-8，引擎的文本接口只收 str）。
    allowed 是允许的字：一串字，或者判断一个字的函数（收 unicode 的一个字）；None 时不限。
    words 为真时服务端按敏感词检查，含敏感词的拒绝（错误码 words）；写 NAMES 时按名字查（给东西起的名字，原版铁砧改名这样查）。
    缺了这个键时用 default（没给 default 就不收）。
    clean 是文本框在客户端用的同一套规则：去掉不允许的字、截到 limit 个字。
    """

    def __init__(self, limit, code="bad_arg", default=MISSING, allowed=None, words=True):
        self.limit, self.code, self.default = int(limit), code, default
        self.allowed = _chars(allowed) if isText(allowed) else allowed
        self.words = words

    def allows(self, char):
        """一个字（unicode）允许不允许。"""
        allowed = self.allowed
        if allowed is None:
            return True
        return bool(allowed(char)) if callable(allowed) else char in allowed

    def parse(self, value, structure):
        if value is MISSING:
            value = self.default
        if not isText(value):
            raise BadRequest(self.code)
        try:
            chars = _chars(value)
        except UnicodeDecodeError:
            raise BadRequest(self.code)
        if len(chars) > self.limit or not all(self.allows(char) for char in chars):
            raise BadRequest(self.code)
        value = text(value)
        if self.words and chars:
            check = (_wordCheck[1] or _wordCheck[0]) if self.words == NAMES else _wordCheck[0]
            if check is not None and not check(value):
                raise BadRequest("words")
        return value

    def clean(self, value):
        """去掉不允许的字、截到 limit 个字（文本框在客户端用）。不是文字、解不开的当作空。"""
        try:
            chars = _chars(value) if isText(value) else u""
        except UnicodeDecodeError:
            chars = u""
        return text(u"".join(char for char in chars if self.allows(char))[:self.limit])


class Ints(Field):
    """0 到 limit 个 [low, high] 里的整数，从小到大、不重复（原版创造栏搜索匹配到的编号）。"""

    def __init__(self, limit, low, high, code="bad_arg"):
        self.limit, self.low, self.high, self.code = limit, low, high, code

    def parse(self, value, structure):
        if not isinstance(value, (list, tuple)) or len(value) > self.limit:
            raise BadRequest(self.code)
        out = [integer(item, self.low, self.high, self.code) for item in value]
        for index in range(1, len(out)):
            if out[index] <= out[index - 1]:
                raise BadRequest(self.code)
        return out

    def encode(self, value, structure):
        return list(value)


class Amount(Int):
    """物品个数：1 到一格的上限（optional 时可以是 None，意思是"整堆"）。"""

    def __init__(self, optional=False):
        Int.__init__(self, 1, Items.CONTAINER_STACK_LIMIT, "bad_amount", optional)


class Ref(Field):
    """格子引用；cursor 为假时不许是手持物；optional 时可以是 None（缺了这个键也是 None）。"""

    def __init__(self, cursor=False, optional=False):
        self.cursor = cursor
        self.optional = optional

    def parse(self, value, structure):
        if self.optional and (value is MISSING or value is None):
            return None
        return ref(None if value is MISSING else value, structure, self.cursor)

    def encode(self, value, structure):
        return None if value is None and self.optional else wireRef(value, structure)


class Refs(Field):
    """1 到 limit 个格子引用（不许是手持物）。"""

    def __init__(self, limit, code):
        self.limit, self.code = limit, code

    def parse(self, value, structure):
        if not isinstance(value, (list, tuple)) or not 0 < len(value) <= self.limit:
            raise BadRequest(self.code)
        return [ref(item, structure, False) for item in value]

    def encode(self, value, structure):
        return [wireRef(item, structure) for item in value]
