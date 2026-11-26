# 棱花 Arris 农夫乐事联动接口文档

作者：Lovely\_小柒丫

> **有新接口了**（2026-11 起）：农夫乐事在加载完时广播 ready 事件，事件里带一个接口对象 `ext`：配方有 ID、原料能写标签、能查能删能覆盖，
> 还能直接在行为包里放配方 JSON。新写联动请看 [docs/EXTENSION-API.md](docs/EXTENSION-API.md)（配方 JSON：[docs/RECIPE-JSON.md](docs/RECIPE-JSON.md)，
> 兼容承诺：[docs/COMPATIBILITY.md](docs/COMPATIBILITY.md)，标签：[docs/TAGS.md](docs/TAGS.md)）。
>
> 本文写的是原来的接口（`CreateModAttr("arris")` 拿的三个函数），现在叫"兼容入口"：照常可用、不改不删，只是不再加新功能。
> 两种接口登记的是同一份数据：这里追加的配方，新接口查得到（ID 是 `legacy:` 开头的派生 ID）。

## 功能描述

本接口主要用于副包或其他模组与农夫乐事主包之间的联动，支持：

- 修改或添加新的厨锅配方
- 添加新的砧板配方
- 添加新的煎锅、炉灶烹饪食材

## 使用前的准备

调用接口前，请监听 `LoadServerAddonScriptsAfter` 事件。假设事件回调函数为
`FarmersDelight`，可以使用 ModAPI 的 `GetAttr` 接口获取主包预留的接口：

```python
def FarmersDelight(self, args):
	factory = serverApi.GetEngineCompFactory()
	mod_attr = factory.CreateModAttr("arris")
	interface = mod_attr.GetAttr("ArrisFarmersDelightInterface")
	obtain = mod_attr.GetAttr("ArrisFarmersDelightObtain")
	addRecipe = mod_attr.GetAttr("ArrisAddCookingPotRecipe")
	# 建议后续使用 if 判断是否获取成功
```

## 联动接口

### 添加小刀

将自定义物品配置为小刀，
在自定义物品的components中添加`arris:knife`标签

示例：
```
"minecraft:tags": {
    "tags": ["arris:knife"]
}
```

### ArrisFarmersDelightInterface

向农夫乐事主包的配置表（`bp/arrisFarmersDelightScripts/Shared/Data/` 下各文件）中的字典或列表添加元素。

| 参数名    | 数据类型                | 说明                             |
| --------- | ----------------------- | -------------------------------- |
| `target`  | `str`                   | 需要调用的变量名称               |
| `element` | `str`、`list` 或 `dict` | 要添加的元素，类型取决于目标对象 |

示例：

```python
testRecipe = {
	"Recipe": [
		[
			("minecraft:stick", 0),
			("minecraft:stick", 0)
		],
		[
			("minecraft:stone", 0),
			("minecraft:stone", 0),
			("minecraft:stone", 0)
		]
	],
	"CookResult": ("minecraft:diamond", 0),
	"Vessel": ("minecraft:bowl", 0),
	"PushItem": [
		("minecraft:apple", 0)
	],
	"text": "钻石"
}

# testRecipe 作为示例配方。
# 物品 ID 后面的 0 代表 AuxValue。
# 此处添加两种钻石配方：2 个木棍或 3 个石头合成 1 个钻石。
# 配方请勿超过 6 个物品。
# Vessel 表示容器为碗，PushItem 表示烹饪完成后吐出一个苹果。

def FarmersDelight(self, args):
	factory = serverApi.GetEngineCompFactory()
	mod_attr = factory.CreateModAttr("arris")
	interface = mod_attr.GetAttr("ArrisFarmersDelightInterface")
	if interface:
		interface("CookingPotRecipeList", testRecipe)
		# 添加自定义厨锅配方
```

备注：

- 本示例仅演示添加厨锅烹饪配方。
- 还可以向其他变量添加元素，可用的变量名见 `Api/LegacyModAttr.py` 的白名单，格式见 `Shared/Data/` 下对应的文件。

### ArrisFarmersDelightObtain

获取主包配置表中的字典或列表（返回的就是配置对象本身，修改会直接生效）。

| 参数名   | 数据类型 | 说明               |
| -------- | -------- | ------------------ |
| `target` | `str`    | 需要获取的变量名称 |

示例：

```python
def FarmersDelight(self, args):
	factory = serverApi.GetEngineCompFactory()
	mod_attr = factory.CreateModAttr("arris")
	obtain = mod_attr.GetAttr("ArrisFarmersDelightObtain")
	if obtain:
		canProvideHeatBlockList = obtain("CanProvideHeatBlockList")
		# 获取可以提供火源的方块列表
```

### AddCookingPotRecipe

在已有厨锅配方的基础上添加新配方。获取该接口时使用的属性名为
`ArrisAddCookingPotRecipe`。

| 参数名   | 数据类型 | 说明              |
| -------- | -------- | ----------------- |
| `name`   | `str`    | 对应烹饪食品的 ID |
| `recipe` | `list`   | 需要添加的配方    |

示例：

```python
testRecipe = [
	("minecraft:apple", 0),
	("minecraft:apple", 0),
	("minecraft:apple", 0),
	("minecraft:stick", 0),
	("minecraft:stick", 0)
]

# testRecipe 作为示例配方。
# 物品 ID 后面的 0 代表 AuxValue。
# 此处为蘑菇煲额外添加一种配方：
# 使用 3 个苹果和 2 个木棍合成 1 个蘑菇煲。
# 配方请勿超过 6 个物品。

def FarmersDelight(self, args):
	factory = serverApi.GetEngineCompFactory()
	mod_attr = factory.CreateModAttr("arris")
	addRecipe = mod_attr.GetAttr("ArrisAddCookingPotRecipe")
	if addRecipe:
		addRecipe("minecraft:mushroom_stew", testRecipe)
		# 在原有蘑菇煲配方上新增配方
```

## 追加的内容怎么到客户端

只要在服务端（`LoadServerAddonScriptsAfter`）调用上面的接口，客户端不用做任何事：农夫乐事在玩家进服时把你追加的内容发给他的客户端，之后表又变了会补发。
四个亲手做菜的站点（装了沉浸式交互前置时的砧板、厨锅、煎锅、炉灶）和手持煎锅读的是客户端那一份表，同步之后和服务端认的一样。

- 追加的值请只用 `str`、数字、`bool`、`None`、`list`、`tuple`、`dict`（嵌套字典的键用 `str`）；`(物品名, aux)` 元组当键、当配方里的食材都可以。
  放了别的东西（自定义对象、集合……）的那一条不会同步：服务端照常认，客户端的站点不认，日志里有一行 `[arrisFarmersDelight] 表同步：……`。
- 砧板配方的 `tool` 请照上面的写法用 `obtain("knifeList")` 拿到的列表本身（不要拷一份）：客户端会换成它自己的那一个，之后追加的刀对所有配方一起生效。
- 字典表（`CuttingBoardDict`、`CanCookedFoodDict` 这些）删掉的键也会同步给客户端；名字列表（`knifeList`、`StoveList` 这些）只同步新增，从列表里删名字不会同步。

## 标签（netease_tags，网易 3.10 起）

农夫乐事用网易 3.10 的 `netease_tags` 登记了一套 `common:` 标签词表，见 [docs/TAGS.md](docs/TAGS.md)；
JE 农夫乐事自己的 `farmersdelight:` 标签（菜、饮料、热源、传热……）见 TAGS.md 的「JE 农夫乐事自己的标签（farmersdelight:）」一节。
团队的烹饪原料标签以森罗物语厨房定的 18 个平铺、单数的 `common:` 标签为准（`common:beef`、`common:egg`、`common:mushroom`……，生的熟的都算），
农夫乐事把自己的东西也登记进了这些标签，见 TAGS.md 的「和森罗物语的标签对照」。别的模组在自己行为包的 `netease_tags/` 里
往同名的标签放自己的东西，农夫乐事就认得。下面三件事原来只能靠追加表，现在也能用标签；**原来的表照旧有效，标签是并上去的**：

- **刀**：在自己的 `netease_tags` 里把刀登记进 `common:knife`。物品 JSON 的 `minecraft:tags` 里写 `arris:knife`、往 `knifeList` 追加，都照旧有效。
- **热源方块**：登记进 `farmersdelight:heat_sources`（和 JE 同名）；方块有点燃状态的（状态名是 `lit` / `*:lit`，或者 `extinguished`）
  要点着才给热，没有这类状态的放上去就热，见 TAGS.md。往 `CanProvideHeatBlockList` 追加照旧有效。
  只在别的状态下才热的方块（像盛着熔岩的炼药锅：这个标签里的 `minecraft:cauldron` 只在 `cauldron_liquid` 是 `lava` 时热）用新联动接口登记状态条件：
  `ext.registerHeatSource(方块名, states={...})`（[docs/EXTENSION-API.md](docs/EXTENSION-API.md) §6.1）。写了条件的方块哪里都按条件判，
  在 `CanProvideHeatBlockList` 里的也一样；读这张表的下游请注意，炼药锅不在表里，它热不热要看状态。
- **能煎的生肉**：写一份原版写法的营火配方（配方 JSON 的 `tags` 带 `campfire`）就行，煎锅、炉灶、手持煎锅都认，煎成配方里的东西。
  往 `CanCookedFoodDict` 追加照旧有效（食谱书、JEI 的煎锅 / 炉灶页只列这张表里的）。

## 联动配置

以下变量支持通过 `ArrisFarmersDelightInterface` 添加内容，或通过
`ArrisFarmersDelightObtain` 获取内容：

| 参数名                    | 数据类型 | 说明                                   |
| ------------------------- | -------- | -------------------------------------- |
| `CanCookedFoodDict`       | `dict`   | 可烹饪的物品 ID 及输出物品 ID          |
| `CanProvideHeatBlockList` | `list`   | 可以提供火源的方块列表                 |
| `CuttingBoardDict`        | `dict`   | 可在砧板上切的物品、输出物品及工具列表 |
| `ComposterItemDict`       | `dict`   | 可堆肥的物品和堆肥成功概率             |
| `CookingPotRecipeList`    | `list`   | 厨锅配方                               |
| `StoveList`               | `list`   | 会烤食物的炉灶方块（点燃状态）         |
| `knifeList`               | `list`   | 小刀列表（砧板配方的刀具条目引用它）   |

读 `CookingPotRecipeList` 的请注意两件事（2026-11 起，新接口带来的）：

- **遍历这张表时跳过带 `"Disabled": True` 的行**：那是被删掉的配方（新接口的 `removeRecipe`），行留在表里只是为了不挪动别的行的位置，
  它的 `Recipe` 原样留着，不跳过就会把删掉的配方当成还在。
- **新接口登记的配方 `Recipe` 可能是空列表**（只写了格子 `Slots`、展开不出具体写法的），读的时候别假定至少有一种写法。

各配置项的详细格式请查看 `bp/arrisFarmersDelightScripts/Shared/Data/` 下对应的文件（`Cooking.py`、`Cutting.py`、`Farming.py`、`CookingPotRecipes.py` 等）。
