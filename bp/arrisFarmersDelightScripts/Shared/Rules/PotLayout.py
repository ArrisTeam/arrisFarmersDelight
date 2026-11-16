# -*- coding: utf-8 -*-
"""PotLayout - 锅里的料按哪道菜摆：选菜、把料摆回格子、照食谱书放料的计划（双端，纯规则）

移植自 Hands-On Delight 的 station/StationRecipes.java（choose / rank / lay / servings / fits / kept / leftOver / fill）。
Java 的锅一格一件地读配方：同种的料扔进去会叠在一格，所以站点要在玩家放完之后把料按"锅读得懂的样子"摆开。
本包的配方是展开过标签的"写法"（Shared/Data/CookingPotRecipes.py）：每个写法是几个 (物品名, aux)，一件占一格。
所以 Java 里"每个配料挑一种料"的搜索这里只剩查表：锅里料的种类集合正好等于某个写法的种类集合时，这个写法就是候选，
它的 parts（每种料占几格）是这种料在写法里出现几次（CookingPot.candidatesFor）。

食材格是 6 项的列表，每项是物品字典（newItemName / newAuxValue / count）或空（None / {}）；种类是 (物品名, aux)。
"""
import copy

from . import CookingPot

INPUT_SLOTS = 6


def keyOf(item):
    if not item or not item.get("newItemName") or (item.get("count") or 0) <= 0:
        return None
    return (item["newItemName"], item.get("newAuxValue") or 0)


def countOf(item):
    return (item.get("count") or 0) if keyOf(item) else 0


def cellsOf(slots):
    """6 格：空格统一成 None，多的截掉、少的补空。"""
    cells = [copy.deepcopy(slot) if keyOf(slot) else None for slot in list(slots)[:INPUT_SLOTS]]
    return cells + [None] * (INPUT_SLOTS - len(cells))


def stackOf(sample, count):
    stack = copy.deepcopy(sample)
    stack["count"] = count
    return stack


def kindsOf(slots):
    """[(种类, 总数)]，按第一次出现的格子排（StationRecipes.kinds：同种的格子算在一起）。"""
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


def _hold(key, maxStackOf):
    return max(1, maxStackOf(key))


def servings(totals, parts, maxStackOf):
    """这些格子最多够做几份：每种料按"它占的格子装得下的件数"和手里的件数取小，再除以格数，取最小的（StationRecipes.servings）。"""
    return min(min(totals[key], count * _hold(key, maxStackOf)) // count for key, count in parts.items())


def fits(totals, parts, maxStackOf):
    """每种料都装得进它占的格子（一格一堆）吗（StationRecipes.fits）。"""
    return all(totals[key] <= count * _hold(key, maxStackOf) for key, count in parts.items())


def kept(totals, parts, maxStackOf):
    """它占的格子一共装得下多少件（StationRecipes.kept）。"""
    return sum(min(totals[key], count * _hold(key, maxStackOf)) for key, count in parts.items())


def leftOver(totals, parts, maxStackOf):
    """做完能做的份数之后，还剩几件没用上（StationRecipes.leftOver）。"""
    return sum(totals.values()) - servings(totals, parts, maxStackOf) * sum(parts.values())


def _rank(candidate, totals, found, wanted, maxStackOf):
    """候选的排序键，小的优先（StationRecipes.choose 的 picked + rank）：书里点的那道先；
    然后没有剩料的先，其中配料多的先（两个糖加一种染料做糖糖染料那道，不做糖染料那道）；再是份数多的、
    锅按现在摆法读出的那道（它本来怎么煮还怎么煮）、剩料少的、配料多的。同分取配方表靠前的（min 取第一个）。"""
    index, parts = candidate
    over = leftOver(totals, parts, maxStackOf)
    size = sum(parts.values())
    clean = over == 0
    return (index != wanted, 0 if clean else 1, -size if clean else 0, -servings(totals, parts, maxStackOf),
            index != found, over, -size)


def choose(kinds, maxStackOf, wanted=None, found=None, overflow=False):
    """这些料做哪道菜：返回 (配方序号, {种类: 占几格})，做不成返回 None（StationRecipes.choose）。
    kinds 是 kindsOf 的结果；wanted 是书里点的那道的序号；found 是锅按现在的摆法读成的那道（CookingPot.matchIndex）；
    overflow：没有哪道菜装得下全部的料时，让装得下最多的那道留着、多的料退回给玩家（站点里有人时才这样）。"""
    totals = dict(kinds)
    held, spilt = [], []
    for index, parts in CookingPot.candidatesFor(totals):
        if sum(parts.values()) > INPUT_SLOTS or any(totals[key] < count for key, count in parts.items()):
            continue                                   # 每个配料都要有一件料可用（StationRecipes.parts）
        (held if fits(totals, parts, maxStackOf) else spilt).append((index, parts))
    if held:
        return min(held, key=lambda candidate: _rank(candidate, totals, found, wanted, maxStackOf))
    if not overflow or not spilt:
        return None
    return min(spilt, key=lambda candidate: (candidate[0] != wanted, -kept(totals, candidate[1], maxStackOf)))


def lay(cells, kinds, parts, maxStackOf):
    """把每种料平分到它占的格子上，一格最多一堆；返回 (新的 6 格, 放不下的 [物品字典])（StationRecipes.lay）。
    一种料留在它原来躺着的格子里（漂在汤里的东西不乱跑），已经摆对的格子不动；没分到料的格子清空。"""
    size = len(cells)
    sample = {}
    for cell in cells:
        if keyOf(cell) is not None:
            sample.setdefault(keyOf(cell), cell)
    kindAt = [-1] * size
    placed = [0] * len(kinds)
    for slot in range(size):
        key = keyOf(cells[slot])
        for index, (kind, _total) in enumerate(kinds):
            if key is not None and key == kind and placed[index] < parts[kind]:
                kindAt[slot] = index
                placed[index] += 1
                break
    free = 0
    for index, (kind, _total) in enumerate(kinds):
        while placed[index] < parts[kind]:
            while kindAt[free] >= 0:
                free += 1
            kindAt[free] = index
            placed[index] += 1
    left = [min(total, parts[kind] * _hold(kind, maxStackOf)) for kind, total in kinds]
    rest = [stackOf(sample[kind], total - left[index]) for index, (kind, total) in enumerate(kinds) if left[index] < total]
    slotsLeft = [parts[kind] for kind, _total in kinds]
    out = [None] * size
    for slot in range(size):
        index = kindAt[slot]
        if index >= 0:
            share = (left[index] + slotsLeft[index] - 1) // slotsLeft[index]
            out[slot] = stackOf(sample[kinds[index][0]], share)
            left[index] -= share
            slotsLeft[index] -= 1
    return out, rest


def layout(slots, maxStackOf, wanted=None, found=None, overflow=True):
    """锅里的料按它做的那道菜摆开（PotLogic.shareOut）：返回 (新的 6 格, 放不下的 [物品字典])；
    做不成任何菜、或已经是这样摆的返回 None（凑不成菜的料原样放着）。"""
    cells = cellsOf(slots)
    kinds = kindsOf(cells)
    choice = choose(kinds, maxStackOf, wanted, found, overflow)
    if choice is None:
        return None
    out, rest = lay(cells, kinds, choice[1], maxStackOf)
    if not rest and [(keyOf(c), countOf(c)) for c in out] == [(keyOf(c), countOf(c)) for c in cells]:
        return None
    return out, rest


def planFill(variants, held, pool, sets, maxStackOf):
    """照书放料的计划（StationRecipes.fill）：返回 ({种类: 一份要几件}, 放几份)；一份都放不了返回 None。
    variants：这道菜的各种写法；held：锅里现有的 {种类: 件数}；pool：背包里的 {种类: 件数}；sets：最多放几份。
    锅里有这种写法用不上的料时这种写法不用（HoD：锅里有这道菜用不上的食物，书什么也不放）；份数受背包、受"每种料装得进
    它占的格子"（整份整份地放，装不下的那一份不放）限制；几种写法取份数最多的，一样多取靠前的。"""
    best, bestSets = None, 0
    for variant in variants:
        each = {}
        for entry in variant:
            kind = (entry[0], entry[1])
            each[kind] = each.get(kind, 0) + 1
        if any(kind not in each for kind in held) or len(each) > INPUT_SLOTS:
            continue
        count = int(sets)
        for kind, need in each.items():
            room = need * _hold(kind, maxStackOf) - held.get(kind, 0)
            count = min(count, pool.get(kind, 0) // need, max(0, room // need))
        if count > bestSets:
            best, bestSets = each, count
    return (best, bestSets) if best is not None else None
