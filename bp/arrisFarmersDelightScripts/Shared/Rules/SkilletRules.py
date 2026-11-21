# -*- coding: utf-8 -*-
"""SkilletRules - 煎锅照 JE 的数值与判断：烹饪时间换算、手持热源范围、按住状态、攻击冷却、耐久磨损、存取煎锅物品（双端，纯规则）

对应 FD 1.3.4：SkilletBlock.getSkilletCookingTime、SkilletItem（isPlayerNearHeatSource / use / getUseDuration / onUseTick /
SkilletEvents.playSkilletAttackSound / hurtEnemy）、SkilletBlockEntity.skilletStack（放下去的那件煎锅连耐久、附魔一起存在方块里）。
"""
import math
import struct

from .MobLoot import enchantLevel

SKILLET_ITEM = "arris:skillet_item"
SKILLET_BLOCK = "arris:skillet"
# EnchantType.WeaponFire：火焰附加
FIRE_ASPECT = 13

TICKS_PER_SECOND = 20
# SkilletBlock.MINIMUM_COOKING_TIME：煎一件最短 3 秒
MINIMUM_COOKING_TICKS = 60
# 营火配方的烹饪时间：JE 里 FD 与原版的营火配方都是 600 刻（30 秒）；没写时间（<= 0）也按它算
CAMPFIRE_TICKS = 600
# 提示的那几句（拿着煎锅、放下的煎锅）和别的服务端提示一起在 Shared/Data/Tips：带着语言文件的键，客户端按玩家的语言给

# 放下的煎锅上放食物的声音，(声音名, 音量, 音调)：每次放进去一声挂灯（SkilletBlock.java:83 LANTERN_PLACE 0.7 / 1.0），锅是空的又在热源上再加一声下料
# （SkilletBlockEntity.java:189 BLOCK_SKILLET_ADD_FOOD 0.8 / 1.0）；取回没有声音（SkilletBlock.java:71-77）
SOUND_PLACE = ("block.lantern.place", 0.7, 1.0)
SOUND_ADD_FOOD = ("ambient.skillet.addfood", 0.8, 1.0)


def _f32(value):
    """Java float 的舍入：getSkilletCookingTime 用 float 运算，取整的结果要和它一位一位对上。"""
    return struct.unpack("f", struct.pack("f", value))[0]


def cookingTicks(originalTicks, fireAspect=0):
    """SkilletBlock.getSkilletCookingTime：营火配方时间先取整秒、乘 0.2，火焰附加每级再少 0.05，最短 60 刻。

    默认 600 刻：不带附魔 120 刻（6 秒），火焰附加 I 80 刻（4 秒），II 起 60 刻（3 秒）。
    最后的夹取照 Mth.clamp(整数)：比下限小就取下限，否则取与配方原时间中小的（所以配方时间 0 会得到 0）。
    """
    cookingTime = originalTicks if originalTicks > 0 else CAMPFIRE_TICKS
    seconds = cookingTime // TICKS_PER_SECOND
    reduction = _f32(0.2)
    if fireAspect > 0:
        reduction = _f32(reduction - fireAspect * 0.05)
    result = int(_f32(seconds * reduction)) * TICKS_PER_SECOND
    if result < MINIMUM_COOKING_TICKS:
        return MINIMUM_COOKING_TICKS
    return min(result, originalTicks)


def cookingSeconds(originalTicks, fireAspect=0):
    return cookingTicks(originalTicks, fireAspect) / float(TICKS_PER_SECOND)


def fireAspectLevel(itemDict):
    """煎锅物品字典上火焰附加的等级，没有返回 0。"""
    return enchantLevel(itemDict, FIRE_ASPECT)


# ---- 手持烹饪的热源（计时与按住状态在 SkilletHandRules.py） ----

# 脚的位置取整时给 y 一点余量：站在方块顶上时脚的 y 可能是 63.9999 一类
_FOOT_EPSILON = 0.001


def heatNeighbourhood(footPos):
    """JE：玩家脚下方块坐标往四周各 1 格的 3x3x3。"""
    x, z = int(math.floor(footPos[0])), int(math.floor(footPos[2]))
    y = int(math.floor(footPos[1] + _FOOT_EPSILON))
    return [(x + dx, y + dy, z + dz) for dx in (-1, 0, 1) for dy in (-1, 0, 1) for dz in (-1, 0, 1)]


def nearHeat(footPos, blockNameAt, heatNames, onFire=False):
    """JE isPlayerNearHeatSource：着火，或四周 3x3x3 里有热源方块。只看方块（JE 看方块标签，不看营火 / 炉灶点没点着）。"""
    if onFire:
        return True
    for pos in heatNeighbourhood(footPos):
        if blockNameAt(pos) in heatNames:
            return True
    return False


# ---- 打人 ----

# 玩家基础攻击速度 4.0 + 煎锅的修饰 -3.1（SkilletItem 构造里）
ATTACK_SPEED = 4.0 - 3.1
# JE playSkilletAttackSound：攻击力度大于 0.8 才是"重击"的声音
STRONG_SCALE = 0.8
SOUND_STRONG = "ambient.skillet.attack_strong"
SOUND_WEAK = "ambient.skillet.attack_weak"


class AttackClock(object):
    """JE 的攻击冷却只用来挑音效：上次挥煎锅到现在够 STRONG_SCALE × 一次攻击的间隔才响"重击"，否则响"轻击"。

    基岩版没有攻击冷却（伤害不会因为连点变小），所以只挑声音，不缩伤害；没有记录的第一次算重击。
    """

    def __init__(self):
        self._last = {}

    def sound(self, playerId, now):
        last = self._last.get(playerId)
        self._last[playerId] = now
        strong = last is None or (now - last) * TICKS_PER_SECOND >= STRONG_SCALE * TICKS_PER_SECOND / ATTACK_SPEED
        return SOUND_STRONG if strong else SOUND_WEAK


# ---- 耐久 ----

def wearAfter(durabilityBefore, durability):
    """JE 里煎锅打一下 / 挖一块都只磨损 1 点；基岩版自定义武器打一下磨损 2 点，多出来的不算。修复（变大）不动。"""
    if durabilityBefore - durability > 1:
        return durabilityBefore - 1
    return durability


# ---- 放成方块时记下的那件煎锅 ----

# 存进方块实体数据的字段：名字、附加值、耐久、附魔、自定义提示、额外 ID、用户数据（改过名、修理次数都在里面）
_STORED_KEYS = ("newItemName", "newAuxValue", "durability", "enchantData", "modEnchantData", "customTips", "extraId", "userData")
_TEXT = type(u"")


def _plain(value):
    """方块实体数据只收 str 键、同类元素的列表、非 unicode 的字符串：元组换成列表，py2 的 unicode 换成 str。"""
    if isinstance(value, dict):
        return dict((_plain(key), _plain(item)) for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    if isinstance(value, _TEXT) and _TEXT is not str:
        return value.encode("utf-8")
    return value


def _blank(value):
    """引擎物品字典里没设置的字段是 None / "" / []；customTips 写成 "" 会盖掉物品自己的 netease:customtips，所以空的一律不存不还。耐久 0 不算空。"""
    return value is None or (value == "" and not isinstance(value, bool)) or (isinstance(value, list) and not value)


def storeItem(itemDict):
    """要记进方块实体数据的那一件煎锅（数量一律 1）。"""
    stored = dict((key, _plain(itemDict[key])) for key in _STORED_KEYS if not _blank(itemDict.get(key)))
    stored["newItemName"] = SKILLET_ITEM
    stored["count"] = 1
    return stored


def restoreItem(stored):
    """拆煎锅时掉出来的那一件：存着的原样（附魔换回 (类型, 等级) 元组）；没存过（/setblock、旧存档）就是一把新煎锅。"""
    item = {"newItemName": SKILLET_ITEM, "newAuxValue": 0, "count": 1}
    if not stored:
        return item
    for key in _STORED_KEYS:
        if not _blank(stored.get(key)):
            item[key] = _plain(stored[key])      # 从方块实体数据读出来的可能是引擎对象，换成普通的字典 / 列表再交给引擎
    for key in ("enchantData", "modEnchantData"):
        if item.get(key):
            item[key] = [tuple(entry) if isinstance(entry, list) else entry for entry in item[key]]
    item["newItemName"], item["count"] = SKILLET_ITEM, 1
    return item


class BreakMarks(object):
    """玩家（创造模式）开始破坏方块时记一笔、方块真没了才取走：JE 创造模式拆煎锅不掉煎锅（战利品表只在非创造时结算）。

    引擎先发"玩家即将破坏方块"，破坏完成才发"方块被移除"（那时不知道是谁拆的）；记录按位置、会过期，防止取消的破坏留下旧记录。
    """
    SECONDS = 5.0
    LIMIT = 64

    def __init__(self):
        self._marks = {}

    def put(self, key, now):
        if len(self._marks) >= self.LIMIT:
            for oldKey in [k for k, expires in self._marks.items() if expires < now]:
                del self._marks[oldKey]
        self._marks[key] = now + self.SECONDS

    def take(self, key, now):
        expires = self._marks.pop(key, None)
        return expires is not None and expires >= now
