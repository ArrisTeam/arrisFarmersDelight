# -*- coding: utf-8 -*-

from common.component.baseComponent import BaseComponent

class RecipeCompServer(BaseComponent):
    def GetRecipeResult(self, recipeId):
        # type: (str) -> list[dict]
        """
        根据配方id获取配方结果。仅支持合成配方
        """
        pass

    def GetRecipesByResult(self, resultIdentifier, tag, aux=0, maxResultNum=-1):
        # type: (str, str, int, int) -> list[dict]
        """
        通过输出物品查询配方所需要的输入材料
        """
        pass

    def AddBrewingRecipes(self, brewType, inputName, reagentName, outputName):
        # type: (str, str, str, str) -> bool
        """
        添加酿造台配方的接口
        """
        pass

    def GetRecipesByInput(self, inputIdentifier, tag, aux=0, maxResultNum=-1):
        # type: (str, str, int, int) -> list[dict]
        """
        通过输入物品查询配方
        """
        pass

