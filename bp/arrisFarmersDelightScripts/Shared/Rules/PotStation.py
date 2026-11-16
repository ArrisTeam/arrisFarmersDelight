# -*- coding: utf-8 -*-
"""PotStation - 厨锅站点的纯规则：份数、放料、按配方摆料、取回、徽章与提示文字（双端）

对应 Hands-On Delight：station/PotLogic.java 的 servingsLeft / shareOut / takeBack 与 PotRecipes.choose 的简化版。
本移植的配方是"每个非空食材格算一件、(物品名, aux) 精确匹配"（Shared/Rules/CookingPot.py），所以一份每格用 1 件，
份数就是非空格里最少的那格。两个番茄的番茄酱要占两格：站点放进来的料按配方摆开（layout），玩家不用自己分格；
凑不出任何配方的料原样放着（HoD："Food that makes nothing stays as it lies"）。
食材格是 6 项的列表，每项是物品字典（newItemName / newAuxValue / count）或空（None / {}）。
"""
import copy

from .CookingPot import isIngredient, partsFor  # noqa: F401 - isIngredient 是站点的放料判定
from .HandsOn.PotCooking import FD_WAY, WAITING

STATION_ID = "arris:cooking_pot"
POT_BLOCKS = ("arris:cooking_pot",)
INPUT_SLOTS = 6
COOK_SECONDS = 10.0          # 一份的配方时长（秒）：FD 原样一份一份煮、搅拌整批煮都按它算

def keyOf(item):
    if not item or not item.get("newItemName") or (item.get("count") or 0) <= 0:
        return None
    return (item["newItemName"], item.get("newAuxValue") or 0)


def countOf(item):
    return (item.get("count") or 0) if keyOf(item) else 0


def servingsLeft(slots):
    """料够做几份：非空格里最少的那格（一份每格用 1 件）。"""
    counts = [countOf(slot) for slot in slots if countOf(slot) > 0]
    return min(counts) if counts else 0


def foodCount(slots):
    return sum(countOf(slot) for slot in slots)


def kindsOf(slots):
    """[(种类, 总数)]，按第一次出现的格子排。"""
    order, totals = [], {}
    for slot in slots:
        key = keyOf(slot)
        if key is None:
            continue
        if key not in totals:
            order.append(key)
            totals[key] = 0
        totals[key] += countOf(slot)
    return [(key, totals[key]) for key in order]


def bestParts(kinds):
    """锅里的料最适合哪个配方写法：种类完全一样、每种料至少够一份；返回 {种类: 占几格}，没有返回 None。
    几个写法都行时取能做份数最多的，一样多取配方表里靠前的。"""
    totals = dict(kinds)
    best, most = None, 0
    for parts in partsFor(totals):
        servings = min(totals[key] // count for key, count in parts.items())
        if servings > most:
            best, most = parts, servings
    return best


def _stack(sample, count):
    stack = copy.deepcopy(sample)
    stack["count"] = count
    return stack


def _cells(slots):
    cells = [copy.deepcopy(slot) if keyOf(slot) else None for slot in list(slots)[:INPUT_SLOTS]]
    return cells + [None] * (INPUT_SLOTS - len(cells))


def placeStack(slots, item, maxStack):
    """把 item 整叠放进食材格：先叠到同种料的格子上（不超过堆叠上限），再放进空格。返回 (新的 6 格, 放进去几件)。"""
    cells, key, left = _cells(slots), keyOf(item), countOf(item)
    if key is None:
        return cells, 0
    for cell in cells:
        if left > 0 and keyOf(cell) == key and cell["count"] < maxStack:
            moved = min(left, maxStack - cell["count"])
            cell["count"] += moved
            left -= moved
    for index, cell in enumerate(cells):
        if left > 0 and cell is None:
            cells[index] = _stack(item, min(left, maxStack))
            left -= cells[index]["count"]
    return cells, countOf(item) - left


def layout(slots, maxStackOf):
    """按配方把料摆开：每种料平分到配方要它占的格数上（每格不超过 maxStackOf(种类)）。
    返回 (新的 6 格, 放不下的物品列表)；凑不出配方或已经是这样摆的返回 None。"""
    kinds = kindsOf(slots)
    parts = bestParts(kinds)
    if parts is None:
        return None
    samples = {}
    for slot in slots:
        if keyOf(slot) is not None:
            samples.setdefault(keyOf(slot), slot)
    cells, rest = [], []
    for key, total in kinds:
        cap = max(1, maxStackOf(key))
        base, extra = divmod(total, parts[key])
        for index in range(parts[key]):
            share = base + (1 if index < extra else 0)
            cells.append(_stack(samples[key], min(share, cap)))
            if share > cap:
                rest.append(_stack(samples[key], share - cap))
    cells += [None] * (INPUT_SLOTS - len(cells))
    if [(keyOf(c), countOf(c)) for c in cells] == [(keyOf(c), countOf(c)) for c in _cells(slots)]:
        return None
    return cells, rest


def takeKind(slots, index):
    """取回第 index 格那种料（所有格子里的这种料一起）。返回 (新的 6 格, 取出的物品列表)。"""
    cells = _cells(slots)
    key = keyOf(cells[index]) if 0 <= index < INPUT_SLOTS else None
    if key is None:
        return cells, []
    taken = [cell for cell in cells if keyOf(cell) == key]
    return [None if keyOf(cell) == key else cell for cell in cells], taken


def badgeOf(data):
    """站点同步来的数据 -> 焦点界面顶部的徽章（星星、菜、进度）；锅里没菜可做也没菜可盛时 None。"""
    if data.get("meals"):
        grade = data.get("grade") or 0
        return {"item": data.get("meal"), "stars": grade, "open": max(grade, data.get("open") or 1), "progress": None}
    if data.get("dish"):
        return {"item": data.get("dish"), "stars": data.get("stars") or 0.0, "open": data.get("open") or 1,
                "progress": data.get("progress") or 0.0}
    return None


def statusText(data):
    """站点同步来的数据 -> 焦点界面底部的一行提示（星星和进度在徽章上）。mode 是锅上一步的煮法（WAITING / FD_WAY / STIRRED）。"""
    if data.get("meals"):
        need = "（要%s）" % data.get("vesselName") if data.get("vesselName") else ""
        return "点锅边浮着的菜盛出 %d 份%s   拖动勺子接着搅" % (data["meals"], need)
    if not any(keyOf(slot) for slot in data.get("inputs") or []):
        return "点下方物品栏把食材放进锅里   潜行右键 = 原来的界面"
    if not data.get("dish"):
        return "这些料凑不出菜：点锅里的料取回"
    if not data.get("heated"):
        return "锅下面没有热源：放在炉灶、营火或岩浆块上"
    if data.get("mode") == FD_WAY:
        return "锅在自己一份一份地煮   拖动勺子搅拌：整批一起煮"
    batch = data.get("batch") or 0
    if data.get("mode") == WAITING:
        return "拖动勺子搅拌才会煮   这批 %d 份" % batch
    return "搅拌中   这批 %d 份，还要 %d 秒" % (batch, data.get("left") or 0)
