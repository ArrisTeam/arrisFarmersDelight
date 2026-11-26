# -*- coding: utf-8 -*-
"""AdvTriggers - JE 农夫乐事的 21 条进度怎么推进：发生了什么 -> 哪条进度的哪个子条件，交给成就系统的接口（服务端，不碰引擎）

节点和条件在 Shared/Data/Advancements。要求 any 的进度做到一个子条件就 setFinish（已经做到的不再调）；
要求 all 的每个子条件 addProgressUnique 一次（子键是 JE 的子条件名，同一个子键只算一次，成就系统替我们记着、随存档）。
接口是成就系统的 dolorAdvancementsScripts.Api.Server 模块（AdvBridge 从它的 ready 事件拿来交给这里）；没有接口时什么都不做。
"""
from ...Shared.Data import Advancements as Data


def buildIndex(criteria):
    """{种类: {键: [(进度 ID, 子条件名, 要求)]}}；没有键的种类（ready / cut / skillet）键是 None。"""
    index = {}
    for name in sorted(criteria):
        requirement, subs = criteria[name]
        for sub, kind, keys in subs:
            for key in keys or (None,):
                index.setdefault(kind, {}).setdefault(key, []).append((Data.NAMESPACE + name, sub, requirement))
    return index


INDEX = buildIndex(Data.CRITERIA)


def keysOf(kind):
    """这一种条件认的全部键（挂处理函数时当匹配用：不相干的事件到不了处理函数）。"""
    return frozenset(key for key in INDEX.get(kind, {}) if key is not None)


def fire(api, playerId, kind, key=None):
    """playerId 做成了 kind / key：推进对应的进度，返回这一下真推进了几条（新完成的、新记上的子条件）。"""
    entries = INDEX.get(kind, {}).get(key) if api is not None and playerId else None
    moved = 0
    for nodeId, sub, requirement in entries or ():
        if requirement == "all":
            moved += 1 if api.addProgressUnique(playerId, nodeId, sub) else 0
        elif not api.isDone(playerId, nodeId):
            moved += 1 if api.setFinish(playerId, nodeId) else 0
    return moved
