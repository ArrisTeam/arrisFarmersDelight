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
"""
from . import RecipeIds

ACTIONS = {"knife": "knife_dig", "axe": "axe_dig", "pickaxe": "pickaxe_dig", "shovel": "shovel_dig", "hoe": "hoe_dig", "shears": "shears_dig"}
JSON_TYPES = {"cooking": "farmersdelight:cooking", "cutting": "farmersdelight:cutting", "campfire_cooking": "minecraft:campfire_cooking"}

try:
    _TEXT = (str, unicode)  # noqa: F821 - py2
except NameError:
    _TEXT = (str,)


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
    if value in ACTIONS:
        return {"type": "farmersdelight:tool_action", "action": ACTIONS[value]}
    return option(value)


class RecipeBuilder(object):
    """一条配方的写法。register 由 ext.recipes 交进来：register(JE 写法的字典, 配方 ID) -> {"ok", "error", "id"}。"""

    def __init__(self, recipeId, recipeType, register):
        self._id = recipeId
        self._type = RecipeIds.typeOf(recipeType)
        self._rawType = recipeType
        self._register = register
        self._fields = {}
        self._ingredients = []
        self._results = []

    def ingredient(self, *options):
        """加一格配料：给几个就是这一格的几个选项（厨锅最多 6 格；砧板、营火只有一格、一样东西）。"""
        if options:
            self._ingredients.append(option(options[0]) if len(options) == 1 else [option(entry) for entry in options])
        return self

    def output(self, item, count=1, chance=None):
        """成品：厨锅、营火一个（count 是一份出几个，营火不看）；砧板可以几个，chance 是概率（缺省必出）。"""
        found = option(item)
        if count != 1:
            found["count"] = count
        if chance is not None:
            found["chance"] = chance
        self._results.append(found)
        return self

    def container(self, item):
        """厨锅：盛这道菜要的容器（JE 的 container）。"""
        self._fields["container"] = option(item)
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
        """查格式、登记：{"ok", "error", "id"}（error 见 docs/EXTENSION-API.md；格式不对时另有 "message" 说哪里不对）。"""
        return self._register(self.toJson(), self._id)
