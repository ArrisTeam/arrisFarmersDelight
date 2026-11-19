# -*- coding: utf-8 -*-
"""Registry - JEI 联动的公共部分：取 arrisJei 的注册表、物品悬停文本（客户端）

未安装 arrisJei 时 GetJeiApiModule() 返回 None，各注册函数直接返回。
"""
from ...Client.Engine import clientApi, compFactory, levelId

def GetJeiApiModule():
    jeiApiModule = clientApi.ImportModule("arrisJeiScripts.api.jei")
    if not jeiApiModule:
        return None
    # 获取注册表单例实例
    registry = jeiApiModule.JeiRecipeRegistry.getInstance()
    return registry

def SetHoverText(recipeControl, renderPath, itemName, aux=0, userData=None, extra=None):
    """
    设置物品鼠标悬停文本；extra 是再加在最后的一行（说明这个位置的东西怎么用）
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
    if extra:
        hoverText += "\n§7" + extra

    hoverTextControl.SetPropertyBag({"#hover_text": hoverText})
