# -*- coding: utf-8 -*-
from common.component.baseComponent import BaseComponent


class PortalComponentServer(BaseComponent):
    def DetectStructure(self, playerId, pattern, defines, touchPos, pos, dimensionId=-1):
        # type: (None, list[str], dict, list[tuple[int,int]], tuple[int,int,int], int) -> tuple[bool,tuple[int,int,int],tuple[int,int,int]]
        """
        检测自定义门的结构
        """
        pass

