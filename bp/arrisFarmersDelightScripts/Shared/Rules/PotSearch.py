# -*- coding: utf-8 -*-
"""PotSearch - 经典厨锅界面的搜索：查询词拆成条件、一道菜逐件比、过滤结果按词记着（双端，纯规则；只在看界面的那一端用）

照 arrisJei 的搜索（它的 core/search.py）：
- 空格分开的几个条件全部满足才算；只有前缀没有内容的词不算条件。
- 前缀：@模组（成品或某个食材的命名空间里有这几个字）、#标签（某一格写的标签名，或成品 / 某个食材带的某个标签里有）、
  & 或 /（成品或某个食材的物品 ID 里有）。arrisJei 的 %创造分类这里没有：照它关掉某种前缀时的做法，整个词当普通文本。
- 普通文本逐件比：写了的标题（行里的 text）比得上，或者某一件物品（成品、某个食材；不算盛菜的容器）自己比得上。不把几件的名字
  拼成一串（"牛肉"不会配上一道分别有"牛"和"肉"两件东西的菜）；几个条件可以由不同的物品满足（"番茄 牛肉"：用了番茄又用了牛肉）。
- 一件物品比不比得上一个普通文本词（FUZZY 是哪一档，wordMatches）：
  SUBSTRING：词是它的显示名或物品 ID 的子串（arrisJei 的缺省）；
  CJK（缺省）：SUBSTRING 之外，词里至少有一个非 ASCII 的字、并且词里每个字都在它的显示名里出现过也算（"牛炖"配得上牛肉炖）——
  纯字母数字的词、物品 ID 一律只认子串（字母的"每个字都出现过"太松：bee 会配上 rabbit_stew）；标题同理；
  ALL：SUBSTRING 之外，词里每个字都在显示名或物品 ID 里出现过就算，字母也一样（arrisJei 打开模糊时的比法）。
  和 arrisJei 的差别：它的模糊是设置里的开关、缺省关（子串），开了对字母也生效，拿悬停文本加物品 ID 一起比，还按拼音比；
  这里没有设置、不搬拼音，缺省只对含中文的词、只对显示名放宽。
- 显示名问 ItemNames（这一端装的引擎口；问不到时这件物品只比物品 ID）；标签问 ItemTags。不分大小写，py2 的字节串和 unicode 混着来都行。
只在看界面的那一端用：各端用自己的语言、自己问到的名字，联机时两端过滤出来的可以不一样，所以选中的是配方在表里的行号
（Shared/Menus/CookingPot 的 pick），服务端不按搜索词判断任何事。
记着的：每行的记录（成品、食材、格子里写的标签、标题）按表的版本和标签的代数；每个搜索词的过滤结果（最多 MEMO_LIMIT 个）按表的长度、
版本、标签的代数、显示名的版本（ItemNames.version：装卸口、新问到名字时变）和比法——界面每画一格都来要一遍，同一个词给同一份。
"""
from ..Data.CookingPotRecipes import CookingPotRecipeList
from . import CookingPot as PotRules
from . import CookingPotBook as Book
from . import ItemNames, ItemTags, PotSlots
from .TableWire import isInt

SUBSTRING, CJK, ALL = "substring", "cjk", "all"
FUZZY = CJK               # 普通文本的比法（见模块说明）
SEARCH_LIMIT = 32         # 搜索词最多几个字：搜索框的上限从搜索动作的参数取（Shared/Menus/CookingPot）
MEMO_LIMIT = 32           # 最多记几个搜索词的结果（边打边搜，每改一个字一个）
TEXT, MOD, TAG, ID = "text", "mod", "tag", "id"
PREFIXES = {u"@": MOD, u"#": TAG, u"&": ID, u"/": ID}

try:
    _TEXT = unicode  # noqa: F821 - py2
except NameError:
    _TEXT = str

_records = {}       # 行号 -> (行对象, 记录)；None 键记着算的时候的 (表的版本, 标签的代数)
_memo = {}          # 规整过的搜索词 -> [签名, 行号们, 食谱格的内容（用到时才建）]


def chars(value):
    """比较用的文字：py2 的 utf-8 字节串解成 unicode；不是文字的当空。"""
    if isinstance(value, bytes):
        return value.decode("utf-8", "ignore")
    return value if isinstance(value, _TEXT) else u""


def parse(text):
    """查询词 -> 条件 ((种类, 关键词), ...)：空格分开，小写；@ # & / 开头的是前缀条件，只有前缀没有内容的不算条件。"""
    found = []
    for token in chars(text).lower().split():
        kind = PREFIXES.get(token[0])
        key = token[1:] if kind is not None else token
        if key:
            found.append((kind or TEXT, key))
    return tuple(found)


def _everyChar(word, text):
    return bool(text) and frozenset(word) <= frozenset(text)


def wordMatches(word, name, itemId=u"", fuzzy=None):
    """一个普通文本词比不比得上一件东西：name 是显示名（或标题），itemId 是物品 ID（标题没有），都是小写的 unicode。规则见模块说明。"""
    fuzzy = FUZZY if fuzzy is None else fuzzy
    if word in name or word in itemId:
        return True
    if fuzzy == ALL:
        return _everyChar(word, name + u" " + itemId)
    return fuzzy == CJK and not all(ord(char) < 128 for char in word) and _everyChar(word, name)


def _record(recipe):
    """一行的记录：(标题（写了的 text，小写；没写是空的），[(物品名, aux)]：成品在前、再是各种写法和各格的选项（标签换成它现在的成员），
    各格写的标签名（小写））。不算盛菜的容器。"""
    result = recipe["CookResult"]
    kinds = [(result[0], result[1])]
    for row in (PotRules.optionsOf(recipe) or []) + PotRules.waysOf(recipe):
        for kind in row:
            pair = (kind[0], kind[1])
            if pair not in kinds:
                kinds.append(pair)
    tags = []
    for slot in PotRules.slotsOf(recipe) or ():
        for option in slot:
            parsed = PotSlots.parseOption(option)
            tag = chars(parsed[1]).lower() if parsed is not None and parsed[0] == "tag" else None
            if tag and tag not in tags:
                tags.append(tag)
    text = chars(recipe.get("text"))
    return (text.lower() if text and text != chars(result[0]) else u""), kinds, tags


def _nameOf(kind):
    name = ItemNames.nameOf(kind[0], kind[1])
    return chars(name).lower() if name is not None else u""


def _holds(condition, record, fuzzy):
    kind, key = condition
    title, kinds, tags = record
    if kind == TEXT:
        return (bool(title) and wordMatches(key, title, u"", fuzzy)) or \
            any(wordMatches(key, _nameOf(item), chars(item[0]).lower(), fuzzy) for item in kinds)
    if kind == MOD:
        return any(key in chars(item[0]).lower().partition(u":")[0] for item in kinds)
    if kind == ID:
        return any(key in chars(item[0]).lower() for item in kinds)
    return any(key in tag for tag in tags) or \
        any(key in chars(tag).lower() for item in kinds for tag in (ItemTags.tagsOf(item[0], item[1]) or ()))


def _matches(record, conditions, fuzzy):
    return all(_holds(condition, record, fuzzy) for condition in conditions)


def matches(recipe, text, fuzzy=None):
    """这道菜（表里的一行）比不比得上搜索词：删掉了的（墓碑）、形状不对的比不上；没有条件时形状对的都比得上。旧的原生界面也用它。"""
    if not Book.isShown(recipe):
        return False
    conditions = parse(text)
    return not conditions or _matches(_record(recipe), conditions, FUZZY if fuzzy is None else fuzzy)


def _signature():
    return (len(CookingPotRecipeList), PotRules.revision(), ItemTags.generation(), ItemNames.version(), FUZZY)


def _recordAt(index, recipe):
    stamp = (PotRules.revision(), ItemTags.generation())
    if _records.get(None) != stamp:
        _records.clear()
        _records[None] = stamp
    found = _records.get(index)
    if found is None or found[0] is not recipe:
        found = _records[index] = (recipe, _record(recipe))
    return found[1]


def _found(text):
    """搜索词过滤的结果（记着）：[签名, 行号们, 食谱格的内容或 None]。签名在算完之后取：这一遍新问到的名字不让刚算好的作废。"""
    word = u" ".join(chars(text).lower().split())
    entry = _memo.get(word)
    if entry is not None and entry[0] == _signature():
        return entry
    conditions = parse(word)
    shown = [index for index, recipe in enumerate(CookingPotRecipeList)
             if Book.isShown(recipe) and (not conditions or _matches(_recordAt(index, recipe), conditions, FUZZY))]
    if len(_memo) >= MEMO_LIMIT:
        _memo.clear()
    entry = _memo[word] = [_signature(), shown, None]
    return entry


def rows(text):
    """搜索词过滤出来的行号，照表里的先后（这一端的食谱格就是这些行的成品）；空的搜索词是全部（形状对的、没删的）。给出去的是拷贝。"""
    return list(_found(text)[1])


def count(text):
    """搜索词过滤后有几道（食谱格显示几格）。"""
    return len(_found(text)[1])


def cells(text):
    """食谱格的内容 {格号: 成品一份}：同一个搜索词（记着的没作废时）给同一个字典——界面每画一格都来要，用的人只读、不改它。"""
    entry = _found(text)
    if entry[2] is None:
        entry[2] = dict((cell, Book.resultOf(CookingPotRecipeList[index])) for cell, index in enumerate(entry[1]))
    return entry[2]


def rowAt(text, cell):
    """搜索词过滤后的第 cell 格是表里的哪一行；没有这一格是 None。"""
    shown = _found(text)[1]
    return shown[cell] if isInt(cell) and 0 <= cell < len(shown) else None


def forget():
    """测试用：忘掉记着的记录和过滤结果。"""
    _records.clear()
    _memo.clear()
