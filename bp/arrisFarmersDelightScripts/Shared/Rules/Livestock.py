# -*- coding: utf-8 -*-
"""Livestock - 狗粮 / 马饲料喂给哪种生物有什么效果（双端，纯规则）"""
from ..Data import Mobs as Data

# AttrType.HEALTH（ModAPI 的属性枚举值）
HEALTH = 0
# 引擎查不到主人时给的"没有主人"：None、空串、"-1"
_NO_OWNER = (None, "", "-1")


def feedFor(itemName, entityType):
    """手里的 itemName 喂给 entityType 这种生物是否有 JE 的喂食效果：
    有就返回 {"effects": [(效果名, 秒, 等级 - 1)], "sound": 声音名, "returns": 还给玩家的容器或 None}，没有返回 None。
    生物是不是驯服的由调用方另查。"""
    if entityType not in Data.FEED_USERS.get(itemName, ()):
        return None
    return {"effects": list(Data.FEED_EFFECTS[itemName]), "sound": Data.FEED_SOUNDS[itemName],
            "returns": Data.FEED_RETURNS.get(itemName)}


def isTamed(tamedFlag, ownerId):
    """引擎的"是否驯服"查不出结果（None）时，退回看有没有主人；查出来了就以它为准。"""
    if tamedFlag is None:
        return ownerId not in _NO_OWNER
    return bool(tamedFlag)
