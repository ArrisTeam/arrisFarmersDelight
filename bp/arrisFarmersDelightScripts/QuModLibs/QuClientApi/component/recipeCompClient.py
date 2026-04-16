# -*- coding: utf-8 -*-

from component.baseComponent import BaseComponent

class RecipeCompClient(BaseComponent):
    def GetRecipesByResult(self, resultIdentifier, tag, aux=0, maxResultNum=-1):
        # type: (str, str, int, int) -> list[dict]
        """
        通过输出物品查询配方所需要的输入材料
        """
        pass

    def GetRecipesByInput(self, inputIdentifier, tag, aux=0, maxResultNum=-1):
        # type: (str, str, int, int) -> list[dict]
        """
        通过输入物品查询配方
        """
        pass


