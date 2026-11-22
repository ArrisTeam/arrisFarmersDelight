# -*- coding: utf-8 -*-
"""PotFill - 厨锅经典界面的"添加食材"：挑一种写法、给每件食材在玩家背包里找来源、整体搬进食材格（双端，纯规则）

旧界面依次试每种写法、用第一种凑得齐的；这里先照锅里已经放着的料排先后，已经照某种写法放了一半的锅接着补那一种：
- 写法按"锅里 6 个食材格已经放着的、这种写法要的件数"从多到少试，一样多的照表里的先后（Book.fillOrder）；
- 空格不够放的跳过，必须放进空格的食材在背包里找不齐的跳过，第一种排得出来的就用它；
- 它一件都挪不了（锅里已经齐了、背包里也没有可再加的）就拒绝 nothing、不再往后试：不把另一种写法的料混进锅；
- 全都排不出来时：有因为缺食材跳过的拒绝 missing，否则 no_room；
- 格子里已经放着配方要的食材时只在放得下时再加一个（反复点就是备多份料，Book.planFill）。
先查后做：找来源的时候不动工作副本，挑定了才搬，搬不成整个拒绝（会话丢掉工作副本，什么都不会放一半）。
"""
from ...dolorContainer.Common import Actions, Items, Rules
from ...dolorContainer.Common.Collections import COMBINED, PLAYER_SIZE
from ..Rules import CookingPotBook as Book


def _sourceOf(ws, key, dst, left):
    """
    背包里第一格能拿一个 key 这种东西放进 dst 的格子（从快捷栏起；拿得走、dst 放得下）；没有为 None。
    left 记着这一次已经预定掉的个数（同一堆要拿几次）。
    """
    for index in range(PLAYER_SIZE):
        ref = (COMBINED, index)
        stack = ws.get(ref)
        if Book.keyOf(stack) == key and left.get(ref, Items.count(stack)) > 0 and ws.canLeave(ref, stack) and ws.room(dst, stack) > 0:
            return ref
    return None


def _moves(ws, slots, placements, topUps):
    """
    给每次"从背包拿一个放进食材格"找来源，返回 [(来源格, 去处格)]；放进空格的（必须的）有一件找不到来源（缺食材、被锁住、
    放不下）时返回 None。给已有的格子再加一个的有就加、找不到就算了。查的时候不动工作副本。
    """
    left, moves = {}, []
    for required, wanted in ((True, placements), (False, topUps)):
        for slot, key in wanted:
            dst = (slots, slot)
            source = _sourceOf(ws, key, dst, left)
            if source is None:
                if required:
                    return None
                continue
            left[source] = left.get(source, Items.count(ws.get(source))) - 1
            moves.append((source, dst))
    return moves


def plan(ws, recipe, slots):
    """
    挑写法并找齐来源（slots 是食材格的集合名）：返回 [(来源格, 去处格)]，空的表示挑中的那种一件都挪不了；
    一种都排不出来时抛 Refused（missing / no_room）。
    """
    keys = [Book.keyOf(ws.get((slots, index))) for index in range(Book.INPUT_SLOTS)]
    missing = False
    for variant in Book.fillOrder(recipe, keys):
        fill = Book.planFill(variant, keys)
        if fill is None:
            continue
        moves = _moves(ws, slots, fill[0], fill[1])
        if moves is None:
            missing = True
            continue
        return moves
    raise Actions.Refused("missing" if missing else "no_room")


def fill(ws, recipe, slots):
    """照 plan 挑定的搬：每件从来源格拿一个放进食材格；一件都挪不了拒绝 nothing，写不进去拒绝 write_failed。"""
    moves = plan(ws, recipe, slots)
    if not moves:
        raise Actions.Refused("nothing")
    for source, dst in moves:
        if Rules.transfer(ws, source, dst, 1) < 1:
            raise Actions.Refused("write_failed")
