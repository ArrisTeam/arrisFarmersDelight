# -*- coding: utf-8 -*-
"""PotItem - 厨锅物品带着锅里煮好的菜：怎么记在物品上、怎么读回来、悬停文字（双端，纯规则）

JE 的厨锅拆下来菜还在锅里：战利品表的 copy_meal 把"盛出格里那叠菜"写进物品的 BlockEntityTag，放回去照样在；
其余的东西（食材、容器、已经盛好的成品）掉出来。物品悬停文字是 CookingPotItem 的"装有 N 份：" + 菜名。
基岩版把那叠菜记在物品字典的 extraId 里（一个字符串，随物品存盘），悬停文字写进 customTips。
"""
POT = "arris:cooking_pot"
PREFIX = "arris_pot_meal"
SEPARATOR = "|"
MOST = 64
# JE 的 tooltip.farmersdelight.cooking_pot.single_serving / many_servings；冒号是英文的（游戏字体把全角冒号画得窄，tests/test_player_text_colons.py 守着）
TIP_ONE = "装有1份:"
TIP_MANY = "装有%d份:"
# netease 的 customTips 是整段悬停文字：前面这几个占位符是物品原来的名字、分类、附魔、攻击伤害
TIP_HEAD = "%name%%category%%enchanting%%attack_damage%"


def extraIdOf(meal):
    """锅里那叠菜 {"newItemName", "newAuxValue", "count"} -> 记在物品上的 extraId；没有菜返回空串。"""
    if not meal or not meal.get("newItemName") or int(meal.get("count") or 0) <= 0:
        return ""
    return SEPARATOR.join([PREFIX, meal["newItemName"], str(int(meal.get("newAuxValue") or 0)),
                           str(min(MOST, int(meal["count"])))])


def mealOf(extraId):
    """物品上的 extraId -> 那叠菜 {"newItemName", "newAuxValue", "count"}；不是厨锅记的、写坏了的返回 None。"""
    parts = extraId.split(SEPARATOR) if hasattr(extraId, "split") else []
    if len(parts) != 4 or parts[0] != PREFIX or not parts[1]:
        return None
    if not (parts[2].isdigit() and parts[3].isdigit()):
        return None
    count = int(parts[3])
    if not 1 <= count <= MOST:
        return None
    return {"newItemName": parts[1], "newAuxValue": int(parts[2]), "count": count}


def tipsOf(mealName, count):
    """带着菜的厨锅的悬停文字（JE：灰色的"装有 N 份："一行，下面是菜名）。"""
    line = TIP_ONE if count == 1 else TIP_MANY % count
    return "%s\n§7%s§r\n%s" % (TIP_HEAD, line, mealName)


def itemOf(meal, mealName):
    """拆下来的厨锅物品字典：带着菜就记进 extraId、写上悬停文字；没有菜就是一口普通的厨锅。"""
    item = {"newItemName": POT, "newAuxValue": 0, "count": 1}
    extraId = extraIdOf(meal)
    if extraId:
        item["extraId"] = extraId
        item["customTips"] = tipsOf(mealName or meal["newItemName"], min(MOST, int(meal["count"])))
    return item


class Pending(object):
    """刚放下去的厨锅带着的东西（它带的菜；放置时点的是不是方块的下面，Server/PotSupport）：放置前记一笔（那时才看得到手里的物品、点的面），
    方块实体建好时取走。按位置记、会过期。"""
    SECONDS = 5.0
    LIMIT = 64

    def __init__(self):
        self._meals = {}

    def put(self, key, value, now):
        if len(self._meals) >= self.LIMIT:
            for oldKey in [k for k, entry in self._meals.items() if entry[1] < now]:
                del self._meals[oldKey]
        self._meals[key] = (value, now + self.SECONDS)

    def take(self, key, now):
        entry = self._meals.pop(key, None)
        return entry[0] if entry is not None and entry[1] >= now else None
