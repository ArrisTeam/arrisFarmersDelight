# -*- coding: utf-8 -*-
"""EventRegistry - 服务端事件注册表（服务端；本模块不导入引擎，离线可测）

每个引擎事件只在 Server/ModServer.py 里挂一次 @Listen，函数体只调 dispatch；
玩法模块用 @registerHandler(事件名, match=..., priority=...) 登记处理函数。

match 说明这个处理函数关心哪些方块 / 物品（与匹配键比较）：
    None                     每次都调（处理函数自己判断）
    "arris:skillet"          匹配键等于它时调
    tuple / frozenset        匹配键属于这组固定名字时调
    list / dict / set        活的配置容器：每次按"键 in 容器"判断，下游往表里追加的名字也会生效
    callable                 match(键) 为真时调
匹配键缺省是 dispatch 传进来的 key；登记时给 keyOf(args) 可以改成从事件参数里取（例如物品名）。

执行顺序：priority 从大到小，同优先级按登记先后。处理函数返回 True 表示已经处理了这次事件，
后面的不再调；返回其它值继续往后。每个处理函数单独隔离异常：打印事件名与 traceback 后继续，
一个模块出错不会拖垮同一事件的其它模块。登记按 (模块, 函数名) 去重（网易热重载会重新执行改动过的模块）。
"""
import traceback

try:
    _STRING_TYPES = (basestring,)  # noqa: F821 - py2
except NameError:
    _STRING_TYPES = (str,)

_handlers = {}
_sequence = [0]


class _Entry(object):
    __slots__ = ("priority", "order", "func", "test", "keyOf", "ident")

    def __init__(self, priority, order, func, test, keyOf, ident):
        self.priority = priority
        self.order = order
        self.func = func
        self.test = test
        self.keyOf = keyOf
        self.ident = ident


def _makeTest(match):
    if match is None:
        return None
    if isinstance(match, _STRING_TYPES):
        return lambda key: key == match
    if isinstance(match, (tuple, frozenset)):
        return frozenset(match).__contains__
    if isinstance(match, (list, dict, set)):
        return match.__contains__
    if callable(match):
        return match
    raise TypeError("registerHandler: 不认识的 match 类型 %r" % (type(match),))


def registerHandler(event, match=None, priority=0, keyOf=None):
    """装饰器：把函数登记为 event 的处理函数（签名 func(args)）。"""
    test = _makeTest(match)

    def decorator(func):
        ident = (getattr(func, "__module__", ""), getattr(func, "__name__", repr(func)))
        _sequence[0] += 1
        entry = _Entry(priority, _sequence[0], func, test, keyOf, ident)
        entries = [e for e in _handlers.get(event, ()) if e.ident != ident]
        entries.append(entry)
        entries.sort(key=lambda e: (-e.priority, e.order))
        # 换成新列表再赋值：dispatch 正在遍历旧列表时登记也安全
        _handlers[event] = entries
        return func
    return decorator


def dispatch(event, args, key=None):
    """按登记顺序调用 event 的处理函数；有处理函数返回 True 时停止并返回 True。"""
    entries = _handlers.get(event)
    if not entries:
        return False
    for entry in entries:
        if entry.test is not None:
            matchKey = entry.keyOf(args) if entry.keyOf is not None else key
            if not entry.test(matchKey):
                continue
        try:
            if entry.func(args) is True:
                return True
        except Exception:  # noqa: BLE001 - 分发边界：隔离单个处理函数的异常
            print("[arrisFarmersDelight] 事件 %s 的处理函数 %s.%s 出错" % (event, entry.ident[0], entry.ident[1]))
            traceback.print_exc()
    return False


def hasHandlers(event):
    return bool(_handlers.get(event))


def handlerNames(event):
    """调试 / 测试用：event 的处理函数（模块, 函数名），按执行顺序。"""
    return [entry.ident for entry in _handlers.get(event, ())]


def clearAll():
    """测试用：清空全部登记。"""
    _handlers.clear()
