# -*- coding: utf-8 -*-
"""CuttingStation - 切菜板站点：FD 砧板配方 -> HoD 刀口计划、挑工具、整批产物（双端，纯规则）

HoD 的切法规则在 HandsOn/Cutting.py；这里只做农夫乐事配方表（Shared/Data/Cutting.py）到它的适配：
- 刀口数按产物件数（Cutting.planCut）；布局按食材：派 / 蛋糕 / 披萨 / 南瓜 / 西瓜过圆心切楔形（HoD 的 cut_in_wedges 标签），
  面团切面条，卷切等宽片，其余横切；
- 工具判定照 JE，经典玩法同一套（fitsTool）：配方列出的工具、配方要求的物品类型（斧 / 镐 / 锹 / 锄）；
  刀切的配方另认任何刀（带 arris:knife 标签的下游刀），别的配方刀不行（JE 的原木要斧头削）；
- 带 chance 的产物每切一件、产物的每一个都各掷一次（JE 的 ChanceResult.rollOutput），工具上每级时运加 FORTUNE_BONUS；
  工具每切一件磨一点耐久，"耐久"附魔每级让磨损有 level / (level + 1) 的概率免掉（JE 的 hurtAndBreak -> ItemStack.hurt）；
- 板上能放一整叠（物品的最大堆叠，BoardStation.BOARD_MAX）；最后一刀切透其中的 BATCH（= HoD 一刀切透的整批 16）件，件数受工具剩余耐久限制。
"""
import random

from ..Data.Cutting import CuttingBoardDict, CuttingTagDict, knifeList
from . import ItemTags
from .HandsOn import Cutting

STATION_ID = "arris:cutting_board"
BOARD_BLOCKS = ["arris:cutting_board"]   # 站点绑定的方块（两端共用同一个列表；附属包的砧板追加到这里）
BATCH = Cutting.BATCH            # 最后一刀一次切透的件数
FORTUNE_ID = 18                  # 时运的附魔编号（网易 EnchantType.MiningLoot）
UNBREAKING_ID = 17               # 耐久的附魔编号（EnchantType.MiningDurability，在时运前面一个）
FORTUNE_BONUS = 0.1              # JE 配置 cuttingBoardFortuneBonus：每级时运给有概率的产物加 10%
# HoD 的 cut_in_wedges 标签：各种派、蛋糕、披萨、奶酪轮，还有南瓜和西瓜（南瓜 4 片 = 2 刀楔形，西瓜 9 片 = 3 刀楔形）
_WEDGE_WORDS = frozenset(("pie", "cake", "cheesecake", "pizza", "tart", "quiche", "pumpkin", "melon"))
_STRIP_WORDS = frozenset(("dough",))
_STRAIGHT_WORDS = frozenset(("roll",))


def recipeKeyOf(key):
    """板上这件东西（key 是 (物品名, aux)）按哪条砧板配方切：CuttingBoardDict 里精确的那条的键；没有就是 CuttingTagDict 里收它的标签名
    （按标签名的顺序，第一个；别的模组登记进 common:dough 的面团也切得了）；都没有是 None。"""
    if not key or not key[0]:
        return None
    key = (key[0], key[1])
    if key in CuttingBoardDict:
        return key
    for tag in sorted(CuttingTagDict):
        if ItemTags.has(key[0], tag):
            return tag
    return None


def recipeOf(key):
    """板上这件东西（(物品名, aux)）的砧板配方：精确的先，再看按标签的；切不了是 None。经典玩法、站点两端、食谱书都问它。"""
    found = recipeKeyOf(key)
    if found is None:
        return None
    return CuttingBoardDict.get(found) if isinstance(found, tuple) else CuttingTagDict.get(found)


def _words(itemName):
    return set(itemName.split(":")[-1].split("_"))


def styleOf(itemName):
    """按名字选刀口布局（HoD 按物品形状 / 标签选，FD 的物品名足够区分）。"""
    words = _words(itemName)
    return Cutting.chooseStyle(wedges=bool(words & _WEDGE_WORDS), strips=bool(words & _STRIP_WORDS),
                               straight=bool(words & _STRAIGHT_WORDS))


def planFor(itemName, recipe):
    """这件食材的刀口计划（几刀、什么布局）。"""
    counts = [entry.get("count", 1) for entry in recipe["itemList"]]
    return Cutting.planCut(counts, styleOf(itemName))


def strokeOf(recipe):
    """这道配方用哪种动作：刀切、斧劈 / 削皮、镐砸……（客户端据此选工具动画）。"""
    tools = list(recipe.get("tool") or [])
    if recipe.get("item_type"):
        tools.insert(0, recipe["item_type"])
    return Cutting.strokeKind(tools, [entry["itemName"] for entry in recipe["itemList"]])


def isKnifeRecipe(recipe):
    """刀切的配方：没要求物品类型，工具表就是刀表（或列着 FD 的刀）。"""
    if recipe.get("item_type"):
        return False
    tools = recipe.get("tool") or ()
    return tools is knifeList or any(name in knifeList for name in tools)


def fitsTool(itemName, itemType, recipe, isKnife):
    """这件东西能不能切这道配方（JE：配方写的工具才行）：列出的工具、要求的物品类型；刀切的配方另认任何刀。"""
    if not itemName:
        return False
    if itemName in (recipe.get("tool") or ()):
        return True
    if recipe.get("item_type") and itemType == recipe["item_type"]:
        return True
    return isKnifeRecipe(recipe) and bool(isKnife(itemName))


def enchantLevel(item, enchantId):
    """工具上某个附魔的等级（物品字典的 enchantData：[(附魔编号, 等级), ...]），没有是 0。"""
    for entry in (item or {}).get("enchantData") or ():
        if entry and len(entry) >= 2 and int(entry[0]) == enchantId:
            return int(entry[1])
    return 0


def fortuneOf(item):
    return enchantLevel(item, FORTUNE_ID)


def unbreakingOf(item):
    return enchantLevel(item, UNBREAKING_ID)


def ignoresWear(item, pick=None):
    """这一下切要不要免磨损（"耐久"附魔：每级让磨损有 level / (level + 1) 的概率免掉，JE 的 shouldIgnoreDurabilityDrop：
    random.nextInt(level + 1) > 0）。没有附魔就总是磨。pick(0, level) 取 0..level 的整数，测试里可以换掉。"""
    level = unbreakingOf(item)
    return level > 0 and (pick or random.randint)(0, level) > 0


def wearFor(count, left, level=0, pick=None):
    """板上有 count 件、工具还剩 left 点耐久（None 是不磨损：创造模式、不会坏的工具）、耐久附魔 level 级，最后一刀这一批：
    (切了几件, 磨掉几点耐久)。一件一件切，每件磨一点（免磨的不磨）；耐久磨到 0 刀就坏了，批在那里停（BoardLogic.chop 的循环）。"""
    most = min(BATCH, max(0, int(count)))
    if left is None:
        return most, 0
    done = spent = 0
    while done < most and left - spent > 0:
        done += 1
        if level <= 0 or (pick or random.randint)(0, level) == 0:
            spent += 1
    return done, spent


def countOf(entry, batch, roll=random.random, fortune=0):
    """一种产物切 batch 件得几个：没有 chance 的每件都给；有 chance 的每件的每一个各掷一次（时运每级加 FORTUNE_BONUS）：
    JE 的 ChanceResult.rollOutput 对数量 n 的产物循环 n 次、每次没掷中就少一个，所以数量 2、概率 50% 的染料是 0 / 1 / 2 个（25 / 50 / 25%），不是 0 或 2。"""
    each = entry.get("count", 1)
    chance = entry.get("chance")
    if chance is None or chance >= 1.0:
        return each * batch
    hit = min(1.0, float(chance) + fortune * FORTUNE_BONUS)
    return sum(1 for _ in range(each * batch) if roll() < hit)


def pickTool(candidates, recipe, isKnife, itemTypeOf):
    """candidates：[(位置, 物品字典或 None)]，按优先顺序（主手、副手、背包）。返回第一个合适的 (位置, 物品) 或 None。"""
    for where, item in candidates:
        if item and item.get("count", 0) > 0 and fitsTool(item.get("newItemName"), itemTypeOf(item), recipe, isKnife):
            return where, item
    return None


def toolLeft(item, maxDurability=None):
    """工具还能用几次；不会损坏的返回 None（不限）。
    网易的物品字典里，不会损坏的物品 durability 也读作 0，所以要看物品的最大耐久（GetItemBasicInfo 的 maxDurability）。"""
    durability = item.get("durability")
    if durability is None or (maxDurability is not None and maxDurability <= 0):
        return None
    return max(0, int(durability))


def resultsFor(recipe, batch, roll=random.random, fortune=0):
    """切 batch 件的全部产物：[(物品名, aux, 数量)]，同种合并，按配方顺序（带 chance 的按 countOf 掷）。"""
    totals = []
    where = {}
    for entry in recipe["itemList"]:
        key = (entry["itemName"], entry.get("auxValue", 0))
        count = countOf(entry, batch, roll, fortune)
        if key in where:
            totals[where[key]][2] += count
        else:
            where[key] = len(totals)
            totals.append([key[0], key[1], count])
    return [tuple(row) for row in totals if row[2] > 0]


def stacks(count, maxStack):
    """把 count 个拆成每叠不超过 maxStack 的若干叠。"""
    maxStack = max(1, int(maxStack))
    full, rest = divmod(max(0, int(count)), maxStack)
    return [maxStack] * full + ([rest] if rest else [])
