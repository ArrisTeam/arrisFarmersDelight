# -*- coding: utf-8 -*-
"""Events - 新联动接口的事件协议：命名空间、系统名、两端的 ready 事件、接口版本、两端的能力名（双端，不碰引擎）

名字和机械动力（arrisCreate 的 Api/ExtensionApi/_events.py）同一套，命名空间换成 arrisFarmersDelight：学过那边的作者不用重学。
别的模组在自己的 ServerSystem / ClientSystem 的 __init__ 里监听（农夫乐事没装时这个事件永远不来，监听本身不出错）：

    self.ListenForEvent("arrisFarmersDelight", "ExtensionApi", "ServerExtensionApiReady", self, self.onFarmersDelightReady)

    def onFarmersDelightReady(self, args):
        ext = args["extension"]          # 这一端的门面（Facade.ExtensionApiFacade）
        if ext.hasCapability("..."):     # 某个接口在不在，看能力名，不拿版本号猜
            ...

载荷是 {"extension": ext, "side": "server" 或 "client", "apiVersion": EXTENSION_API_VERSION}。ext 是同一个进程里的对象：不能跨端，不能经 Call / Notify 转发。
农夫乐事在服务端的 LoadServerAddonScriptsAfter、客户端的 LoadClientAddonScriptsAfter 里各广播一次（Ready）。
本模块只放常量、不导入别的：别的模组 ImportModule 它拿常量，不会顺带拉起门面。
"""

# 公共接口的版本：只有破坏性变更（改名、删除、改变含义）才加一；新增接口不动它，各自登记能力名
EXTENSION_API_VERSION = 1

EXTENSION_API_NAMESPACE = "arrisFarmersDelight"
EXTENSION_API_SYSTEM_NAME = "ExtensionApi"

SERVER_EXTENSION_API_READY_EVENT = "ServerExtensionApiReady"
SERVER_EXTENSION_API_READY_EVENT_ID = "arrisFarmersDelight:ExtensionApi:ServerExtensionApiReady"
CLIENT_EXTENSION_API_READY_EVENT = "ClientExtensionApiReady"
CLIENT_EXTENSION_API_READY_EVENT_ID = "arrisFarmersDelight:ExtensionApi:ClientExtensionApiReady"

SIDES = ("server", "client")
READY_EVENTS = {"server": SERVER_EXTENSION_API_READY_EVENT, "client": CLIENT_EXTENSION_API_READY_EVENT}

# 行为包里的 farmersdelight_recipes/（Api/ExtensionApi/RecipeFiles.py）：服务端照常读，但跨包读文件用的是引擎内部的 server_resource
# （Server/Helpers/PackJson.py），游戏里还没核过；核过之前不登记它的能力名 recipe_json_files，核过把这里改成 True。
RECIPE_JSON_FILES_VERIFIED = False

# 两端各自的能力名（ext.hasCapability 查的就是这两张）：一项接口实现了、有测试、写进对外文档了才登记，按端分（只在一端有用的只登记那一端）。
# 门面的标识（side、apiVersion、hostVersion、capabilities、hasCapability）是 apiVersion 1 起就有的，不单列能力名。
SERVER_CAPABILITIES = frozenset(["recipe_json_files"] if RECIPE_JSON_FILES_VERIFIED else [])
CLIENT_CAPABILITIES = frozenset()
