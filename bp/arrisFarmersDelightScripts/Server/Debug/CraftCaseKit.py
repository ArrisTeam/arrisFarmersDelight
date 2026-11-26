# -*- coding: utf-8 -*-
"""CraftCaseKit - 工作台标签配方自检的用例：怎么摆、做完一份该有什么（服务端，只给 Server/Debug/McdkCraftTest 用）

用例来自 tools/gen_crafts.py 生成的 CraftCases（31 份写了标签的工作台配方），每份两例：base 标签格取第一个成员（农夫乐事自己的 / 原版的），
swap 换另一个成员（引擎现在的成员，别的包并进标签的也算，挑最后一个不一样的；标签只有一个成员时 same 为真）。
expect 是做一份之后合成格 + 背包里该有的全部东西：成品，加上剩下的容器（有序配方是 result 数组写的；无序配方按放进去的物品查 Remainders，
keeps 原样留下）。dish 为真的一例，料正好是砧板上某道菜的一条配方（Shared/Rules/DishStation.isDishCraft）：装着前置包、砧板站点登上了时
工作台拦这一下（Compat/Diegesis/DishCrafts），格子里的料一件不少、什么都不出——拦截在不在看 vetoActive()。
"""
from . import CraftCases
from ..EventRegistry import handlerNames
from ...Shared.Data import Remainders
from ...Shared.Rules import DishStation, ItemTags

CRAFT_EVENT = "CraftItemOutputChangeServerEvent"
VETO = "DishCrafts"          # 拦砧板菜的处理函数所在的模块（Compat/Diegesis/DishCrafts：没装前置包、砧板站点没登上时不导入、不登记）


def members(tag):
    """标签现在的成员（引擎的，别的包并进来的也算）；引擎答不出时用生成表里抄的静态成员。"""
    return tuple(ItemTags.itemsOf(tag)) or tuple(CraftCases.MEMBERS.get(tag, ()))


def pick(cell, avoid=None):
    """格子里放什么：物品就是它；"#标签" 取第一个成员，给了 avoid 就挑最后一个不一样的（没有就还是 avoid）。"""
    if cell is None or not cell.startswith("#"):
        return cell
    found = members(cell[1:])
    if avoid is None:
        return found[0] if found else None
    others = [name for name in found if name != avoid]
    return others[-1] if others else avoid


def expected(recipe, items):
    """做一份之后合成格 + 背包里该有的：成品，加上剩下的容器（有序配方是 result 数组写的；无序配方按放进去的物品查 Remainders，keeps 原样留下）。"""
    want = {recipe["result"][0]: recipe["result"][1]}
    extras = list(recipe["extras"])
    if recipe["kind"] == "shapeless":
        for cell, name in zip(recipe["grid"], items):
            left = name if name is not None and cell in recipe["keeps"] else Remainders.craftRemainderOf(name)
            if name is not None and left:
                extras.append((left, 1))
    for name, count in extras:
        want[name] = want.get(name, 0) + count
    return want


def ingredients(items):
    """被拦下时合成格里该原样留着的：{物品名: 件数}（一格一件）。"""
    found = {}
    for name in items:
        if name:
            found[name] = found.get(name, 0) + 1
    return found


def cases():
    """全部用例（每份配方 base、swap 两例，按 CraftCases.RECIPES 的先后；index 就是下标）。"""
    found = []
    for recipe in CraftCases.RECIPES:
        base = [pick(cell) for cell in recipe["grid"]]
        swap = [pick(cell, chosen) for cell, chosen in zip(recipe["grid"], base)]
        for label, items in (("base", base), ("swap", swap)):
            found.append({"index": len(found), "source": recipe["source"], "variant": label, "kind": recipe["kind"],
                          "grid": items, "expect": expected(recipe, items), "same": label == "swap" and swap == base,
                          "dish": DishStation.isDishCraft(recipe["result"][0], tuple(sorted(name for name in items if name))),
                          "unresolved": [cell for cell, name in zip(recipe["grid"], items) if cell is not None and name is None]})
    return found


def vetoActive():
    """工作台拦砧板菜的处理函数登记着没有（装着前置包、砧板站点登上了才有）。玩家自己在前置包的设置里关了砧板时不拦，这里看不出来，按开着算。"""
    return any(module.split(".")[-1] == VETO for module, _name in handlerNames(CRAFT_EVENT))
