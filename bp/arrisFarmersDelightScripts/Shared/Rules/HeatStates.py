# -*- coding: utf-8 -*-
"""HeatStates - 热源方块的状态条件：满足没有、登记时写法对不对、按 aux 列出满足条件的 aux（双端，纯规则）

条件表是 Shared/Data/Cooking.HeatSourceStateDict：{方块名: {状态名: 条件}}，一个方块的几条条件都满足才算（规则在 Shared/Rules/HeatSources）。
条件三种写法：
- 一个值（str / int / bool）：状态等于它；布尔照 HeatSources 认点燃状态的写法，True 也认 1、"true"，False 也认 0、"false"；
- 一组值（list / tuple，不空，元素是上面那几种）：状态是其中之一；
- 数值范围 {"min": n} / {"max": n}（两个可以都写，min 不大于 max，含两端）：状态是数（布尔不算）而且在范围里。
状态读不到（None、不是字典）、缺这个状态：不满足。

客户端读不到方块状态（官方文档：GetBlockStates / GetBlockStatesFromAuxValue 只有服务端有），只有 GetBlock 给的 (名字, aux)，
所以服务端按条件列出满足条件的 aux（auxSet，引擎的 GetBlockStatesFromAuxValue 当 read）给客户端（Shared/Data/Cooking.HeatSourceAuxDict）。
aux 的来历（Strata 引擎研究 kb/engine/bp/10_blocks/types/states_permutations.md §2）：各状态按位拼起来，每个状态占 ⌈log₂(值个数)⌉ 位，
值个数不是 2 的幂时有几个位组合没有方块——炼药锅的 fill_level 有 7 个值（0–6），aux 7、15、23 是空号；熔岩（cauldron_liquid 的第 2 个值）
是 8 + fill_level（3.10 实机：服务端熔岩 6 级读到 14）。所以问到空号不能停（停在 7 就漏了熔岩的 9–14），怎么停见 auxSet。
引擎对空号、越界的 aux 给什么没在游戏里量过：None、{}、不是字典、和前面某个 aux 一模一样的状态（夹回 / 绕回）都当"这个 aux 没有方块"。
"""
from .TableWire import INT_TYPES, TEXT, toStr

_TRUE = (True, 1, "true", "True")
_FALSE = (False, 0, "false", "False")
_INF = float("inf")
_BAD = object()
RANGE_KEYS = ("min", "max")
LIMIT = 1024        # 最多问到 aux 1023（10 位）：热源方块用不到更多位的状态；引擎一直给有效状态时也停在这里
MIN_SCAN = 16       # 至少问到 aux 15：aux 0 问不出东西（方块不认识、接口一时不通）也多看一段


def _isNumber(value):
    return isinstance(value, INT_TYPES + (float,)) and not isinstance(value, bool)


def _same(value, expected):
    if isinstance(expected, bool):
        return value in (_TRUE if expected else _FALSE)
    if isinstance(value, bool):
        return False                    # 布尔状态只和写成布尔的条件比（Python 里 True == 1，这里不认）
    return toStr(value) == expected


def _fits(value, condition):
    if isinstance(condition, dict):
        if not _isNumber(value):
            return False
        low, high = condition.get("min"), condition.get("max")
        return (low is None or value >= low) and (high is None or value <= high)
    if isinstance(condition, (list, tuple)):
        return any(_same(value, option) for option in condition)
    return _same(value, condition)


def matches(states, conditions):
    """states（引擎读到的方块状态）满不满足 conditions 的每一条；读不到状态、缺状态、条件是空的都不满足。"""
    if not isinstance(states, dict) or not isinstance(conditions, dict) or not conditions:
        return False
    for name, condition in conditions.items():
        if name not in states or not _fits(states[name], condition):
            return False
    return True


# ---------------------------------------------------------------- 登记时的写法

def _scalar(value):
    value = toStr(value)
    if isinstance(value, (bool, str)):
        return value
    if isinstance(value, INT_TYPES):
        return int(value)
    return _BAD


def _normalRange(condition):
    bounds = {}
    for key, bound in condition.items():
        key = toStr(key)
        if key not in RANGE_KEYS:
            return None, "范围只能写 min / max"
        if not _isNumber(bound) or bound != bound or bound in (_INF, -_INF):
            return None, "min / max 要是有限的数"
        bounds[key] = int(bound) if isinstance(bound, INT_TYPES) else bound
    if not bounds:
        return None, "范围至少写 min、max 之一"
    if "min" in bounds and "max" in bounds and bounds["min"] > bounds["max"]:
        return None, "min 比 max 大"
    return bounds, None


def _normalCondition(condition):
    if isinstance(condition, dict):
        return _normalRange(condition)
    if isinstance(condition, (list, tuple)):
        values = [_scalar(option) for option in condition]
        if not values:
            return None, "一组值不能是空的"
        if any(value is _BAD for value in values):
            return None, "一组值里只能写 str / int / bool"
        return values, None
    value = _scalar(condition)
    if value is _BAD:
        return None, '只能写一个值（str / int / bool）、一组值（list）或范围（{"min": n, "max": n}）'
    return value, None


def normalize(conditions):
    """登记口（ext.registerHeatSource 的 states）给的条件 → (规整后的条件, None)；写法不对 → (None, 哪里不对)。
    规整：状态名和字符串换成 str（py2 的 unicode），一组值换成 list，整数统一成 int，范围只留写了的 min / max。"""
    if not isinstance(conditions, dict) or not conditions:
        return None, "states 要是不空的字典 {状态名: 条件}"
    found = {}
    for name, condition in conditions.items():
        key = toStr(name)
        if not isinstance(key, str) or not key or key != key.strip():
            return None, "状态名 %r 不对" % (name,)
        value, problem = _normalCondition(condition)
        if problem is not None:
            return None, "状态 %s 的条件 %r：%s" % (key, condition, problem)
        found[key] = value
    return found, None


# ---------------------------------------------------------------- 按 aux 列出满足条件的

def _plain(value):
    if isinstance(value, bool) or isinstance(value, float):
        return value
    if isinstance(value, INT_TYPES):
        return int(value)
    if isinstance(value, TEXT):
        return toStr(value)
    return repr(value)


def _key(states):
    """一份状态的可比较的样子：不是字典、空字典给 None（当这个 aux 没有方块）；键和值里的 unicode 换成 str、整数统一成 int。"""
    if not isinstance(states, dict) or not states:
        return None
    return tuple(sorted((toStr(name) if isinstance(name, TEXT) else repr(name), _plain(value)) for name, value in states.items()))


def auxSet(read, conditions, limit=LIMIT):
    """满足 conditions 的 aux：read(aux) 给这个 aux 的方块状态（服务端：引擎的 GetBlockStatesFromAuxValue）。
    返回 {"aux": 升序的列表, "top": 问出过状态的最大 aux（一个都没有是 -1）, "asked": 问了几个 aux}。
    停：问到 limit；或者问到 max(MIN_SCAN, 2 × (top + 1)) 还没有新的有效 aux。按位拼的 aux 里，一个有效 aux 后面的下一个有效 aux
    一定比 2 × (它 + 1) 小（低位的几个状态都满了才进位到上一个状态，而低位的最大值至少占了它那几位的一半），所以中间的空号不会让它漏掉；
    引擎越界之后一直给 None / {} / 前面出现过的状态时，也停在这里。"""
    found, seen, top, asked = [], set(), -1, 0
    for aux in range(limit):
        if aux >= max(MIN_SCAN, 2 * (top + 1)):
            break
        asked += 1
        states = read(aux)
        key = _key(states)
        if key is None or key in seen:
            continue
        seen.add(key)
        top = aux
        if matches(states, conditions):
            found.append(aux)
    return {"aux": found, "top": top, "asked": asked}
