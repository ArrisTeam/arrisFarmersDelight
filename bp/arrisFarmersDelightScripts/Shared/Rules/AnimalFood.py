# -*- coding: utf-8 -*-
"""AnimalFood - 原版动物认农夫乐事的食物：从生效的实体定义算出该给实体加哪几个组件（双端，纯规则）

服务端（Server/AnimalFood.py）读包栈里生效的实体定义，plan() 算一次"每个要补的组件在它的每个出处（顶层 components 或某个组件组）
在列表末尾追加了本包的条目以后的 JSON 串"，按实体类型记着；实体出现、换了组件组以后，拿 GetEntityDefinitions 给的定义栈折出
"现在每个组件由谁提供"，send() 给出要 AddActorComponent 的那几个——只给实体现在真有的组件、用它现在那个出处的值
（给成年的鸡加 ageable 会让它重新变成能长大的，野猫的 tempt 换成驯服猫那一组的值也不对）。
组件写在哪、哪些事件会换这些组件组，一律从定义里读：别的包改过的定义，就在改过的那份上追加。

定义栈的折法照引擎（Strata 引擎研究 11_entities/ENTITY_ENGINE.md §3、§10，3.9 / 3.10 实测）：栈从底往上，"+组"加上组里的组件、
盖掉同名的；"-组"拿掉组里有的组件，连顶层的同名组件一起拿掉；顶层（实体自己的 identifier）一直在，除非被"-组"拿掉。
栈里我们认不得的条目（AddActorComponent 自己压的 "##netease::组件名"、别的包的东西）不管。
"""
import json
import re

BASE = ""                       # 出处：顶层 components（组件组的名字不会是空串）
ENTITIES = "entities"
_NESTED = ("sequence", "randomize", "first_valid")
_TOKENS = re.compile(r'"(?:\\.|[^"\\])*"|,(\s*[}\]])')

try:
    _TEXT = (str, unicode)  # noqa: F821 - py2
except NameError:
    _TEXT = (str,)


def definitionPath(entityType):
    """原版的实体定义按短名放：minecraft:chicken -> entities/chicken.json。"""
    return "%s/%s.json" % (ENTITIES, entityType.split(":")[-1])


def _dropTrailingCommas(text):
    """对象 / 数组末尾多余的逗号去掉（引擎认这种写法，json 不认）；字符串里的不动。"""
    return _TOKENS.sub(lambda match: match.group(0) if match.group(1) is None else match.group(1), text)


def identifierOf(data):
    """定义里写的 identifier；形状不对是 None。"""
    entity = data.get("minecraft:entity") if isinstance(data, dict) else None
    description = entity.get("description") if isinstance(entity, dict) else None
    return description.get("identifier") if isinstance(description, dict) else None


def parse(text, identifier):
    """剥过注释的实体定义文本 -> 定义（dict）；不是 JSON、不是 identifier 这只实体的定义：None。"""
    if not isinstance(text, _TEXT) or not text.strip():
        return None
    try:
        data = json.loads(_dropTrailingCommas(text))
    except ValueError:
        return None
    return data if identifierOf(data) == identifier else None


def _itemName(entry):
    if isinstance(entry, _TEXT):
        return entry
    return entry.get("item") if isinstance(entry, dict) else None


def _copy(value):
    return json.loads(json.dumps(value))


def patched(component, field, extra):
    """组件的值（dict）在 field 列表的末尾追加 extra 里还没有的条目（按物品名比），给出 JSON 串；
    field 是单个字符串的当成一项的列表；组件不是 dict、没有 field、field 不是列表 / 字符串：看不懂，None。"""
    if not isinstance(component, dict):
        return None
    value = _copy(component)
    items = value.get(field)
    if isinstance(items, _TEXT):
        items = [items]
    if not isinstance(items, list):
        return None
    have = set(name for name in (_itemName(entry) for entry in items) if name is not None)
    for entry in extra:
        name = _itemName(entry)
        if name not in have:
            items.append(_copy(entry))
            have.add(name)
    value[field] = items
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


class Plan(object):
    """一种实体的补丁。identifier；base：顶层带着的、要补的组件；groups：{组件组: 组里带着的、要补的组件}；
    jsons：{(组件, 出处): 拼好的 JSON 串}（看不懂的那一处没有）；events：会加 / 减这些组件组的事件名（含经 trigger 转过去的）；
    missing：定义里哪儿都没有的组件；unreadable：[(组件, 出处)] 形状看不懂、不下发的。"""
    __slots__ = ("identifier", "base", "groups", "jsons", "events", "missing", "unreadable")


def _places(entity):
    components = entity.get("components")
    groups = entity.get("component_groups")
    places = [(BASE, components if isinstance(components, dict) else {})]
    if isinstance(groups, dict):
        places.extend(sorted((name, body) for name, body in groups.items() if isinstance(body, dict)))
    return places


def plan(definition, patches):
    """定义 + 这种动物的补丁 ((组件, 列表字段, 追加的条目), ...) -> Plan；一个能下发的都没有（定义里没有这些组件、都看不懂）是 None。"""
    entity = definition.get("minecraft:entity") if isinstance(definition, dict) else None
    if not isinstance(entity, dict):
        return None
    fields = dict((name, (field, extra)) for name, field, extra in patches)
    result = Plan()
    result.identifier, result.base, result.groups, result.jsons, result.unreadable = identifierOf(definition), frozenset(), {}, {}, []
    seen = set()
    for provider, components in _places(entity):
        found = frozenset(name for name in fields if name in components)
        for name in sorted(found):
            text = patched(components[name], fields[name][0], fields[name][1])
            if text is None:
                result.unreadable.append((name, provider))
            else:
                result.jsons[(name, provider)] = text
        seen.update(found)
        if provider == BASE:
            result.base = found
        elif found:
            result.groups[provider] = found
    result.missing = sorted(name for name in fields if name not in seen)
    result.events = refreshEvents(entity.get("events"), result.groups)
    return result if result.jsons else None


def _walk(node, touched, triggered):
    """一个事件（或它的一段）里加 / 减的组件组、trigger 到的本实体事件，连 sequence / randomize / first_valid 里套着的。"""
    if not isinstance(node, dict):
        return
    for key in ("add", "remove"):
        change = node.get(key)
        names = change.get("component_groups") if isinstance(change, dict) else None
        touched.update(name for name in (names if isinstance(names, list) else ()) if isinstance(name, _TEXT))
    trigger = node.get("trigger")
    if isinstance(trigger, dict) and trigger.get("target", "self") == "self":
        trigger = trigger.get("event")
    if isinstance(trigger, _TEXT):
        triggered.add(trigger)
    for key in _NESTED:
        for child in node.get(key) if isinstance(node.get(key), list) else ():
            _walk(child, touched, triggered)


def refreshEvents(events, groups):
    """会加 / 减 groups 里哪个组件组的事件名，加上 trigger 过去（转几手都算）的事件：这些事件之后组件回到定义里的值，要重新下发。"""
    if not isinstance(events, dict):
        return frozenset()
    result, links = set(), {}
    for name, body in events.items():
        touched, triggered = set(), set()
        _walk(body, touched, triggered)
        if touched.intersection(groups):
            result.add(name)
        links[name] = triggered
    grown = True
    while grown:
        grown = False
        for name, targets in links.items():
            if name not in result and targets & result:
                result.add(name)
                grown = True
    return frozenset(result)


def current(thePlan, stack):
    """GetEntityDefinitions 给的定义栈（["+minecraft:chicken", "+minecraft:chicken_adult", "-minecraft:chicken_baby", ...]）->
    {组件: 出处}：现在每个要补的组件由谁提供。栈读不懂（不是列表）是 None。"""
    if not isinstance(stack, (list, tuple)):
        return None
    where = dict((name, BASE) for name in thePlan.base)
    for entry in stack:
        if not isinstance(entry, _TEXT) or entry[:1] not in ("+", "-"):
            continue
        name = entry[1:]
        if name == thePlan.identifier:
            provider, components = BASE, thePlan.base
        elif name in thePlan.groups:
            provider, components = name, thePlan.groups[name]
        else:
            continue
        for component in components:
            if entry[0] == "+":
                where[component] = provider
            else:
                where.pop(component, None)
    return where


def send(thePlan, stack):
    """要 AddActorComponent 的 [(组件, JSON 串)]，按组件名排。栈读不懂时只给顶层的（组件组现在是哪个说不准，宁可不下发）。"""
    where = current(thePlan, stack)
    if where is None:
        where = dict((name, BASE) for name in thePlan.base)
    return [(name, thePlan.jsons[(name, provider)]) for name, provider in sorted(where.items()) if (name, provider) in thePlan.jsons]
