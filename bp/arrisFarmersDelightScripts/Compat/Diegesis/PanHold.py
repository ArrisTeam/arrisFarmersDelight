# -*- coding: utf-8 -*-
"""PanHold - 煎锅站点的触屏长按（前置包的表现钩子 onHold，条目和返回值的写法见 HoldMenu.py）：手指按在锅里按住不动，有什么右键 / Shift 点击的变体可给（客户端）

只给"和点一下不一样"的变体（PanView._withStack / onPointer 里点一下、右键各做什么）：
- 手上拿着一叠点锅（锅口、锅里的食物、锅柄，哪处都一样）：点一下整叠放进去（一批为止），右键一个——手上不止一个、锅里放得进（view.fits），才有"放一个"；
- 空手点锅里的食物（SkilletBehavior.onEvent 的 food）：点一下颠一下，熟了才是全拿回背包，右键永远是全拿回——食物还没熟（颠得动）时有"全部取回"。
锅柄（抓住往上提 = 颠，笔画一按下就开始，不能等）、别处都是 None：按下立刻生效。
"""
from . import HoldMenu
from ...Shared.Rules import PanStation as Rules


def onHold(owner, event):
    """PanViewMixin.onHold：owner 是表现，event 是和按下收到的同一种拾取事件。"""
    scene, view = owner.scene, owner.view
    if scene is None:
        return None
    key = event.hit.node.key if event.hit is not None else None
    if view.hand is not None:
        if key is not None and view.hand["count"] > 1 and view.fits(Rules.GROUP_PAN) is not None:
            return HoldMenu.menu(HoldMenu.PUT_ONE)
        return None
    if key == "food" and scene.show.shown is not None and not scene.show.isShownDone():
        return HoldMenu.menu(HoldMenu.TAKE_ALL_BACK)
    return None
