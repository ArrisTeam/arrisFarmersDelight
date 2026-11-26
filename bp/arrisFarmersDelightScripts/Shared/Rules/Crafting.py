# -*- coding: utf-8 -*-
"""Crafting - 工作台合成的纯规则：格子里摆的是哪条配方、实际做了几份、剩余物放哪（双端）

JE 的 ResultSlot.onTake：做完一份，每格原料用掉一件，再按配方的 getRemainingItems（原料自带的合成剩余物，
Shared/Data/Remainders.py；面团配方把水桶原样留下）放回去——那格空了放回那格，同一种就叠上去，否则进背包，背包满了掉地上。
基岩版有序配方把剩余物写进 result 数组由引擎给；无序配方的 result 数组只出第一项，由服务端补：取结果时（CraftItemOutputChange
ServerEvent）记下格子，下一刻再读一遍，按每格真的少了几件算做了几份（取消了、请求被拒都是 0 份），再按本包的无序配方表
（tools/gen_crafts.py 生成的 Shared/Data/CraftReturns.py）认出是哪条、放回格子 / 给玩家。
表里每条配方一格一个选项（物品名，或 "#标签"：按 Shared/Rules/ItemTags 现问，别的模组并进标签的东西也认）；还什么按格子里**实际放的物品**
查 Remainders（和 JE 一样按物品算；别的模组并进来的、表里没有的物品不留东西），keeps 里的选项原样留下（面团的水桶）。
两条不变式：一次合成每格最多还一次（crafts 份就还 crafts 件，不和别的路叠）；认不出是哪条配方（没有一条对得上，或者对上了不止一条）
时什么都不还。
格子是 {槽位: (物品名, 个数)}；槽位是 PlayerUISlot：2×2 是 28..31，3×3 是 32..40。
"""
from ..Data import Remainders
from . import ItemTags

GRID_SLOTS = tuple(range(28, 41))


def namesOf(grid):
    """格子 -> 排好序的物品名元组（一格算一件，叠了几个不管）。"""
    return tuple(sorted(name for name, _count in grid.values()))


def fits(name, option):
    """这件物品算不算这一格的选项：物品名一样，或者选项是 "#标签" 而它带这个标签。"""
    if not name or not option:
        return False
    if option.startswith("#"):
        return ItemTags.has(name, option[1:])
    return name == option


def _assign(names, slots):
    """格子里的物品（一格一件）能不能一一对上配方的各格（无序配方：哪件放哪格不管）：回溯找一种对法。"""
    if not names:
        return not slots
    first, rest = names[0], names[1:]
    tried = set()
    for index, option in enumerate(slots):
        if option in tried or not fits(first, option):
            continue
        tried.add(option)
        if _assign(rest, slots[:index] + slots[index + 1:]):
            return True
    return False


def entryFor(entries, grid):
    """这个成品的配方条目里，格子里的东西正好一一对得上的那条（标签格按标签认）；没有、或者不止一条对得上，返回 None。"""
    names = namesOf(grid)
    found = [entry for entry in entries or () if len(entry["slots"]) == len(names) and _assign(names, tuple(entry["slots"]))]
    return found[0] if len(found) == 1 else None


def leftOf(entry, name):
    """这件原料做完一份剩下什么：keeps 里的选项原样留下，否则查 Remainders（没有是 None）。"""
    for option in entry.get("keeps") or ():
        if fits(name, option):
            return name
    return Remainders.craftRemainderOf(name)


def craftsDone(before, after, most=None):
    """取结果前后的格子 -> 实际做了几份：每格都少了的件数取最少的那格（同一刻里玩家又挪走别的格子也不会多算）；
    most 是按取出的个数算出的上限（取出 N 个、一份出 k 个最多 N // k 份）。"""
    if not before:
        return 0
    done = None
    for slot, (name, count) in before.items():
        now = after.get(slot)
        left = now[1] if now is not None and now[0] == name else 0
        used = max(0, count - left)
        done = used if done is None else min(done, used)
    if most is not None:
        done = min(done, max(0, int(most)))
    return done or 0


def mostCrafts(taken, perCraft):
    """一次取出 taken 个、每份出 perCraft 个 -> 最多做了几份（至少 1）。"""
    return max(1, int(taken or 0) // max(1, int(perCraft or 1)))


def returnsOf(entry, before, crafts):
    """要还的剩余物：[(槽位, 剩余物名, 个数)]，按槽位排序；crafts 份，每份每格还一件（按那格实际放的物品算）。"""
    if crafts <= 0 or entry is None:
        return []
    plan = []
    for slot in sorted(before):
        left = leftOf(entry, before[slot][0])
        if left:
            plan.append((slot, left, crafts))
    return plan


def settle(now, left, count, maxStack):
    """剩余物 count 个放回那格：那格现在是 now（(物品名, 个数) 或 None）。
    返回 (那格该设成的 (物品名, 个数)，None 表示不动；进背包的个数)。"""
    room = max(1, int(maxStack or 1))
    if now is None:
        put = min(count, room)
        return (left, put), count - put
    if now[0] == left and now[1] < room:
        put = min(count, room - now[1])
        return (left, now[1] + put), count - put
    return None, count
