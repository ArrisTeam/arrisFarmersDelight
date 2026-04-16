# -*- coding: utf-8 -*-

from common.component.baseComponent import BaseComponent

class BlockStateComponentServer(BaseComponent):
    def GetBlockStates(self, pos, dimensionId=-1):
        # type: (tuple[float,float,float], int) -> dict
        """
        获取方块状态
        """
        pass

    def SetBlockStates(self, pos, data, dimensionId=-1):
        # type: (tuple[float,float,float], dict, int) -> bool
        """
        设置方块状态
        """
        pass

    def GetBlockAuxValueFromStates(self, blockName, states):
        # type: (str, dict) -> int
        """
        根据方块名称和方块状态获取方块附加值AuxValue
        """
        pass

    def GetBlockStatesFromAuxValue(self, blockName, auxValue):
        # type: (str, int) -> dict
        """
        根据方块名称和方块附加值AuxValue获取方块状态
        """
        pass

