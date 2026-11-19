# -*- coding: utf-8 -*-
"""GrillHold - 炉灶站点的触屏长按（前置包的表现钩子 onHold，条目和返回值的写法见 HoldMenu.py）：手指按在烤架上按住不动，有什么右键 / Shift 点击的变体可给（客户端）

只给"和点一下不一样"的变体（GrillView._place / _piece 里点一下、右键各做什么）：
- 手上拿着东西点烤架（mouth）：左键每个空位摆一件（先摆第一个空位），右键只摆离光标最近的空位那一件——空位不止一个，选哪一格才有区别、而且烤架收这件东西
  （view.fits：鸡蛋、铁锭、泥土烤架不收，左键右键都放不上去），才有"只放这一格"。前置包有数量档、手上又不止一个时不给：那个按钮的"单个"档点一下就是右键
  （只摆离光标最近的那一格一件），"全部"档是每个空位一件；手上只有一个时两档都是左键（摆第一个空位），选哪一格还得靠它；
- 空手点烤位上的一件（piece）：生的、半熟的点一下翻面，右键取下（烤好的左键右键都是取下）——点一下确实是翻面（不是已经烤好、也不是刚翻过还在空中）时有"取下"。
别处是 None：按下立刻生效。
"""
from . import HoldMenu
from ...Shared.Rules import GrillStation as Rules
from ...Shared.Rules.HandsOn import StoveLayout


def onHold(owner, event):
    """GrillViewMixin.onHold：owner 是表现，event 是和按下收到的同一种拾取事件。"""
    if owner.scene is None:
        return None
    key = event.hit.node.key if event.hit is not None else None
    if owner.view.hand is not None:
        view = owner.view
        covered = HoldMenu.tapMode(view) and view.hand["count"] > 1            # 数量档管着：单个 = 只放这一格
        puts = key == "mouth" and not covered and owner._free().count(True) > 1 and view.fits(Rules.GROUP_GRILL) is not None
        return HoldMenu.menu(HoldMenu.PUT_HERE) if puts else None
    if key != "piece":
        return None
    pieces, place = owner.scene.pieces, event.hit.node.payload
    item = pieces.shown[place]
    if item is None:
        return None
    tap = StoveLayout.pieceClick(0, Rules.isDone(item["newItemName"]), pieces.clock - pieces.turnedAt[place])
    return HoldMenu.menu(HoldMenu.TAKE_PIECE) if tap == StoveLayout.TURN else None
