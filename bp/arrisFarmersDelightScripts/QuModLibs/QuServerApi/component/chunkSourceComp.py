# -*- coding: utf-8 -*-

from common.component.baseComponent import BaseComponent


class ChunkSourceCompServer(BaseComponent):
    def SetAddArea(self, key, dimensionId, minPos, maxPos):
        # type: (str, int, tuple[int,int,int], tuple[int,int,int]) -> bool
        """
        设置区块的常加载
        """
        pass

    def DeleteArea(self, key):
        # type: (str) -> bool
        """
        删除一个常加载区域
        """
        pass

    def DeleteAllArea(self):
        # type: () -> int
        """
        删除所有常加载区域
        """
        pass

    def GetAllAreaKeys(self):
        # type: () -> list[str]
        """
        获取所有常加载区域名称列表
        """
        pass

    def CheckChunkState(self, dimension, pos):
        # type: (int, tuple[int,int,int]) -> bool
        """
        判断指定位置的chunk是否加载完成
        """
        pass

    def GetLoadedChunks(self, dimension):
        # type: (int) -> object
        """
        获取指定维度当前已经加载完毕的全部区块的坐标列表
        """
        pass

    def GetChunkEntites(self, dimension, pos):
        # type: (int, tuple[int,int,int]) -> object
        """
        获取指定位置的区块中，全部的实体和玩家的ID列表
        """
        pass

    def GetChunkMinPos(self, chunkPos):
        # type: (tuple[int,int]) -> object
        """
        获取某区块最小点的坐标
        """
        pass

    def GetChunkMaxPos(self, chunkPos):
        # type: (tuple[int,int]) -> object
        """
        获取某区块最大点的坐标
        """
        pass

    def GetChunkMobNum(self, dimension, chunkPos):
        # type: (int, tuple[int,int]) -> int
        """
        获取某区块中的生物数量（不包括玩家，但包括盔甲架）
        """
        pass

    def GetChunkPosFromBlockPos(self, blockPos):
        # type: (tuple[int,int,int]) -> object
        """
        通过方块坐标获得该方块所在区块坐标
        """
        pass

    def IsChunkGenerated(self, dimensionId, chunkPos):
        # type: (int, tuple[int,int]) -> bool
        """
        获取某个区块是否生成过。
        """
        pass

    def IsSlimeChunk(self, dimensionId, chunkPos):
        # type: (int, tuple[int,int]) -> bool
        """
        获取某个区块是否史莱姆区块。
        """
        pass

