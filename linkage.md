# 棱花 Arris 农夫乐事联动接口文档

作者：Lovely\_小柒丫

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
四个亲手做菜的站点（装了场景交互前置时的砧板、厨锅、煎锅、炉灶）和手持煎锅读的是客户端那一份表，同步之后和服务端认的一样。

- 追加的值请只用 `str`、数字、`bool`、`None`、`list`、`tuple`、`dict`（嵌套字典的键用 `str`）；`(物品名, aux)` 元组当键、当配方里的食材都可以。
  放了别的东西（自定义对象、集合……）的那一条不会同步：服务端照常认，客户端的站点不认，日志里有一行 `[arrisFarmersDelight] 表同步：……`。
- 砧板配方的 `tool` 请照上面的写法用 `obtain("knifeList")` 拿到的列表本身（不要拷一份）：客户端会换成它自己的那一个，之后追加的刀对所有配方一起生效。
- 只同步新增和改动，从表里删东西不会同步。

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

各配置项的详细格式请查看 `bp/arrisFarmersDelightScripts/Shared/Data/` 下对应的文件（`Cooking.py`、`Cutting.py`、`Farming.py`、`CookingPotRecipes.py` 等）。
