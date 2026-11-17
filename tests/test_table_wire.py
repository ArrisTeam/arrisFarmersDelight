# -*- coding: utf-8 -*-
# runner: both
"""数据表里的值和 Call 载荷之间的编码（Shared/Rules/TableWire.py）：元组当键 / 当配方食材、混类型的列表、py2 的 unicode、登记过的容器引用，
编出来的东西守前置包 Wire 的规矩（键 str、列表元素类型一致、没有元组和 unicode），走一趟 JSON（和网络一样：元组变列表、py2 字符串变 unicode）再换回来
和原来一模一样；传不了的值抛 WireError，不是别的异常。
"""
from __future__ import print_function

import json

import fdtest
import tablekit as K

Wire = fdtest.load("Shared.Rules.TableWire")
Cutting = fdtest.load("Shared.Data.Cutting")
CODEC = Wire.Codec({"knifeList": Cutting.knifeList, "axeList": Cutting.axeList})


def _trip(value, codec=CODEC):
    """编码 -> 守 Wire 的规矩 -> JSON 来回 -> 解码。"""
    encoded = codec.encode(value)
    assert K.Wire.wireProblem(encoded) is None, K.Wire.wireProblem(encoded)
    return codec.decode(json.loads(json.dumps(encoded)))


def _same(a, b):
    """值相等，类型也一样（元组还是元组、列表还是列表、str 还是 str）。"""
    if type(a) is not type(b) and not (isinstance(a, list) and isinstance(b, list)):
        return False
    if isinstance(a, dict):
        return sorted(a) == sorted(b) and all(_same(a[key], b[key]) for key in a)
    if isinstance(a, (list, tuple)):
        return len(a) == len(b) and all(_same(x, y) for x, y in zip(a, b))
    return a == b


def testScalarsPassThrough():
    for value in (None, True, False, 0, -3, 7, 2 ** 20, 1.5, -0.25, "", "arris:iron_knife", "紫颂酱"):
        assert _same(_trip(value), value), value
    assert CODEC.encode(True) is True and CODEC.encode(None) is None


def testAPairIsOneCompactString():
    encoded = CODEC.encode(("minecraft:beef", 0))
    assert encoded == {"$pair": "minecraft:beef|0"}, encoded
    assert CODEC.encode(("arris:x", -2)) == {"$pair": "arris:x|-2"}
    assert _same(_trip(("minecraft:beef", 0)), ("minecraft:beef", 0)) and _same(_trip(("arris:x", -2)), ("arris:x", -2))


def testOtherTuplesAndMixedListsKeepTheirType():
    for value in ((1, 2, 3), ("a", "b"), ("a", 1, True), (), ("only",), (("a", 0), ("b", 1)), ["x", 1, None], [1, 2.5], [("a", 0), "b"],
                  ("a|b", 1), (True, 1), ("a", 1.5)):
        assert _same(_trip(value), value), value
    assert CODEC.encode((1, 2, 3)) == {"$tuple": [1, 2, 3]}, "元素类型一致的元组：标记里是个列表"
    assert CODEC.encode(["x", 1]) == {"$mixed": {"0": "x", "1": 1}}, "类型不一致的列表按下标放进字典（载荷里的列表元素类型必须一致）"
    assert CODEC.encode([]) == [] and CODEC.encode({}) == {}


def testABarInTheNameOrABoolAuxIsNotAPair():
    assert Wire.PAIR not in CODEC.encode(("a|b", 1)) and Wire.PAIR not in CODEC.encode(("a", True)), "名字里有 | 或 aux 是 bool：走一般的元组"
    assert _same(_trip(("a|b", 1)), ("a|b", 1)) and _same(_trip(("a", True)), ("a", True))


def testNestedTablesLikeTheRealOnesComeBackEqual():
    cutting = {"itemList": [{"itemName": "ends_delight:ender_pearl_grain", "count": 4}, {"itemName": "minecraft:bone_meal", "count": 1, "chance": 0.5}],
               "tool": ["x:a", "x:b"], "type": "", "item_type": None}
    pot = {"Recipe": [[("a:b", 0), ("c:d", 1)], [("e:f", 0)]], "CookResult": ("g:h", 0), "Vessel": ("minecraft:bowl", 0), "PushItem": [("i:j", 0)],
           "text": "紫颂酱", "CookTime": 5.0, "CookCount": 2}
    feast = {"target": None, "item": None}
    for value in (cutting, pot, feast):
        assert _same(_trip(value), value), value


def testPyTwoUnicodeBecomesStrOnBothSides():
    """引擎在 py2 里收到的字符串可能是 unicode，数据表里只放 str（utf-8）：编码时、解码时各换一次；py3 里本来就都是 str。"""
    wide = u"ends_delight:ender_pearl"
    assert type(CODEC.encode(wide)) is str and type(_trip(wide)) is str and _trip(wide) == "ends_delight:ender_pearl"
    pair = _trip((wide, 0))
    assert pair == ("ends_delight:ender_pearl", 0) and type(pair[0]) is str
    back = _trip({u"键": [u"紫颂酱", (u"a", 1), u"b"]})
    assert all(type(key) is str for key in back), back
    values = back[Wire.toStr(u"键")]
    assert type(values[0]) is str and type(values[1][0]) is str and type(values[2]) is str and values[0] == Wire.toStr(u"紫颂酱"), back


def testAnAliasOfARegisteredContainerIsARefAndComesBackAsTheLocalObject():
    knives = Cutting.knifeList
    encoded = CODEC.encode({"tool": knives})
    assert encoded == {"tool": {"$ref": "knifeList"}}
    back = CODEC.decode(json.loads(json.dumps(encoded)))
    assert back["tool"] is knives, "换回本端的同名对象，之后往里追加的刀对所有引用它的配方一起生效"
    plainCopy = CODEC.encode({"tool": list(knives)})
    assert Wire.REF not in str(plainCopy), "内容一样但不是那个对象：当普通列表发过去"
    assert CODEC.decode(plainCopy)["tool"] == knives and CODEC.decode(plainCopy)["tool"] is not knives


def testWhatCannotBeSentRaisesWireErrorAndNothingElse():
    nan = float("nan")
    loop = []
    loop.append(loop)
    deep = [[[[[[[[[[[[[[[[[[1]]]]]]]]]]]]]]]]]]
    for bad in (object(), set([1]), frozenset(["a"]), {1: "a"}, {("a", 0): 1}, {"$x": 1}, {"$ref": "knifeList", "b": 1}, nan, float("inf"),
                loop, deep, [object()], {"a": {"b": object()}}, lambda: 0):
        try:
            CODEC.encode(bad)
        except Wire.WireError:
            continue
        raise AssertionError("应该编不了: %r" % (bad,))


def testABadWireRaisesWireErrorAndNothingElse():
    for bad in ({"$ref": "noSuchList"}, {"$ref": 3}, {"$pair": "nobar"}, {"$pair": "a|x"}, {"$pair": 7}, {"$tuple": "abc"}, {"$tuple": {"a": 1}},
                {"$mixed": {"0": 1, "2": 3}}, {"$mixed": [1]}, {"$weird": 1}, {"a": 1, "$ref": "knifeList"}, (1, 2), object(), {"$mixed": {"x": 1}}):
        try:
            CODEC.decode(bad)
        except Wire.WireError:
            continue
        raise AssertionError("应该换不回来: %r" % (bad,))


def testPyTwoLongIntegersFromTheEngineComeBackAsInt():
    """引擎在 py2 里给的整数可能是 long：解码换回 int（别处 isinstance(x, int) 认不得 long），isInt 两种都认、bool 不算。"""
    big = Wire.INT_TYPES[-1]
    for value in (big(0), big(7), big(-3)):
        assert Wire.isInt(value) and type(CODEC.decode(value)) is int and CODEC.decode(value) == value
    assert Wire.isInt(5) and not Wire.isInt(True) and not Wire.isInt(1.0) and not Wire.isInt("1")
    back = CODEC.decode({"$pair": "a:b|%d" % big(3)})
    assert back == ("a:b", 3) and type(back[1]) is int


def testDecodingNeverSharesObjectsWithTheWire():
    encoded = CODEC.encode({"a": [1, 2], "b": ("x", 1)})
    first, second = CODEC.decode(encoded), CODEC.decode(encoded)
    first["a"].append(3)
    assert second["a"] == [1, 2] and encoded["a"] == [1, 2], "解码出来的是新对象，改它不会改到载荷"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
