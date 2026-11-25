# -*- coding: utf-8 -*-
"""RecipeJson - 配方 JSON（JE 农夫乐事的写法，物品名写网易的）读成规整的配方：厨锅、砧板、营火烹饪（双端，纯规则）

格式就是 JE 农夫乐事的配方 JSON（recipes/cooking、recipes/cutting）和原版的营火配方，把物品名换成网易版的就能用：
- 厨锅 {"type": "farmersdelight:cooking", "ingredients": [配料, ...]（1 到 6 格）, "result": {"item", "count"}, "container": {"item"},
       "cookingtime": 刻（缺省 200）, "experience": 数（缺省 0，JE 的缺省）, "text": 经典界面食谱格里的名字（农夫乐事加的，可不写）}；
- 砧板 {"type": "farmersdelight:cutting", "ingredients": [一个配料], "tool": 工具, "result": [{"item", "count", "chance"}, ...]（1 到 4 个）}；
- 营火 {"type": "minecraft:campfire_cooking", "ingredient": 物品, "result": 物品}（煎锅、炉灶、手持煎锅读的那张表，只认物品）。
配料：{"item": 名, "data": aux}、{"tag": 标签名}，或它们的列表（一格几个选项）；物品也可以直接写成字符串 "ns:name" / "#标签名"。
JE 的标签名（forge:...）照 aliases（Shared/Data/Tags.JE_NAMES 反过来查）换成 common: 名，认不出的标签名原样用（别的模组可能登记了它）。
工具：JE 的 {"type": "farmersdelight:tool_action", "action": "knife_dig"} 这类、{"tag": "forge:tools/knives"} 这类、{"item": 名}，或它们的列表。
"id"、"recipe_book_tab"、"group"、"sound" 这些不管（id 由调用的人处理）。
parse(数据, aliases) -> (规整的配方, None) 或 (None, 一句说哪里不对的话)：
    {"type": "cooking", "slots": [[选项, ...], ...], "result": (名, aux), "count": 个数, "container": (名, aux) 或 None,
     "cookingTime": 刻, "experience": 数, "text": 名字或 None}
    {"type": "cutting", "input": (名, aux) 或 "#标签", "tool": 工具种类（"knife"……）或 [物品名], "results": [{"itemName", "count", ("auxValue"), ("chance")}]}
    {"type": "campfire_cooking", "input": 名, "result": 名}
"""
from ..Data.Tags import JE_NAMES
from .TableWire import INT_TYPES

_NUMBER = INT_TYPES + (float,)      # py2 的 long 也算

TYPES = {"cooking": "cooking", "farmersdelight:cooking": "cooking", "cutting": "cutting", "farmersdelight:cutting": "cutting",
         "campfire_cooking": "campfire_cooking", "minecraft:campfire_cooking": "campfire_cooking"}
# JE 的工具（tool_action / 标签）-> 工具种类：Shared/Data/Cutting.py 的工具表加物品类型
TOOL_ACTIONS = {"knife_dig": "knife", "axe_dig": "axe", "axe_strip": "axe", "pickaxe_dig": "pickaxe", "shovel_dig": "shovel",
                "hoe_dig": "hoe", "shears_dig": "shears"}
TOOL_TAGS = {"forge:tools/knives": "knife", "farmersdelight:tools/knives": "knife", "common:knife": "knife", "arris:knife": "knife",
             "minecraft:axes": "axe", "minecraft:pickaxes": "pickaxe", "minecraft:shovels": "shovel", "minecraft:hoes": "hoe",
             "forge:shears": "shears"}
MOST_SLOTS = 6
MOST_RESULTS = 4

try:
    _TEXT = (str, unicode)  # noqa: F821 - py2
except NameError:
    _TEXT = (str,)


class _Bad(ValueError):
    pass


def text(value):
    """py2 的 unicode（json 读出来的）换成 utf-8 的 str：表里只放 str。"""
    if not isinstance(value, str) and isinstance(value, _TEXT):
        return value.encode("utf-8")
    return value


def _int(value, default, what):
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, _NUMBER) or int(value) != value or value < 0:
        raise _Bad("%s 要是不小于 0 的整数，给的是 %r" % (what, value))
    return int(value)


def _number(value, default, what):
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, _NUMBER) or value < 0:
        raise _Bad("%s 要是不小于 0 的数，给的是 %r" % (what, value))
    return float(value)


def _name(value, what):
    value = text(value)
    if not isinstance(value, str) or ":" not in value or " " in value or value.startswith("#"):
        raise _Bad("%s 要是 ns:name 这样的物品名，给的是 %r" % (what, value))
    return value


def _stack(value, what):
    """{"item": 名, "data": aux, "count": 个数} 或 "ns:name" -> (名, aux, 个数)。"""
    if isinstance(value, _TEXT):
        return _name(value, what), 0, 1
    if not isinstance(value, dict) or "item" not in value:
        raise _Bad('%s 要写成 {"item": 物品名}，给的是 %r' % (what, value))
    return _name(value["item"], what), _int(value.get("data"), 0, what + " 的 data"), _int(value.get("count"), 1, what + " 的 count")


def _option(value, aliases, what):
    """一个配料选项 -> (名, aux) 或 "#标签"。"""
    if isinstance(value, _TEXT) and text(value).startswith("#"):
        value = {"tag": text(value)[1:]}
    if isinstance(value, dict) and "tag" in value:
        tag = text(value["tag"])
        if not isinstance(tag, str) or ":" not in tag or " " in tag:
            raise _Bad("%s 的标签名 %r 写法不对" % (what, tag))
        return "#" + aliases.get(tag, tag)
    name, aux, _count = _stack(value, what)
    return (name, aux)


def _slot(value, aliases, what):
    options = value if isinstance(value, list) else [value]
    if not options:
        raise _Bad("%s 是空的" % what)
    return [_option(option, aliases, what) for option in options]


def _cooking(data, aliases):
    ingredients = data.get("ingredients")
    if not isinstance(ingredients, list) or not 1 <= len(ingredients) <= MOST_SLOTS:
        raise _Bad("ingredients 要是 1 到 %d 个配料" % MOST_SLOTS)
    name, aux, count = _stack(data.get("result"), "result")
    container = data.get("container")
    return {"type": "cooking", "slots": [_slot(entry, aliases, "第 %d 个配料" % (index + 1)) for index, entry in enumerate(ingredients)],
            "result": (name, aux), "count": max(1, count),
            "container": _stack(container, "container")[:2] if container is not None else None,
            "cookingTime": _int(data.get("cookingtime"), 200, "cookingtime"), "experience": _number(data.get("experience"), 0.0, "experience"),
            "text": text(data["text"]) if isinstance(data.get("text"), _TEXT) else None}


def _tool(value):
    for entry in (value if isinstance(value, list) else [value]):
        if isinstance(entry, dict) and text(entry.get("type")) == "farmersdelight:tool_action" and text(entry.get("action")) in TOOL_ACTIONS:
            return TOOL_ACTIONS[text(entry["action"])]
        if isinstance(entry, dict) and text(entry.get("tag")) in TOOL_TAGS:
            return TOOL_TAGS[text(entry["tag"])]
    items = [_name(entry["item"], "tool 的 item") for entry in (value if isinstance(value, list) else [value])
             if isinstance(entry, dict) and "item" in entry]
    if not items:
        raise _Bad('tool 认不出：要写 farmersdelight:tool_action 的 action、刀 / 斧 / 镐 / 锹 / 锄 / 剪刀的标签，或 {"item": 物品名}')
    return items


def _cutting(data, aliases):
    ingredients = data.get("ingredients")
    if not isinstance(ingredients, list) or len(ingredients) != 1:
        raise _Bad("砧板配方的 ingredients 要正好一个配料")
    options = _slot(ingredients[0], aliases, "配料")
    if len(options) != 1:
        raise _Bad("砧板配方的配料只能是一样东西或一个标签")
    results = data.get("result")
    if not isinstance(results, list) or not 1 <= len(results) <= MOST_RESULTS:
        raise _Bad("result 要是 1 到 %d 个产物" % MOST_RESULTS)
    found = []
    for index, entry in enumerate(results):
        name, aux, count = _stack(entry, "第 %d 个产物" % (index + 1))
        result = {"itemName": name, "count": max(1, count)}
        if aux:
            result["auxValue"] = aux
        chance = entry.get("chance") if isinstance(entry, dict) else None
        if chance is not None:
            result["chance"] = _number(chance, 1.0, "chance")
            if result["chance"] > 1.0:
                raise _Bad("chance 不能大于 1")
        found.append(result)
    return {"type": "cutting", "input": options[0], "tool": _tool(data.get("tool")), "results": found}


def _campfire(data, aliases):
    source = data.get("ingredient")
    if isinstance(source, list) and len(source) == 1:
        source = source[0]
    if isinstance(source, dict) and "tag" in source:
        raise _Bad("营火烹饪只认物品：煎锅、炉灶读的那张表按物品名查（要按标签煎，给原料写原版的营火配方）")
    result = data.get("result")
    name = _stack(result, "result")[0] if not isinstance(result, _TEXT) else _name(result, "result")
    return {"type": "campfire_cooking", "input": _stack(source, "ingredient")[0], "result": name}


def javaAliases():
    """JE 的标签名 -> 词表的 common: 名（Shared/Data/Tags.JE_NAMES 反过来；测试保证一个 JE 名只对应一个）。"""
    return dict((javaName, name) for name, javaNames in JE_NAMES.items() for javaName in javaNames)


ALIASES = javaAliases()


def parse(data, aliases=None):
    """一份配方 JSON（读出来的字典）-> (规整的配方, None)；读不成是 (None, 哪里不对)。aliases 缺省是 ALIASES。"""
    if not isinstance(data, dict):
        return None, "配方要是 JSON 对象"
    kind = TYPES.get(text(data.get("type")))
    if kind is None:
        return None, "type %r 不认识：要 farmersdelight:cooking、farmersdelight:cutting 或 minecraft:campfire_cooking" % (data.get("type"),)
    try:
        return {"cooking": _cooking, "cutting": _cutting, "campfire_cooking": _campfire}[kind](data, ALIASES if aliases is None else aliases), None
    except _Bad as error:
        return None, str(error)
