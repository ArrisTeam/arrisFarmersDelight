# -*- coding: utf-8 -*-
"""DishStation - 砧板摆盘的纯规则：哪些菜在砧板上做、什么能打底、下一层能放什么、做成哪道、做几份、提示（双端）

对应 Hands-On Delight 的 assembly/AssemblyRecipes（规则内核已移植到 HandsOn/Assembly.py）：先放底座（面包、碗、签子、海带、
小麦、派皮……按配料名里的关键词挑），再一层一层往上放，最后一层放对了整叠就成了那道菜；一层是一叠，每做一份每层用一件，
最多 16 份。还能接着加料做成更大的菜时先不自动做成，等厨师点一下。菜谱表 Shared/Data/Dishes.py 由 tools/gen_dishes.py 生成。
层是 (物品名, aux)；配料也是 (物品名, aux)，按名字和 aux 精确匹配。
做一份剩下的东西照 JE 的合成剩余物（HoD 的 Assembling.make 用配方的 getRemainingItems）：extras 是换成了别的东西的容器，
keeps 是原样留下的配料（面团配方的水桶）——它每轮都放回去，不限做几份，做完整个还给厨师。
"""
from ..Data.Dishes import DishList
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
                        "count": int(entry.get("count") or 1),
                        "extras": [tuple(extra) for extra in entry.get("extras") or ()],
                        "keeps": tuple(entry.get("keeps") or ())})
        _results.add(entry["result"][0])


def _accepts(ingredient, layer):
    return ingredient == layer


def dishes():
    """全部摆盘的菜（索引的拷贝）：{"ingredients", "base"（底座在 ingredients 里的下标）, "kind", "result", "count",
    "extras", "keeps"}。"""
    return [dict(dish) for dish in _dishes]


def targetOf(layers):
    """板上现有的层朝着哪道菜去：做成了的那道，否则第一道还能接上的；空板或接不上返回 None。"""
    done = completed(layers) if layers else None
    if done is not None:
        return done
    for dish in _dishes if layers else ():
        if Assembly.fits([dish], list(layers), _accepts):
            return dish
    return None


def isDishResult(itemName):
    """这个成品是不是改在砧板上做。"""
    return itemName in _results


def isDishCraft(itemName, names):
    """工作台上取 itemName、合成格里的原料名（排好序，一格一个）正好是它在砧板上的某条配方：前置包在场时要拦。
    同一成品的别的配方（切片拼回整个派，只有一种原料）不是砧板菜；创造模式从物品栏拿东西时合成格对不上；都不拦。"""
    names = tuple(names)
    for dish in _dishes:
        if dish["result"][0] == itemName and tuple(sorted(name for name, _aux in dish["ingredients"])) == names:
            return True
    return False


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


def roundsOf(dish, stacks):
    """板上的层 [((物品名, aux), 个数), ...] 做 dish 能做几份：原样留下的配料（keeps）不限份数，其余最薄的一层说了算。"""
    counts = [count for kind, count in stacks if kind[0] not in dish["keeps"]]
    return Assembly.rounds(counts, BATCH) if counts else 1


def leftOf(dish, kind, count, made):
    """做了 made 份以后这一层还剩几个要还给厨师：原样留下的配料整层还，其余还多出来的。"""
    return count if kind[0] in dish["keeps"] else max(0, count - made)


def makeOf(dish, stacks):
    """板上这些层 stacks（[((物品名, aux), 个数)]，底座在前）做成 dish：{"made": 做了几份, "left": [((物品名, aux), 这层还剩几个)] 按层序,
    "extras": [(物品名, aux, 个数)] 换成了别的东西的容器（桶、瓶、碗）一份还一套, "result": (物品名, aux, 个数)}（HoD 的 Assembling.make）。"""
    made = roundsOf(dish, stacks)
    return {"made": made, "left": [(kind, leftOf(dish, kind, count, made)) for kind, count in stacks],
            "extras": [(name, aux, count * made) for name, aux, count in dish["extras"]],
            "result": (dish["result"][0], dish["result"][1], made * dish["count"])}


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
