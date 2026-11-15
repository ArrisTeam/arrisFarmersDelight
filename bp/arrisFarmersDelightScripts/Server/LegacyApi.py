# -*- coding: utf-8 -*-
"""LegacyApi - 把联动契约 v1 的三个函数挂到 ModAttr("arris")（服务端）

下游在 LoadServerAddonScriptsAfter 里 GetAttr 取用；函数本身与白名单见 Api/LegacyModAttr.py。
键名一个字母都不能动（linkage.md 写的就是这三个）。
"""
from .Helpers.Engine import compFactory
from ..Api.LegacyModAttr import ArrisFarmersDelightInterface, ArrisFarmersDelightObtain, AddCookingPotRecipe

MODATTR_OWNER = "arris"

_modAttr = compFactory.CreateModAttr(MODATTR_OWNER)
_modAttr.SetAttr("ArrisFarmersDelightInterface", ArrisFarmersDelightInterface)
_modAttr.SetAttr("ArrisFarmersDelightObtain", ArrisFarmersDelightObtain)
_modAttr.SetAttr("ArrisAddCookingPotRecipe", AddCookingPotRecipe)
