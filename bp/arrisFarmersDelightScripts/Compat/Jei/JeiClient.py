# -*- coding: utf-8 -*-
"""JeiClient - JEI 联动入口：界面系统就绪后登记四类配方；沉浸式交互前置联动上、砧板站点开着时再登记"砧板摆盘"（客户端）

单独在 modMain 里登记，Client/ 不导入 Compat/；未安装 arrisJei 时什么都不做。
"砧板摆盘"是 Hands-On Delight 的内容（它的 JEI 插件）：没装前置包、前置包太旧、配置里关了砧板站点时不登记，JEI 照农夫乐事原样；
联动的判定可能比界面就绪晚，所以等判定出来再看（HandsOnMode.whenDecided）。
"""
from ...QuModLibs.Client import Listen
from ...Shared.Rules import HandsOnMode
from ...Shared.Rules import HandsOnOptions as Options
from .BoardAssembly import RegisterBoardAssemblyRecipes
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
    HandsOnMode.whenDecided("client", _whenDecided)


def _whenDecided(mode):
    if mode == HandsOnMode.LINKED and Options.cuttingBoard():
        RegisterBoardAssemblyRecipes(Options.removeCraftingRecipes())
