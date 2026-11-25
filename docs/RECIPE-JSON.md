# 配方 JSON（行为包里的 farmersdelight_recipes/）

不写 Python 也能给农夫乐事加配方：在你自己的行为包根下建 `farmersdelight_recipes/` 目录，放配方 JSON。
写法就是 JE 农夫乐事的配方 JSON，物品名换成网易版的、标签写农夫乐事词表里的 `common:` 名（JE 的标签名也认，见 §3）：
把 JE 的配方文件改改物品名就能用。代码里登记用的是同一种写法（`ext.recipes.registerFromJson`、Builder 的 `toJson()`，见 [EXTENSION-API.md](EXTENSION-API.md) §5）。

> 能力名 `recipe_json_files`（服务端）。跨行为包读文件用的是引擎内部的 `server_resource`（和机械动力的 `create_recipes/` 同一条路），
> 2026-11-26 在游戏里核过：另一个行为包里不写 `id`、带注释的配方 JSON 开服时读到了，按路径派生了 ID，登记上了。

---

## 1. 放在哪、配方 ID 怎么定

```text
mymod_bp/
└── farmersdelight_recipes/
    └── mymod/                      ← 第一层目录 = 配方 ID 的命名空间
        ├── cooking/
        │   └── tomato_stew.json    → mymod:cooking/tomato_stew
        └── cutting/
            └── tofu.json           → mymod:cutting/tofu
```

- 一个 `.json` 文件一条配方，`farmersdelight_recipes/` 下面的目录怎么分随你。
- 配方 ID：文件里写了 `"id"` 就用它；没写按路径，`farmersdelight_recipes/<命名空间>/<其余>.json` → `<命名空间>:<其余>`。
  直接放在 `farmersdelight_recipes/` 下、又没写 `"id"` 的文件不收（不知道算谁的）。ID 的规矩和代码登记一样（EXTENSION-API.md §5.2）：
  用你自己的命名空间；`farmersdelight:` 只能覆盖农夫乐事已有的配方；`legacy:` 不能用。
- 可以写 `//` 和 `/* */` 注释，文件用 UTF-8。
- 读的时机：ready 广播之后（EXTENSION-API.md §1.3 的 T4），所以别的模组在 ready 里用代码登记的同 ID 配方会被文件覆盖。
  全部行为包的文件按路径排好序一个一个读；同一个 ID 写了两份时后读的覆盖先读的（别这么写）。
- 读不进来的文件，每个在日志里写一行，不耽误别的文件：

  ```text
  [arrisFarmersDelight] 行为包里的配方 farmersdelight_recipes/mymod/cooking/bad.json 没有登记：invalid_recipe message=result 要写成 {"item": 物品名}，给的是 None
  ```

  原因是错误码加说明：`invalid_json`（不是 JSON）、`no_id`（没 ID）、或者代码登记时的错误码（EXTENSION-API.md §4）。

---

## 2. 厨锅 `farmersdelight:cooking`

```json
{
  "type": "farmersdelight:cooking",
  "ingredients": [
    {"tag": "common:tomato"},
    {"tag": "common:tomato"},
    [{"item": "mymod:tofu"}, {"tag": "common:raw_beef"}]
  ],
  "result": {"item": "mymod:tomato_stew"},
  "container": {"item": "minecraft:bowl"},
  "cookingtime": 200,
  "experience": 1.0
}
```

| 键 | 必填 | 说明 |
| --- | --- | --- |
| `type` | 是 | `"farmersdelight:cooking"`（`"cooking"` 也认） |
| `ingredients` | 是 | 1 到 6 个配料，一个是一格（写法见 §3）；锅里每件东西要分给一个收它的格，格子正好用完才配得上 |
| `result` | 是 | `{"item": 物品名, "count": 一份出几个, "data": aux}`，`count`、`data` 可不写（1、0）；也可以直接写物品名字符串 |
| `container` | 否 | 盛这道菜要的容器 `{"item": 物品名}`。不写时照 JE 推：成品有合成剩余物（农夫乐事的剩余物表 `Shared/Data/Remainders.py`：碗装的菜剩碗、饮料剩玻璃瓶、奶桶剩桶……）就要它，没有就不要容器；别的模组的成品不在那张表里，要容器就写明 |
| `cookingtime` | 否 | 一份煮多少刻（20 刻一秒），不写是 200 |
| `experience` | 否 | 一份给多少经验，不写是 0（JE 的缺省） |
| `text` | 否 | 农夫乐事加的：经典厨锅界面食谱格里的名字，不写是成品的物品名 |
| `id` | 否 | 配方 ID（§1） |

JE 的 `recipe_book_tab` 这类键不管。几条配方都配得上同一锅东西时，表里靠前的赢（农夫乐事自己的在最前）。

---

## 3. 配料的写法

| 写法 | 意思 |
| --- | --- |
| `{"item": "mymod:tofu"}` | 这样物品（aux 0） |
| `{"item": "minecraft:dye", "data": 4}` | 这样物品、这个 aux |
| `{"tag": "common:tomato"}` | 现在带这个标签的任何物品（标签没有 aux） |
| `[配料, 配料, ...]` | 这一格的几个选项，任一个都行 |
| `"mymod:tofu"`、`"#common:tomato"` | 字符串的简写，同上面两种 |

- 标签写农夫乐事词表里的 `common:` 名（[TAGS.md](TAGS.md)）。JE 农夫乐事、Forge 的标签名（`forge:raw_beef`、`forge:vegetables/tomato`……）
  按 TAGS.md 的对照表自动换成 `common:` 名，认不出的标签名原样用（可能是别的模组登记的标签）。
- 一个标签此刻一个成员都没有时，那一格什么都不收，这条配方配不上；不报错。
- 原版的蛋写 `{"tag": "minecraft:egg"}`（普通、蓝色、棕色三种都收）；JE 的 `forge:eggs` 也换成它。

---

## 4. 砧板 `farmersdelight:cutting`

```json
{
  "type": "farmersdelight:cutting",
  "ingredients": [{"item": "mymod:tofu_block"}],
  "tool": {"type": "farmersdelight:tool_action", "action": "knife_dig"},
  "result": [
    {"item": "mymod:tofu", "count": 4},
    {"item": "mymod:okara", "chance": 0.5}
  ]
}
```

| 键 | 必填 | 说明 |
| --- | --- | --- |
| `type` | 是 | `"farmersdelight:cutting"`（`"cutting"` 也认） |
| `ingredients` | 是 | 正好一个配料，一样物品或一个标签（不能是几个选项）。一样原料只能有一条砧板配方 |
| `tool` | 是 | 用什么工具切，见下表；可以是几个的列表，认第一个认得出的动作或标签，都没有就是列出的物品 |
| `result` | 是 | 1 到 4 个产物 `{"item", "count", "data", "chance"}`；`chance` 是 0 到 1 的概率，不写是必出 |

| `tool` 的写法 | 意思 |
| --- | --- |
| `{"type": "farmersdelight:tool_action", "action": "knife_dig"}`、`{"tag": "forge:tools/knives"}`、`{"tag": "common:knife"}` | 刀：农夫乐事认作刀的东西都行（`knifeList`、带 `common:knife` 或 `arris:knife` 标签的） |
| `"action": "axe_dig"` / `"axe_strip"`、`{"tag": "minecraft:axes"}` | 斧：原版的斧、物品类型是斧的 |
| `"action": "pickaxe_dig"`、`{"tag": "minecraft:pickaxes"}` | 镐 |
| `"action": "shovel_dig"`、`{"tag": "minecraft:shovels"}` | 锹 |
| `"action": "hoe_dig"`、`{"tag": "minecraft:hoes"}` | 锄 |
| `"action": "shears_dig"`、`{"tag": "forge:shears"}` | 剪刀：原版剪刀、物品类型是剪刀的 |
| `{"item": "mymod:saw"}`（或几个） | 只认列出的这几样 |

---

## 5. 营火烹饪 `minecraft:campfire_cooking`

```json
{
  "type": "minecraft:campfire_cooking",
  "ingredient": {"item": "mymod:tofu"},
  "result": "mymod:grilled_tofu"
}
```

煎锅、炉灶、手持煎锅读的"能煎烤什么"：一样物品煎成一样物品。`ingredient` 只能是物品（不收标签），`result` 写物品名或 `{"item": 物品名}`；
JE 的 `experience`、`cookingtime` 不管（煎锅、炉灶的时间是它们自己的）。一样原料只有一条。

这里登记的和原版的营火配方是两回事：煎锅、炉灶先查这里，查不到再问引擎的营火配方（配方 JSON 的 `tags` 带 `campfire` 的），所以给自己的生肉写一份原版的
营火配方也能煎。登记在这里的好处是食谱书、JEI 的煎锅 / 炉灶页会列出它。

---

## 6. 从 JE 搬一份

JE 农夫乐事（1.20.1）的 `data/farmersdelight/recipes/cooking/beef_stew.json`：

```json
{
  "type": "farmersdelight:cooking",
  "cookingtime": 200,
  "experience": 1.0,
  "ingredients": [{"tag": "forge:raw_beef"}, {"tag": "forge:crops/carrot"}, {"tag": "forge:crops/potato"}],
  "recipe_book_tab": "meals",
  "result": {"item": "farmersdelight:beef_stew"}
}
```

照它给你自己的一道菜写一份：标签名不用改（会自动换成 `common:raw_beef`、`common:carrot`、`common:potato`），配料、成品换成你的，给它一个你的 ID。
JE 的文件常常不写 `container`（JE 用成品物品的合成剩余物：碗装的菜就要碗），这边同样推，但只认得农夫乐事那张剩余物表（§2）：
你自己的成品不在表里，要容器就写明。

```json
{
  "id": "mymod:cooking/venison_stew",
  "type": "farmersdelight:cooking",
  "container": {"item": "minecraft:bowl"},
  "cookingtime": 200,
  "experience": 1.0,
  "ingredients": [{"item": "mymod:venison"}, {"tag": "forge:crops/carrot"}, {"tag": "forge:crops/potato"}],
  "result": {"item": "mymod:venison_stew"}
}
```

要改农夫乐事自带的那一道，用它的 ID（`farmersdelight:cooking/beef_stew`）覆盖：照搬上面 JE 那份、成品写 `arris:cookbeef_stew`，
不写 `container` 也会推出碗（牛肉炖在剩余物表里）。
