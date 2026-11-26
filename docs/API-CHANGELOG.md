# 公共接口变更记录

记录农夫乐事公共接口（范围见 [COMPATIBILITY.md](COMPATIBILITY.md) §2）的增减，新的在上面。

以后每次改公共接口，都在本文最上方加一条：标题写 `hostVersion`、日期和 `apiVersion`，内容按"新增 / 变更 / 废弃 / 删除"分项；
新增能力时写出能力名和所在的端，联动代码据此用 `ext.hasCapability(name)` 探测。还没发版的改动先记在"未发版"那一条下，发版时把标题换成那一版的 `hostVersion`。

---

## 未发版（2026-11-26 起，apiVersion 1）

新增：

- **新联动接口**：农夫乐事在服务端的 `LoadServerAddonScriptsAfter`、客户端的 `LoadClientAddonScriptsAfter` 各广播一次 ready 事件
  （命名空间 `arrisFarmersDelight`、系统 `ExtensionApi`，事件 `ServerExtensionApiReady` / `ClientExtensionApiReady`），载荷带这一端的门面 `ext`。
  `ext.side`、`ext.apiVersion`（1）、`ext.hostVersion`、`ext.capabilities`、`ext.hasCapability(name)`。也可以主动导入
  `arrisFarmersDelightScripts.Api.ExtensionApi.Facade.getExtensionApi(side)`（兜底）。见 [EXTENSION-API.md](EXTENSION-API.md) §1–§3。
- **配方 `ext.recipes`**：厨锅（`cooking`）、砧板（`cutting`）、营火烹饪（`campfire_cooking`）三类配方有 ID，能用 Builder（`createBuilder`）
  或 JE 写法的 JSON（`registerFromJson`）登记，同 ID 覆盖，`getRecipeById` / `getRecipesOfType` 查（JE 写法，带 `id`），`removeRecipe` 删；
  厨锅的配料能写标签（`{"tag": "common:tomato"}`），配对照 JE 逐格配；砧板的原料能是一个标签；兼容入口追加的配方有 `legacy:` 开头的派生 ID。
  `matchCooking(物品列表)`：只读，这几件东西在厨锅里做成什么。`syncToClients()`：进服之后改了配方，现在就发给在线玩家。
  `onRecipesChanged(handler)`：`syncToClients` 之后、开服读完行为包配方 JSON 之后调。
  能力 `cooking_recipes`、`cutting_recipes`、`campfire_recipes`、`recipe_json_registration`、`recipe_client_sync`、`recipe_change_events`（服务端），
  `recipe_queries`、`cooking_match`（两端）。见 EXTENSION-API.md §4、§5。
- **Builder 认机械动力的写法**：`ingredient(..., data=aux, count=格数)`（只收关键字）、`ingredientTag(标签, count=1)`，`output(物品, count, data, chance)`、
  `container(物品, data)` 的参数次序和机械动力一样（`output` 的第三个位置参数是 `data`，概率写 `chance=`）；写法上的错不抛，`register()` 答
  `invalid_recipe` 并说哪里不对。见 EXTENSION-API.md §5.3。
- **配方 JSON 照机械动力多认几种写法**：字符串 `"ns:name:aux"`（带 aux 的简写）、物品字典里的 `"id"`（当 `"item"`）、`"cookingTime"` /
  `"cooking_time"`（当 `"cookingtime"`）；物品名只能有一个冒号，别的多冒号写法报 `invalid_recipe`（以前被当成一个永远配不上的物品名收下，
  `cookingTime` 以前被忽略、照缺省 200 刻）。见 RECIPE-JSON.md §2、§3。
- **配方以外的登记口**：`ext.registerKnife`、`ext.registerHeatSource`、`ext.registerStove`（点着的炉灶）、`ext.registerCompostable`。
  能力 `knives`、`heat_sources`、`stoves`、`compostables`（服务端）。见 EXTENSION-API.md §6。
- **标签 `ext.tags`**：`has` / `itemsOf` / `tagsOf` / `blockHas` / `blocksOf` / `generation` / `names`，词表里每个标签的名字常量。
  能力 `item_tags`（两端）。见 EXTENSION-API.md §7、[TAGS.md](TAGS.md)。
- **行为包里的配方 JSON**：任何行为包根下的 `farmersdelight_recipes/**.json`，开服时在 ready 广播之后读，写法同 `registerFromJson`。
  跨行为包读文件 2026-11-26 在游戏里核过。能力 `recipe_json_files`（服务端）。见 [RECIPE-JSON.md](RECIPE-JSON.md)。
- **兼容入口的表**：白名单多一个名字 `CuttingTagDict`（原料是一个物品标签的砧板配方，`{标签名: 和 CuttingBoardDict 一样的值}`），
  JE 的 `cutting/tag_dough`（`common:dough` 切成生意面）在这里。

变更：

- 农夫乐事自带的砧板 / 营火配方 ID 和原料绑死：用它登记（覆盖，或删掉以后加回来）时原料必须还是那一样，否则新的错误码 `input_mismatch`；
  也只能登记回原来那一类配方，否则 `type_mismatch`（EXTENSION-API.md §4、§5.2）。
- 兼容入口的 `CookingPotRecipeList`：被新接口删掉的配方留一个墓碑（行里多 `"Disabled": True`，`Recipe` / `Slots` 原样留着），遍历这张表的下游包要跳过它；
  新接口登记的配方 `Recipe` 可能是空列表。见 linkage.md、[COMPATIBILITY.md](COMPATIBILITY.md) §2。
- 农夫乐事自带的 28 道厨锅菜按 JE 还原了标签格（厨锅配方行多了 `Id`、`Slots` 两个键；`Recipe` 里的写法和原来一样）：别的模组的番茄、米、面团、生肉……
  登记进同名的 `netease_tags` 就能进这些菜。鸡蛋的格子收普通、蓝色、棕色三种蛋。
- 兼容入口的字典表（`CuttingBoardDict`、`CanCookedFoodDict`……）删掉的键也会同步给客户端（以前只同步新增和改动）。
- 砧板上剪刀的 6 条拆解配方多了 `item_type: "shears"`：别的模组的剪刀（物品类型是剪刀的）也能用。
