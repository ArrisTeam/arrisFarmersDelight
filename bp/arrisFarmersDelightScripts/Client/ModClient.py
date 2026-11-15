# -*- coding: utf-8 -*-
"""ModClient - 客户端入口：导入各客户端模块（导入即登记），注册 query 变量、指南书界面与 JEI 配方（客户端）

客户端的引擎事件少且互不重叠，各模块直接用 @Listen，不需要事件注册表。
"""
from ..QuModLibs.Client import Listen
from .Engine import clientApi, compFactory, levelId
from ..Shared.Data.GuideBook import uiGuideBookPath, uiGuideBookScreen

from . import Endpoints  # noqa: F401
from . import BlockEntityRestore  # noqa: F401
from . import Input  # noqa: F401
from .Ui import CookingPotScreen  # noqa: F401

# 展示实体的渲染控制器读这两个 query 变量
_QUERY_VARIABLES = ("query.mod.item_display_mode", "query.mod.item_display_animation")


@Listen("LoadClientAddonScriptsAfter")
def OnLoadClientAddonScriptsAfter(args):
    queryComp = compFactory.CreateQueryVariable(levelId)
    for name in _QUERY_VARIABLES:
        queryComp.Register(name, 0.0)


@Listen("UiInitFinished")
def OnUiInitFinished(args):
    clientApi.RegisterUI("arris", "farmerDelightGuideBook", uiGuideBookPath, uiGuideBookScreen)
    # JEI 联动：未安装 arrisJei 时各注册函数直接返回
    from ..compat.jei.cutting_board import RegisterCuttingBoardRecipes
    from ..compat.jei.cooking_pot import RegisterCookingPotRecipes
    from ..compat.jei.skillet import RegisterSkilletRecipes
    from ..compat.jei.stove import RegisterStoveRecipes
    RegisterCuttingBoardRecipes()
    RegisterCookingPotRecipes()
    RegisterSkilletRecipes()
    RegisterStoveRecipes()
