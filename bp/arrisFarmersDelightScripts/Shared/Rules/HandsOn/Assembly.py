# -*- coding: utf-8 -*-
"""Assembly - 摆盘：前缀匹配、可否继续加料、底座与收尾分类（双端）

移植自 Hands-On Delight 的 assembly/AssemblyRecipes.java（fits / canGrow / complete / assign / Base / Finish /
isTossed）与 assembly/Assembling.java（整批轮数）。

一道菜 = 一串配料，其中一个是"底座"，先放底座，再一层一层往上放；板上的层必须是某道菜的配料的一部分（前缀匹配，
每层各占一个没被用过的配料，顺序不限，只有第一层必须是底座）。层数等于配料数且各层都对上，就能做成。
一套层一轮做一份，每轮每层各用一件，一次最多 BATCH 轮。

配料是调用方给的任意对象，能不能放某一层由 accepts(配料, 层) 决定（FD 的配料可以是标签，这里不依赖物品系统）。
一道菜是 {"ingredients": [配料...], "base": 底座配料的序号}。
"""
GRID = 3                 # 3x3 的合成格
MOST_LAYERS = 9          # 一道菜最多几层 = GRID * GRID
BATCH = 16               # 一次最多做几份

FINISH_PRESS = "press"           # 从上往下压在一起：派皮、果汁、蛋糕
FINISH_TOSS = "toss"             # 碗里拌：沙拉
FINISH_ROLL = "roll"             # 卷起来：海带卷、卷饼
FINISH_SKEWER = "skewer"         # 沿签子从尖往下穿
FINISH_KNEAD = "knead"           # 揉
FINISH_ARRANGE = "arrange"       # 一块块摆进碗里：套餐、盛宴
FINISH_SANDWICH = "sandwich"     # 面包切开，上半合住馅：三明治、汉堡
FINISH_SHAPE = "shape"           # 米饭压成块，片放上面：握寿司
FINISH_FREEZE = "freeze"         # 水果冻在签子顶上：冰棒
FINISH_CHOP = "chop"             # 用刀一起切开

BASE_FIRST = "first"             # 没有任何关键词命中：第一个配料打底，按压处理

# 底座种类：(种类, 关键词, 默认收尾)。按这个顺序，每种按关键词顺序，每个词按配料顺序，第一个命中的说了算。
# 关键词在配料的物品名/标签名的路径(冒号后面)里找子串。
BASES = (
    ("bowl", ("bowl",), FINISH_TOSS),
    ("bottle", ("glass_bottle",), FINISH_PRESS),
    ("bread", ("bread", "burger"), FINISH_PRESS),            # 做好的汉堡也算：它的面包打开再合上
    ("tortilla", ("tortilla", "flatbread"), FINISH_ROLL),    # 先于米饭：馅卷在饼里
    ("toast", ("toast",), FINISH_PRESS),
    ("crust", ("pie_crust",), FINISH_PRESS),
    ("stick", ("stick", "rods/wooden", "blaze_rod"), FINISH_SKEWER),
    ("kelp", ("kelp",), FINISH_ROLL),
    ("rice", ("rice",), FINISH_ROLL),
    ("wheat", ("wheat", "dough", "flour"), FINISH_KNEAD),
)


def pathOf(name):
    """"minecraft:bread" -> "bread"。"""
    return name.split(":")[-1]


def names(ingredient, word):
    """配料（一个名字，或候选名字的列表）里有没有哪个的路径含 word。"""
    if hasattr(ingredient, "lower"):
        return word in pathOf(ingredient)
    return any(word in pathOf(choice) for choice in ingredient)


def baseOf(ingredients):
    """(底座在配料里的序号, 底座种类)；没有任何命中就是 (0, BASE_FIRST)。"""
    for kind, words, _finish in BASES:
        for word in words:
            for index, ingredient in enumerate(ingredients):
                if names(ingredient, word):
                    return index, kind
    return 0, BASE_FIRST


def baseFinish(kind):
    """底座种类的默认收尾。"""
    for baseKind, _words, finish in BASES:
        if baseKind == kind:
            return finish
    return FINISH_PRESS


def isTossed(tagged=False, arranged=False, isBlock=False, others=()):
    """碗里的菜是拌的(沙拉)还是摆的：打了"拌"标签就是拌；打了"摆"标签或成品是方块就是摆；
    否则只要有一样肉、鱼、蛋(裂开的)、或名字带 egg/bacon 的就是摆，纯植物才是拌。
    others 是底座之外每个配料的描述 {"name":, "meat":, "fish":, "cracked":}。"""
    if tagged:
        return True
    if arranged or isBlock:
        return False
    for food in others:
        path = pathOf(food.get("name", ""))
        if food.get("meat") or food.get("fish") or food.get("cracked") or "egg" in path or "bacon" in path:
            return False
    return True


def finishOf(kind, resultName="", hasTool=False, isBlock=False, tossed=False, arranged=False,
             frozen=False, hasIce=False, wrapped=False):
    """成品怎么收尾（AssemblyRecipes.Assembly.finish）：要刀的 -> 切；碗 -> 拌/摆；成品是方块 -> 压；
    成品名以 dough 结尾 -> 揉；签子 -> 冻(成品打了冻标签或配料有冰)/穿；面包 -> 卷(打了卷标签或名字含 wrap/burrito)/夹；
    米饭 -> 摆(打了摆标签)/压块；其余按底座默认。tossed 用 isTossed() 算。"""
    path = pathOf(resultName)
    if hasTool:
        return FINISH_CHOP
    if kind == "bowl":
        return FINISH_TOSS if tossed else FINISH_ARRANGE
    if isBlock:
        return FINISH_PRESS
    if path.endswith("dough"):
        return FINISH_KNEAD
    if kind == "stick":
        return FINISH_FREEZE if frozen or hasIce else FINISH_SKEWER
    if kind == "bread":
        return FINISH_ROLL if wrapped or "wrap" in path or "burrito" in path else FINISH_SANDWICH
    if kind == "rice":
        return FINISH_ARRANGE if arranged else FINISH_SHAPE
    return baseFinish(kind)


def assign(dish, layers, accepts, allIngredients=False):
    """各层分别占哪个配料（返回配料序号列表，第一个是底座），对不上返回 None。
    allIngredients=True 时要求每个配料都被占（层数 == 配料数）。"""
    ingredients = dish["ingredients"]
    base = dish["base"]
    if not layers or len(layers) > len(ingredients) or (allIngredients and len(layers) != len(ingredients)):
        return None
    if not accepts(ingredients[base], layers[0]):
        return None
    taken = [base] + [0] * (len(layers) - 1)
    used = [False] * len(ingredients)
    used[base] = True
    return taken if _assign(ingredients, layers, 1, used, taken, accepts) else None


def _assign(ingredients, layers, nextLayer, used, taken, accepts):
    """回溯：第 nextLayer 层挑一个没被占且收这一层的配料，后面放不下就换一个。"""
    if nextLayer == len(layers):
        return True
    for index in range(len(ingredients)):
        if not used[index] and accepts(ingredients[index], layers[nextLayer]):
            used[index] = True
            taken[nextLayer] = index
            if _assign(ingredients, layers, nextLayer + 1, used, taken, accepts):
                return True
            used[index] = False
    return False


def isBase(dishes, item, accepts):
    """item 能不能作为某道菜的第一层。"""
    return any(accepts(dish["ingredients"][dish["base"]], item) for dish in dishes)


def fits(dishes, layers, accepts):
    """板上现有的层（底座在前）是不是都属于某一道菜。"""
    return any(assign(dish, layers, accepts) is not None for dish in dishes)


def canGrow(dishes, layers, accepts):
    """还能不能再往上加料做成更大的一道菜：做好的菜这时要等厨师说"好了"，而不是立刻成品。"""
    return any(len(dish["ingredients"]) > len(layers) and assign(dish, layers, accepts) is not None for dish in dishes)


def complete(dishes, layers, accepts):
    """现有的层恰好做成的那道菜（全部配料各被一层占满），没有就是 None。"""
    for dish in dishes:
        if assign(dish, layers, accepts, True) is not None:
            return dish
    return None


def rounds(layerCounts, most=BATCH):
    """能做几轮：每轮每层各用一件，所以最薄的一层定数量；工具耐久等限制通过 most 传入。"""
    return min(most, min(layerCounts)) if layerCounts else 0
