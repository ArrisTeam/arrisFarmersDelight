# -*- coding: utf-8 -*-
"""FlatSprites - 站点表现回答前置包的 flatSprite 钩子：哪些方块物品引擎画成一张平面图（客户端，纯逻辑）

手上拿着的东西（前置包的光标栈）里，方块物品引擎有的画成一个小立方体、有的画成一张平面图（花、野生作物：物品类型是 block，掉落物却是一张贴图）；
前置包只看得到物品类型，分不出这两种，所以让表现说（前置包的可选钩子 flatSprite(item)，Protocol.FLAT_SPRITES）。答案是 Shared/Data/FlatBlockItems——
砧板画板上的东西用的同一张表（BoardStation.Env.isRaised，实机量过这 21 件）：在表里的前置包就当贴图物品画（边长、往后仰、影子都和别的贴图物品一样），
并按引擎的规矩抬高着摆（前置包的 PropMath.raisedShift，和 Shared/Rules/ItemPose.raisedShift 同一个公式），不再画成两倍大的立方体和方形的影子。
老版本的前置包没有这个钩子（api 上没有 FLAT_SPRITES）：表现类不挂它，和从前一样。四个站点（厨锅、砧板、煎锅、炉灶）的表现类都挂：
手上拿着的东西在哪个站点里都画。
"""
from ...Shared.Data.FlatBlockItems import FlatBlockItems
from ...Shared.Rules.BoardStation import shownItem


def flatSprite(owner, item):
    """表现的 flatSprite 钩子：这件方块物品引擎画成一张平面图吗（前置包只对方块物品问）。"""
    name = item.get("newItemName") if item else None
    return name in FlatBlockItems


def shownAs(owner, item):
    """表现的 shownAs 钩子（前置包的 Protocol.SHOWN_AS）：手上这件画出来用哪件物品——蘑菇丛换成它的平面物品，别的不换（None）。"""
    shown = shownItem(item) if item else item
    return shown if shown is not item else None


def attrs(api, base):
    """表现类的属性：前置包认 FLAT_SPRITES 才加上 flatSprite 钩子、认 SHOWN_AS 才加上 shownAs 钩子（老版本既不认也不会问，不加）。
    base 是原来要交给 type() 的属性字典。"""
    found = dict(base, flatSprite=flatSprite) if getattr(api, "FLAT_SPRITES", False) else base
    return dict(found, shownAs=shownAs) if getattr(api, "SHOWN_AS", False) else found
