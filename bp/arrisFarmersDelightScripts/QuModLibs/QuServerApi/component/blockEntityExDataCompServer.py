# -*- coding: utf-8 -*-


from common.component.baseComponent import BaseComponent
from server.blockEntityData import BlockEntityData

class BlockEntityExDataCompServer(BaseComponent):
    def GetBlockEntityData(self, dimension, pos):
        # type: (int, tuple[int,int,int]) -> object
        """
        用于获取可操作某个自定义方块实体数据的对象，操作方式与dict类似
        """
        pass

