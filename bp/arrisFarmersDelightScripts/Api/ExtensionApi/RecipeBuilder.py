# -*- coding: utf-8 -*-
"""RecipeBuilder - 一条配方一句一句写出来再登记（ext.recipes.createBuilder 给的）：厨锅、砧板、营火烹饪（双端，不碰引擎）

字段照 JE 的配方 JSON 取名，写出来的就是一份 JE 写法的配方 JSON（toJson），登记时和 registerFromJson 走同一条路
（Shared/Rules/RecipeJson.parse 查格式，Api/ExtensionApi/RecipeTables.register 写表），所以两种写法的含义一模一样。例：

    recipes = ext.recipes
    builder = recipes.createBuilder("mymod:cooking/tomato_stew", "cooking")
    builder.ingredient("#common:tomato").ingredient("#common:raw_beef", "mymod:tofu").output("mymod:tomato_stew")
    builder.container("minecraft:bowl").cookingTime(200).experience(1.0)
    answer = builder.register()          # {"ok": True, "error": None, "id": "mymod:cooking/tomato_stew"}

物品写 "ns:name"（aux 0）或 ("ns:name", aux)，标签写 "#标签名"；一次 ingredient 是一格，给几个就是这一格的几个选项。
机械动力的写法也认（关键字）：ingredient("ns:name", data=aux)、ingredient(..., count=2)（厨锅一格一件：两格同样的）、
ingredientTag("标签名", count=1)；output(物品, count=1, data=0, chance=None)、container(物品, data=0) 的参数次序和机械动力一样。
写错了（不认识的关键字、把数量当成位置参数……）不抛：记下来，register() 答 invalid_recipe（message 说哪里不对）。
"""
from . import RecipeIds
from ...Shared.Rules.TableWire import isInt

ACTIONS = {"knife": "knife_dig", "axe": "axe_dig", "pickaxe": "pickaxe_dig", "shovel": "shovel_dig", "hoe": "hoe_dig", "shears": "shears_dig"}
JSON_TYPES = {"cooking": "farmersdelight:cooking", "cutting": "farmersdelight:cutting", "campfire_cooking": "minecraft:campfire_cooking"}

try:
    _TEXT = (str, unicode)  # noqa: F821 - py2
except NameError:
    _TEXT = (str,)
try:
    _NUMBERS = (int, long, float)  # noqa: F821 - py2
except NameError:
    _NUMBERS = (int, float)


def option(value):
    """一个选项（"ns:name" / (名, aux) / "#标签" / 已经是 JE 写法的字典）-> JE 写法（{"item", "data"} / {"tag"}）。"""
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, (tuple, list)) and len(value) == 2:
        return {"item": value[0], "data": value[1]} if value[1] else {"item": value[0]}
    if isinstance(value, _TEXT) and value.startswith("#"):
        return {"tag": value[1:]}
    return {"item": value}


def tool(value):
    """工具：刀 / 斧 / 镐 / 锹 / 锄 / 剪刀（"knife"……）、"#标签"、"ns:name"，或它们的列表 -> JE 写法。"""
    if isinstance(value, (list, tuple)):
        return [tool(entry) for entry in value]
    if isinstance(value, _TEXT) and value in ACTIONS:
        return {"type": "farmersdelight:tool_action", "action": ACTIONS[value]}
    return option(value)


class RecipeBuilder(object):
    """一条配方的写法。register 由 ext.recipes 交进来：register(JE 写法的字典, 配方 ID, 写法上的错或 None) -> {"ok", "error", "id"}。"""

    def __init__(self, recipeId, recipeType, register):
        self._id = recipeId
        self._type = RecipeIds.typeOf(recipeType)
        self._rawType = recipeType
        self._register = register
        self._fields = {}
        self._ingredients = []
        self._results = []
        self._problems = []          # 写法上的错：不抛，register() 时答 invalid_recipe

    def _wrong(self, problem):
        self._problems.append(problem)
        return self

    def ingredient(self, *options, **keywords):
        """加一格配料：给几个就是这一格的几个选项（厨锅最多 6 格；砧板、营火只有一格、一样东西）。
        关键字照机械动力：data=aux（只给一样物品时），count=几格（厨锅一格一件，count=2 是两格同样的；砧板、营火只能是 1）。"""
        count, data = keywords.pop("count", 1), keywords.pop("data", None)
        if keywords:
            return self._wrong("ingredient() 不认识的参数：%s" % ", ".join(sorted(keywords)))
        numbers = [entry for entry in options if isinstance(entry, _NUMBERS) and not isinstance(entry, bool)]
        if numbers:
            return self._wrong("ingredient() 的位置参数是这一格的几个选项，%r 不是物品：数量写 count=，aux 写 data=" % (numbers[0],))
        if not isInt(count) or count < 1:
            return self._wrong("ingredient() 的 count 要是正整数，给的是 %r" % (count,))
        if data is not None:
            if len(options) != 1 or not isinstance(options[0], _TEXT) or options[0].startswith("#"):
                return self._wrong("ingredient(..., data=) 只用在写成 \"ns:name\" 的一样物品上（标签没有 aux；几个选项时写 (物品名, aux)）")
            options = ((options[0], data),)
        for _copy in range(count if options else 0):
            self._ingredients.append(option(options[0]) if len(options) == 1 else [option(entry) for entry in options])
        return self

    def ingredientTag(self, tag, count=1):
        """机械动力的写法：加 count 格这个标签（标签名写不写 # 都行）。"""
        if not isinstance(tag, _TEXT) or not tag.lstrip("#"):
            return self._wrong("ingredientTag() 要给标签名，给的是 %r" % (tag,))
        return self.ingredient("#" + tag.lstrip("#"), count=count)

    def output(self, item, count=1, data=0, chance=None):
        """成品：厨锅、营火一个（count 是一份出几个，营火不看）；砧板可以几个，chance 是概率（缺省必出）。
        参数次序照机械动力：(物品, count, data, chance)。"""
        if data and not isinstance(item, _TEXT):
            return self._wrong("output(..., data=) 只用在写成 \"ns:name\" 的物品上")
        found = option((item, data) if data else item)
        if count != 1:
            found["count"] = count
        if chance is not None:
            found["chance"] = chance
        self._results.append(found)
        return self

    def container(self, item, data=0):
        """厨锅：盛这道菜要的容器（JE 的 container）；data 是它的 aux（照机械动力的写法）。"""
        if data and not isinstance(item, _TEXT):
            return self._wrong("container(..., data=) 只用在写成 \"ns:name\" 的物品上")
        self._fields["container"] = option((item, data) if data else item)
        return self

    def cookingTime(self, ticks):
        """厨锅：一份煮多少刻（JE 的单位，20 刻一秒；缺省 200）。"""
        self._fields["cookingtime"] = ticks
        return self

    def experience(self, value):
        """厨锅：煮出一份给多少经验（缺省 0，JE 的缺省）。"""
        self._fields["experience"] = value
        return self

    def tool(self, value):
        """砧板：用什么工具切。"""
        self._fields["tool"] = tool(value)
        return self

    def text(self, name):
        """厨锅：经典界面食谱格里的名字（缺省是成品的物品名）。"""
        self._fields["text"] = name
        return self

    def toJson(self):
        """写成 JE 配方 JSON 的样子（带 "id"）：可以存成 farmersdelight_recipes/ 下的文件，也能交给 registerFromJson。"""
        data = dict(self._fields)
        data["type"] = JSON_TYPES.get(self._type, self._rawType)
        data["id"] = self._id
        if self._type == "campfire_cooking":
            if self._ingredients:
                data["ingredient"] = self._ingredients[0] if len(self._ingredients) == 1 else self._ingredients
            if self._results:
                data["result"] = self._results[0]["item"] if len(self._results) == 1 and "item" in self._results[0] else self._results
            return data
        data["ingredients"] = list(self._ingredients)
        if self._type == "cutting":
            data["result"] = list(self._results)
        elif self._results:
            data["result"] = self._results[0] if len(self._results) == 1 else list(self._results)
        return data

    def register(self):
        """查格式、登记：{"ok", "error", "id"}（error 见 docs/EXTENSION-API.md；格式不对、写法上有错时另有 "message" 说哪里不对）。"""
        return self._register(self.toJson(), self._id, self._problems[0] if self._problems else None)
