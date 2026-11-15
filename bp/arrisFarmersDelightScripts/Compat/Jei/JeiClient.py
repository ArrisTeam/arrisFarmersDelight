# -*- coding: utf-8 -*-
"""JeiClient - JEI 联动入口：界面系统就绪后登记四类配方（客户端）

单独在 modMain 里登记，Client/ 不导入 Compat/；未安装 arrisJei 时什么都不做。
"""
from ...QuModLibs.Client import Listen
from .CookingPot import RegisterCookingPotRecipes
from .CuttingBoard import RegisterCuttingBoardRecipes
from .Skillet import RegisterSkilletRecipes
from .Stove import RegisterStoveRecipes


@Listen("UiInitFinished")
def OnUiInitFinished(args):
    RegisterCuttingBoardRecipes()
    RegisterCookingPotRecipes()
    RegisterSkilletRecipes()
    RegisterStoveRecipes()
