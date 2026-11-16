# -*- coding: utf-8 -*-
"""FoodEffects - 吃喝之后要追加的结算（双端，纯规则）

JE 里牛奶瓶、热可可是 Item 子类的 affectConsumer（MilkBottleItem / HotCocoaItem），原版汤是 CommonEvents 里的
LivingEntityUseItemEvent.Finish 事件；网易的 minecraft:food 表达不了这些，由服务端在 PlayerEatFoodServerEvent 里结算。
这里只决定"做什么"（返回动作元组），引擎调用在 Server/FoodEffects.py，所以不碰引擎、离线可测。

动作：
    (REMOVE, 效果名)
    (ADD, 效果名, 秒, 等级, 是否显示粒子)
"""
from ..Data.Effects import negativeEffect, VANILLA_SOUP_BUFFS

REMOVE = "remove"
ADD = "add"

MILK_BOTTLE = "arris:milk_bottle"
HOT_COCOA = "arris:hot_cocoa"


def _milk(activeEffects, rng):
    # 牛奶瓶：随机清除身上的一个效果
    if not activeEffects:
        return []
    return [(REMOVE, rng.choice(list(activeEffects)))]


def _hotCocoa(activeEffects, rng):
    # 热可可：随机清除身上的一个有害效果（JE 的 HotCocoaItem：有害的里随机挑一个）
    harmful = [name for name in activeEffects if name in negativeEffect]
    if not harmful:
        return []
    return [(REMOVE, rng.choice(harmful))]


def _soup(itemName):
    # 原版汤：蘑菇煲 / 甜菜汤给滋养 3 分钟，兔肉煲给滋养 5 分钟和跳跃提升 II 10 秒
    buffs = VANILLA_SOUP_BUFFS[itemName]
    return lambda activeEffects, rng: [(ADD,) + buff for buff in buffs]


# 物品名 -> 结算函数 (activeEffects, rng) -> [动作]
_RULES = {
    MILK_BOTTLE: _milk,
    HOT_COCOA: _hotCocoa,
}
for _name in VANILLA_SOUP_BUFFS:
    _RULES[_name] = _soup(_name)

# 有追加结算的食物（登记事件处理函数时当匹配表用）
HANDLED = frozenset(_RULES)


def eatActions(itemName, activeEffects, rng):
    """吃 / 喝 itemName 之后要做的事。

    activeEffects：玩家身上当前的效果名列表；rng：要有 choice(序列)（random 模块或 random.Random 都行）。
    没有追加结算的食物返回空列表。
    """
    rule = _RULES.get(itemName)
    if rule is None:
        return []
    return rule(activeEffects, rng)
