# -*- coding: utf-8 -*-
"""PotHold - 厨锅站点的触屏长按（前置包的表现钩子 onHold，条目和返回值的写法见 HoldMenu.py）：手指按在厨锅场景里按住不动，有什么右键 / Shift 点击的变体可给（客户端）

只给"和点一下不一样"的变体（PotView.onPointer 里点一下、右键、Shift 各做什么）：
- 手上拿着一叠料点锅口（PotPick.dropOnMouth）：左键整叠放进第一格放得下的，右键一个——手上不止一个、放得进，才有"放一个"；
- 手上拿着盛这锅菜的容器点锅口、勺柄、漂着的料、盛好的那格（PotPick.withStack）：点一下盛一份，Shift 盛到没菜或没容器——锅里有不止一份菜、手上的容器也不止一个，才有"全部盛出"；
- 空手点漂着的料 / 盛好的那格（PotView.onPointer）：左键整格拿到手上，右键一半——这一格有不止一个：取份量条（那一格、那么多），松手发 TAKE；
- 空手点悬着碗的汤（PotOffer.soupClick）：点一下盛一份，Shift 全盛——锅里有不止一份菜、背包里的容器也不止一个，才有"全部盛出"。
勺柄（握勺子的笔画一按下就开始，不能等）、沉底的料（只有一种做法）、别处都是 None：按下立刻生效。
"""
from . import HoldMenu, PotOffer, PotPick
from ...Shared.Rules import PotStation as Rules


def onHold(owner, event):
    """PotViewMixin.onHold：owner 是表现，event 是和按下收到的同一种拾取事件。"""
    scene, view = owner.scene, owner.view
    if scene is None or scene.look is None:
        return None
    key = event.hit.node.key if event.hit is not None else None
    payload = event.hit.node.payload if event.hit is not None else None
    if view.hand is not None:
        return _withStack(view, key)
    if key in ("item", "served"):
        stack = scene.look.items[int(payload)] if key == "item" else scene.look.served
        return HoldMenu.take(owner._slotOf(key, payload), stack["count"] if stack else 0)
    if key == "soup" and _servings(view) > 1 and _vessels(view) > 1:
        return HoldMenu.menu(HoldMenu.SCOOP_ALL)
    return None


def _servings(view):
    """锅里的菜还有几份。"""
    meal = view.data.get("meal")
    return meal["count"] if meal else 0


def _vessels(view):
    """背包里盛这锅菜的容器有几个。"""
    name = (view.data.get("vessel") or {}).get("newItemName")
    return PotOffer.carried(name) if name else 0


def _withStack(view, key):
    hand = view.hand
    if PotPick.holdsVessel(view):
        return HoldMenu.menu(HoldMenu.SCOOP_ALL) if key in PotPick.SCOOPS and min(_servings(view), hand["count"]) > 1 else None
    if key == "mouth" and hand["count"] > 1 and view.fits(Rules.GROUP_INGREDIENTS) is not None:
        return HoldMenu.menu(HoldMenu.PUT_ONE)
    return None
