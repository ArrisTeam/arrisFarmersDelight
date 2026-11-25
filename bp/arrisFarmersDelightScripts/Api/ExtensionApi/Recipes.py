# -*- coding: utf-8 -*-
"""Recipes - 门面上的配方接口 ext.recipes：厨锅（cooking）、砧板（cutting）、营火烹饪（campfire_cooking）的登记、查询、删除（双端，不碰引擎）

    createBuilder(配方 ID, 类型)          一句一句写（RecipeBuilder），.register() 登记
    registerFromJson(JSON 文本或字典, 配方 ID=None)   JE 写法的配方 JSON（Shared/Rules/RecipeJson.py）；ID 不给就用 JSON 里的 "id"
    getRecipeById(ID) / getRecipesOfType(类型)        查：写成 JE 配方 JSON 的样子（带 "id"），删掉的查不到
    removeRecipe(ID)                       删：厨锅打墓碑，砧板 / 营火真删（表同步把删除发给客户端）
    matchCooking(物品列表)                 只读：这几件东西在厨锅里做成什么（给别的模组的锅做回退）；没有是 None
    onRecipesChanged(处理函数)             syncToClients 之后、行为包里的配方 JSON 读完之后调 handler(event)：event.types、event.recipeIds
    syncToClients(类型=None, ID=None)      进服之后改了配方：现在就发给在线的玩家（不调也会在 5 秒内补发，见 Server/TableSync.py）
登记、删除、syncToClients、onRecipesChanged 只在服务端（客户端一律返回 {"ok": False, "error": "server_only"}，不抛：两端可以共用登记的代码）；
查询和 matchCooking 两端都能用（客户端读的是表同步过来的那一份）。服务端要做的引擎的事（现在就同步）由服务端入口在广播 ready 之前交进来（provide）。
"""
import json
import traceback

from . import RecipeIds, RecipeTables, RecipeViews
from .RecipeBuilder import RecipeBuilder
from ...Shared.Data.CookingPotRecipes import CookingPotRecipeList
from ...Shared.Rules import CookingPot, RecipeJson

_services = {}                 # 服务端入口交进来的：{"syncNow": 现在就把表同步发给在线玩家的函数}
_handlers = []                 # onRecipesChanged 登记的处理函数（按登记的先后，不重复）
_reported = set()              # 出过错、已经打过调用栈的处理函数（同一个只打一次）


def provide(**services):
    """服务端入口（Server/ExtensionReady.py）交进来引擎那边的事：syncNow=函数。"""
    _services.update(services)


class RecipesChanged(object):
    """onRecipesChanged 的处理函数收到的：types 是改动涉及的配方类型（"cooking" / "cutting" / "campfire_cooking"，不分类型时 None），
    recipeIds 是调用方给的配方 ID（没给时 None）。以后只加属性，不改已有的。"""

    def __init__(self, types, recipeIds):
        self.types = types
        self.recipeIds = recipeIds


def notify(types=None, recipeIds=None):
    """按登记的先后调 onRecipesChanged 的处理函数；一个抛了异常只打一次调用栈，不耽误别的。"""
    event = RecipesChanged(types, recipeIds)
    for handler in list(_handlers):
        try:
            handler(event)
        except Exception:  # noqa: BLE001 - 别的模组的处理函数出错不能连累农夫乐事和别的处理函数
            if id(handler) not in _reported:
                _reported.add(id(handler))
                print("[arrisFarmersDelight] 新联动接口：onRecipesChanged 的处理函数出错（别的模组的），之后再出错不再打印")
                traceback.print_exc()


def _list(value):
    if value is None:
        return None
    return [value] if not isinstance(value, (list, tuple)) else list(value)


def _asItem(item):
    """物品字典 / (物品名, aux) / 物品名 -> 物品字典；空的是 None。"""
    if isinstance(item, dict):
        return item if item.get("newItemName") else None
    if isinstance(item, (tuple, list)) and len(item) == 2:
        return {"newItemName": item[0], "newAuxValue": item[1], "count": 1}
    return {"newItemName": item, "newAuxValue": 0, "count": 1} if item else None


class Recipes(object):
    """一端的 ext.recipes。"""

    def __init__(self, side):
        self._side = side

    def _refused(self, recipeId=None):
        return RecipeTables.answer(False, "server_only", recipeId) if self._side != "server" else None

    def createBuilder(self, recipeId, recipeType):
        return RecipeBuilder(recipeId, recipeType, self._register)

    def registerFromJson(self, source, recipeId=None):
        """登记一份 JE 写法的配方 JSON（文本或已经读出来的字典）；配方 ID 不给就用 JSON 里的 "id"。"""
        refused = self._refused(recipeId)
        if refused is not None:
            return refused                   # 客户端：先答 server_only，坏文本也一样（不先去读它）
        data = source
        if not isinstance(source, dict):
            try:
                data = json.loads(source)
            except (TypeError, ValueError) as error:
                return RecipeTables.answer(False, "invalid_json", recipeId, message=str(error))
        return self._register(data, recipeId if recipeId is not None else (data.get("id") if isinstance(data, dict) else None))

    def _register(self, data, recipeId):
        refused = self._refused(recipeId)
        if refused is not None:
            return refused
        recipeId = RecipeJson.text(recipeId)
        if RecipeIds.split(recipeId) is None:
            return RecipeTables.answer(False, "invalid_id", recipeId)
        spec, problem = RecipeJson.parse(data)
        if problem is not None:
            return RecipeTables.answer(False, "invalid_recipe", recipeId, message=problem)
        return RecipeTables.register(spec, recipeId)

    def getRecipeById(self, recipeId):
        """这个 ID 的配方（JE 配方 JSON 的样子，带 "id"）；没有或已经删了是 None。"""
        return RecipeViews.view(recipeId)

    def getRecipesOfType(self, recipeType):
        """这一类的全部配方（同上的样子）；类型不认识是 []。"""
        kind = RecipeIds.typeOf(recipeType)
        return [RecipeViews.view(recipeId) for recipeId in RecipeTables.idsOf(kind)] if kind else []

    def removeRecipe(self, recipeId):
        return self._refused(recipeId) or RecipeTables.remove(recipeId)

    def matchCooking(self, items):
        """只读：这几件东西（物品字典、(物品名, aux) 或物品名，一件算一格）在厨锅里做成什么：
        {"id", "result": 成品物品字典（count 是一份出几个）, "container": 盛它的容器 (物品名, aux) 或 None, "pushItems": 余料}；做不成是 None。"""
        dicts = [_asItem(item) for item in items or ()]
        index = CookingPot.matchIndex(dicts)
        if index is None:
            return None
        meal, pushed = CookingPot.matchRecipe(dicts)
        index = int(index)                   # 上面已经排除了 None（机审的 pylint 推不出来）
        vessel = CookingPot.vesselOf(meal["newItemName"])     # 锅实际会用的：这个成品的第一条活配方的容器（锅只记得成品）
        return {"id": RecipeIds.cookingIds(CookingPotRecipeList)[index], "result": meal,
                "container": tuple(vessel) if vessel else None, "pushItems": pushed}

    def onRecipesChanged(self, handler):
        refused = self._refused()
        if refused is not None:
            return refused
        if not callable(handler):
            return RecipeTables.answer(False, "invalid_handler", None)
        if handler not in _handlers:
            _handlers.append(handler)
        return RecipeTables.answer(True, None, None)

    def syncToClients(self, recipeTypes=None, recipeIds=None):
        """进服之后改了配方：现在就把表的改动发给在线的玩家，再通知 onRecipesChanged 的处理函数。"""
        refused = self._refused()
        if refused is not None:
            return refused
        types = _list(recipeTypes)
        if types is not None and any(RecipeIds.typeOf(value) is None for value in types):
            return RecipeTables.answer(False, "invalid_recipe_types", None)
        syncNow = _services.get("syncNow")
        if syncNow is not None:
            syncNow()
        notify([RecipeIds.typeOf(value) for value in types] if types is not None else None, _list(recipeIds))
        return RecipeTables.answer(True, None, None)
