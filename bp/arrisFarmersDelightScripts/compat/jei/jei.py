# -*- coding: utf-8 -*-
from ...QuModLibs.Client import *
from ...modCommon.modConfig import *

def GetJeiApiModule():
    jeiApiModule = clientApi.ImportModule("arrisJeiScripts.api.jei")
    if not jeiApiModule:
        return None
    # 获取注册表单例实例
    registry = jeiApiModule.JeiRecipeRegistry.getInstance()
    return registry

def SetHoverText(recipeControl, renderPath, itemName, aux=0, userData=None):
    """
    设置物品鼠标悬停文本
    """
    hoverTextControl = recipeControl.GetChildByPath(renderPath + "/button_ref/hover/hover_text")
    if not hoverTextControl:
        return

    # 获取物品的格式化悬停文本
    itemComp = compFactory.CreateItem(levelId)
    if userData:
        hoverText = itemComp.GetItemFormattedHoverText(itemName, aux, False, userData)
    else:
        hoverText = itemComp.GetItemFormattedHoverText(itemName, aux, False)

    # 添加命名空间标识
    namespace = itemName.split(":")[0].capitalize()
    hoverText += "\n§9" + namespace

    hoverTextControl.SetPropertyBag({"#hover_text": hoverText})
