# -*- coding: utf-8 -*-
"""TableWire - 数据表里的值和网易 Call 载荷之间的编码（双端，纯规则）

下游往数据表里追加的东西（Api/LegacyModAttr.py 的白名单）只存在服务端，站点的客户端要认得就得发过去。可它们的写法网易的 Call 载荷收不了：
(物品名, aux) 元组当键、元组当配方食材、列表里类型混着（["x", 0]）、py2 的 unicode；而载荷的规矩是键只能是 str、列表元素类型要一致、
不能有 unicode、元组到对端会变列表（前置包 Shared/Wire.py 记着同一组规矩；两个包互不导入，这里照它写一份，tests 用它的 wireProblem 核对）。
编码后只剩 None / bool / int / float / str / list / dict；元组、混类型的列表、登记过的容器对象包一层带 "$" 的标记，对端照标记换回来：
    {"$pair": "物品名|aux"}          (str, int) 二元组：配方里最多的就是它，所以单独压成一个字符串
    {"$tuple": 序列}                 别的元组
    {"$mixed": {"0": .., "1": ..}}   元素类型不一致的列表（按下标放进字典，字典的值什么类型都行）
    {"$ref": "knifeList"}            就是登记过的那个容器对象：砧板配方的 tool 引用的是 knifeList 本身，客户端换回它自己的那一个
传不了的值（自定义对象、集合、键不是 str 的嵌套字典、以 "$" 开头的键、嵌套太深）抛 WireError，由调用方跳过那一条并记日志。
"""
_UNICODE = type(u"")
INT_TYPES = (int, type(2 ** 64))   # py2 的 int / long（引擎给的整数可能是 long），py3 的 int
_INF = float("inf")
TEXT = (str, _UNICODE)      # py2 的 str / unicode，py3 的 str
MAX_DEPTH = 16              # 嵌套上限：自己套着自己的数据不能把递归拖垮
PAIR, TUPLE, MIXED, REF = "$pair", "$tuple", "$mixed", "$ref"


class WireError(ValueError):
    """这个值编不了，或收到的编码换不回来。"""


def toStr(value):
    """py2 的 unicode 换成 utf-8 的 str（引擎在 py2 里收到的字符串可能是 unicode，数据表里只放 str），别的原样。"""
    if _UNICODE is not str and isinstance(value, _UNICODE):
        return value.encode("utf-8")
    return value


def isInt(value):
    """整数（int / long），bool 不算。"""
    return isinstance(value, INT_TYPES) and not isinstance(value, bool)


def kindOf(value):
    """值是哪一类：none / bool / int / float / str / dict / list / tuple，别的给类型名。bool 不算 int。"""
    if value is None:
        return "none"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, INT_TYPES):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, TEXT):
        return "str"
    if isinstance(value, dict):
        return "dict"
    if isinstance(value, list):
        return "list"
    if isinstance(value, tuple):
        return "tuple"
    return type(value).__name__


def _isPair(value):
    """(物品名, aux)：二元组，名字是不含 | 的文字，aux 是整数。"""
    return len(value) == 2 and kindOf(value[0]) == "str" and kindOf(value[1]) == "int" and "|" not in toStr(value[0])


def _seq(items):
    """已经编好的一串：元素类型一致就是列表，不一致包成 $mixed（载荷里的列表元素类型必须一致）。"""
    if len(set(kindOf(item) for item in items)) <= 1:
        return items
    return {MIXED: dict((str(index), item) for index, item in enumerate(items))}


class Codec(object):
    """refs 是 {名字: 容器对象}：编码时碰到的就是其中某个对象本身（身份相同）的列表写成 {"$ref": 名字}，解码时换回本端的同名对象。"""

    def __init__(self, refs=None):
        self.refs = dict(refs or {})
        self._names = dict((id(obj), name) for name, obj in self.refs.items())

    # ---------------------------------------------------------------- 编码

    def encode(self, value, depth=0):
        if depth > MAX_DEPTH:
            raise WireError("嵌套超过 %d 层" % MAX_DEPTH)
        kind = kindOf(value)
        if kind in ("none", "bool", "int"):
            return value
        if kind == "float":
            if value != value or value in (_INF, -_INF):
                raise WireError("非有限浮点数")
            return value
        if kind == "str":
            return toStr(value)
        if kind == "dict":
            return self._encodeDict(value, depth)
        if kind == "list":
            name = self._names.get(id(value))
            return {REF: name} if name is not None else self.encodeSeq(value, depth)
        if kind == "tuple":
            if _isPair(value):
                return {PAIR: "%s|%d" % (toStr(value[0]), value[1])}
            return {TUPLE: self.encodeSeq(value, depth)}
        raise WireError("不认识的类型 %s" % kind)

    def encodeSeq(self, items, depth=0):
        """一串值（列表或元组的元素）-> 列表，或元素类型不一致时的 $mixed。"""
        return _seq([self.encode(item, depth + 1) for item in items])

    def _encodeDict(self, value, depth):
        out = {}
        for key, item in value.items():
            if not isinstance(key, TEXT):
                raise WireError("嵌套字典的键 %r 不是 str" % (key,))
            key = toStr(key)
            if key.startswith("$"):
                raise WireError("键 %r 以 $ 开头（留给编码的标记）" % (key,))
            out[key] = self.encode(item, depth + 1)
        return out

    # ---------------------------------------------------------------- 解码

    def decode(self, wire, depth=0):
        if depth > MAX_DEPTH:
            raise WireError("嵌套超过 %d 层" % MAX_DEPTH)
        kind = kindOf(wire)
        if kind in ("none", "bool", "float"):
            return wire
        if kind == "int":
            return int(wire)                      # py2 的 long 换回 int（引擎给的整数可能是 long，别处 isinstance(.., int) 认不得它）
        if kind == "str":
            return toStr(wire)
        if kind == "list":
            return [self.decode(item, depth + 1) for item in wire]
        if kind != "dict":
            raise WireError("载荷里不该有 %s" % kind)
        if len(wire) == 1:
            tag, payload = list(wire.items())[0]
            tag = toStr(tag)
            if tag.startswith("$"):
                return self._decodeTagged(tag, payload, depth)
        out = {}
        for key, item in wire.items():
            key = toStr(key)
            if key.startswith("$"):
                raise WireError("键 %r 以 $ 开头，却不是编码的标记" % (key,))
            out[key] = self.decode(item, depth + 1)
        return out

    def decodeSeq(self, wire, depth=0):
        """encodeSeq 的逆：列表，或 {"$mixed": {...}} -> 解码后的列表。"""
        if isinstance(wire, list):
            return [self.decode(item, depth + 1) for item in wire]
        if isinstance(wire, dict) and len(wire) == 1 and toStr(list(wire)[0]) == MIXED:
            slots = list(wire.values())[0]
            if not isinstance(slots, dict):
                raise WireError("$mixed 的内容不是字典")
            slots = dict((toStr(key), item) for key, item in slots.items())
            if any(str(index) not in slots for index in range(len(slots))):
                raise WireError("$mixed 的下标不连续")
            return [self.decode(slots[str(index)], depth + 1) for index in range(len(slots))]
        raise WireError("序列的写法不对")

    def _decodeTagged(self, tag, payload, depth):
        if tag == REF:
            name = toStr(payload)
            if not isinstance(name, str) or name not in self.refs:
                raise WireError("不认识的引用 %r" % (payload,))
            return self.refs[name]
        if tag == PAIR:
            name, bar, aux = toStr(payload).rpartition("|") if isinstance(payload, TEXT) else ("", "", "")
            if not bar or not aux.lstrip("-").isdigit():
                raise WireError("$pair 的写法不对 %r" % (payload,))
            return (name, int(aux))
        if tag == TUPLE:
            return tuple(self.decodeSeq(payload, depth))
        if tag == MIXED:
            return self.decodeSeq({MIXED: payload}, depth)
        raise WireError("不认识的标记 %r" % (tag,))
