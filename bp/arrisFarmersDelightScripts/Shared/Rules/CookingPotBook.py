# -*- coding: utf-8 -*-
"""CookingPotBook - 厨锅经典界面的食谱规则：格号、搜索与食谱格、选中食谱的详情（写法轮换）、容器与食材的分辨、补食材的计划（双端，纯规则）

厨锅容器是 netease:block_container 的 8 个格子：0-5 食材，6 容器（碗、玻璃瓶……），7 成品。
食谱表是 Shared/Data/CookingPotRecipes.CookingPotRecipeList，下游模组会在运行时往里追加。搜索结果按搜索词记着（界面画食谱格时每一格都要问一遍），
表的长度或配方索引重建的次数（CookingPot.revision：联动接口改表、客户端并表之后都重建）变了就重算；容器、食材、写法这些每次现读。
下游追加的食谱没人校验形状，而这里的函数在服务端界面的定时刷新里跑（出错会让所有开着界面的人都收不到更新），
所以形状不对的食谱（缺成品、变体不是 (物品名, aux) 的列表）一律当没有，不报错。
"""
from ..Data.CookingPotRecipes import CookingPotRecipeList
from . import CookingPot as PotRules
from . import ItemNames
from .TableWire import isInt

INPUT_SLOTS = 6
VESSEL_SLOT = 6
RESULT_SLOT = 7
POT_SLOTS = 8
# 选中食谱的详情格：与厨锅格同序，0-5 食材，6 容器（成品画在锅形的预览框里，是另一样界面数据）
BOOK_CELLS = 7
# 搜索词最多几个字
SEARCH_LIMIT = 16
# 选中的食谱有几种写法时，详情的食材格每这么多秒换成下一种（照旧界面：刚选中先完整显示第一种一个周期）
VARIANT_SECONDS = 1.0
# 还没选食谱时详情上方的标题：dolorContainer 的可本地化文字（Data.Lang 的写法 {"t": 语言文件的键}），服务端只给键，
# 客户端按玩家的语言查（rp/texts 的 zh_CN.lang / en_US.lang）；选了食谱时标题是食谱表里那道菜的 text，原样显示（没写 text 的是成品的显示名，titleOf）
UNPICKED_TITLE = {"t": "arris_fd.pot_screen.pick_recipe"}
_MEMO_LIMIT = 32   # 最多记几个搜索词的结果（边打边搜，每改一个字一个）
_memo = {}         # 搜索词（小写） -> [表的签名, 过滤后的下标, 食谱格的内容（用到时才建）]

try:
    _TEXT = unicode  # noqa: F821 - py2
except NameError:
    _TEXT = str


def _chars(value):
    """比较用的文字：py2 的 utf-8 字节串解成 unicode（不然和 unicode 的食谱名比较会抛异常），不是文字的当空。"""
    if isinstance(value, bytes):
        return value.decode("utf-8", "ignore")
    return value if isinstance(value, _TEXT) else u""


def _pair(value):
    """(物品名, aux)：名字是文字，aux 是整数。"""
    return (isinstance(value, (tuple, list)) and len(value) == 2 and isinstance(value[0], (str, _TEXT))
            and isInt(value[1]))


def _wellFormed(recipe):
    """食谱字典的形状对不对：不是墓碑（Disabled）、成品 (物品名, aux)、每个变体是非空的 (物品名, aux) 列表、容器可以没有；
    至少一个变体，或者有写对了的格子（Slots：新接口登记的配方，标签格一个成员都没有时展开出来的写法是空的）。"""
    if not isinstance(recipe, dict) or recipe.get("Disabled") or not _pair(recipe.get("CookResult")):
        return False
    rows = recipe.get("Recipe")
    if not isinstance(rows, (tuple, list)) or not (rows or PotRules.optionsOf(recipe) is not None):
        return False
    if not all(isinstance(row, (tuple, list)) and row and all(_pair(item) for item in row) for row in rows):
        return False
    return not recipe.get("Vessel") or _pair(recipe["Vessel"])


def _recipes():
    return [recipe for recipe in CookingPotRecipeList if _wellFormed(recipe)]


def _stack(item, count=1):
    return {"newItemName": item[0], "newAuxValue": item[1], "count": count}


def matchesSearch(recipe, search):
    """搜索框：这道菜比不比得上搜索词。按行里的 text 比、不分大小写——两端同步过来的同一份数据，哪种联机下两端过滤出来的都一样，
    选中的格号对得上；没写 text 的行 text 记的是成品的物品 ID，按物品 ID 搜得到。显示名只用在标题上（titleOf：各端自己问引擎，
    联机时两端可能不一样），不参与搜索。搜索词为空时都比得上。旧的原生界面（Client/Ui/CookingPotProxy）也用它。"""
    word = _chars(search).lower()
    return not word or word in _chars(recipe.get("text")).lower()


def _found(search):
    """搜索词过滤的结果（记着）：[表的签名, 下标们, 食谱格的内容或 None]。表的签名是长度加索引重建的次数。"""
    word = _chars(search).lower()
    signature = (len(CookingPotRecipeList), PotRules.revision())
    entry = _memo.get(word)
    if entry is None or entry[0] != signature:
        if len(_memo) >= _MEMO_LIMIT:
            _memo.clear()
        indices = [index for index, recipe in enumerate(CookingPotRecipeList) if _wellFormed(recipe) and matchesSearch(recipe, word)]
        entry = _memo[word] = [signature, indices, None]
    return entry


def visibleRecipes(search):
    """搜索词过滤后的食谱：表里的下标，保持表的顺序。搜索词为空是全部；按食谱名包含判断，不分大小写。"""
    return list(_found(search)[1])


def shownCount(search):
    """搜索词过滤后有几道食谱（食谱格显示几格）。"""
    return len(_found(search)[1])


def gridCells(search):
    """
    食谱格的内容 {格号: 物品堆}：过滤后每道食谱的成品，一份，照表的顺序。同一个搜索词（表没变时）给同一个字典：
    界面每画一格都来要，用的人只读、不改它。
    """
    entry = _found(search)
    if entry[2] is None:
        entry[2] = dict((slot, _stack(CookingPotRecipeList[index]["CookResult"])) for slot, index in enumerate(entry[1]))
    return entry[2]


def recipeAt(index):
    """表里第 index 条食谱；越界或形状不对为 None。"""
    recipe = CookingPotRecipeList[index] if 0 <= index < len(CookingPotRecipeList) else None
    return recipe if _wellFormed(recipe) else None


def pickedRecipe(search, picked):
    """（搜索词，在过滤后的食谱格里选中的格号）-> 食谱字典；没选中或越界为 None。"""
    shown = _found(search)[1]
    return recipeAt(shown[picked]) if 0 <= picked < len(shown) else None


def setNamePort(port):
    """再装一个显示名的口：port(物品名, aux) -> 显示名或 None（Shared/Rules/ItemNames.setPort；两端的经典界面那一侧各装一个。单机时
    两个口都在这一份模块里、各自只在自己那一端的线程里答得出，真去问时挨个问，第一个给出名字的算数）。None 是卸下全部（测试用）。"""
    ItemNames.setPort(port)


def titleOf(recipe):
    """选中食谱时详情上方的标题：食谱表里那道菜的 text，原样显示。没写 text（新接口登记时没写，表里记的是成品的物品 ID）的显示成品的
    显示名（界面所在那一端问引擎，ItemNames），要不到用物品 ID。只管显示，搜索按 text（matchesSearch）。下游写的 text 不一定是字：
    和原来的文字字段一样 str() 一下，界面数据的定时刷新不因为它出错（可本地化的文字只收字、数、列表和 {"t": 键}）。"""
    text = recipe.get("text")
    result = recipe.get("CookResult")
    if _pair(result) and result[0] and (text is None or _chars(text) == _chars(result[0])):     # py2：字节串 / unicode 换成同一种再比
        named = ItemNames.nameOf(result[0], result[1])
        return named if named is not None else result[0]
    if isinstance(text, (bytes, _TEXT)):
        return text
    return "" if text is None else str(text)


def variantCount(recipe):
    """详情的食材格轮换几帧：有格子（Slots）的每格轮换自己的选项（标签是它现在的成员），没有的一种写法一帧（PotRules.framesOf）。"""
    return max(1, len(PotRules.framesOf(recipe)))


def variantOf(recipe, variant):
    """详情的第 variant 帧（超出帧数时取模）：[(物品名, aux), ...]。"""
    frames = PotRules.framesOf(recipe)
    return list(frames[variant % len(frames)]) if frames else []


def shownVariant(count, since, now, period=VARIANT_SECONDS):
    """
    详情现在显示第几种写法：从选中的时刻 since 起每 period 秒换下一种，从第一种开始、到最后一种后回到第一种（旧界面的
    FoodRecipeTimerSwitch）。只有一种写法时总是 0；钟往回走了（since 在 now 之后）当刚选中。
    """
    if count <= 1 or now <= since:
        return 0
    return int((now - since) // period) % count


def vesselNames():
    """现有食谱用到的容器物品名（碗、玻璃瓶……）；下游追加的食谱也算。"""
    return frozenset(recipe["Vessel"][0] for recipe in _recipes() if recipe.get("Vessel"))


def ingredientNames():
    """现有食谱的食材物品名（任何一个变体里出现过的）。"""
    return frozenset(item[0] for recipe in _recipes() for row in recipe["Recipe"] for item in row)


def _isIngredientName(name):
    """这个物品名是不是某个食谱的食材：某种写法里出现过，或者配方认它（某格写着它、某个标签格收它，PotRules.isIngredient）。"""
    return name in ingredientNames() or PotRules.isIngredient((name, 0))


def isPureVessel(name):
    """只当容器用的东西（碗、玻璃瓶）：Shift 点击只往容器格放，不往食材格放，不然会混进食材把配方搅乱。"""
    return name in vesselNames() and not _isIngredientName(name)


def isAmbiguous(name):
    """既是某个食谱的容器、又是别的食谱的食材（卷心菜叶）：Shift 点击当食材放，只有容器格里已经是它时才续上。"""
    return name in vesselNames() and _isIngredientName(name)


def bookCells(recipe, variant):
    """选中食谱的详情格 {格号: 物品堆}：食材（第 variant 种写法）、容器（没有就空着）。"""
    cells = dict((index, _stack(item)) for index, item in enumerate(variantOf(recipe, variant)[:INPUT_SLOTS]))
    if recipe.get("Vessel"):
        cells[VESSEL_SLOT] = _stack(recipe["Vessel"])
    return cells


def resultOf(recipe):
    """选中食谱的成品（一份），画在详情的锅形预览框里。"""
    return _stack(recipe["CookResult"])


def keyOf(stack):
    """物品堆 -> (物品名, aux)，空为 None。配方按这两样认食材，附加数据不看。"""
    if not stack or stack.get("count", 0) <= 0:
        return None
    return (stack.get("newItemName"), int(stack.get("newAuxValue") or 0))


def presentCount(variant, slotKeys):
    """锅里 6 个食材格已经放着的、这种写法要的食材有几件（一格算一件，同种要几件就要几格，和 planFill 的认法一样）。"""
    need = [tuple(item) for item in variant]
    count = 0
    for key in slotKeys:
        if key is not None and key in need:
            need.remove(key)
            count += 1
    return count


def fillOrder(recipe, slotKeys, stock=()):
    """添加食材时试写法的先后：锅里已经放着的件数从多到少，一样多的照表里的先后（排序是稳定的）。
    有格子（Slots）的食谱，写法是旧写法加上格子按锅里和背包里有的料（stock：背包各格的 (物品名, aux)）具体化出来的（PotRules.waysWith）。"""
    if PotRules.optionsOf(recipe) is None:
        rows = [variantOf(recipe, index) for index in range(variantCount(recipe))]
    else:
        rows = PotRules.waysWith(recipe, [key for key in list(slotKeys) + list(stock) if key is not None])
    return sorted(rows, key=lambda row: -presentCount(row, slotKeys))


def planFill(variant, slotKeys):
    """
    把配方变体的食材补进厨锅 6 个食材格的计划：返回 (放进空格的, 给已有的格子再加一个的) 或 None（空格不够）。
    - 一个食材占一个格子（锅按"每个非空格算一件食材"匹配，同一格叠几个都只算一件，所以同种食材要几件就占几格）；
    - 格子里已经放着配方要的食材时，那一格不再另占空格，只在放得下时再加一个（反复点就是备多份料）；
    - 两个列表的元素都是 (格号, (物品名, aux))；放进空格的是必须成功的，加一个的有就加、没有或放不下就算了。
    variant 是 [(物品名, aux), ...]，slotKeys 是 6 个食材格现有东西的 keyOf（空格为 None）。
    """
    need = [tuple(item) for item in variant]
    topUps = []
    for index, key in enumerate(slotKeys):
        if key is not None and key in need:
            need.remove(key)
            topUps.append((index, key))
    empty = [index for index, key in enumerate(slotKeys) if key is None]
    if len(need) > len(empty):
        return None
    return list(zip(empty, need)), topUps
