# -*- coding: utf-8 -*-
"""HeatAux - 写了状态条件的热源方块：照引擎算出"满足条件的 aux"，给读不到方块状态的客户端（服务端）

客户端读不到方块状态（官方文档：GetBlockStates / GetBlockStatesFromAuxValue 只有服务端有），手持煎锅"身边有没有热源"只能按 GetBlock 给的 aux 判
（Shared/Rules/HeatSources.heatsByAux）。这里对状态条件表（Shared/Data/Cooking.HeatSourceStateDict）里每个方块问引擎
CreateBlockState(levelId).GetBlockStatesFromAuxValue(方块名, aux)，满足条件的 aux 写进 HeatSourceAuxDict（就地改；怎么枚举、什么时候停：
Shared/Rules/HeatStates.auxSet），表同步把两张表一起发给客户端（Shared/Rules/SyncTables）。
什么时候算：表同步每次算差异之前（Server/TableSync._refresh：玩家进服、之后每 5 秒一次、ext.recipes.syncToClients），只算条件变了的方块
（新写进来的、换了条件的；一个方块的同一份条件只算一次），所以服务端新写的条件最晚约 5 秒后连同 aux 集合一起到客户端。
引擎一个状态也问不出来（接口没有、方块不认识、调用抛异常）：表里原来的不动（熔岩炼药锅有静态的初值），打一行日志，条件不变就不再问。
GetBlockStatesFromAuxValue 对空号、越界的 aux（3.10 实机，2026-11-26，炼药锅）：空号 7、15 和越界的 23 以上给的都是缺省状态
{"cauldron_liquid": "water", "fill_level": 0}，不是 None、不抛异常——HeatStates.auxSet 把和前面重复的状态当"这个 aux 没有方块"，算出来正是
熔岩 1–6 级 = aux 9–14（问 46 次），写表成功；进服时问这 46 次，错误日志是空的。None、{}、抛异常也照样当没有方块（别的方块、别的版本）。
游戏内自检 Server/Debug/McdkHeatTest 把原始返回值列出来。
"""
import copy

from .Helpers.Engine import compFactory, levelId
from ..Shared.Data.Cooking import HeatSourceAuxDict, HeatSourceStateDict
from ..Shared.Rules import HeatStates

_done = {}          # 方块名 -> 上次算 aux 集合时的条件（深拷贝）：一样就不再算
_last = {}          # 方块名 -> 上次算出了什么（HeatStates.auxSet 的返回，加上条件、写没写进表），自检读 report()


def reader(blockName):
    """read(aux) -> 引擎给这个方块、这个 aux 的方块状态；组件或接口没有、调用抛异常都给 None（当这个 aux 没有方块）。"""
    def read(aux):
        try:
            return compFactory.CreateBlockState(levelId).GetBlockStatesFromAuxValue(blockName, aux)
        except Exception:  # noqa: BLE001 - 3.10 越界不抛（给缺省状态）；别的版本 / 别的方块抛了也只当这个 aux 没有方块
            return None
    return read


def refresh():
    """条件变了（或还没算过）的方块重算满足条件的 aux，写进 HeatSourceAuxDict；返回这次表里变了的方块名。"""
    changed = []
    for name, conditions in list(HeatSourceStateDict.items()):
        if _done.get(name) == conditions:
            continue
        _done[name] = copy.deepcopy(conditions)
        found = HeatStates.auxSet(reader(name), conditions)
        readable = found["top"] >= 0
        _last[name] = dict(found, conditions=_done[name], written=False)
        if not readable:
            print("[arrisFarmersDelight] 热源：引擎问不出 %s 的方块状态（GetBlockStatesFromAuxValue），客户端照原来的 aux 判" % (name,))
            continue
        if HeatSourceAuxDict.get(name) != found["aux"]:
            HeatSourceAuxDict[name] = list(found["aux"])
            changed.append(name)
        _last[name]["written"] = True
    return changed


def report():
    """最近一次每个方块算出了什么（游戏内自检读）：{方块名: {"aux", "top", "asked", "conditions", "written"}}；
    written：表里现在是不是这一份（引擎问不出状态时是 False，表照旧）。"""
    return copy.deepcopy(_last)
