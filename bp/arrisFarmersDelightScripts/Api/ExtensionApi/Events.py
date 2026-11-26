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

# 行为包里的 farmersdelight_recipes/（Api/ExtensionApi/RecipeFiles.py）：跨包读文件用的是引擎内部的 server_resource（Server/Helpers/PackJson.py）。
# 2026-11-26 在游戏里核过（另一个行为包里不写 id 的配方 JSON 开服时读到了、按路径派生了 ID），能力名 recipe_json_files 登记上。
RECIPE_JSON_FILES_VERIFIED = True

# 两端各自的能力名（ext.hasCapability 查的就是这两张）：一项接口实现了、有测试、写进对外文档了才登记，按端分（只在一端有用的只登记那一端）。
# 门面的标识（side、apiVersion、hostVersion、capabilities、hasCapability）是 apiVersion 1 起就有的，不单列能力名。
# 每一项是什么、在哪一端：docs/EXTENSION-API.md §3（tests/test_extension_docs.py 核对两边一样）。
SERVER_CAPABILITIES = frozenset([
    "cooking_recipes",           # ext.recipes 的 cooking 类型：厨锅配方的登记、覆盖、删除（Builder 和 JSON），原料能写标签
    "cutting_recipes",           # ext.recipes 的 cutting 类型：砧板配方（原料是物品或一个标签）
    "campfire_recipes",          # ext.recipes 的 campfire_cooking 类型：煎锅、炉灶、手持煎锅读的"能煎烤什么"（只认物品）
    "recipe_json_registration",  # ext.recipes.registerFromJson（JE 写法的配方 JSON，文本或字典）
    "recipe_queries",            # ext.recipes.getRecipeById / getRecipesOfType（JE 写法，带 id；旧接口追加的有 legacy: 派生 ID）
    "recipe_client_sync",        # ext.recipes.syncToClients（进服之后改了配方：现在就发给在线的玩家）
    "recipe_change_events",      # ext.recipes.onRecipesChanged（syncToClients 之后、开服读完行为包 JSON 之后调）
    "cooking_match",             # ext.recipes.matchCooking（只读：这几件东西在厨锅里做成什么）
    "recipe_lookup",             # ext.recipes.findRecipe（只读：这件东西在砧板 / 营火上按哪条配方做，同机械动力的 findRecipe）
    "knives",                    # ext.registerKnife
    "heat_sources",              # ext.registerHeatSource
    "heat_source_states",        # ext.registerHeatSource 的 states：带状态条件的热源（盛着熔岩的炼药锅那样，"方块 + 状态"）
    "stoves",                    # ext.registerStove（点着的炉灶方块）
    "compostables",              # ext.registerCompostable
    "item_tags",                 # ext.tags（标签的只读查询、词表的名字常量）
] + (["recipe_json_files"] if RECIPE_JSON_FILES_VERIFIED else []))   # 行为包里的 farmersdelight_recipes/（docs/RECIPE-JSON.md）
CLIENT_CAPABILITIES = frozenset([
    "recipe_queries",            # 客户端读的是表同步过来的那一份
    "cooking_match",
    "recipe_lookup",
    "item_tags",
])
