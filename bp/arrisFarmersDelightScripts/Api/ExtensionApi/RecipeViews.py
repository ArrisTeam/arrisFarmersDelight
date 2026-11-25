# -*- coding: utf-8 -*-
"""RecipeViews - 新接口查配方时给的样子：一条配方写成 JE 配方 JSON（带 "id"），能原样交回 registerFromJson（双端，不碰引擎）

配方在哪、ID 怎么找在 RecipeTables.py；这里只管"写成什么样"：厨锅一格一格写回配料（格子的选项，没有格子的按第一种写法一格一样），
时间写回刻、经验照行里的；砧板写回工具的动作或物品列表、产物带概率；营火就是原料和成品。
"""
from .RecipeTables import TOOLS, _table, find
from ...Shared.Data.Cooking import CanCookedFoodDict
from ...Shared.Data.CookingPotRecipes import CookingPotRecipeList
from ...Shared.Rules import CookingPot, PotSlots


def _item(kind, count=None):
    found = {"item": kind[0]}
    if kind[1]:
        found["data"] = kind[1]
    if count is not None and count != 1:
        found["count"] = count
    return found


def _ingredient(slot):
    options = []
    for option in slot:
        parsed = PotSlots.parseOption(option)
        if parsed is not None:
            options.append({"tag": parsed[1]} if parsed[0] == "tag" else _item(parsed[1]))
    return options[0] if len(options) == 1 else options


def _number(value, default=None):
    try:
        return float(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def view(recipeId):
    """这个 ID 的配方写成 JE 配方 JSON 的样子（加上 "id"），能原样交回 registerFromJson；没有是 None。"""
    found = find(recipeId)
    return None if found is None else viewAt(found, recipeId)


def viewAt(found, recipeId):
    """已经找到的配方（RecipeTables.find / entriesOf 给的 (类型, 下标或键)）写成 JE 配方 JSON 的样子。"""
    kind, key = found
    if kind == "campfire_cooking":
        return {"id": recipeId, "type": "minecraft:campfire_cooking", "ingredient": {"item": key}, "result": CanCookedFoodDict[key]}
    if kind == "cutting":
        entry = _table(kind, key)[key]
        actions = [action for tools, _itemType, action in TOOLS.values() if tools is entry.get("tool")]
        tool = {"type": "farmersdelight:tool_action", "action": actions[0]} if actions else [{"item": name} for name in entry.get("tool") or ()]
        results = [dict(_item((result["itemName"], result.get("auxValue", 0)), result.get("count", 1)),
                        **({"chance": result["chance"]} if "chance" in result else {})) for result in entry["itemList"]]
        source = {"tag": key} if not isinstance(key, tuple) else _item(key)
        return {"id": recipeId, "type": "farmersdelight:cutting", "ingredients": [source], "tool": tool, "result": results}
    row = CookingPotRecipeList[key]
    slots = CookingPot.slotsOf(row) or [[entry] for entry in (CookingPot.waysOf(row) or [[]])[0]]
    data = {"id": recipeId, "type": "farmersdelight:cooking", "ingredients": [_ingredient(slot) for slot in slots],
            "result": _item(row["CookResult"], max(1, int(row.get("CookCount") or 1))),
            "cookingtime": int(round((_number(row.get("CookTime")) or CookingPot.DEFAULT_COOK_SECONDS) * 20)),
            "experience": _number(row.get("Experience"), CookingPot.DEFAULT_EXPERIENCE)}
    if row.get("Vessel"):
        data["container"] = _item(row["Vessel"])
    if row.get("text") and row["text"] != row["CookResult"][0]:
        data["text"] = row["text"]
    return data
