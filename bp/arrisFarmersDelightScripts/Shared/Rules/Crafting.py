# -*- coding: utf-8 -*-
"""Crafting - 工作台合成的纯规则：格子里摆的是哪条配方、实际做了几份、剩余物放哪（双端）

JE 的 ResultSlot.onTake：做完一份，每格原料用掉一件，再按配方的 getRemainingItems（原料自带的合成剩余物，
Shared/Data/Remainders.py；面团配方把水桶原样留下）放回去——那格空了放回那格，同一种就叠上去，否则进背包，背包满了掉地上。
基岩版有序配方把剩余物写进 result 数组由引擎给；无序配方的 result 数组只出第一项，由服务端补：取结果时（CraftItemOutputChange
ServerEvent）记下格子，下一刻再读一遍，按每格真的少了几件算做了几份（取消了、请求被拒都是 0 份），再按本包配方的剩余物表
（tools/gen_crafts.py 生成的 Shared/Data/CraftReturns.py）放回格子 / 给玩家。
格子是 {槽位: (物品名, 个数)}；槽位是 PlayerUISlot：2×2 是 28..31，3×3 是 32..40。
"""
GRID_SLOTS = tuple(range(28, 41))


def namesOf(grid):
    """格子 -> 排好序的物品名元组（一格算一件，叠了几个不管）。"""
    return tuple(sorted(name for name, _count in grid.values()))


def entryFor(entries, grid):
    """这个成品的配方条目里，原料正好是格子里这些的那条；没有返回 None。"""
    names = namesOf(grid)
    for entry in entries or ():
        if tuple(entry["ingredients"]) == names:
            return entry
    return None


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
    """要还的剩余物：[(槽位, 剩余物名, 个数)]，按槽位排序；crafts 份，每份每格还一件。"""
    if crafts <= 0:
        return []
    returns = entry.get("returns") or {}
    plan = []
    for slot in sorted(before):
        left = returns.get(before[slot][0])
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
