# -*- coding: utf-8 -*-
"""GrillBlocks - 炉灶的两种方块（点着的 / 熄着的）、哪些方块能摆烤位、熄着时 FD 的件怎么冷却、什么东西点得着 / 灭得了（双端，纯规则）

JE 的炉灶只有一个方块，点没点着是方块状态 LIT（AbstractStoveBlock.java:53）：放食物、开站点、画烤架都不看 LIT（use 对 LIT 只分点火 / 灭火，:66-77），
只有"烤不烤"看（AbstractStoveBlockEntity.serverTick:104-108：点着 cookAndOutputItems，熄着 coolItems）。基岩版的方块状态改不了名字，
点着的是 arris:stove，熄着的是另一个方块 arris:stove_extinguish（bp/netease_blocks/arris_stove_extinguish.json），点火 / 灭火就是换方块（Server/StoveSwap.py）。
对外的两张名单不动（下游按引用读，linkage.md）：StoveList = 会烤东西的（点着的）炉灶，CanProvideHeatBlockList = 给上面的锅和煎锅热的方块，
熄着的方块不在里面：熄着的灶上不烤、不烫脚、不给锅热。"能摆东西 / 开站点 / 要画"是另一个说法：灶方块 = 点着的 + 熄着的（GRILL_BLOCKS，活的）。
下游往 StoveList 追加的炉灶没有熄着的孪生方块：照旧只有点着的，点不灭也灭不了（UNLIT_OF 里没有它，twinOf 回 None）。
"""
from ..Data.Cooking import StoveList

UNLIT_OF = {"arris:stove": "arris:stove_extinguish"}      # 点着的炉灶 -> 熄着的孪生方块（我们自己的，不是对外契约）
LIT_OF = dict((unlit, lit) for lit, unlit in UNLIT_OF.items())

COOL_PER_SECOND = 2.0      # 熄着时 FD 的件每刻进度 -2（AbstractStoveBlockEntity.java:147），烤的时候每刻 +1（:120）：凉得比烤得快一倍；都按真实时间

FLINT_AND_STEEL, FIRE_CHARGE = "minecraft:flint_and_steel", "minecraft:fire_charge"
WATER_BUCKETS = ("minecraft:water_bucket",)       # FD 的 #forge:buckets/water（CommonTags.Items.BUCKETS_WATER），原版里只有水桶
IGNITE, EXTINGUISH = "ignite", "extinguish"
WEAR, SPEND, EMPTY = "wear", "spend", "empty"      # 用掉什么：磨损 1 点耐久（hurtAndBreak）/ 少一个（shrink）/ 换成剩余物（getCraftingRemainingItem，空桶）
SOUND_IGNITE, SOUND_CHARGE, SOUND_FIZZ = "fire.ignite", "mob.ghast.fireball", "random.fizz"     # FLINTANDSTEEL_USE / FIRECHARGE_USE / 灭火声
SOUND_FOOD = ("block.lantern.place", 0.5, 1.0)       # 放食物上去（AbstractStoveBlock.java:140 的 LANTERN_PLACE 0.5 / 1.0）：(声音名, 音量, 音调)


def isLit(blockName):
    """点着的炉灶：StoveList 里的（下游追加的也算）。"""
    return blockName in StoveList


def isUnlit(blockName):
    return blockName in LIT_OF


def isGrill(blockName):
    """能摆烤位、开站点、要画烤架的方块：点着的和熄着的。"""
    return isLit(blockName) or isUnlit(blockName)


def twinOf(blockName):
    """点火 / 灭火要换成的方块：点着的 -> 熄着的，熄着的 -> 点着的；没有孪生方块的炉灶（下游追加的）是 None。"""
    return UNLIT_OF.get(blockName) or LIT_OF.get(blockName)


class GrillBlocks(object):
    """"in" 判断的活容器：点着的炉灶（StoveList，下游追加的也在）加上熄着的孪生方块。前置包登记站点只用 in
    （Server/Station.binds、Client/Registry.behaviorOf），所以给它这个对象：附属包追加的炉灶照旧开站，熄着的那个方块也开站（HoD 的 StoveStation.opens 不看 LIT）。
    只读：顺序是 StoveList 在前、熄着的在后，能取长度、按下标取、遍历（GrillStation.STOVE_BLOCKS 原来就是 StoveList 这个列表，别处的写法不用改）。"""

    def __contains__(self, blockName):
        return isGrill(blockName)

    def __iter__(self):
        return iter(list(StoveList) + sorted(LIT_OF))

    def __len__(self):
        return len(StoveList) + len(LIT_OF)

    def __getitem__(self, index):
        """原来 STOVE_BLOCKS 就是 StoveList 这个列表：按下标取（第 0 个还是 arris:stove）、切片的写法照旧能用。"""
        return (list(StoveList) + sorted(LIT_OF))[index]

    def __repr__(self):
        return "GrillBlocks(%r)" % (list(self),)


GRILL_BLOCKS = GrillBlocks()


def cooledTimer(timer, seconds, total):
    """熄着的炉灶上 FD 原样烤的那一件：倒数的计时过了 seconds 秒之后是多少（AbstractStoveBlockEntity.coolItems，java:139-150）。
    计时是"还剩几秒烤好"，烤满 total 秒（Server/Stove.COOK_TIMER）；烤了多少 = total - timer，每秒凉 COOL_PER_SECOND 秒，不会凉过 0
    （clamp(进度 - 2, 0, 总时长)）；一点没烤的（进度 <= 0）不动（:145 的 continue）。"""
    if timer is None:
        return total
    if timer >= total:
        return timer
    return min(total, timer + COOL_PER_SECOND * seconds)


def useOf(lit, itemName, itemType):
    """手里的东西对这座炉灶有没有点火 / 灭火的用法（AbstractStoveBlock.use：点着的先看 tryToExtinguish，熄着的先看 tryToIgnite）。
    返回 (动作, 用掉什么, 声音) 或 None。灭火：铲子（ToolActions.SHOVEL_DIG，引擎的物品类型 shovel）磨损 1 点，水桶换成空桶；
    点火：打火石磨损 1 点，火焰弹少一个。创造模式的不磨不少不换由调用方管（JE 的 instabuild / hurtAndBreak）。"""
    if lit:
        if itemType == "shovel":
            return (EXTINGUISH, WEAR, SOUND_FIZZ)
        if itemName in WATER_BUCKETS:
            return (EXTINGUISH, EMPTY, SOUND_FIZZ)
    else:
        if itemName == FLINT_AND_STEEL:
            return (IGNITE, WEAR, SOUND_IGNITE)
        if itemName == FIRE_CHARGE:
            return (IGNITE, SPEND, SOUND_CHARGE)
    return None


def isTool(itemName, itemType):
    """炉灶自己用的工具（点火的、灭火的）：不管炉灶这会儿点着没点着都不算"不能烹饪的东西"（JE 里点着的炉灶拿打火石什么也不提示）。"""
    return itemName in (FLINT_AND_STEEL, FIRE_CHARGE) or itemName in WATER_BUCKETS or itemType == "shovel"
