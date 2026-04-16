# -*- coding: utf-8 -*-

class BlockPaletteComponent():
    def SerializeBlockPalette(self):
        # type: () -> dict
        """
        序列化方块调色板中的数据，用于方块调色板在客户端及服务端的事件数据之间传输。
        """
        pass

    def DeserializeBlockPalette(self, datadict):
        # type: (dict) -> bool
        """
        反序列化方块调色板数据字典中的数据，用于方块调色板在客户端及服务端的事件数据之间传输。
        """
        pass

    def GetBlockCountInBlockPalette(self, blockName, auxValue=-1):
        # type: (str, int) -> int
        """
        获取方块调色板BlockPalette中某个类型的方块的数量。
        """
        pass

    def DeleteBlockInBlockPalette(self, blockName, auxValue=-1):
        # type: (str, int) -> int
        """
        删除方块调色板BlockPalette中某个类型的方块。
        """
        pass

    def ReplaceBlockInBlockPalette(self, blockName, auxValue, blockName2, auxValue2=-1):
        # type: (str, int, str, int) -> int
        """
        替换方块调色板BlockPalette中某个类型的方块。
        """
        pass

    def ReplaceAirByStructureVoid(self, enable):
        # type: (bool) -> bool
        """
        设置是否将方块调色板BlockPalette中所有空气替换为结构空位。
        """
        pass

    def GetVolumeOfBlockPalette(self):
        # type: () -> tuple[int,int,int]
        """
        获取方块调色板BlockPalette所占据的长方体的长宽高。长指的是在方块调色板BlockPalette在世界坐标中占据的x轴方向的长度，宽指的是z轴方向的长度，高指的是y轴方向的长度。
        """
        pass

    def GetLocalPoslistOfBlocks(self, blockName, auxValue=-1):
        # type: (str, int) -> list[tuple[int,int,int]]
        """
        获取方块调色板中某种方块的相对位置列表。方块调色板记录了多个方块组成的一个三维空间下的方块组合，而相对位置则指的是，以这些方块中最小坐标的方块所在位置作为原点的坐标轴下的相对位置。
        """
        pass


