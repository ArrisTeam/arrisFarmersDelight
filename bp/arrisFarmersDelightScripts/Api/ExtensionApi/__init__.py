# -*- coding: utf-8 -*-
"""ExtensionApi - 新联动接口的包：主动导入时的兜底入口 getExtensionApi(side)，写法和机械动力一样（双端，不碰引擎）

能监听 ready 事件就别用它（docs/EXTENSION-API.md §1.4）；实在接不到时，在 LoadServerAddonScriptsAfter / LoadClientAddonScriptsAfter 之后：

    try:
        package = serverApi.ImportModule("arrisFarmersDelightScripts.Api.ExtensionApi")   # 农夫乐事没装是 None
        ext = package.getExtensionApi("server") if package else None                      # 客户端写 "client"
    except Exception:
        ext = None              # 装的是还没有这个包的旧版本，或者这个包、门面导入时出错

农夫乐事没装时 ImportModule 返回 None。装的是还没有这个包的旧版本时它不给 None，而是抛 ImportError: No module named ExtensionApi
（引擎的 ImportModule 只在模组的脚本目录不在时给 None，目录在、下面没有这个模块就抛；2026-11-26 在 3.10 的游戏里量过）；
这个包或者 getExtensionApi 这时才导入的门面自己出错，异常也原样抛进调用的代码。这几种都当拿不到。
拿到的和 ready 载荷里的是同一个对象；原来的 arrisFarmersDelightScripts.Api.ExtensionApi.Facade.getExtensionApi 照旧能用。
这里顶层什么都不导入：别的模组 ImportModule 本包里的 Events 拿常量时 Python 先执行本文件，不能顺带拉起门面。门面到调用时才导入。
"""


def getExtensionApi(side):
    """这一端的门面（Facade.getExtensionApi：同一端总是同一个对象）；side 不是 "server" / "client" 抛 ValueError。"""
    from .Facade import getExtensionApi as facadeOf
    return facadeOf(side)
