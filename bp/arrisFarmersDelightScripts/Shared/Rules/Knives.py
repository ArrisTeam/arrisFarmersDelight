# -*- coding: utf-8 -*-
"""Knives - 是不是刀（双端，纯规则）

JE 的 ItemUtils.isKnife：farmersdelight:tools/knives 标签（或刀的工具动作）。这边下面三样任一个说是就是：
- knifeList（Shared/Data/Cutting，联动契约：下游往里追加名字，两端经表同步；砧板刀切配方的 tool 就是这个列表对象）；
- 带 arris:knife 物品标签（linkage.md 让下游在物品 JSON 的 minecraft:tags 里给自己的刀挂它；农夫乐事自己的五把刀经 netease_tags 也挂上了）；
- 带 common:knife 物品标签（团队约定的通用刀，别的模组在自己的 netease_tags 里登记，JE 的 forge:tools/knives）。
标签都经 Shared/Rules/ItemTags 问：两端各有引擎口，按单件问的口没准备好也问；没有口（离线、沙箱）时按静态词表，农夫乐事自己的五把刀照样是刀。
这里不缓存（ItemTags 自己缓存，客户端进世界之前的答案它不留）。
服务端 Server/Helpers/Items.IsKnife、客户端 Client/BlockItems.isKnife（砧板站点、板上插着的刀也问它）、炉灶站点开不开（GrillStation.opens）问的都是这里。
"""
from ..Data import Tags
from ..Data.Cutting import knifeList
from . import ItemTags


def isKnife(itemName):
    """这件东西（物品名）是不是刀。"""
    if not itemName:
        return False
    return itemName in knifeList or ItemTags.has(itemName, Tags.LEGACY_KNIFE) or ItemTags.has(itemName, Tags.KNIFE)
