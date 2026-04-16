# -*- coding: utf-8 -*-

from component.blockPaletteComp import BlockPaletteComponent
from component.baseComponent import BaseComponent

class BlockGeometryCompClient(BaseComponent):
    def CombineBlockPaletteToGeometry(self, blockPalette, geometryName, unsupportedMode=0):
        # type: (BlockPaletteComponent, str, int) -> str
        """
        将BlockPalette中的所有方块合并并转换为能用于实体的几何体模型。
        """
        pass

    def CombineBlockBetweenPosToGeometry(self, startPos, endPos, geometryName, unsupportedMode=0, useStructureVoid=False):
        # type: (tuple[int,int,int], tuple[int,int,int], str, int, bool) -> BlockPaletteComponent
        """
        根据输入的两个位置，搜索这两个位置之间的所有方块，并将这些方块合并和转换为能用于实体的几何体模型。
        """
        pass

    def CombineBlockFromPoslistToGeometry(self, poslist, geometryName, unsupportedMode=0, useStructureVoid=False):
        # type: (list[tuple[int,int,int]], str, int, bool) -> BlockPaletteComponent
        """
        根据输入的方块位置列表，搜索这些位置的所有方块，并将这些方块合并和转换为能用于实体的几何体模型。
        """
        pass


