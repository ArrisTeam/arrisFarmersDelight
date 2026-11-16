# -*- coding: utf-8 -*-
"""CuttingStation - 切菜板站点：FD 砧板配方 -> HoD 刀口计划、挑工具、整批产物（双端，纯规则）

HoD 的切法规则在 HandsOn/Cutting.py；这里只做农夫乐事配方表（Shared/Data/Cutting.py）到它的适配：
- 刀口数按产物件数（Cutting.planCut）；布局按食材：派 / 蛋糕 / 披萨过圆心切楔形，面团切面条，卷切等宽片，其余横切；
- 工具判定照 JE，经典玩法同一套（fitsTool）：配方列出的工具、配方要求的物品类型（斧 / 镐 / 锹 / 锄）；
  刀切的配方另认任何刀（带 arris:knife 标签的下游刀），别的配方刀不行（JE 的原木要斧头削）；
- 带 chance 的产物每切一件掷一次（JE 的 ChanceResult），工具上每级时运加 FORTUNE_BONUS；
- 板上最多放一叠 BOARD_LIMIT（= HoD 一刀切透的整批 16）件；最后一刀切透整叠，件数受工具剩余耐久限制。
"""
import random

from ..Data.Cutting import knifeList
from .HandsOn import Cutting

STATION_ID = "arris:cutting_board"
BOARD_BLOCKS = ["arris:cutting_board"]   # 站点绑定的方块（两端共用同一个列表；附属包的砧板追加到这里）
BOARD_LIMIT = Cutting.BATCH
FORTUNE_ID = 18                  # 时运的附魔编号（网易 EnchantType）
FORTUNE_BONUS = 0.1              # JE 配置 cuttingBoardFortuneBonus：每级时运给有概率的产物加 10%
_WEDGE_WORDS = frozenset(("pie", "cake", "cheesecake", "pizza", "tart", "quiche"))
_STRIP_WORDS = frozenset(("dough",))
_STRAIGHT_WORDS = frozenset(("roll",))


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


def fortuneOf(item):
    """工具上时运的等级（物品字典的 enchantData：[(附魔编号, 等级), ...]），没有是 0。"""
    for entry in (item or {}).get("enchantData") or ():
        if entry and len(entry) >= 2 and int(entry[0]) == FORTUNE_ID:
            return int(entry[1])
    return 0


def countOf(entry, batch, roll=random.random, fortune=0):
    """一种产物切 batch 件得几个：没有 chance 的每件都给；有 chance 的每件各掷一次（时运每级加 FORTUNE_BONUS）。"""
    each = entry.get("count", 1)
    chance = entry.get("chance")
    if chance is None or chance >= 1.0:
        return each * batch
    hit = min(1.0, float(chance) + fortune * FORTUNE_BONUS)
    return each * sum(1 for _ in range(batch) if roll() < hit)


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
