# -*- coding: utf-8 -*-

from common.component.baseComponent import BaseComponent

class TagComponentServer(BaseComponent):
    def GetEntityTags(self):
        # type: () -> list[str]
        """
        获取实体标签列表
        """
        pass

    def AddEntityTag(self, tag):
        # type: (str) -> bool
        """
        增加实体标签
        """
        pass

    def RemoveEntityTag(self, tag):
        # type: (str) -> bool
        """
        移除实体某个指定的标签
        """
        pass

    def EntityHasTag(self, tag):
        # type: (str) -> bool
        """
        判断实体是否存在某个指定的标签
        """
        pass

