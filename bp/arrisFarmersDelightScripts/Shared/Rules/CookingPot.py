# -*- coding: utf-8 -*-
"""CookingPot - 厨锅配方匹配与出料结算（双端，纯规则）

配方表一行的写法见 Shared/Data/CookingPotRecipes.py。一锅里每个非空输入格算一件食材（同一格叠了多个也只算一件，与 JE 一致）。
一条配方配得上，当且仅当它有一种"形"和锅里的东西一一对上（JE 的 CookingPotRecipe.matches：RecipeMatcher.findMatches）：
- Slots 形：每件东西分给一个互不相同、收它的格，格子正好用完（二分图完美匹配，Shared/Rules/PotSlots.py；标签格问 ItemTags）；
- Recipe 里的每一种旧写法各是一个形：种类和件数正好相同。
几条配方都配得上时表里靠前的赢；墓碑（Disabled）跳过。索引和记着的答案在 Shared/Rules/PotRecipeTable.py：配方表改过（rebuildIndex：
联动接口、客户端并表）下次用到时重算，标签的答案变了（ItemTags.generation）只清记着的答案——登记一条配方不再整张重建。
出锅一份：成品 CookCount 个（JE 的配方结果数量，饺子 2 个），吐出 PushItem 加上锅里那几件料剩下的空容器（JE 的
CookingPotBlockEntity：配料的合成剩余物，再加 INGREDIENT_REMAINDER_OVERRIDES，表在 Shared/Data/Remainders.py——
奶桶剩桶、奶瓶剩玻璃瓶、番茄酱剩碗……；配方的 PushItem 里已经写了的不重复给）。
另有几样给厨锅站点用（Shared/Rules/PotStation.py、PotLayout.py）：一锅种类的各种摆法（候选，带配方序号）、哪些物品是食材、
哪些物品是盛菜的容器、一份煮出来给多少经验（锅里记着煮了几份，盛出时一并给，见 Server/Helpers/PotContainer.py）。
"""
from ..Data.CookingPotRecipes import CookingPotRecipeList
from ..Data.Remainders import potRemainderOf
from . import ItemTags, PotSlots
from . import PotRecipeTable as Table

DEFAULT_COOK_SECONDS = Table.DEFAULT_COOK_SECONDS     # JE 的厨锅配方缺省 200 刻
DEFAULT_EXPERIENCE = Table.DEFAULT_EXPERIENCE         # 旧格式没写 Experience 时给的经验（新接口登记的把经验明写进行里，JE 的缺省是 0）
WAYS_CAP = 64                                         # 按手头的料具体化出来的写法最多几种
isLive = Table.isLive                                 # 这一行是不是一条配方（不是墓碑、不是坏行）


def revision():
    """配方表改过几次（rebuildIndex：联动接口、客户端并表都要调）；按表缓存的东西和它一起比，变了就重算。"""
    return Table.revision()


def rebuildIndex():
    """配方表改过之后调：下次用到时重算索引，记着的答案作废（不再当场整张重建）。"""
    Table.touch()


def pushItemsOf(variant, declared):
    """锅里这几件料出锅一份吐出什么：配方写的 PushItem，再加上料剩下的空容器（PushItem 里已有的那件不重复）。"""
    pushed = list(declared or [])
    spare = list(pushed)
    for entry in variant:
        name = potRemainderOf(entry[0])
        if name is None:
            continue
        left = (name, 0)
        if left in spare:
            spare.remove(left)
        else:
            pushed.append(left)
    return pushed


def _entries(itemDicts):
    return [(itemDict["newItemName"], itemDict.get("newAuxValue") or 0) for itemDict in itemDicts or () if itemDict]


def inputKeyOf(itemDicts):
    """输入格物品列表（空格为 {} 或 None）→ 查表键（排好序的 (物品名, aux)）；全空返回 None。"""
    entries = _entries(itemDicts)
    return tuple(sorted(entries)) if entries else None


def _hit(entries):
    """锅里的料（按格子的先后）-> (配方序号, 余料按哪几件算)；配不上 (None, None)。配上的是旧写法时余料照那种写法算（和原来一样）。"""
    if not entries:
        return Table.MISS
    Table.table()
    index, variant = Table.resolve(tuple(sorted(entries)))
    return (index, variant if variant is not None else entries) if index is not None else Table.MISS


def matchRecipe(itemDicts):
    """返回 (成品 itemDict（count 是一份出几个）, 余料列表)；没有匹配的配方返回 (None, None)。"""
    index, used = _hit(_entries(itemDicts))
    if index is None:
        return None, None
    recipe = CookingPotRecipeList[index]
    result = recipe["CookResult"]
    return ({"newItemName": result[0], "newAuxValue": result[1], "count": Table.countOf(recipe)},
            pushItemsOf(used, recipe.get("PushItem")))


def matchIndex(itemDicts):
    """格子里的料按现在的摆法被读成哪个配方（配方表里的序号）；读不成返回 None。"""
    return _hit(_entries(itemDicts))[0]


def lookupRecipe(inputKey):
    """inputKey 为 tuple(sorted([(name, aux), ...]))；返回 (成品 (name, aux), 余料列表) 或 None。"""
    index, used = _hit([(entry[0], entry[1]) for entry in inputKey or ()])
    if index is None:
        return None
    recipe = CookingPotRecipeList[index]
    return recipe["CookResult"], pushItemsOf(used, recipe.get("PushItem"))


def candidatesFor(kinds):
    """种类集合正好是 kinds 的各种摆法：[(配方序号, {种类: 占几格}), ...]，按配方表顺序（站点选菜用，PotLayout.choose）。
    旧写法照原来一种写法一条；Slots 形给出它能摆的全部（重复的不要）。不看每种有几件：够不够由 choose 判。"""
    Table.table()
    return Table.candidates(kinds)


def partsFor(kinds):
    """种类集合正好是 kinds 的各种摆法：[{种类: 占几格}, ...]。"""
    return [parts for _index, parts in candidatesFor(kinds)]


def isIngredient(kind):
    """(物品名, aux) 是不是某个配方的食材：某种写法里有它、某格写着它，或者某个标签格收它。"""
    if not kind:
        return False
    found = Table.table()
    kind = (kind[0], kind[1])
    return kind in found["exact"] or (bool(found["tags"]) and Table.tagged(kind))


def isVessel(itemName):
    """这个物品是不是某道菜盛菜用的容器（只比物品名，和锅自己装碗一致）。"""
    return itemName in Table.table()["vessels"]


def findRecipeByResult(resultItemName):
    """按成品名找第一条配方（与旧实现"首个匹配获胜"一致，墓碑跳过）；没有返回 None。"""
    for recipeDict in CookingPotRecipeList:
        if isLive(recipeDict) and recipeDict["CookResult"][0] == resultItemName:
            return recipeDict
    return None


def vesselOf(resultName):
    """盛这道菜要的容器 (物品名, aux)，不要容器的菜返回 None。"""
    recipe = findRecipeByResult(resultName)
    return recipe.get("Vessel") if recipe else None


def resultNameOf(index):
    """配方表里第 index 条的成品名（锅记着的上一条配方的成品，见 PotRecipeMemory）。"""
    return CookingPotRecipeList[index]["CookResult"][0]


def cookSecondsOf(resultName):
    """这道菜一份煮多久（秒）：配方表里的 CookTime，没写就是 10 秒（JE 的 200 刻）。"""
    return Table.table()["seconds"].get(resultName, DEFAULT_COOK_SECONDS)


def experienceOf(resultName):
    """盛出一个这道菜给多少经验：配方表里一份的 Experience（旧格式没写就是 1）除以一份出几个。"""
    return Table.table()["perItem"].get(resultName, DEFAULT_EXPERIENCE)


def servingExperienceOf(resultName):
    """煮出一份这道菜给多少经验（JE 的 Experience；盛出时按煮了几份算，见 experienceOrb）。"""
    return Table.table()["perServing"].get(resultName, DEFAULT_EXPERIENCE)


def experienceOrb(experience, count, roll):
    """盛出 count 个共给多少整数经验：整数部分照给，零头按概率进一（JE 的厨锅 / 熔炉同款）；roll 是 0..1 的随机数。"""
    total = max(0.0, float(experience) * count)
    whole = int(total)
    return whole + (1 if roll < total - whole else 0)


def optionsOf(recipe):
    """有 Slots 的配方：每格能放的具体物品 [[(物品名, aux), ...], ...]（标签换成它现在的成员）；没有 Slots 或写坏了是 None。
    站点书、经典界面、JEI 一格一格轮换着画它。"""
    slots = Table.slotsOf(recipe)
    return None if slots is None else [PotSlots.optionsOf(slot, ItemTags.itemsOf) for slot in slots]


def extraWays(recipe):
    """旧写法里格子不收的那几种（契约的 AddCookingPotRecipe 给有 Slots 的配方加的写法）；没有 Slots 的配方就是它的全部写法。"""
    slots = Table.slotsOf(recipe)
    ways = Table.waysOf(recipe)
    return ways if slots is None else [way for way in ways if not PotSlots.fits(slots, way, ItemTags.has)]


def framesOf(recipe):
    """画这道菜的配料时轮换的几帧 [[(物品名, aux), ...], ...]：有 Slots 的每格轮换自己的选项（第 n 帧每格取第 n % 这格选项数 种，
    帧数是选项最多那一格的个数），格子不收的旧写法各占一帧接在后面；没有 Slots 的就是它的各种写法。某格一个成员都没有时格子那一段不画。"""
    options = optionsOf(recipe)
    if options is None:
        return Table.waysOf(recipe)
    frames = []
    if options and all(options):
        frames = [[cell[n % len(cell)] for cell in options] for n in range(max(len(cell) for cell in options))]
    return frames + extraWays(recipe)


def usesOf(recipe):
    """这条配方用到的每一样 [(物品名, aux)]（JEI 按用途查它时用）：格子的全部选项（标签换成它现在的成员）、旧写法里的物品、盛菜的容器；
    去重，按先后。"""
    found = []
    for kinds in (optionsOf(recipe) or []) + Table.waysOf(recipe):
        found += [kind for kind in kinds if kind not in found]
    vessel = recipe.get("Vessel") if isinstance(recipe, dict) else None
    if Table.isPair(vessel) and (vessel[0], vessel[1]) not in found:
        found.append((vessel[0], vessel[1]))
    return found


def waysWith(recipe, available):
    """这道菜用手头有的种类（available：(物品名, aux) 的序列，锅里的在前）能凑出的写法：旧写法 + 格子按手头的料具体化出来的
    （重复的不要，最多 WAYS_CAP 种）。站点书里放料（PotLayout.planFill）、经典界面添加食材（CookingPotBook.fillOrder）用。"""
    ways = Table.waysOf(recipe)
    slots = Table.slotsOf(recipe)
    if slots is not None:
        seen = set(tuple(sorted(way)) for way in ways)
        for way in PotSlots.concretize(slots, list(available), ItemTags.has, WAYS_CAP):
            key = tuple(sorted(way))
            if key not in seen:
                seen.add(key)
                ways.append(way)
    return ways


def transferAmount(previewCount, resultCount, maxStackSize, vesselCount=None):
    """预览槽 → 产出槽这一次能转移多少份。

    不超过待出料数、产出槽剩余堆叠空间；成品需要容器时还不超过容器格里的容器数。
    """
    amount = min(previewCount, maxStackSize - resultCount)
    if vesselCount is not None:
        amount = min(amount, vesselCount)
    return max(0, amount)
