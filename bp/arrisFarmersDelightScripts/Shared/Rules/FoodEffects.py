# -*- coding: utf-8 -*-
"""FoodEffects - 吃喝之后要追加的结算（双端，纯规则）

JE 里牛奶瓶、热可可、西瓜汁、冰棒是 Item 子类的 affectConsumer（MilkBottleItem / HotCocoaItem / MelonJuiceItem /
PopsicleItem），原版汤是 CommonEvents 里的 LivingEntityUseItemEvent.Finish 事件；网易的 minecraft:food 表达不了这些，
由服务端在 PlayerEatFoodServerEvent 里结算。这里只决定"做什么"（返回动作元组），引擎调用在 Server/FoodEffects.py，
所以不碰引擎、离线可测。

动作：
    (REMOVE, 效果名)
    (ADD, 效果名, 秒, 等级, 是否显示粒子)
    (HEAL, 生命值)
    (EXTINGUISH,)
"""
from ..Data.Effects import negativeEffect, VANILLA_SOUP_BUFFS, MELON_JUICE_HEAL

REMOVE = "remove"
ADD = "add"
HEAL = "heal"
EXTINGUISH = "extinguish"

MILK_BOTTLE = "arris:milk_bottle"
HOT_COCOA = "arris:hot_cocoa"
MELON_JUICE = "arris:melon_juice"
MELON_POPSICLE = "arris:melon_popsicle"


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


def _melonJuice(activeEffects, rng):
    # 西瓜汁：回 2 点生命（以前靠瞬间治疗效果，等级对不上）
    return [(HEAL, MELON_JUICE_HEAL)]


def _popsicle(activeEffects, rng):
    # 西瓜冰棒：灭火（JE 的 PopsicleItem：clearFire）
    return [(EXTINGUISH,)]


def _soup(itemName):
    # 原版汤：蘑菇煲 / 甜菜汤给滋养 3 分钟，兔肉煲给滋养 5 分钟和跳跃提升 II 10 秒
    buffs = VANILLA_SOUP_BUFFS[itemName]
    return lambda activeEffects, rng: [(ADD,) + buff for buff in buffs]


# 物品名 -> 结算函数 (activeEffects, rng) -> [动作]
_RULES = {
    MILK_BOTTLE: _milk,
    HOT_COCOA: _hotCocoa,
    MELON_JUICE: _melonJuice,
    MELON_POPSICLE: _popsicle,
}
for _name in VANILLA_SOUP_BUFFS:
    _RULES[_name] = _soup(_name)

# 有追加结算的食物（登记事件处理函数时当匹配表用）
HANDLED = frozenset(_RULES)


def healedValue(current, top, amount):
    """回 amount 点之后的生命值；已经满了或已经倒下（<= 0）时返回 None，不用设置。"""
    if current <= 0 or current >= top:
        return None
    return min(top, current + amount)


def eatActions(itemName, activeEffects, rng):
    """吃 / 喝 itemName 之后要做的事。

    activeEffects：玩家身上当前的效果名列表；rng：要有 choice(序列)（random 模块或 random.Random 都行）。
    没有追加结算的食物返回空列表。
    """
    rule = _RULES.get(itemName)
    if rule is None:
        return []
    return rule(activeEffects, rng)


# 舒适（JE 1.3.4 的 ComfortEffect，已弃用：没有食物再给，只能用指令拿到）：每 80 刻（4 秒）一次，身上有生命恢复、
# （玩家）还有饱和度可花、或者满血时什么都不做，否则回 1 点血；不管等级。旧版这里是"免疫负面效果"，JE 早就不是了
COMFORT_SECONDS = 4.0
COMFORT_HEAL = 1.0


def comfortHeals(hasRegeneration, saturation, health, maxHealth):
    """舒适这一下回不回血。"""
    return not hasRegeneration and saturation <= 0.0 and health < maxHealth


# 滋养（JE 1.3.4 NourishmentEffect.applyEffectTick，每刻一次）：除了"开着自然回血、受了伤、还有饱和度"（这时回血照常花饱和度），
# 都把消耗度清零——疾跑、跳跃、挨打既不掉饱和度也不掉饥饿值。这边 0.25 秒清一次：消耗度攒到 4 才扣一次，0.25 秒里攒不到
NOURISHMENT_SECONDS = 0.25


def nourishmentClears(naturalRegen, health, maxHealth, saturation):
    """滋养这一下要不要把消耗度清零。"""
    return not (naturalRegen and health < maxHealth and saturation > 0.0)
