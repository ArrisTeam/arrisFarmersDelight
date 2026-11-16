# -*- coding: utf-8 -*-
"""DishStation - 砧板摆盘的纯规则：哪些菜在砧板上做、什么能打底、下一层能放什么、做成哪道、做几份、提示（双端）

对应 Hands-On Delight 的 assembly/AssemblyRecipes（规则内核已移植到 HandsOn/Assembly.py）：先放底座（面包、碗、签子、海带、
小麦、派皮……按配料名里的关键词挑），再一层一层往上放，最后一层放对了整叠就成了那道菜；一层是一叠，每做一份每层用一件，
最多 16 份。还能接着加料做成更大的菜时先不自动做成，等厨师点一下。菜谱表 Shared/Data/Dishes.py 由 tools/gen_dishes.py 生成。
层是 (物品名, aux)；配料也是 (物品名, aux)，按名字和 aux 精确匹配。
"""
from ..Data.Dishes import DishList
from ..Data.Food import shapedRecipeContainerDict
from .HandsOn import Assembly

BATCH = Assembly.BATCH
_dishes = []
_results = set()


def rebuildIndex(dishList=None):
    """按菜谱表建索引；附属包往 DishList 里加菜后调用。"""
    del _dishes[:]
    _results.clear()
    for entry in (DishList if dishList is None else dishList):
        ingredients = [(name, aux) for name, aux in entry["ingredients"]]
        base, kind = Assembly.baseOf([name for name, _aux in ingredients])
        _dishes.append({"ingredients": ingredients, "base": base, "kind": kind, "result": tuple(entry["result"]),
                        "count": int(entry.get("count") or 1)})
        _results.add(entry["result"][0])


def _accepts(ingredient, layer):
    return ingredient == layer


def isDishResult(itemName):
    """这个成品是不是改在砧板上做（前置包在场时工作台不出它）。"""
    return itemName in _results


def isBase(kind):
    """(物品名, aux) 能不能放在空砧板上打底。"""
    return Assembly.isBase(_dishes, kind, _accepts)


def fitsNext(layers, kind):
    """板上现有的层再放一层 kind，还是不是某道菜的一部分。"""
    return Assembly.fits(_dishes, list(layers) + [kind], _accepts)


def completed(layers):
    """现有的层恰好做成的那道菜（dict：result、count、kind……），没有就是 None。"""
    return Assembly.complete(_dishes, list(layers), _accepts)


def canGrow(layers):
    return Assembly.canGrow(_dishes, list(layers), _accepts)


def autoFinishes(layers):
    """放下这层就直接做成（做成了、而且没法再往上加料）。"""
    return completed(layers) is not None and not canGrow(layers)


def rounds(counts):
    return Assembly.rounds(counts, BATCH)


def containerOf(resultName):
    """做一份还给厨师的空容器（桶、玻璃瓶、碗）和"一份"的件数，和工作台合成后返还的一致；没有返回 None。"""
    return shapedRecipeContainerDict.get(resultName)


def statusText(data, nameOf=None):
    """站点数据 -> 摆盘时焦点界面底部的一行提示。data：layers（层的物品字典）、dish（做好的那叠）、ready（做成的菜名）。"""
    if data.get("dish"):
        return "做好了：点一下砧板拿走"
    layers = data.get("layers") or []
    if not layers:
        return ""
    ready = data.get("ready")
    if ready:
        shown = nameOf(ready) if nameOf else ready
        return "点一下砧板做成%s   也可以接着加料   潜行右键 = 原来的玩法" % shown
    return "点下方物品栏往上放下一层（共 %d 层）   点一下砧板全拿回来" % len(layers)


rebuildIndex()
