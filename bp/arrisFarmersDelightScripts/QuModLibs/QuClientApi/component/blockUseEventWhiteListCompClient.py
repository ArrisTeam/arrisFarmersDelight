# -*- coding: utf-8 -*-

from component.baseComponent import BaseComponent

class BlockUseEventWhitelistComponentClient(BaseComponent):
    def AddBlockItemlistenForUseEvent(self, blockName):
        # type: (str) -> bool
        """
        增加blockName方块对ClientBlockUseEvent事件的脚本层监听
        """
        pass

    def RemoveBlockItemlistenForUseEvent(self, blockName):
        # type: (str) -> bool
        """
        移除blockName方块对ClientBlockUseEvent事件的脚本层监听
        """
        pass

    def ClearAlllistenForBlockUseEventItems(self):
        # type: () -> bool
        """
        清空所有已添加方块对ClientBlockUseEvent事件的脚本层监听
        """
        pass


