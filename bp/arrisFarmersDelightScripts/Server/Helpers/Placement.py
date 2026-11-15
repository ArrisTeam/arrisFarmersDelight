# -*- coding: utf-8 -*-
"""Placement - 方块朝向（服务端：需要查游戏规则）"""
from .Engine import compFactory, levelId
from ...Shared.Rules.Placement import holidayAuxMap

_auxMap = []


def DetectionExperimentalHoliday():
    """方块 aux → 朝向 0-3 的映射表。

    实验性玩法只能在建档时设定，查一次后缓存；新版本里可能没有 experimental_holiday 这一项，按"未开启"处理。
    """
    if not _auxMap:
        gameRules = compFactory.CreateGame(levelId).GetGameRulesInfoServer() or {}
        optionInfo = gameRules.get("option_info") or {}
        _auxMap.append(holidayAuxMap(optionInfo.get("experimental_holiday") is True))
    return _auxMap[0]


def FacingOfAux(blockAuxValue):
    """方块 aux → 朝向 0-3（查不到时原样返回，与旧实现一致）。"""
    return DetectionExperimentalHoliday().get(blockAuxValue, blockAuxValue)
