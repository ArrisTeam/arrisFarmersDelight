# -*- coding: utf-8 -*-
"""ExtensionApi - 新联动接口的包：主动导入时的兜底入口 getExtensionApi(side)，写法和机械动力一样（双端，不碰引擎）

能监听 ready 事件就别用它（docs/EXTENSION-API.md §1.4）；实在接不到时，在 LoadServerAddonScriptsAfter / LoadClientAddonScriptsAfter 之后：

    package = serverApi.ImportModule("arrisFarmersDelightScripts.Api.ExtensionApi")   # 农夫乐事没装是 None
    ext = package.getExtensionApi("server") if package else None                      # 客户端写 "client"

拿到的和 ready 载荷里的是同一个对象；原来的 arrisFarmersDelightScripts.Api.ExtensionApi.Facade.getExtensionApi 照旧能用。
这里顶层什么都不导入：别的模组 ImportModule 本包里的 Events 拿常量时 Python 先执行本文件，不能顺带拉起门面。门面到调用时才导入。
"""


def getExtensionApi(side):
    """这一端的门面（Facade.getExtensionApi：同一端总是同一个对象）；side 不是 "server" / "client" 抛 ValueError。"""
    from .Facade import getExtensionApi as facadeOf
    return facadeOf(side)
