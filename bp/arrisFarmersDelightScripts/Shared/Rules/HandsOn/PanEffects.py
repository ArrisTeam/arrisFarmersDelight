# -*- coding: utf-8 -*-
"""PanEffects - 服务端发来的一次性表现：别人颠了锅、放进了东西、被拒、取走、煎好了（双端）

移植自 Hands-On Delight 的 client/SkilletBehavior.java 的 onEffect（880-916）和 ready（918-925）。名字照 SkilletStation 的：
    tossed {"strength"}        谁颠的都演；本人自己颠过 0.6 秒内的不再演第二遍（他的客户端已经演了）
    untossed {}                服务端没认这一颠：食物照原来的样子躺着
    placed {"one"}             放进来了：热锅里下料的滋啦一声、挂灯一声（食物自己落进来由状态变化带出来）
    refused {"stack"}          放不进去的那一件弹开
    taken {"stack"}            全拿走了：每块抬起缩没
    fried {"stack", "in_pan", "to_cook"}   一批煎好：留在锅里（in_pan）就是一团汽一闪；否则走了（到厨师手上或跳出锅外）
"""
from functools import partial

from .PanLand import leaves, refused
from .PanToss import tossed

OWN_TOSS = 0.6      # 自己颠过之后这么久里，服务端回的颠不再演第二遍（SkilletBehavior 883）


def onEffect(show, name, data):
    if name == "tossed":
        if not show.focused or show.clock - show.tossedAt > OWN_TOSS:
            tossed(show, data.get("strength") or 0.0)
    elif name == "untossed":
        show.tossedUp, show.lookHeldUntil = None, 0.0
        show.refresh()
    elif name == "placed":
        if show.heated:
            show.sound("add_food", 0.8, 1.0)
        show.sound("lantern_place", 0.5, 1.0)
    elif name == "refused" and data.get("stack"):
        refused(show, data["stack"])
    elif name == "taken":
        leaves(show, data.get("stack"), True)
        show.sound("item_pickup", 0.3, 1.5)
    elif name == "fried":
        if data.get("in_pan"):
            ready(show)
        else:
            leaves(show, data.get("stack"), bool(data.get("to_cook")))
        show.sound("item_pickup", 0.35, 1.3)


def ready(show):
    """一批熟了留在锅里等人取：一团汽、一闪，油安静下来（918-925）。"""
    show.particles("steam", show.heat.onFood(), (0.0, 3.0, 0.0), 2.0, 4, 0x60FFFFFF)
    show.particles("glint", show.heat.onFood(), (0.0, 2.0, 0.0), 2.5, 4, 0xFFFFE9A0)
    show.sound("add_food", 0.4, 0.75)
    show.steps.after(0.35, partial(show.sound, "campfire_crackle", 0.6, 0.9))
