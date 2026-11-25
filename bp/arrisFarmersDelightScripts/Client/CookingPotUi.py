# -*- coding: utf-8 -*-
"""CookingPotUi - 厨锅的 dolorContainer 界面在客户端要做的几件事：登记界面模型、导入方块宿主的客户端一半与食谱格的控件（客户端）

界面本身由库的客户端服务（dolorContainer.Client.Service，modMain 里登记）按布局推出：布局源文件是
layouts/cooking_pot.json，编译进 dolorLayouts.py 与 rp/ui/dolor_layout_*.json。
- 界面模型要在两端都登记：客户端按同样的名字与参数建同一份，预测与服务端执行跑同一套规则；
- 方块宿主的客户端一半：自定义方块在客户端不算能交互的方块，对着厨锅右键时手里的东西会被引擎对空气使用
  （扔雪球、打开手里的书），它在同一下的"使用物品"里取消；
- 食谱格是按行回收的格子区（库的大件 scroll_grid，缺省登记里没有）：在这里导入它的控件，打开界面时不用再临时载入。
"""
from ..dolorContainer.Std.Block import Client as BlockClient  # noqa: F401
from ..dolorContainer.Std.Windowed import Client as WindowedClient  # noqa: F401
from ..Shared.Menus import CookingPot as PotMenu  # noqa: F401
from ..Shared.Rules import CookingPotBook
from .Engine import compFactory, levelId


def _displayName(name, aux):
    """经典界面里没写 text 的配方显示成品的显示名（Shared/Rules/ItemNames）：客户端的 GetItemBasicInfo（进了世界才都是显示名）。"""
    info = compFactory.CreateItem(levelId).GetItemBasicInfo(name, aux)
    return info.get("itemName") if info else None


CookingPotBook.setNamePort(_displayName)
