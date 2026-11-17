# -*- coding: utf-8 -*-
"""PotPick - 厨锅站点里点得到什么：给内核的拾取盒，和手上拿着盛汤容器时哪些点法算盛一份（客户端）

对应 Hands-On Delight：scenes/cooking_pot.json 里带碰撞盒的节点、client/PotBehavior.java 的 onItemClick（516-539）、
Diegesis 的 FocusInput.offerCarried（420-423）：手上拿着东西点下去，内核先把这一下交给表现的 onItemClick，交的是光标下最前面的那个
开着的、有碰撞盒的节点（pickable 为假的没有盒子，关着的、触发区不算），不看是哪个键，Shift 是全盛。厨锅的 onItemClick 里，除了 preview
（徽章上那个小图标，这里徽章是界面，没有它的盒子）和食谱书，只要手上是这锅煮好的菜的容器、锅里有菜（canScoop），点到哪个节点都盛一份。
cooking_pot.json 里带盒子的节点，对应这里的拾取盒：
- ladle   勺柄露在锅沿上的那一截（scene.spoon.pickAabb）：一直开着；
- mouth   锅口，整口锅（drop_zone "ingredients"）；
- item_N  漂着的料（料到了、不是沉底的才开），盛好的那一格 served（锅里有菜才开）；
- soup、sunk  只在手空着时开（offerBowl / offerTakeBack 里手上有东西就关），拿着东西时点不到；
- pot（锅身）、broth（液面）、scoop、melt_N、hand_N、spill_N、badge、dial 是 pickable: false，没有盒子，点它们等于点到后面的节点。
所以拿着容器时有四种盒子（mouth、ladle、item、served），点哪个都盛；拿着别的东西（料）时 onItemClick 不管，点到的节点里只有锅口会接
（drop_zone），料所在的格在锅口里面、被锅口挡在后面，所以手上拿着料时只留锅口。点下去怎么办（盛，还是放进锅口）在 withStack。
"""
from ...Shared.Rules import PotStation as Rules
from ...Shared.Rules.HandsOn import PotDriftExtras

MOUTH = ((2.0, 6.0, 2.0), (14.0, 14.0, 14.0))       # 锅口：拿着东西时整口锅都是它
SOUP = ((4.0, 2.0, 4.0), (12.0, 9.0, 12.0))          # 悬着碗的时候才接点击（offerBowl 里 soup.setEnabled）
SUNK_HALF = 0.3                                     # 取回沉下去的料：贴着汤面上下各 0.3 的一层（sunk 节点），漂着的料比它高
ITEM_HALF, ITEM_TALL = 1.6, 0.3                     # 漂着的料的命中盒：左右各 1.6，上下各 0.3
SCOOPS = ("mouth", "ladle", "item", "served")       # 手上拿着盛这道菜的容器时，点到这几种盒子都是盛一份


def holdsVessel(view):
    """手上拿着的是这锅煮好的菜的容器、锅里有菜（PotBehavior.canScoop：菜不空、容器合用）。"""
    hand, meal, vessel = view.hand, view.data.get("meal"), view.data.get("vessel") or {}
    return bool(hand is not None and meal and vessel.get("newItemName") and hand.get("newItemName") == vessel["newItemName"])


def _local(owner, key, lo, hi, payload=None):
    """锅自己的坐标里的一个盒子 -> 站点像素里的拾取盒（锅按方块朝向转，站点按玩家站的一侧转）。"""
    a, b = owner.toStation(*lo), owner.toStation(*hi)
    return owner.api.box(key, tuple(min(a[i], b[i]) for i in range(3)), tuple(max(a[i], b[i]) for i in range(3)), payload=payload)


def boxes(owner):
    """owner（PotViewMixin）现在能点的盒子。手空着：勺柄、漂着的料、盛好的那格，再加悬着碗时的 soup 或能取回时的 sunk；
    手上拿着盛这道菜的容器：锅口、勺柄、漂着的料、盛好的那格；拿着别的：只有锅口。"""
    scene = owner.scene
    if scene is None or scene.look is None:
        return []
    api, carrying = owner.api, owner.view.hand is not None
    if carrying and not holdsVessel(owner.view):
        return [api.box("mouth", MOUTH[0], MOUTH[1])]
    lo, hi = scene.spoon.pickAabb()
    found = [api.box("mouth", MOUTH[0], MOUTH[1])] if carrying else []
    found.append(_local(owner, "ladle", (8.0 + lo[0], lo[1], 8.0 + lo[2]), (8.0 + hi[0], hi[1], 8.0 + hi[2])))
    drift, look = scene.drift, scene.look
    for slot in range(len(look.items)):
        if look.items[slot] is not None and drift.visible[slot] and not drift.waiting[slot]:
            x, y, z = drift.x[slot], drift.y[slot], drift.z[slot]
            found.append(_local(owner, "item", (x - ITEM_HALF, y - ITEM_TALL, z - ITEM_HALF), (x + ITEM_HALF, y + ITEM_TALL, z + ITEM_HALF), slot))
    if look.served is not None:
        x, y, z = PotDriftExtras.servedAt(scene.liquid.surfaceY())
        found.append(api.box("served", (x - ITEM_HALF, y - ITEM_TALL, z - ITEM_HALF), (x + ITEM_HALF, y + ITEM_TALL, z + ITEM_HALF)))
    if carrying:
        return found
    if owner.serve.offer is not None and owner.serve.offered is not None:
        found.append(api.box("soup", SOUP[0], SOUP[1]))
    elif owner.serve.takesBack:
        level = scene.liquid.surfaceY()
        found.append(api.box("sunk", (SOUP[0][0], level - SUNK_HALF, SOUP[0][2]), (SOUP[1][0], level + SUNK_HALF, SOUP[1][2])))
    return found


def withStack(owner, event, key):
    """手上拿着东西点下去（PotView.onPointer）：盛这道菜的容器 = 盛一份，点到锅口、勺柄、漂着的料、盛好的那格哪个都行（带碰撞盒的节点），
    Shift 全盛，哪个键都行（PotBehavior.onItemClick 不看节点和 button）；别的 = 点锅口放进去（dropOnMouth），点在别处不接
    （右键由内核把手上的放回背包）。返回真 = 这一下接了。"""
    view = owner.view
    if holdsVessel(view) and key in SCOOPS:
        view.sendAction("scoop", {"all": bool(event.quick), "from_inventory": False})
        owner.serve.bowlWentIn(surfacePoint(owner, event))
        return True
    return key == "mouth" and dropOnMouth(owner, event)


def dropOnMouth(owner, event):
    """手上的东西点锅口：落在第一格放得下的（同种没满的优先，否则第一个空格），左键整叠、右键一个。
    按下时只记下是哪一格、哪个键，松手才发（Diegesis 的 FocusInput.clickItem 末尾和 release：锅口是放置区，onItemClick 不接它，所以走这条）：
    松在哪里都算按下时那一格，拖过托盘的格子就是平分，放下的那一声也是内核在松手时放；从托盘直接拖到锅上，内核在松手处补的一按一松同样走这里。
    没有格子放得下什么也不接。"""
    view = owner.view
    index = view.fits(Rules.GROUP_INGREDIENTS)
    if index is None:
        return False
    spread = getattr(view, "spread", None)
    if spread is None:                    # 老版本的前置包没有平分手势：照旧按下就放
        return view.dropInto(Rules.GROUP_INGREDIENTS, event.button) is not None
    return spread.begin(owner.api.stationTarget(Rules.GROUP_INGREDIENTS, index), event.button, event.screen)


def surfacePoint(owner, event):
    """手上的容器点下去，水波敲在光标射线和液面相交的那一点上（PotBehavior 的 view.cursorOn(surface)），不是射线先碰到的那个盒子上的点
    （点勺柄时那一点在锅外面）；没有射线时才用盒子上的点。"""
    ray = event.ray
    point = owner.api.Geometry.planeAtHeight(ray, owner.scene.liquid.surfaceY()) if ray is not None else None
    return point if point is not None else event.point
