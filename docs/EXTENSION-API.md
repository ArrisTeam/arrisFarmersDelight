# 农夫乐事联动接口（新接口）

给别的模组作者看：怎么拿到农夫乐事（arrisFarmersDelight）的联动接口 `ext`、它能做什么、农夫乐事没装时怎么办。

- 旧接口（`CreateModAttr("arris")` 拿的三个函数，见 [linkage.md](../linkage.md)）照常可用，本文叫它"兼容入口"：不改不删，不再加新功能，新功能只进 `ext`。
- 兼容承诺见 [COMPATIBILITY.md](COMPATIBILITY.md)，每次增减见 [API-CHANGELOG.md](API-CHANGELOG.md)，
  配方 JSON 的写法见 [RECIPE-JSON.md](RECIPE-JSON.md)，标签（`netease_tags`）见 [TAGS.md](TAGS.md)。
- 事件和名字照机械动力（arrisCreate）的扩展接口取，命名空间换成 `arrisFarmersDelight`：对接过机械动力的不用重学。

---

## 1. 拿到 ext：监听 ready 事件

农夫乐事在服务端、客户端各广播一次 ready 事件，载荷里的 `"extension"` 就是这一端的 `ext`。

### 1.1 原生系统

```python
# mymodScripts/FarmersDelightLink.py
import mod.server.extraServerApi as serverApi

ServerSystem = serverApi.GetServerSystemCls()


class MyServerSystem(ServerSystem):
    def __init__(self, namespace, systemName):
        ServerSystem.__init__(self, namespace, systemName)
        # 在 __init__ 里监听（理由见 1.3）。农夫乐事没装时这个事件永远不来，监听本身不出错。
        self.ListenForEvent("arrisFarmersDelight", "ExtensionApi", "ServerExtensionApiReady", self, self.onFarmersDelightReady)

    def onFarmersDelightReady(self, args):
        ext = args["extension"]
        if ext.hasCapability("cooking_recipes"):
            answer = ext.recipes.createBuilder("mymod:cooking/tomato_stew", "cooking") \
                .ingredient("#common:tomato").ingredient("#common:tomato").ingredient("mymod:tofu") \
                .output("mymod:tomato_stew").container("minecraft:bowl").cookingTime(200).register()
            if not answer["ok"]:
                print("[mymod] 农夫乐事的厨锅配方没登记上：%s" % answer)
```

客户端一样，系统换成 `GetClientSystemCls()`，事件名换成 `"ClientExtensionApiReady"`。客户端的 `ext` 只能查（见 §5、§7），登记都在服务端做。

### 1.2 QuModLibs 模组

QuModLibs 的 `@Listen` / `ListenForEvent` 只听引擎自己的事件（命名空间固定是引擎的），而且要等加载器第一次 `Update` 才导入你的模块、登记监听，
不保证赶得上农夫乐事的广播。用 QuModLibs 的 `regNativePyServer` / `regNativePyClient` 注册一个只管接 ready 的原生小系统：
它在 `InitServer` 时就构造，`__init__` 里的监听一定在广播之前。

```python
# modMain.py
from .QuModLibs.QuMod import *

MOD = EasyMod()
MOD.Server("Server")                  # 你原来的 QuModLibs 服务端
MOD.Client("Client")
# 只为接农夫乐事的 ready：命名空间、系统名用你自己的，最后一段是"模块路径.类名"（相对你的脚本目录）
MOD.regNativePyServer("myMod", "FarmersDelightServerLink", "FarmersDelightServerLink.FarmersDelightServerLink")
MOD.regNativePyClient("myMod", "FarmersDelightClientLink", "FarmersDelightClientLink.FarmersDelightClientLink")
```

```python
# FarmersDelightServerLink.py（和 modMain.py 在同一层）
# -*- coding: utf-8 -*-
import mod.server.extraServerApi as serverApi

ServerSystem = serverApi.GetServerSystemCls()


class FarmersDelightServerLink(ServerSystem):
    def __init__(self, namespace, systemName):
        ServerSystem.__init__(self, namespace, systemName)
        self.ListenForEvent("arrisFarmersDelight", "ExtensionApi", "ServerExtensionApiReady", self, self.onReady)

    def onReady(self, args):
        from .FarmersDelightRecipes import register     # 你的登记代码（普通函数，QuModLibs 的模块里也能写）
        register(args["extension"])
```

```python
# FarmersDelightClientLink.py：客户端要查配方、问标签时把 ext 存下来
# -*- coding: utf-8 -*-
import mod.client.extraClientApi as clientApi

ClientSystem = clientApi.GetClientSystemCls()
LINK = {}


class FarmersDelightClientLink(ClientSystem):
    def __init__(self, namespace, systemName):
        ClientSystem.__init__(self, namespace, systemName)
        self.ListenForEvent("arrisFarmersDelight", "ExtensionApi", "ClientExtensionApiReady", self, self.onReady)

    def onReady(self, args):
        LINK["ext"] = args["extension"]
```

服务端、客户端的系统分两个文件写：服务端的文件不要导入客户端的接口，反过来也一样。

这一节是对着 QuModLibs 的源码写的（农夫乐事带的那份，arrisCreate 的 kit），**还没在游戏里跑过**（2026-11-26 实机核的是 §1.1 原生系统的写法）。
源码里看得到的：`regNativePyServer(命名空间, 系统名, 路径)` 只是记下来，路径前面拼上你的脚本目录名（`EasyMod` 的 `_modDirName`）；
QuMod 在自己的 `InitServer` 里对记下的每一个调 `serverApi.RegisterSystem`（引擎当场构造系统，`__init__` 里的监听在这时就登记了），
这早于引擎发 `LoadServerAddonScriptsAfter`，所以赶得上农夫乐事的广播；客户端的 `regNativePyClient` 同理（`InitClient`）。
别的版本的 QuModLibs 没核过：用之前看一眼它的 `QuMod.py` 里有没有 `regNativePyServer`。

### 1.3 什么时候监听、先后顺序

- **在系统的 `__init__` 里监听**（或者 QuModLibs 的原生小系统，1.2）。不要在你自己的 `LoadServerAddonScriptsAfter` 处理函数里才监听：
  各模组的 `LoadServerAddonScriptsAfter` 谁先谁后没有保证，农夫乐事可能已经播过了，你就永远收不到。
- **各模组的 ready 处理函数之间也没有先后保证**：你在 ready 里查到的配方表里，不一定已经有别的模组在 ready 里登记的配方。
  要等"大家都登记完"再做的事（比如把农夫乐事的厨锅配方抄进你自己的机器），放进 `ext.recipes.onRecipesChanged` 的处理函数里
  （开服时 ready 广播和行为包配方 JSON 读完之后调一次，§5.8），或者用到的时候再查。
- **不冻结**：农夫乐事的表一直是活的，ready 之后再登记照样生效。建议在 ready 里登记完；进服之后再改配方，改完调 `ext.recipes.syncToClients()`。

服务端的先后：

```text
T0  各模组的系统 __init__：监听 ServerExtensionApiReady
T1  引擎发 LoadServerAddonScriptsAfter
T2  农夫乐事广播 ServerExtensionApiReady（载荷带服务端的 ext）
T3  各模组的处理函数登记配方、刀、热源……
T4  农夫乐事读全部行为包里的 farmersdelight_recipes/**.json（RECIPE-JSON.md）
T5  调一次 onRecipesChanged 的处理函数（types、recipeIds 都是 None）
T6  玩家进服：表同步把 T3、T4 的改动发给他的客户端
```

T2 → T5 的先后 2026-11-26 在游戏里核过：第三方在 ready 的处理函数里查不到行为包里的 JSON 配方（还没读），`onRecipesChanged` 在读完之后才调。

客户端：`__init__` 里监听 `ClientExtensionApiReady` → 引擎发 `LoadClientAddonScriptsAfter` → 农夫乐事广播。客户端的配方表是服务端同步过来的：
玩家进服之前，客户端只有农夫乐事自带的配方。

### 1.4 兜底：主动导入（兼容入口）

实在接不到事件时，可以主动导入门面模块：

```python
facadeModule = serverApi.ImportModule("arrisFarmersDelightScripts.Api.ExtensionApi.Facade")   # 农夫乐事没装是 None
ext = facadeModule.getExtensionApi("server") if facadeModule else None                         # 客户端写 "client"
```

拿到的和 ready 载荷里的是同一个对象。**只在 `LoadServerAddonScriptsAfter` 之后用**（比如玩家进服时）：表同步的基线是农夫乐事服务端模块导入那一刻的表，
在那之前登记的配方会被当成"本来就有"，不会同步给客户端（站点、书、JEI 不认它）。能监听事件就别用这条路。

### 1.5 农夫乐事没装时

事件永远不来，处理函数不会被调，不用 `try/except`。主动导入（1.4）拿到 `None`。

---

## 2. 事件协议

| 常量 | 值 |
| --- | --- |
| `EXTENSION_API_VERSION` | `1` |
| `EXTENSION_API_NAMESPACE` | `"arrisFarmersDelight"` |
| `EXTENSION_API_SYSTEM_NAME` | `"ExtensionApi"` |
| `SERVER_EXTENSION_API_READY_EVENT` | `"ServerExtensionApiReady"` |
| `CLIENT_EXTENSION_API_READY_EVENT` | `"ClientExtensionApiReady"` |

常量在 `arrisFarmersDelightScripts.Api.ExtensionApi.Events`（只放常量，导入它不会拉起别的模块），也可以直接写字符串。载荷：

```python
{"extension": ext, "side": "server",   # 或 "client"
 "apiVersion": 1}                      # = EXTENSION_API_VERSION
```

事件由农夫乐事专用的系统 `("arrisFarmersDelight", "ExtensionApi")` 用 `BroadcastEvent` 在本端广播：服务端事件只有服务端收得到，客户端事件只有客户端收得到。
`ext` 是同一个进程里的对象，**不能跨端、不能经 Call / 网络事件转发**。你的处理函数抛了异常不会拖垮农夫乐事（农夫乐事打一次调用栈，接着往下走），
但同一次广播里排在你后面的处理函数会不会照常被调，取决于引擎事件总线（按引擎源码看是每个监听者单独兜着，自定义事件没在游戏里量过）：处理函数里自己接住异常最稳。

---

## 3. ext 的标识和能力名

| 成员 | 说明 |
| --- | --- |
| `ext.side` | `"server"` 或 `"client"` |
| `ext.apiVersion` | 公共接口的版本，只有破坏性变更（改名、删除、改含义）才加一。现在是 1 |
| `ext.hostVersion` | 农夫乐事的版本号元组，如 `(1, 0, 2)`，和 manifest 的 `header.version` 一样，每次发版都变 |
| `ext.capabilities` | 这一端的全部能力名（`frozenset`） |
| `ext.hasCapability(name)` | 这一端有没有这项能力；名字不是字符串时是 `False`，不抛 |

**某个接口在不在，看能力名，不要拿版本号猜。** 能力名按端分，只在一端有用的只登记在那一端：

| 能力名 | 端 | 接口 |
| --- | --- | --- |
| `cooking_recipes` | 服务端 | `ext.recipes` 的 `cooking` 类型：厨锅配方的登记、覆盖、删除，原料能写标签（§5） |
| `cutting_recipes` | 服务端 | `ext.recipes` 的 `cutting` 类型：砧板配方，原料是一样物品或一个标签（§5） |
| `campfire_recipes` | 服务端 | `ext.recipes` 的 `campfire_cooking` 类型：煎锅、炉灶、手持煎锅能煎烤什么（§5） |
| `recipe_json_registration` | 服务端 | `ext.recipes.registerFromJson`（§5.4） |
| `recipe_queries` | 两端 | `ext.recipes.getRecipeById` / `getRecipesOfType`（§5.5） |
| `recipe_client_sync` | 服务端 | `ext.recipes.syncToClients`（§5.8） |
| `recipe_change_events` | 服务端 | `ext.recipes.onRecipesChanged`（§5.8） |
| `cooking_match` | 两端 | `ext.recipes.matchCooking`（§5.7） |
| `knives` | 服务端 | `ext.registerKnife`（§6） |
| `heat_sources` | 服务端 | `ext.registerHeatSource`（§6） |
| `stoves` | 服务端 | `ext.registerStove`（§6） |
| `compostables` | 服务端 | `ext.registerCompostable`（§6） |
| `item_tags` | 两端 | `ext.tags`（§7） |
| `recipe_json_files` | 服务端 | 行为包里的 `farmersdelight_recipes/`（[RECIPE-JSON.md](RECIPE-JSON.md)；跨行为包读文件 2026-11-26 在游戏里核过） |

---

## 4. 返回值和错误码

登记、删除这类方法返回字典 `{"ok": bool, "error": 错误码或 None, "id": 配方 ID 或名字}`，有的错误另带说明的键。
**看 `ok` 判断成败，不要只比对已知的错误码**：以后可能加新的错误码，也可能多出新的键。

| 错误码 | 什么时候 | 另带的键 |
| --- | --- | --- |
| `server_only` | 在客户端调了登记、删除、`syncToClients`、`onRecipesChanged` | |
| `invalid_id` | 配方 ID 不是 `命名空间:路径` 的写法 | |
| `reserved_namespace` | ID 是 `legacy:`，或者是 `farmersdelight:` 却不是覆盖农夫乐事已有的配方 | |
| `invalid_recipe` | 配方的格式不对 | `message`：哪里不对 |
| `invalid_json` | `registerFromJson` 给的文本不是 JSON | `message` |
| `type_mismatch` | 用已有的 ID 登记了另一类配方 | `current`：那个 ID 现在的类型 |
| `input_taken` | 砧板 / 营火：这样原料已经有一条别的 ID 的配方（一样原料只有一条） | `by`：占着它的配方 ID |
| `not_found` | 删除时没有这个 ID（或者已经删了） | |
| `invalid_handler` | `onRecipesChanged` 给的不是函数 | |
| `invalid_recipe_types` | `syncToClients` 给的类型不认识 | |
| `invalid_name` | §6 的登记口：名字不是 `命名空间:名字`（或 aux 不对） | |
| `invalid_chance` | `registerCompostable` 的概率不在 (0, 100] 里 | |

客户端调登记类方法一律返回 `server_only`、不抛异常：两端可以共用同一份登记代码。

---

## 5. 配方：ext.recipes

### 5.1 三类配方

| 类型 | 写法（都认） | 是什么 | 删了怎样 |
| --- | --- | --- | --- |
| `cooking` | `"cooking"`、`"farmersdelight:cooking"` | 厨锅：1 到 6 格配料，一份出几个成品，可以要容器 | 留墓碑（见 5.6） |
| `cutting` | `"cutting"`、`"farmersdelight:cutting"` | 砧板：一样原料（物品或一个标签）、一种工具、1 到 4 个产物（可以带概率） | 真删 |
| `campfire_cooking` | `"campfire_cooking"`、`"minecraft:campfire_cooking"` | 煎锅、炉灶、手持煎锅"能煎烤什么"：一样物品 -> 一样物品 | 真删 |

**同一个成品只有一套容器、时间、经验**：锅只记得煮的是哪个成品，盛的时候按表里这个成品的**第一条活配方**要容器、算时间和经验。
再登记一条同成品、容器不同的配方，锅里实际照第一条来（`matchCooking` 报的也是这一套）；要换掉自带那道菜的容器，就用它的 ID 覆盖它。

配方存在农夫乐事原来那几张表里（和兼容入口同一份数据：`CookingPotRecipeList`、`CuttingBoardDict` / `CuttingTagDict`、`CanCookedFoodDict`），
所以两种接口登记的配方是一回事：旧接口追加的新接口查得到，新接口登记的旧读者（下游包、表同步）也看得到。
玩家进服时客户端由表同步拿到这些表（服务端改了之后 5 秒内补发，或者调 `syncToClients` 现在就发）。

`campfire_cooking` 只认物品：煎锅、炉灶按物品名查这张表，查不到再问引擎有没有以它为原料的营火配方（配方 JSON 的 `tags` 里带 `campfire` 的）。
所以给你的生肉写一份原版写法的营火配方，不登记到这里也能煎；登记到这里的好处是食谱书和 JEI 的煎锅 / 炉灶页会列出它（那两处只列这张表）。

### 5.2 配方 ID

- 写成 `命名空间:路径`，用你自己的命名空间，如 `mymod:cooking/tomato_stew`（路径里写不写类型随你，建议写）。
- **同一个 ID 再登记 = 覆盖**：厨锅配方原地换掉（在表里的位置不变），砧板 / 营火换掉那一条。
- `farmersdelight:` 留给农夫乐事：只能用来覆盖农夫乐事已有的配方（比如改一道菜的配料），不能新加。
  农夫乐事的厨锅配方 ID 照 JE：`farmersdelight:cooking/<JE 的配方文件名>`，如 `farmersdelight:cooking/beef_stew`；
  砧板 `farmersdelight:cutting/<物品的命名空间>/<物品名>`（aux 不是 0 时后面加 `_<aux>`），按标签的那条照 JE 叫 `farmersdelight:cutting/tag_dough`；
  营火 `farmersdelight:campfire_cooking/<物品的命名空间>/<物品名>`。不确定就 `getRecipesOfType` 列出来看。
- `legacy:` 是兼容入口追加的配方的派生 ID，只读：能查、能删，不能用来登记。
  厨锅 `legacy:cooking/<成品的命名空间>/<成品名>`，同一个成品的第 2、3 条按表里的先后加 `_2`、`_3`；
  砧板 `legacy:cutting/<原料的命名空间>/<原料名>`（aux 不是 0 加 `_<aux>`），按标签的 `legacy:cutting/tag/<标签的命名空间>/<标签名>`；
  营火 `legacy:campfire_cooking/<原料的命名空间>/<原料名>`。派生 ID 跟着表里的东西走：下游包加载的先后变了，`_2`、`_3` 可能对调。
- 砧板、营火一样原料只有一条配方。要换掉别人占着的那条：用它的 ID 覆盖，或者先 `removeRecipe` 它再登记你的。

### 5.3 Builder

```python
recipes = ext.recipes
recipes.createBuilder("mymod:cooking/tomato_stew", "cooking") \
    .ingredient("#common:tomato") \
    .ingredient("#common:raw_beef", "mymod:tofu") \
    .output("mymod:tomato_stew", count=1) \
    .container("minecraft:bowl") \
    .cookingTime(200).experience(1.0) \
    .register()                          # {"ok": True, "error": None, "id": "mymod:cooking/tomato_stew"}

recipes.createBuilder("mymod:cutting/tofu", "cutting") \
    .ingredient("mymod:tofu_block") \
    .tool("knife") \
    .output("mymod:tofu", count=4).output("mymod:okara", chance=0.5) \
    .register()

recipes.createBuilder("mymod:campfire_cooking/tofu", "campfire_cooking") \
    .ingredient("mymod:tofu").output("mymod:grilled_tofu").register()
```

| 方法 | 用在 | 说明 |
| --- | --- | --- |
| `ingredient(*选项)` | 三类 | 加一格配料；给几个就是这一格的几个选项（任一个都行）。厨锅最多 6 格；砧板、营火只有一格、一个选项 |
| `output(物品, count=1, chance=None)` | 三类 | 成品。厨锅、营火一个（厨锅的 `count` 是一份出几个，营火不看）；砧板可以加几个（最多 4 个），`chance` 是概率（0 到 1，不写是必出） |
| `container(物品)` | 厨锅 | 盛这道菜要的容器（JE 的 `container`）。不写时照 JE 推：成品在农夫乐事的剩余物表里（碗装的菜、饮料……）就要那个容器，没有就不要（RECIPE-JSON.md §2） |
| `cookingTime(刻)` | 厨锅 | 一份煮多少刻（20 刻一秒），不写是 200 |
| `experience(数)` | 厨锅 | 一份给多少经验，不写是 0（JE 的缺省） |
| `tool(工具)` | 砧板 | `"knife"`、`"axe"`、`"pickaxe"`、`"shovel"`、`"hoe"`、`"shears"`，或 `"#标签"`、`"物品名"`、它们的列表（见 RECIPE-JSON.md §4） |
| `text(名字)` | 厨锅 | 经典厨锅界面食谱格里的名字。不写时界面显示成品物品的显示名（界面所在那一端的语言；物品没有名字时显示物品 ID），搜索也按它搜；覆盖已有配方时不写则沿用原来的名字。`getRecipeById` 给的样子里只有写了的 `text` |
| `toJson()` | | 写成 JE 配方 JSON 的样子（带 `"id"`），可以存成 `farmersdelight_recipes/` 下的文件 |
| `register()` | | 查格式、登记，返回 §4 的字典 |

物品写 `"命名空间:名字"`（aux 0）或 `("命名空间:名字", aux)`，标签写 `"#标签名"`（标签没有 aux）。Builder 写出来的就是一份 JSON，
`register()` 和 `registerFromJson` 走同一条路：两种写法的规矩一模一样。

### 5.4 registerFromJson

```python
ext.recipes.registerFromJson(文本或字典, recipeId=None)
```

JE 农夫乐事写法的配方 JSON（[RECIPE-JSON.md](RECIPE-JSON.md)），物品名写网易的。ID 不给就用 JSON 里的 `"id"`。JE 的标签名（`forge:raw_beef`……）
自动换成农夫乐事词表里的 `common:` 名（对照表在 TAGS.md）。

### 5.5 查询

```python
ext.recipes.getRecipeById("farmersdelight:cooking/beef_stew")
# {"id": "farmersdelight:cooking/beef_stew", "type": "farmersdelight:cooking",
#  "ingredients": [{"tag": "common:raw_beef"}, {"tag": "common:carrot"}, {"tag": "common:potato"}],
#  "result": {"item": "arris:cookbeef_stew"}, "cookingtime": 200, "experience": 1.0, "container": {"item": "minecraft:bowl"},
#  "text": "牛肉炖"}
ext.recipes.getRecipesOfType("cutting")      # 这一类的全部，同样的样子；类型不认识是 []
```

给的是 JE 配方 JSON 的样子（带 `"id"`），改几个字段原样交回 `registerFromJson` 就是覆盖。删了的查不到（`None`）。
兼容入口只写了物品写法的厨锅配方，`ingredients` 按它的第一种写法一格一样东西给。

客户端也能查，查的是表同步过来的那一份（玩家进服之后才有别的模组的配方）。厨锅、砧板的配方 ID 两端一样；**营火烹饪例外**：那张表的值只是成品的物品名，
放不下 ID，新接口登记的营火配方在客户端查到的是派生的 `legacy:campfire_cooking/...` ID。

### 5.6 删除

```python
ext.recipes.removeRecipe("legacy:cooking/mymod/old_stew")
```

厨锅配方删了留一个墓碑（表里那一行带 `"Disabled": True`）：农夫乐事和站点拿"配方在表里的位置"当身份，不能从表里摘掉。
删了的厨锅配方哪里都不认（锅、书、界面、JEI），同 ID 再登记就回来（还在原来的位置）。砧板、营火是真删，删除也会同步给客户端。

### 5.7 matchCooking

```python
ext.recipes.matchCooking(["mymod:tomato", "mymod:tomato", ("minecraft:beef", 0)])
# {"id": 配方 ID, "result": 成品物品字典（count 是一份出几个）, "container": ("minecraft:bowl", 0) 或 None, "pushItems": 余料}，做不成是 None
```

只读：这几件东西放进厨锅会做成什么（一件算一格；物品字典、`(物品名, aux)`、物品名都行）。给别的模组的锅、机器做回退用。两端都能用。

### 5.8 onRecipesChanged 和 syncToClients（服务端）

```python
def onChanged(event):
    event.types        # 涉及的类型列表（"cooking" / "cutting" / "campfire_cooking"），不分类型时 None
    event.recipeIds    # 调用的人给的配方 ID 列表，没给时 None
ext.recipes.onRecipesChanged(onChanged)

ext.recipes.syncToClients(recipeTypes=None, recipeIds=None)   # 类型可以是一个或列表
```

- `syncToClients`：进服之后改了配方，现在就把表的改动发给在线的玩家（不调也会在 5 秒内补发），然后调 `onRecipesChanged` 的处理函数。
- `onRecipesChanged` 的处理函数在两种时候被调：每次 `syncToClients` 之后（带它的参数）；开服时 ready 广播和行为包配方 JSON 读完之后一次（两个都是 `None`）。
  按登记的先后调，同一个函数只登记一次；处理函数抛了异常只打一次调用栈，不耽误别的处理函数。

### 5.9 标签格怎么配

厨锅的一格写 `#common:tomato`，就收"现在带这个标签的任何物品"：农夫乐事自己的番茄，加上别的模组在自己的 `netease_tags` 里登记进
`common:tomato` 的番茄（TAGS.md）。配对照 JE（`RecipeMatcher`）：锅里每件东西分给一个收它的格，格子正好用完就配上；几条配方都配得上时表里靠前的赢。
远端玩家的客户端在进世界之前读不全标签，农夫乐事那时按自己的词表答，进世界后跟上。

表里那一行（`CookingPotRecipeList` 的元素）对新接口登记的配方多三个键：`Id`、`Slots`（每格的选项）、`Recipe`。
**`Recipe` 只是给旧读者看的快照**：按登记那一刻标签的成员展开成具体物品的写法（最多 64 种），给只认物品写法的下游包读；配方以 `Slots` 为准。
读这张表的下游包请容忍 `Recipe` 是空列表（只写了格子、展开不出写法的配方）。

---

## 6. 配方以外的登记口（服务端）

| 方法 | 做什么 |
| --- | --- |
| `ext.registerKnife(物品名)` | 这件物品算刀（砧板上切东西、刀杀生物多掉东西、切蛋糕……），追加进 `knifeList` |
| `ext.registerHeatSource(方块名)` | 这个方块给厨锅、煎锅加热（不看方块状态），追加进 `CanProvideHeatBlockList` |
| `ext.registerStove(方块名)` | 这个方块是点着的炉灶（会烤上面的东西、站上去烫脚、炉灶站点认它），追加进 `StoveList`；方块要像农夫乐事的炉灶一样带方块实体 |
| `ext.registerCompostable(物品名, 概率, aux=0)` | 这件物品能放进原版堆肥桶，概率是让桶升一层的百分数（大于 0、不超过 100），写进 `ComposterItemDict` |

- **刀和热源优先用标签**：在你自己的 `netease_tags` 里把刀登记进 `common:knife`、热源方块登记进 `common:heat_source`
  （要看点燃状态的登记进 `common:heat_source_lit`），见 TAGS.md。这几个登记口是给没法用标签的情况。
- 名字写 `命名空间:名字`；已经在表里的不重复加，照样返回 `ok`。返回 §4 的字典，`"id"` 是登记的名字。
- 炉灶只登记点着的那个方块。熄灭的孪生方块、点火 / 灭火换方块这一套这一版不开。

---

## 7. 标签：ext.tags（两端，只读）

```python
tags = ext.tags
tags.RAW_BEEF                                  # "common:raw_beef"：词表里每个标签都有一个名字常量（TAGS.md）
tags.has("mymod:steak", tags.RAW_BEEF)         # 这件物品带不带这个标签
tags.itemsOf(tags.TOMATO)                      # 标签现在的全部成员（元组：农夫乐事词表里的在前，别的模组登记的接在后面）
tags.tagsOf("mymod:steak")                     # 这件物品的全部标签（frozenset），可以给 aux
tags.blockHas("mymod:hot_rock", tags.HEAT_SOURCE)
tags.blocksOf(tags.HEAT_SOURCE)
tags.generation()                              # 答案可能变了就加一：按标签建了索引的，拿它判断要不要重建
tags.names()                                   # 词表里的物品标签名，排好序
```

农夫乐事所有"按标签认"的地方问的都是这一份答案。引擎的标签读不全时（远端客户端进世界之前）按农夫乐事的词表答，`generation()` 变了说明答案可能变了。

---

## 8. 最小模板

```text
mymod_bp/
├── pack_manifest.json           # 不用声明依赖农夫乐事：运行时看事件来不来
├── netease_tags/                # 可选：把你的番茄、刀……登记进 common: 标签（TAGS.md）
├── farmersdelight_recipes/      # 可选：配方 JSON（RECIPE-JSON.md）
│   └── mymod/cooking/tomato_stew.json
└── mymodScripts/
    ├── modMain.py
    └── FarmersDelightLink.py    # §1.1 或 §1.2 的系统
```

```python
# 服务端的登记代码
def register(ext):
    recipes = ext.recipes
    if ext.hasCapability("cooking_recipes"):
        recipes.createBuilder("mymod:cooking/tomato_stew", "cooking") \
            .ingredient("#common:tomato").ingredient("#common:tomato").ingredient("mymod:tofu") \
            .output("mymod:tomato_stew").container("minecraft:bowl").register()
    if ext.hasCapability("cutting_recipes"):
        recipes.createBuilder("mymod:cutting/tofu", "cutting") \
            .ingredient("mymod:tofu_block").tool("knife").output("mymod:tofu", count=4).register()
    if ext.hasCapability("knives"):
        ext.registerKnife("mymod:jade_knife")      # 更好的做法：netease_tags 里登记进 common:knife
```

---

## 9. 常见问题

**问：ready 里登记的配方，玩家的客户端什么时候有？** 玩家进服时表同步一次发过去。进服之后改的，调 `syncToClients()` 或等 5 秒。

**问：我用兼容入口（旧接口）加的配方，新接口查得到吗？** 查得到，ID 是 `legacy:` 开头的派生 ID（§5.2），也能删。

**问：怎么改农夫乐事自带的一道菜？** 用它的 `farmersdelight:` ID 覆盖：`getRecipeById` 拿到 JSON，改了交回 `registerFromJson`。
别的模组用兼容入口（`AddCookingPotRecipe`）给这道菜加的写法，覆盖之后照样留着（接在新行的 `Recipe` 后面），和谁先加载无关。

**问：一个标签里没有成员会怎样？** 那一格什么都不收，这条配方配不上；不报错。等有模组登记了成员（或玩家装了那个模组）就能配。

**问：为什么不像机械动力那样在 ready 之后冻结？** 农夫乐事的表从旧接口起就一直允许随时追加，表同步每 5 秒比一次；没有哪里要在某一刻之后才建好的缓存。
