# -*- coding: utf-8 -*-
"""
把物品附加数据（引擎物品字典里 userData 的写法）编成引擎网络格式的 NBT，再 base64：物品飞行渲染器的
flying_item_user_data 要的就是它（原版飞行时带上物品的附加数据，飞着的旗帜、盾牌、装好的弩才画得对）。

userData 的写法：标量是 {"__type__": 类型, "__value__": 值}，复合是普通字典，列表是普通列表；
没有类型标记的照引擎收 Python 值的规矩：bool 字节、整数 Int（超出 32 位用 Int64）、浮点 Float、字符串 String。
网络格式：根是一个无名复合；复合里每项写类型字节、名字、内容，最后写 0；字符串是 VarInt 长度加 utf-8；
Int / Int64 是 zigzag VarInt；Short、Float、Double 是小端定长；列表是元素类型字节、zigzag VarInt 个数、各元素内容。
纯逻辑。
"""
import base64
import struct

END, BYTE, SHORT, INT, INT64, FLOAT, DOUBLE, BYTE_ARRAY, STRING, LIST, COMPOUND, INT_ARRAY = range(12)

try:
    _TEXT = (str, unicode)  # noqa: F821
    _INTS = (int, long)  # noqa: F821
except NameError:
    _TEXT = (str,)
    _INTS = (int,)


def _unsigned(out, value):
    value &= 0xFFFFFFFFFFFFFFFF
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            out.append(byte | 0x80)
        else:
            out.append(byte)
            return


def _zigzag(out, value, bits):
    value = int(value)
    _unsigned(out, (value << 1) ^ (value >> (bits - 1)) if value < 0 else value << 1)


def _string(out, text):
    data = text if isinstance(text, bytes) else text.encode("utf-8")
    _unsigned(out, len(data))
    out.extend(bytearray(data))


def kindOf(value):
    """一个值的 NBT 类型。"""
    if isinstance(value, dict):
        if "__type__" in value and "__value__" in value:
            return int(value["__type__"])
        return COMPOUND
    if isinstance(value, (list, tuple)):
        return LIST
    if isinstance(value, bool):
        return BYTE
    if isinstance(value, _INTS):
        return INT if -0x80000000 <= value <= 0x7FFFFFFF else INT64
    if isinstance(value, float):
        return FLOAT
    if isinstance(value, _TEXT) or isinstance(value, bytes):
        return STRING
    raise ValueError("unsupported value %r" % (value,))


def _payload(out, kind, value):
    if isinstance(value, dict) and "__type__" in value and "__value__" in value:
        value = value["__value__"]
    if kind == BYTE:
        out.append(int(value) & 0xFF)
    elif kind == SHORT:
        out.extend(bytearray(struct.pack("<h", int(value))))
    elif kind == INT:
        _zigzag(out, value, 32)
    elif kind == INT64:
        _zigzag(out, value, 64)
    elif kind == FLOAT:
        out.extend(bytearray(struct.pack("<f", float(value))))
    elif kind == DOUBLE:
        out.extend(bytearray(struct.pack("<d", float(value))))
    elif kind == BYTE_ARRAY:
        _zigzag(out, len(value), 32)
        out.extend(bytearray(int(item) & 0xFF for item in value))
    elif kind == STRING:
        _string(out, value)
    elif kind == LIST:
        element = kindOf(value[0]) if value else END
        out.append(element)
        _zigzag(out, len(value), 32)
        for item in value:
            _payload(out, element, item)
    elif kind == COMPOUND:
        for name in sorted(value):
            _named(out, name, value[name])
        out.append(END)
    elif kind == INT_ARRAY:
        _zigzag(out, len(value), 32)
        for item in value:
            _zigzag(out, item, 32)
    else:
        raise ValueError("unsupported tag type %r" % (kind,))


def _named(out, name, value):
    kind = kindOf(value)
    out.append(kind)
    _string(out, name)
    _payload(out, kind, value)


def encode(compound):
    """复合（字典）-> 网络格式 NBT 的字节。"""
    out = bytearray()
    _named(out, "", compound)
    return bytes(out)


def networkBase64(compound):
    """复合 -> base64 文本（str）；空的为空串。"""
    if not compound:
        return ""
    text = base64.b64encode(encode(compound))
    return text if isinstance(text, str) else text.decode("utf-8")
