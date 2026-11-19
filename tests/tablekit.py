# -*- coding: utf-8 -*-
"""tablekit - 表同步（下游在服务端追加的内容发给客户端）离线测试的共用小工具（不是测试本身，跑器只收 test_*.py）

服务端和客户端是两个进程，各有一份 Shared/Data；离线只有一个进程，所以把行为包脚本根换个顶层包名再导入一遍（Package）：
同一份源码，模块对象和里面的表是各自的——一份当服务端、一份当客户端，消息经 transport 走一趟（前置包 Wire 的规矩核对一遍，再 JSON 来回：
py2 里字符串变 unicode、元组变列表，和网络上一样）。要测真的客户端模块（BoardView 这些，导入时认默认包名）时，默认包当客户端，
用 Pristine 记下它的表、用完放回去。downstream() 照 Ends Delight 的写法（LoadServerAddonScriptsAfter 里经联动契约追加）往一份包里追加东西。
"""
from __future__ import print_function

import importlib
import itertools
import json
import os
import sys
import types

import prereq  # noqa: F401 - 前置包不在这个仓库里：旁边没有它就跳过（tests/prereq.py）
import dgtest
import fdtest

Wire = dgtest.load("Shared.Wire")
_counter = itertools.count(1)

# downstream() 追加的东西的名字，测试对着它核对
KNIFE = "ends_delight:jade_knife"
CUT_KEY = ("ends_delight:ender_pearl", 0)
CUT_AXE_KEY = ("ends_delight:chorus_log", 0)
COOKABLE = "ends_delight:shulker_meat"
COOKED = "ends_delight:roasted_shulker_meat"
STOVE = "ends_delight:end_stove"
FEAST = "ends_delight:steamed_dragon_egg_stage1"
SAUCE = ("ends_delight:chorus_sauce", 0)
SUCCULENT = ("ends_delight:chorus_succulent", 0)
CHORUS_FRUIT = ("minecraft:chorus_fruit", 0)
MUSHROOM_VARIANT = [("ends_delight:chorus_mushroom", 0), ("ends_delight:chorus_mushroom", 0)]


class Package(object):
    """行为包脚本根的一份独立副本：name 是顶层包名；load("Shared.Rules.TableDiff") 导入这一份里的模块。"""

    def __init__(self, name=None):
        self.name = name or "fdcopy%d" % next(_counter)
        if self.name != fdtest.SCRIPTS:
            package = types.ModuleType(self.name)
            package.__path__ = [os.path.join(fdtest.BP, fdtest.SCRIPTS)]
            sys.modules[self.name] = package

    def load(self, dotted):
        return importlib.import_module(self.name + "." + dotted)

    def tables(self):
        return self.load("Shared.Rules.SyncTables").TABLES


DEFAULT = Package(fdtest.SCRIPTS)      # 其它测试和真的客户端 / 服务端模块导入时认的那一份


def transport(message):
    """网络上走一趟：Wire 的规矩（键 str、列表元素类型一致、没有元组和 unicode）核对一遍，再 JSON 来回。"""
    problem = Wire.wireProblem(message)
    assert problem is None, "载荷违反 Call 的规矩：%s" % problem
    return json.loads(json.dumps(message))


def deliver(messages, client, wire=transport):
    """把服务端的消息一条条发给 client 这份包：返回 [apply 的结果]。"""
    merge = client.load("Shared.Rules.TableMerge")
    return [merge.apply(wire(message)) for message in messages]


class Pristine(object):
    """某份包里各张同步表现在的样子：测试往里追加 / 并入东西之后 restore 放回去（就地改，对象不换，厨锅配方的索引和砧板的缓存也重算）。"""

    def __init__(self, package):
        self.package = package
        self.saved = []
        for name, kind, container in package.tables():
            if kind == "map":
                saved = dict(container)
            elif kind == "items":
                saved = list(container)
            else:
                saved = [(row, dict(row), list(row["Recipe"]) if "Recipe" in row else None) for row in container]     # 厨锅配方的 Recipe 列表就地放回；摆盘菜的行没有它
            self.saved.append((kind, container, saved))

    def restore(self):
        for kind, container, saved in self.saved:
            if kind == "map":
                container.clear()
                container.update(saved)
            elif kind == "items":
                container[:] = saved
            else:
                container[:] = [row for row, _fields, _variants in saved]
                for row, fields, variants in saved:
                    row.clear()
                    row.update(fields)
                    if variants is not None:
                        row["Recipe"][:] = variants
        self.package.load("Shared.Rules.CookingPot").rebuildIndex()
        self.package.load("Shared.Rules.BoardStation").invalidate()
        self.package.load("Shared.Rules.DishStation").rebuildIndex()


def recipe(result, variants, vessel=("minecraft:bowl", 0), text="紫颂酱", **extra):
    return dict({"Recipe": variants, "CookResult": result, "Vessel": vessel, "PushItem": [], "text": text}, **extra)


def downstream(package):
    """照 Ends Delight / Nether's Delight 的写法往这份包的表里追加（它们在 LoadServerAddonScriptsAfter 里，经 ModAttr 取到联动契约的三个函数）：
    砧板配方的 tool 是 obtain("knifeList") 拿到的那个列表本身（有的带多余的键），再往 knifeList 里加一把刀、斧列表里加一把斧；
    厨锅配方（含 AddCookingPotRecipe 给已有的菜加一种写法）；可烹饪物、炉灶、热源；盘装的盛宴。返回 obtain 拿到的 knifeList。"""
    legacy = package.load("Api.LegacyModAttr")
    interface, obtain, addRecipe = legacy.ArrisFarmersDelightInterface, legacy.ArrisFarmersDelightObtain, legacy.AddCookingPotRecipe
    knives, axes = obtain("knifeList"), obtain("axeList")
    interface("CuttingBoardDict", {
        CUT_KEY: {"itemList": [{"itemName": "ends_delight:ender_pearl_grain", "count": 4}], "tool": knives, "type": ""},
        CUT_AXE_KEY: {"itemList": [{"itemName": "minecraft:stick", "count": 2, "chance": 0.5}], "tool": axes, "item_type": "axe"},
    })
    knives.append(KNIFE)
    axes.append("ends_delight:chorus_axe")
    interface("StoveList", STOVE)
    interface("CanProvideHeatBlockList", STOVE)
    interface("CanCookedFoodDict", {COOKABLE: COOKED})
    interface("CookingPotRecipeList", recipe(SAUCE, [[SUCCULENT, CHORUS_FRUIT], [SUCCULENT, ("ends_delight:chorus_fruit_grain", 0)]]))
    interface("CookingPotRecipeList", recipe(("ends_delight:chorus_tea", 0), [[("ends_delight:chorus_flower", 0)]], vessel=("minecraft:glass_bottle", 0),
                                              text="紫颂茶", CookTime=5.0, CookCount=2, Experience=0.35))
    addRecipe("minecraft:mushroom_stew", list(MUSHROOM_VARIANT))
    interface("platePackagedFoodDict", {FEAST: {"target": "ends_delight:steamed_dragon_egg_stage2", "item": "ends_delight:steamed_dragon_egg"},
                                        "ends_delight:steamed_dragon_egg_leftover": {"target": None, "item": None}})
    return knives


def mushroomStew(package):
    """这份包的厨锅配方里蘑菇煲那一条。"""
    for row in package.load("Shared.Data.CookingPotRecipes").CookingPotRecipeList:
        if row["CookResult"][0] == "minecraft:mushroom_stew":
            return row
    raise AssertionError("没有蘑菇煲")


def snapshot(package):
    """各张同步表的值（深拷贝成能比较的普通结构，tool 引用按名字记）：两份包同步之后拿它比。"""
    refs = package.load("Shared.Rules.SyncTables").REFS
    names = dict((id(obj), name) for name, obj in refs.items())

    def plain(value):
        if isinstance(value, dict):
            return dict((key, plain(item)) for key, item in value.items())
        if isinstance(value, list):
            return ("ref", names[id(value)]) if id(value) in names else [plain(item) for item in value]
        return value

    def contents(container):
        items = container.items() if isinstance(container, dict) else enumerate(container)
        found = dict((key, plain(item)) for key, item in items)
        return found if isinstance(container, dict) else [found[index] for index in range(len(found))]

    return dict((name, contents(container)) for name, _kind, container in package.tables())
