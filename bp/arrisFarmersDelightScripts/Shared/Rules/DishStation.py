# -*- coding: utf-8 -*-
"""DishStation - 砧板摆盘的纯规则：哪些菜在砧板上做、什么能打底、下一层能放什么、做成哪道、做几份、提示（双端）

对应 Hands-On Delight 的 assembly/AssemblyRecipes（规则内核已移植到 HandsOn/Assembly.py）：先放底座（面包、碗、签子、海带、
小麦、派皮……按配料名里的关键词挑），再一层一层往上放，最后一层放对了整叠就成了那道菜；一层是一叠，每做一份每层用一件，
最多 16 份。还能接着加料做成更大的菜时先不自动做成，等厨师点一下。菜谱表 Shared/Data/Dishes.py 由 tools/gen_dishes.py 生成。
层是 (物品名, aux)；配料也是 (物品名, aux)，按名字和 aux 精确匹配。
做一份剩下的东西照 JE 的合成剩余物（HoD 的 Assembling.make 用配方的 getRemainingItems）：extras 是换成了别的东西的容器，
keeps 是原样留下的配料（面团配方的水桶）——它每轮都放回去，不限做几份，做完整个还给厨师。
做成时怎么收尾（finishOf，客户端挑动画用）照 AssemblyRecipes.Assembly.finish（199-249）：碗里的菜"拌"还是"摆"要看成品是不是方块（盛宴、派、蛋糕）、
打没打 tossed 标签、配料里有没有肉 / 鱼 / 蛋——标签和物品属性基岩没有，下面几张名单就是它们的替身（JE 的 BoardTests.everyFoodCraftComesToTheBoard 逐道断言过）。
"""
from ..Data import PotSunk
from ..Data.Dishes import DishList
from ..Data.Food import pieList, platePackagedFoodDict
from .HandsOn import Assembly

BATCH = Assembly.BATCH
_dishes = []
_results = set()
CAKE = "minecraft:cake"
# HoD 的 tossed / frozen / wrapped 标签里 FD 本体的成品（arranged 标签只有 Barbeque's Delight 的拌饭，这边没有）
_TOSSED = frozenset(("arris:mixed_salad", "arris:fruit_salad", "arris:nether_salad", "arris:gleaming_salad_block_stage0"))
_FROZEN = frozenset(("arris:melon_popsicle",))
_WRAPPED = frozenset(("arris:mutton_wrap",))
# FoodProperties.isMeat / #minecraft:fishes 的替身：物品名（冒号后面按下划线拆开）里有这些词的当肉、当鱼。
# 蛋（KitchenTags.CRACKED，AssemblyRecipes 244 行）不另抄一份：读 PotSunk.CRACKED，和厨锅、砧板、煎锅同一张（_flagsOf 每次现读）
_MEAT_WORDS = frozenset(("beef", "porkchop", "chicken", "mutton", "rabbit", "ham", "bacon", "flesh", "patty", "chops", "cuts"))
_FISH_WORDS = frozenset(("cod", "salmon", "fish", "pufferfish"))


def rebuildIndex(dishList=None):
    """按菜谱表建索引；附属包往 DishList 里加菜后调用。"""
    del _dishes[:]
    _results.clear()
    for entry in (DishList if dishList is None else dishList):
        if not entry.get("ingredients"):
            continue                              # 没有配料的行不是一道菜（表同步时传不过来的那一行用空行占着下标，SyncTables.HOLES）
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


def isDishRecipe(itemName, slots):
    """配方书用（前置包原版工作台站点的书，客户端）：成品 itemName、每格能放的几种 slots（[[(物品名, aux 或 None), ...], ...]）的这条配方
    是不是它在砧板上的某条配方——料一件对一格、名字对得上（和 isDishCraft 一样不看 aux）。和 isDishCraft 同一张表、同一个判法：拦配方不拦成品，
    同一成品的别的配方（切片拼回整个派）不算。"""
    slots = [set(name for name, _aux in options) for options in slots]
    for dish in _dishes:
        if dish["result"][0] == itemName and len(dish["ingredients"]) == len(slots) and _paired(dish["ingredients"], slots):
            return True
    return False


def _paired(ingredients, slots):
    """砧板配方的每件料各配一格（那一格能放它），一对一（二分匹配）。"""
    owner = {}

    def take(index, seen):
        for slot, names in enumerate(slots):
            if slot in seen or ingredients[index][0] not in names:
                continue
            seen.add(slot)
            if slot not in owner or take(owner[slot], seen):
                owner[slot] = index
                return True
        return False

    return all(take(index, set()) for index in range(len(ingredients)))


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


def isBlockResult(name):
    """成品是不是放下去就是一整块（BlockItem）：盛宴、整个的派、蛋糕。基岩的 itemType 不一定这么说（盛宴按食物算），所以按名字认。"""
    return name in platePackagedFoodDict or name == CAKE or (name.endswith("_item") and name[:-len("_item")] in pieList)


def _flagsOf(kind):
    """一件配料在 isTossed 眼里是什么（肉 / 鱼 / 生蛋）；名字带 egg、bacon 的 Assembly.isTossed 自己认。"""
    words = set(kind[0].split(":")[-1].split("_"))
    cracked = any(kind[0] == name for name, _aux in PotSunk.CRACKED)
    return {"name": kind[0], "meat": bool(words & _MEAT_WORDS), "fish": bool(words & _FISH_WORDS), "cracked": cracked}


def finishOf(dish):
    """这道菜做成时怎么收尾（Assembly.finish）：Assembly.finish* 常量之一。dish 是 dishes() 里的一条。"""
    name, block = dish["result"][0], isBlockResult(dish["result"][0])
    others = [_flagsOf(kind) for index, kind in enumerate(dish["ingredients"]) if index != dish["base"]]
    tossed = Assembly.isTossed(tagged=name in _TOSSED, isBlock=block, others=others)
    return Assembly.finishOf(dish["kind"], name, isBlock=block, tossed=tossed, frozen=name in _FROZEN,
                             hasIce=any(kind[0] == "minecraft:ice" for kind in dish["ingredients"]), wrapped=name in _WRAPPED)


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
