# -*- coding: utf-8 -*-
"""
物品飞行动画的配对，照原版比较操作前后状态的做法：

1. 逐格比较前后：完全相同的格子不管；前后是同一种东西的，先抵消没动的数量（两边各减去较少的那个）；
2. 按顺序把每个还有余量的"前"格子，配给还有余量、同种的"后"格子，各生成一次飞行，两边各减去搬走的数量；
   同时照原版标出目标格是不是从空变成有东西（原版据此安排"到达处淡入"，实测目标格的图标并不会被藏起来，界面不用这一项）。

哪些操作有飞行（与原版一致）：快速转移（各种输入方式）；触屏的搬运、分配、双击收集；键鼠的数字键（手上没东西时）。
键鼠与手柄拿在指针上的拿放不飞。纯逻辑，界面拿结果去驱动引擎的物品飞行渲染器。
"""
from ..Common import Items


def _same(a, b):
    """同一种东西（名字、aux、userData 都相同，不看数量）。"""
    return a is not None and b is not None and Items.sameKind(a, b)


def _equal(a, b):
    return _same(a, b) and Items.count(a) == Items.count(b) or (a is None and b is None)


def transfers(changes, order=None, origin=None):
    """
    changes：{格: (之前, 之后)}，只含变了的格子（不含手持物）；order：格子先后的排序键（缺省按格子本身排）；
    origin：配对之后还有没来处的东西（凭空多出来的：交易做出来的产物）时，它们从这一格飞出来（None 为不飞）。
    返回 [(物品堆, 来源格, 目标格, 到达处是否隐藏图标)]，按格子顺序配对。
    """
    entries = []
    for ref in sorted(changes, key=order):
        old, new = (Items.normalize(stack) for stack in changes[ref])
        if _equal(old, new):
            continue
        oldCount, newCount = Items.count(old), Items.count(new)
        if _same(old, new):
            unmoved = min(oldCount, newCount)
            oldCount -= unmoved
            newCount -= unmoved
        entries.append({"ref": ref, "old": old, "left": oldCount, "new": new, "arrive": newCount,
                        "fade": old is None and new is not None})
    out = []
    for source in entries:
        for target in entries:
            if source["left"] <= 0:
                break
            if target["arrive"] > 0 and _same(source["old"], target["new"]):
                out.append((Items.withCount(source["old"], source["left"]), source["ref"], target["ref"],
                            target["fade"]))
                moved = min(source["left"], target["arrive"])
                source["left"] -= moved
                target["arrive"] -= moved
    if origin is not None:
        for target in entries:
            if target["arrive"] > 0 and target["ref"] != origin:
                out.append((Items.withCount(target["new"], target["arrive"]), origin, target["ref"], target["fade"]))
    return out
