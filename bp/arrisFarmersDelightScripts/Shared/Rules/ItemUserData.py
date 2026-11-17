# -*- coding: utf-8 -*-
"""ItemUserData - 物品的 userData 能不能原样交给前置包的站点载荷（双端，纯逻辑）

厨锅站点的槽组直接绑在方块容器格上（Server/Helpers/PotContainer.ContainerSlots），前置包的内核把格子里的物品原样编进状态载荷
（它的 Wire.toWire，不合规就抛错，光标栈的物品它会兜底、格子里的不会）。物品连 userData 一起读（改过名、带自定义数据的料取出来、
摆开、退回、煮掉一部分时数据都跟着走，JE 的物品栈本来就带）之后，userData 得守内核的规矩：键是文本、list 里的元素同一类
（整数和小数混着可以，内核补齐）、数是有限的、嵌套不超过 16 层；再加一个大小的上限，站点每次变化都要把整个物品发给所有看着的人。
不合规的 userData 站点读格子时不带（和以前一样，那件物品的数据就是不跟着走）。
"""
MAX_DEPTH = 16        # 内核 Shared/Wire.MAX_DEPTH
MAX_VALUES = 1024     # 一件物品的 userData 至多这么多个值：收纳袋、潜影盒这种大的不带

_TEXT = type(u"")     # py2 的 unicode；py3 里就是 str
_TEXTS = (str, _TEXT)
_INTS = (int, type(2 ** 64))
_INF = float("inf")


def _kind(value):
    if value is None:
        return "none"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, _INTS):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, _TEXTS):
        return "str"
    if isinstance(value, dict):
        return "dict"
    if isinstance(value, (list, tuple)):
        return "list"
    return "other"


def _fits(value, depth, left):
    left[0] -= 1
    if left[0] < 0:
        return False
    kind = _kind(value)
    if kind in ("none", "bool", "int", "str"):
        return True
    if kind == "float":
        return value == value and value != _INF and value != -_INF
    if kind == "other" or depth >= MAX_DEPTH:
        return False
    if kind == "dict":
        return all(isinstance(key, _TEXTS) and _fits(item, depth + 1, left) for key, item in value.items())
    kinds = set(_kind(item) for item in value)
    return (len(kinds) <= 1 or kinds == set(["int", "float"])) and all(_fits(item, depth + 1, left) for item in value)


def fitsWire(userData):
    """userData（引擎读出来的字典，没有是 None / 空）能原样放进站点的载荷吗。"""
    return not userData or _fits(userData, 1, [MAX_VALUES])
