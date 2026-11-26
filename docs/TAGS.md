# 农夫乐事的标签（netease_tags）

农夫乐事（arrisFarmersDelight）用网易 3.10 的 `netease_tags` 把自己的物品、方块和用到的原版物品、方块登记进一套 `common:` 标签，
JE 农夫乐事自己定义的标签照 JE 的名字登记成 `farmersdelight:` 标签。
别的模组往同名的标签里放自己的东西，引擎会把成员合并，农夫乐事和其他模组就能认出对方的番茄、米、刀、热源。

词表以代码为准：`bp/arrisFarmersDelightScripts/Shared/Data/Tags.py`。`bp/netease_tags/` 下的文件和本文的词表都由 `py -3 tools/gen_tags.py` 从它生成，
`tests/test_netease_tags.py` 核对文件是不是最新、成员是不是真的、和 JE 的标签对不对得上。

## 名字和成员照什么定

**名字照 JE 1.21，成员照 JE 1.20.1。** 名字跟着 NeoForge 和 Fabric 从 1.21 起统一的 `c:` 标签走；成员跟着这边移植的版本走
（Farmer's Delight 1.3.4 / Minecraft 1.20.1，`forge:` 标签）。

- 名字是 `common:` 加 `c:` 名的最后一段，单复数照 JE。`c:` 的写法是"复数的类目 / 单数的名字"：`c:crops/tomato` → `common:tomato`、
  `c:foods/raw_beef` → `common:raw_beef`、`c:tools/knife` → `common:knife`；只有一层的类目名在 JE 里是复数，这边也是：
  `c:crops` → `common:crops`、`c:seeds` → `common:seeds`、`c:bones` → `common:bones`、`c:mushrooms` → `common:mushrooms`。
- 最后一段只是材料名、单拿出来说不清是什么的，照机械动力的写法把类目的单数接在后面：`c:buckets/water` → `common:water_bucket`
  （机械动力的 `c:plates/iron` → `common:iron_plate`、`c:flours/wheat` → `common:wheat_flour` 也是这样来的）。
- JE 没有对应 `c:` 名的，照物品名：`common:rice_panicle`、`common:mutton_chops`、`common:tomato_seeds`。
- JE 农夫乐事自己定义的标签，照 JE 的原名 `farmersdelight:<路径>`：`farmersdelight:heat_sources`、`farmersdelight:meals`……
- 不用 `/` 分层，一个名字只有一段。JE 两个版本的名字（1.20.1 的 `forge:`、1.21 的 `c:`）都列在下面词表里；行为包里照 JE 写的配方 JSON
  用这两种名字都行，农夫乐事会换成这边的名字（[RECIPE-JSON.md](RECIPE-JSON.md)）。
- 成员照 1.20.1，1.21 有两处不同，这边不跟：1.21 的 `c:foods/vegetable` 多了金胡萝卜；`c:foods/raw_fish` 含河豚，
  农夫乐事 1.21 自己的配方用的是去掉河豚的 `c:foods/safe_raw_fish`，和这边的 `common:raw_fish` 一样。

## 别的模组怎么加入

在你自己的行为包里放 `netease_tags/` 目录，一个 JSON 一个标签，`type` 和 `identifier` 和农夫乐事的一样，`items` 里只写你自己的物品：

```json
{
  "type": "item",
  "identifier": "common:tomato",
  "items": ["mymod:tomato"]
}
```

文件名随意，农夫乐事用的是 `item_<标签名，冒号和斜杠换成下划线>.json`。两个模组都登记了 `common:tomato` 时，引擎里这个标签的成员是两边的合起来。

几条规矩：

- 只写你自己的物品和原版物品。写别的模组的物品名，对方没装时引擎会一直往日志里写 ERROR。
- 只写物品名，没有 aux。
- `#标签名` 引用另一个同一类的标签。引原版标签（`#minecraft:egg`）、引别的包用 `netease_tags` 登记的标签（`#common:tomato`），引擎都展开，
  按标签反查、按物品问、配方匹配三处都认；方块标签里的 `#` 也展开（3.10 实机）。不要引只在物品 JSON 里声明的标签：引擎展开这种引用时只拿到经 `netease_tags` 加进去的成员。
- 农夫乐事的文件照 JE 的标签文件写 `#`：JE 用 `#` 引了别的标签、那个标签这边也登记的地方，这边也引。比如 `common:vegetable` 写的是
  `#common:beetroot`、`#common:carrot`、`#common:onion`、`#common:potato`、`#common:tomato`，你把番茄登记进 `common:tomato`，它也就算蔬菜、
  算作物，和 JE 一样（3.10 实机：别的包登记进 `common:tomato` 的番茄，反查 `common:vegetable`、`common:crops` 都有它）。
  下面词表"农夫乐事登记的"一列照文件列（含 `#`）。
- 你自己的物品也可以继续在物品 JSON 的 `minecraft:tags` 里写标签，引擎两种写法都认；原版物品只能用 `netease_tags`。

### 配方里的标签原料

农夫乐事自带的厨锅菜照 JE 按标签认料，砧板切生意面也收 `common:dough` 里的面团，工作台配方里 JE 写标签的格子这边也写标签
（`{"tag": "common:tomato"}` 这种，31 条 JE 配方）：哪几道菜、哪条砧板配方、哪些工作台配方读哪个标签，见下面词表的最后一列。
把你的东西登记进那个标签，它就能进这些配方（工作台配方 3.10 实机：别的包并进同一标签的物品，有序、无序配方都认；31 条配方都在工作台里做过，标签不止一个成员的换着成员各做一次）。
例外：有序的工作台配方里会剩容器的格子写的是具体物品——蛋糕、巧克力派、芝士蛋糕、派皮的奶（奶桶、奶瓶每种摆法一份配方），厨锅配方的水桶，
所以别的模组的奶进不了这四样有序配方；铁锭照团队的写法写 `minecraft:iron_ingot`。你自己的厨锅、砧板配方也可以把一格写成标签，写法见
[EXTENSION-API.md](EXTENSION-API.md) §5（代码里登记）和 [RECIPE-JSON.md](RECIPE-JSON.md) §3（行为包里的配方 JSON）。

### 刀

挂上 `common:knife` 就是刀。农夫乐事的老标签 `arris:knife` 照旧有效（`linkage.md` 教的是在物品 JSON 里写它）。
`linkage.md` 里往 `knifeList` 追加名字的办法也照旧有效。三样任一个说是刀，农夫乐事就当它是刀：砧板上刀切的配方、借刀、插刀，刀杀生物的额外掉落，
刀切蛋糕和派，刀收稻穗，蘑菇菌落，炉灶站点开不开。

### 热源方块

热源照 JE 用农夫乐事自己的方块标签 `farmersdelight:heat_sources`（JE 的森罗物语也把炉灶登记进这个名字）。方块在这个标签里，放在它上面的厨锅、煎锅就会热；
方块有"点没点着"这类状态的要点着才算，和 JE 一样（JE 是"带 LIT 状态的看 LIT"）：状态里有名字是 `lit` 或以 `:lit` 结尾的状态，值为真；
或者有 `extinguished` 状态，值为假。没有这类状态的方块在标签里就算热，比如火、熔岩、岩浆块、农夫乐事点着的炉灶（点着和熄着是两个方块名，登记的是点着的那个）。

JE 的这个标签里还有熔岩炼药锅。基岩版没有这个方块（3.10 实机：`minecraft:lava_cauldron` 放出来的是盛水、0 级的 `minecraft:cauldron`），
熔岩炼药锅是炼药锅盛着熔岩的状态（`cauldron_liquid` = `lava`），标签表达不了，所以这边的标签里没有它，农夫乐事按状态认：
盛着熔岩的炼药锅上面的锅、煎锅会热，站在它旁边能手持煎锅，和 JE 一样。往这个标签里写 `minecraft:lava_cauldron` 不起作用。

手持煎锅"身边有没有热源"只看方块，不看点没点着（和 JE 一样）。
`linkage.md` 里往 `CanProvideHeatBlockList` 追加名字的办法照旧有效。

### 能煎烤什么

煎锅、炉灶、手持煎锅能煎什么，先看农夫乐事的表 `CanCookedFoodDict`（`linkage.md` 可以追加），表里没有的再问引擎的营火配方。
给你的生肉写一份营火配方（配方 JSON 的 `tags` 里带 `campfire`），它就能放到农夫乐事的煎锅、炉灶上煎，煎好是你配方里的东西。
食谱书和 JEI 里"能煎烤的东西"那几页只列表里的。

基岩版的三种蛋（鸡蛋、蓝色鸡蛋、棕色鸡蛋，原版标签 `minecraft:egg` 的成员）一视同仁：都能在煎锅上煎成煎蛋，只煎一面，炉灶站点的烤架不收，
熔炉、烟熏炉、营火也收（JE 只有一种蛋）。工作台配方里 JE 写 `#forge:eggs` 的四样（蛋糕、南瓜派、烤鸡、鸡蛋面团）写的是 `minecraft:egg` 标签，三种蛋都收。

## JE 农夫乐事自己的标签（farmersdelight:）

JE 农夫乐事自己定义的标签，这边照 JE 的名字登记成 `farmersdelight:<路径>`。成员照 JE 的标签文件换成这边的名字；JE 用 `#` 引的标签这边也登记的
照写 `#`（`farmersdelight:heat_sources` 引 `#farmersdelight:tray_heat_sources`；方块标签里的 `#` 引擎也展开，3.10 实机：反查 `heat_sources`
是炉灶、营火、灵魂营火、火、灵魂火、熔岩、流动的熔岩、岩浆块 8 个，营火按方块问同时带 `heat_sources` 和 `tray_heat_sources`），引的是这边没有的（`#minecraft:campfires`、`#farmersdelight:cabinets/wooden`……）展开写成员；只写农夫乐事自己的和原版的东西，JE 里别的模组的可选成员不写（`heat_conductors` 里机械动力的溜槽由机械动力自己登记）。

方块标签有七个。农夫乐事读它们的地方都是"原来的名单 ∪ 标签"：名单原样留着，不在名单里、带了标签的方块也算。
热源的名单 `CanProvideHeatBlockList` 在 `linkage.md` 的接口里，另外六张不在，别的模组要加进来就用标签。

| 标签 | 方块在这个标签里时 | 农夫乐事登记的 |
| --- | --- | --- |
| `farmersdelight:heat_sources` | 放在它上面的厨锅、煎锅会热（有点燃状态的要点着，见上一节） | 岩浆块、炉灶、熔岩、营火、火（JE 还有熔岩炼药锅：基岩版是炼药锅的状态，按状态认） |
| `farmersdelight:heat_conductors` | 厨锅、煎锅下面是它时，再看它下面一格是不是热源 | 漏斗 |
| `farmersdelight:tray_heat_sources` | 放在它上面的厨锅、煎锅画托盘 | 熔岩、营火、火 |
| `farmersdelight:compost_activators` | 有机肥周围 3×3×3 里每有一个，有机肥变成沃土就快一点 | 蘑菇、灰化土、菌丝、有机肥、沃土、沃土耕地、蘑菇菌落 |
| `farmersdelight:unaffected_by_rich_soil` | 长在沃土、沃土耕地上也不被催熟 | 草方块、草、蕨、高花、野生作物、蘑菇菌落等 |
| `farmersdelight:mushroom_colony_growable_on` | 蘑菇菌落在它上面才会长 | 沃土 |
| `farmersdelight:drops_cake_slice` | 拿刀右键：变成少一片的蛋糕，掉一片蛋糕 | 插蜡烛的蛋糕（17 种） |

`drops_cake_slice` 里别的模组的方块被切时不掉蜡烛，也不掉它自己战利品表里的东西（JE 会掉）。

物品标签有十个，农夫乐事自己不读，给别的模组认农夫乐事的东西：`farmersdelight:meals`（饭菜）、`snacks`（小吃）、`sweets`（甜食）、
`drinks`（饮料）、`feasts`（大餐）、`pies`（派）、`wild_crops`（野生作物）、`mushroom_colonies`（蘑菇菌落）、`cabinets`（橱柜）、
`serving_containers`（盛饭菜的容器）。成员见下面的词表，原版的蘑菇煲、蛋糕、南瓜派、碗这些也在里面。
JE 里 `feasts`、`pies`、`wild_crops`、`mushroom_colonies`、`cabinets` 还各有一个同名的方块标签，这边没有登记。
JE 的刀标签 `farmersdelight:tools/knives` 就是这边的 `common:knife`，不另登记。

## 词表

名字怎么来的见开头「名字和成员照什么定」。团队里已经在用的名字照用：`common:crops`、`common:seeds`、`common:flowers`（机械动力附属）、
`common:dough`、`common:wheat_flour`（机械动力），都和那条规则对得上。

- `common:mushrooms` 是能吃的蘑菇（红蘑菇、棕蘑菇），和机械动力的 `common:mushroom_block`（蘑菇方块）不是一回事。
- 小麦粉用机械动力的 `common:wheat_flour`，没有 `common:flour`。
- 鸡蛋用原版自带的 `minecraft:egg`（鸡蛋、蓝色鸡蛋、棕色鸡蛋），不另起。别的模组的蛋登记进它就行：`netease_tags` 的 `identifier` 写
  `minecraft:egg`（3.10 实机：引擎把它并进原版标签，反查、按物品问都有它；工作台自检里蛋那一格放它，蛋糕、南瓜派、烤鸡、鸡蛋面团都做出来了）。
- 农夫乐事没有成员的名字只在下表里列着，不生成文件，别的模组可以往里登记。

<!-- gen_tags: 词表开始（tools/gen_tags.py 从 Shared/Data/Tags.py 生成，别手改） -->
| 标签 | 种类 | 意思 | JE 1.20.1（forge:） | JE 1.21（c:） | 农夫乐事登记的 | 农夫乐事在哪里读 |
| --- | --- | --- | --- | --- | --- | --- |
| `common:tomato` | 物品 | 番茄 | `forge:crops/tomato`、`forge:vegetables/tomato` | `c:crops/tomato`、`c:foods/tomato` | `arris:tomato` | 厨锅的格子：番茄酱、蔬菜杂烩、鱿鱼墨面、烘焙鳕鱼炖（Shared/Data/CookingPotRecipes 的 Slots）；工作台：`arris:bacon_sandwich`、`arris:barbecue_stick`、`arris:gleaming_salad_block_stage0`、`arris:hamburger`、`arris:mixed_salad`、`arris:roasted_mutton_chops`（bp/recipes） |
| `common:tomato_seeds` | 物品 | 番茄种子 | `forge:seeds/tomato` | — | `arris:tomato_seeds` | — |
| `common:rice` | 物品 | 米（也是水稻的种子） | `forge:crops/rice`、`forge:grain/rice`、`forge:seeds/rice` | `c:crops/rice` | `arris:rice` | 厨锅的格子：米饭、炒饭、蘑菇饭、填馅南瓜、狗粮（Shared/Data/CookingPotRecipes 的 Slots） |
| `common:rice_panicle` | 物品 | 稻穗 | — | — | `arris:rice_panicle` | — |
| `common:cooked_rice` | 物品 | 米饭 | `forge:cooked_rice` | `c:foods/cooked_rice` | `arris:cooked_rice` | — |
| `common:dough` | 物品 | 面团 | `forge:dough`、`forge:dough/wheat` | `c:foods/dough`、`c:foods/dough/wheat` | `arris:wheat_dough` | 厨锅的格子：饺子（Shared/Data/CookingPotRecipes 的 Slots）；砧板按标签切成 `arris:raw_pasta`（Shared/Data/Cutting.CuttingTagDict，Shared/Rules/CuttingStation.recipeOf） |
| `common:cooked_egg` | 物品 | 做熟的蛋（煎蛋） | `forge:cooked_eggs` | `c:foods/cooked_egg` | `arris:fried_egg` | 工作台：`arris:bacon_and_eggs`、`arris:egg_sandwich`（bp/recipes） |
| `common:mutton_chops` | 物品 | 生羊排 | — | — | `arris:mutton_chops` | — |
| `common:cooked_mutton_chops` | 物品 | 熟羊排 | — | — | `arris:cooked_mutton_chops` | — |
| `common:knife` | 物品 | 刀 | `forge:tools/knives`、`farmersdelight:tools/knives` | `farmersdelight:tools/knives`、`c:tools/knife` | `arris:flint_knife`、`arris:golden_knife`、`arris:iron_knife`、`arris:diamond_knife`、`arris:netherite_knife` | 是不是刀（Shared/Rules/Knives） |
| `arris:knife` | 物品 | 刀（农夫乐事的老标签，照旧有效） | — | — | `arris:flint_knife`、`arris:golden_knife`、`arris:iron_knife`、`arris:diamond_knife`、`arris:netherite_knife` | 是不是刀（Shared/Rules/Knives） |
| `common:raw_beef` | 物品 | 生牛肉（含牛肉末） | `forge:raw_beef` | `c:foods/raw_beef` | `minecraft:beef`、`arris:minced_beef` | 厨锅的格子：饺子、牛肉炖（Shared/Data/CookingPotRecipes 的 Slots） |
| `common:raw_pork` | 物品 | 生猪肉（含培根） | `forge:raw_pork` | `c:foods/raw_pork` | `minecraft:porkchop`、`#common:raw_bacon` | 厨锅的格子：饺子、南瓜汤、面条汤（Shared/Data/CookingPotRecipes 的 Slots） |
| `common:raw_chicken` | 物品 | 生鸡肉（含鸡块） | `forge:raw_chicken` | `c:foods/raw_chicken` | `minecraft:chicken`、`arris:chicken_cuts` | 厨锅的格子：饺子、鸡肉汤（Shared/Data/CookingPotRecipes 的 Slots） |
| `common:raw_mutton` | 物品 | 生羊肉（含羊排） | `forge:raw_mutton` | `c:foods/raw_mutton` | `minecraft:mutton`、`arris:mutton_chops` | 厨锅的格子：羊排意面（Shared/Data/CookingPotRecipes 的 Slots） |
| `common:raw_meat` | 物品 | 生肉：上面四种和生兔肉 | `forge:raw_meat` | `c:foods/raw_meat` | `minecraft:rabbit`、`#common:raw_beef`、`#common:raw_chicken`、`#common:raw_pork`、`#common:raw_mutton` | 厨锅的格子：卷心菜卷、狗粮（Shared/Data/CookingPotRecipes 的 Slots） |
| `common:cooked_beef` | 物品 | 熟牛肉（含牛肉饼） | `forge:cooked_beef` | `c:foods/cooked_beef` | `minecraft:cooked_beef`、`arris:beef_patty` | 工作台：`arris:stuffed_potato`（bp/recipes） |
| `common:cooked_pork` | 物品 | 熟猪肉（含熟培根） | `forge:cooked_pork` | `c:foods/cooked_pork` | `minecraft:cooked_porkchop`、`#common:cooked_bacon` | — |
| `common:cooked_chicken` | 物品 | 熟鸡肉（含熟鸡块） | `forge:cooked_chicken` | `c:foods/cooked_chicken` | `minecraft:cooked_chicken`、`arris:cooked_chicken_cuts` | 工作台：`arris:chicken_sandwich`（bp/recipes） |
| `common:cooked_mutton` | 物品 | 熟羊肉（含熟羊排） | `forge:cooked_mutton` | `c:foods/cooked_mutton` | `minecraft:cooked_mutton`、`arris:cooked_mutton_chops` | 工作台：`arris:mutton_wrap`、`arris:shepherds_pie_block_stage0`（bp/recipes） |
| `common:cooked_meat` | 物品 | 熟肉：四种熟肉和熟兔肉 | — | `c:foods/cooked_meat` | `minecraft:cooked_rabbit`、`#common:cooked_beef`、`#common:cooked_chicken`、`#common:cooked_pork`、`#common:cooked_mutton` | 工作台：`arris:barbecue_stick`（bp/recipes） |
| `common:raw_fish` | 物品 | 生鱼（含鱼片，不含河豚） | `forge:raw_fishes` | `c:foods/safe_raw_fish`、`c:foods/raw_fish` | `#common:raw_cod`、`#common:raw_salmon`、`minecraft:tropical_fish` | 厨锅的格子：鱿鱼墨面、卷心菜卷、鱼肉炖（Shared/Data/CookingPotRecipes 的 Slots） |
| `common:vegetable` | 物品 | 蔬菜（不含卷心菜） | `forge:vegetables` | `c:foods/vegetable` | `#common:beetroot`、`#common:carrot`、`#common:onion`、`#common:potato`、`#common:tomato` | 厨锅的格子：蔬菜面、蔬菜杂烩、填馅南瓜、卷心菜卷、鸡肉汤（Shared/Data/CookingPotRecipes 的 Slots）；工作台：`arris:kelp_roll`（bp/recipes） |
| `common:cabbage` | 物品 | 卷心菜（含卷心菜叶） | `forge:crops/cabbage` | `c:crops/cabbage`、`c:foods/cabbage` | `arris:cabbage`、`arris:cabbage_leaf` | 厨锅的格子：饺子、卷心菜卷（Shared/Data/CookingPotRecipes 的 Slots）；工作台：`arris:grilled_salmon`（bp/recipes） |
| `common:leafy_green` | 物品 | 沙拉用的叶菜（JE 的 salad_ingredients） | `forge:salad_ingredients`、`forge:salad_ingredients/cabbage` | `c:foods/leafy_green` | `#common:cabbage` | 厨锅的格子：蔬菜面、鸡肉汤、蔬菜汤、南瓜汤（Shared/Data/CookingPotRecipes 的 Slots）；工作台：`arris:bacon_sandwich`、`arris:chicken_sandwich`、`arris:hamburger`、`arris:mixed_salad`、`arris:mutton_wrap`（bp/recipes） |
| `common:milk` | 物品 | 奶（奶桶、奶瓶） | `forge:milk` | `c:drinks/milk` | `minecraft:milk_bucket`、`arris:milk_bottle` | 厨锅的格子：南瓜汤、洋葱汤、热可可、发光浆果蛋奶沙司（Shared/Data/CookingPotRecipes 的 Slots）；工作台：`arris:shepherds_pie_block_stage0`、`arris:stuffed_potato`（bp/recipes） |
| `common:mushrooms` | 物品 | 能吃的蘑菇 | `forge:mushrooms` | `c:mushrooms` | `minecraft:brown_mushroom`、`minecraft:red_mushroom` | 厨锅的格子：蔬菜面、卷心菜卷、大骨汤（Shared/Data/CookingPotRecipes 的 Slots） |
| `common:onion` | 物品 | 洋葱 | `forge:crops/onion`、`forge:vegetables/onion` | `c:crops/onion`、`c:foods/onion` | `arris:onion` | 厨锅的格子：炒饭、饺子、蔬菜杂烩、填馅南瓜、鱼肉炖、洋葱汤（Shared/Data/CookingPotRecipes 的 Slots）；工作台：`arris:barbecue_stick`、`arris:grilled_salmon`、`arris:hamburger`、`arris:mutton_wrap`、`arris:roast_chicken_block_stage0`、`arris:shepherds_pie_block_stage0`、`arris:steak_and_potatoes`（bp/recipes） |
| `common:carrot` | 物品 | 胡萝卜 | `forge:crops/carrot`、`forge:vegetables/carrot` | `c:crops/carrot` | `minecraft:carrot` | 厨锅的格子：兔肉煲、炒饭、蔬菜面、牛肉炖、鸡肉汤、蔬菜汤（Shared/Data/CookingPotRecipes 的 Slots）；工作台：`arris:chicken_sandwich`、`arris:roast_chicken_block_stage0`（bp/recipes） |
| `common:potato` | 物品 | 土豆 | `forge:crops/potato`、`forge:vegetables/potato` | `c:crops/potato` | `minecraft:potato` | 厨锅的格子：兔肉煲、填馅南瓜、牛肉炖、蔬菜汤、烘焙鳕鱼炖（Shared/Data/CookingPotRecipes 的 Slots） |
| `common:beetroot` | 物品 | 甜菜根 | `forge:crops/beetroot`、`forge:vegetables/beetroot` | `c:crops/beetroot` | `minecraft:beetroot` | 厨锅的格子：甜菜汤、蔬菜杂烩、蔬菜汤（Shared/Data/CookingPotRecipes 的 Slots）；工作台：`arris:gleaming_salad_block_stage0`、`arris:mixed_salad`、`arris:roasted_mutton_chops`（bp/recipes） |
| `common:wheat` | 物品 | 小麦 | `forge:crops/wheat`、`forge:grain/wheat` | `c:crops/wheat` | `minecraft:wheat` | 工作台：`arris:apple_pie_item`、`minecraft:cake`、`arris:honey_cookie`、`arris:pie_crust`、`arris:sweet_berry_cookie`、`arris:wheat_dough`（bp/recipes） |
| `common:bread` | 物品 | 面包 | `forge:bread`、`forge:bread/wheat` | `c:foods/bread` | `minecraft:bread` | 厨锅的格子：洋葱汤（Shared/Data/CookingPotRecipes 的 Slots）；工作台：`arris:bacon_sandwich`、`arris:chicken_sandwich`、`arris:egg_sandwich`、`arris:hamburger`、`arris:mutton_wrap`（bp/recipes） |
| `common:pasta` | 物品 | 生意面 | `forge:pasta`、`forge:pasta/raw_pasta` | `c:foods/pasta` | `arris:raw_pasta` | 厨锅的格子：肉丸意面、羊排意面、蔬菜面、鱿鱼墨面、面条汤（Shared/Data/CookingPotRecipes 的 Slots） |
| `common:berry` | 物品 | 浆果 | `forge:berries` | `c:foods/berry` | `minecraft:sweet_berries`、`minecraft:glow_berries` | 厨锅的格子：填馅南瓜（Shared/Data/CookingPotRecipes 的 Slots）；工作台：`arris:fruit_salad`（bp/recipes） |
| `common:bones` | 物品 | 骨头 | `forge:bones` | `c:bones` | `minecraft:bone` | 厨锅的格子：大骨汤（Shared/Data/CookingPotRecipes 的 Slots） |
| `common:raw_cod` | 物品 | 生鳕鱼（含鱼片） | `forge:raw_fishes/cod` | `c:foods/raw_cod` | `minecraft:cod`、`arris:cod_slice` | 厨锅的格子：烘焙鳕鱼炖（Shared/Data/CookingPotRecipes 的 Slots） |
| `common:raw_salmon` | 物品 | 生鲑鱼（含鱼片） | `forge:raw_fishes/salmon` | `c:foods/raw_salmon` | `minecraft:salmon`、`arris:salmon_slice` | — |
| `common:cooked_fish` | 物品 | 熟鱼（含熟鱼片） | `forge:cooked_fishes` | `c:foods/cooked_fish` | `#common:cooked_cod`、`#common:cooked_salmon` | 工作台：`arris:barbecue_stick`（bp/recipes） |
| `common:cooked_cod` | 物品 | 熟鳕鱼（含熟鱼片） | `forge:cooked_fishes/cod` | `c:foods/cooked_cod` | `minecraft:cooked_cod`、`arris:cooked_cod_slice` | — |
| `common:cooked_salmon` | 物品 | 熟鲑鱼（含熟鱼片） | `forge:cooked_fishes/salmon` | `c:foods/cooked_salmon` | `minecraft:cooked_salmon`、`arris:cooked_salmon_slice` | 工作台：`arris:grilled_salmon`（bp/recipes） |
| `common:raw_bacon` | 物品 | 生培根 | `forge:raw_bacon` | `c:foods/raw_bacon` | `arris:bacon` | — |
| `common:cooked_bacon` | 物品 | 熟培根 | `forge:cooked_bacon` | `c:foods/cooked_bacon` | `arris:cooked_bacon` | 工作台：`arris:bacon_sandwich`（bp/recipes） |
| `common:cabbage_seeds` | 物品 | 卷心菜种子 | `forge:seeds/cabbage` | — | `arris:cabbage_seeds` | — |
| `common:water_bucket` | 物品 | 水桶 | `forge:buckets/water` | `c:buckets/water` | `minecraft:water_bucket` | — |
| `common:crops` | 物品 | 作物（团队已有的名字；原版的那部分 JE 里是 Forge 给的，这边也登记） | `forge:crops` | `c:crops` | `#common:cabbage`、`#common:onion`、`#common:rice`、`#common:tomato`、`#common:beetroot`、`#common:carrot`、`minecraft:nether_wart`、`#common:potato`、`#common:wheat` | — |
| `common:seeds` | 物品 | 种子（团队已有的名字；同上） | `forge:seeds` | `c:seeds` | `#common:cabbage_seeds`、`#common:rice`、`#common:tomato_seeds`、`minecraft:beetroot_seeds`、`minecraft:melon_seeds`、`minecraft:pumpkin_seeds`、`minecraft:wheat_seeds` | — |
| `common:flowers` | 物品 | 花（团队已有的名字） | `minecraft:flowers` | `minecraft:flowers` | `arris:wild_carrots`、`arris:wild_potatoes`、`arris:wild_beetroots`、`arris:wild_cabbages`、`arris:wild_tomatoes`、`arris:wild_onions`、`arris:wild_rice` | — |
| `farmersdelight:meals` | 物品 | 饭菜（盛在碗里的一份；原版的蘑菇煲、甜菜汤、兔肉煲也算） | `farmersdelight:meals` | `farmersdelight:meals` | `minecraft:mushroom_stew`、`minecraft:beetroot_soup`、`minecraft:rabbit_stew`、`arris:mixed_salad`、`arris:cooked_rice`、`arris:bone_broth`、`arris:cookbeef_stew`、`arris:vegetable_soup`、`arris:fish_stew`、`arris:chicken_soup`、`arris:fried_rice`、`arris:pumpkin_soup`、`arris:baked_cod_stew`、`arris:noodle_soup`、`arris:onion_soup`、`arris:bacon_and_eggs`、`arris:ratatouille`、`arris:steak_and_potatoes`、`arris:pasta_with_meatballs`、`arris:pasta_with_mutton_chop`、`arris:mushroom_rice`、`arris:roasted_mutton_chops`、`arris:vegetable_noodles`、`arris:squid_ink_pasta`、`arris:grilled_salmon`、`arris:roast_chicken`、`arris:stuffed_pumpkin`、`arris:honey_glazed_ham`、`arris:shepherds_pie`、`arris:gleaming_salad` | — |
| `farmersdelight:snacks` | 物品 | 小吃（三明治、汉堡、卷、饺子……） | `farmersdelight:snacks` | `farmersdelight:snacks` | `arris:barbecue_stick`、`arris:egg_sandwich`、`arris:chicken_sandwich`、`arris:hamburger`、`arris:bacon_sandwich`、`arris:mutton_wrap`、`arris:dumplings`、`arris:stuffed_potato`、`arris:cabbage_rolls`、`arris:salmon_roll`、`arris:cod_roll`、`arris:kelp_roll`、`arris:kelp_roll_slice` | — |
| `farmersdelight:sweets` | 物品 | 甜食（蛋糕、曲奇、派的切片、冰棍……） | `farmersdelight:sweets` | `farmersdelight:sweets` | `minecraft:cake`、`minecraft:cookie`、`arris:cake_slice`、`arris:apple_pie_slice`、`arris:sweet_berry_cheesecake_slice`、`arris:chocolate_pie_slice`、`arris:pumpkin_pie_slice`、`arris:sweet_berry_cookie`、`arris:honey_cookie`、`arris:melon_popsicle`、`arris:glow_berry_custard`、`arris:fruit_salad` | — |
| `farmersdelight:drinks` | 物品 | 饮料（瓶装的） | `farmersdelight:drinks` | `farmersdelight:drinks` | `arris:milk_bottle`、`arris:apple_cider`、`arris:melon_juice`、`arris:hot_cocoa` | — |
| `farmersdelight:feasts` | 物品 | 大餐（放在地上、一份一份盛出来的那几样） | `farmersdelight:feasts` | `farmersdelight:feasts` | `arris:roast_chicken_block_stage0`、`arris:stuffed_pumpkin_block_stage0`、`arris:shepherds_pie_block_stage0`、`arris:honey_glazed_ham_block_stage0`、`arris:gleaming_salad_block_stage0`、`arris:rice_roll_medley_block_stage0` | — |
| `farmersdelight:pies` | 物品 | 派（原版的南瓜派也算） | `farmersdelight:pies` | `farmersdelight:pies` | `minecraft:pumpkin_pie`、`arris:apple_pie_item`、`arris:sweet_berry_cheesecake_item`、`arris:chocolate_pie_item` | — |
| `farmersdelight:wild_crops` | 物品 | 野生作物 | `farmersdelight:wild_crops` | `farmersdelight:wild_crops` | `arris:wild_carrots`、`arris:wild_potatoes`、`arris:wild_beetroots`、`arris:wild_cabbages`、`arris:wild_tomatoes`、`arris:wild_onions`、`arris:wild_rice` | — |
| `farmersdelight:mushroom_colonies` | 物品 | 蘑菇菌落 | `farmersdelight:mushroom_colonies` | `farmersdelight:mushroom_colonies` | `arris:brown_mushroom_colony`、`arris:red_mushroom_colony` | — |
| `farmersdelight:cabinets` | 物品 | 橱柜 | `farmersdelight:cabinets` | `farmersdelight:cabinets` | `arris:oak_cabinet`、`arris:spruce_cabinet`、`arris:birch_cabinet`、`arris:jungle_cabinet`、`arris:acacia_cabinet`、`arris:dark_oak_cabinet`、`arris:mangrove_cabinet`、`arris:cherry_cabinet`、`arris:bamboo_cabinet`、`arris:crimson_cabinet`、`arris:warped_cabinet` | — |
| `farmersdelight:serving_containers` | 物品 | 盛饭菜的容器（碗、玻璃瓶、桶） | `farmersdelight:serving_containers` | `farmersdelight:serving_containers` | `minecraft:bowl`、`minecraft:glass_bottle`、`minecraft:bucket` | — |
| `farmersdelight:heat_sources` | 方块 | 热源：给上面的锅 / 煎锅加热（有点燃状态的要点着） | `farmersdelight:heat_sources` | `farmersdelight:heat_sources` | `minecraft:magma`、`arris:stove`、`#farmersdelight:tray_heat_sources` | 热源（Shared/Rules/HeatSources；锅底下的有点燃状态要点着，手持煎锅身边的不看） |
| `farmersdelight:heat_conductors` | 方块 | 把热传给上面一格的方块 | `farmersdelight:heat_conductors` | `farmersdelight:heat_conductors` | `minecraft:hopper` | 锅 / 煎锅下面是它时看再下面一格（HeatSources.conducts） |
| `farmersdelight:tray_heat_sources` | 方块 | 锅 / 煎锅放在上面要画托盘的方块 | `farmersdelight:tray_heat_sources` | `farmersdelight:tray_heat_sources` | `minecraft:lava`、`minecraft:flowing_lava`、`minecraft:campfire`、`minecraft:soul_campfire`、`minecraft:fire`、`minecraft:soul_fire` | 锅 / 煎锅画不画托盘（Server/Helpers/Heat.RefreshHeat） |
| `farmersdelight:compost_activators` | 方块 | 有机肥周围的催化剂 | `farmersdelight:compost_activators` | `farmersdelight:compost_activators` | `minecraft:brown_mushroom`、`minecraft:red_mushroom`、`minecraft:podzol`、`minecraft:mycelium`、`arris:organic_compost_stage0`、`arris:organic_compost_stage1`、`arris:organic_compost_stage2`、`arris:organic_compost_stage3`、`arris:rich_soil`、`arris:rich_soil_farmland`、`arris:rich_soil_farmland_moist`、`arris:brown_mushroom_colony`、`arris:red_mushroom_colony` | 有机肥堆沤的概率（Server/OrganicCompost） |
| `farmersdelight:unaffected_by_rich_soil` | 方块 | 沃土不催熟的植物 | `farmersdelight:unaffected_by_rich_soil` | `farmersdelight:unaffected_by_rich_soil` | `minecraft:grass_block`、`minecraft:moss_block`、`minecraft:crimson_nylium`、`minecraft:warped_nylium`、`minecraft:short_grass`、`minecraft:tall_grass`、`minecraft:fern`、`minecraft:large_fern`、`minecraft:twisting_vines`、`minecraft:big_dripleaf`、`minecraft:pink_petals`、`minecraft:sunflower`、`minecraft:lilac`、`minecraft:rose_bush`、`minecraft:peony`、`minecraft:pitcher_plant`、`arris:sandy_shrub`、`arris:brown_mushroom_colony`、`arris:red_mushroom_colony`、`arris:wild_carrots`、`arris:wild_potatoes`、`arris:wild_beetroots`、`arris:wild_cabbages`、`arris:wild_tomatoes`、`arris:wild_onions`、`arris:wild_rice` | 沃土 / 沃土耕地催不催熟上面的植物（Server/BoneMeal.BoostPlant） |
| `farmersdelight:mushroom_colony_growable_on` | 方块 | 蘑菇菌落在它上面才长 | `farmersdelight:mushroom_colony_growable_on` | `farmersdelight:mushroom_colony_growable_on` | `arris:rich_soil` | 蘑菇菌落长不长（Server/MushroomColony） |
| `farmersdelight:drops_cake_slice` | 方块 | 拿刀右键切得下一片蛋糕的方块（插蜡烛的蛋糕） | `farmersdelight:drops_cake_slice` | `farmersdelight:drops_cake_slice` | `minecraft:candle_cake`、`minecraft:white_candle_cake`、`minecraft:orange_candle_cake`、`minecraft:magenta_candle_cake`、`minecraft:light_blue_candle_cake`、`minecraft:yellow_candle_cake`、`minecraft:lime_candle_cake`、`minecraft:pink_candle_cake`、`minecraft:gray_candle_cake`、`minecraft:light_gray_candle_cake`、`minecraft:cyan_candle_cake`、`minecraft:purple_candle_cake`、`minecraft:blue_candle_cake`、`minecraft:brown_candle_cake`、`minecraft:green_candle_cake`、`minecraft:red_candle_cake`、`minecraft:black_candle_cake` | 拿刀右键切蛋糕（Server/KnifeSlicing.cutsLikeACake） |
| `minecraft:egg` | 物品（原版自带，不生成文件） | 蛋（原版自带的标签） | `forge:eggs` | `c:eggs` | `minecraft:egg`、`minecraft:blue_egg`、`minecraft:brown_egg` | 厨锅的格子：炒饭、烘焙鳕鱼炖、面条汤、发光浆果蛋奶沙司（Shared/Data/CookingPotRecipes 的 Slots）；工作台：`minecraft:cake`、`minecraft:pumpkin_pie`、`arris:roast_chicken_block_stage0`、`arris:wheat_dough`（bp/recipes） |
| `common:fruit` | 物品（农夫乐事没有成员，不生成文件） | 水果 | — | — | — | — |
| `common:wheat_flour` | 物品（农夫乐事没有成员，不生成文件） | 小麦粉（机械动力的） | — | — | — | — |
<!-- gen_tags: 词表结束 -->

## 限制

- 要网易 3.10 以上。3.10 以前没有 `netease_tags`，农夫乐事只认自己的东西和物品 JSON 里声明的标签，和以前一样。
- 没有 aux：同一个物品名的不同 aux 是同一组标签。
- 客户端的标签要到进世界的过程中才全（实机，单人游戏：客户端脚本加载完时原版物品还查不到标签，两秒多以后才全；联机时远端客户端要多久
  没有量过）。农夫乐事在这之前按自己的词表答，别的模组的东西这时候可能还认不出来，进世界之后就认了。服务端从一开始就是全的。
  客户端能用的查询（3.10 实机）：`LookupItemsByItemTag`、`LookupBlocksByBlockTag`、`GetItemTags`、`CreateRecipe(levelId).GetRecipesByInput`；
  按方块问的 `GetBlockTags` 只有服务端有。
- 进世界时引擎日志里会有一批 `netease_tags: apply item tag ...: item ... not found`，是引擎在原版物品注册之前先挂了一遍，之后查得到，不是名字写错了。
  名字真写错了的，这条日志会一直出现。
- 营火配方的返回值只在 3.10 上量过（2026-11-26，两端一样）：`GetRecipesByInput(名字, "campfire", aux, 1)` 返回一个列表，每条是
  `{"input": 原料名, "output": 产物名}`，比如生牛肉 → `[{'input': 'minecraft:beef', 'output': 'minecraft:cooked_beef'}]`。
  农夫乐事照这个读，也认别的写法（`result`、带 aux 的名字、字典），留着给别的版本；认不出来的就当没有这条配方。
- 方块的状态只有服务端读得到：客户端判断热源时不看点没点着。
- 原版方块要先登记右键事件，拿刀右键时才切得到。农夫乐事只登记了蛋糕和插蜡烛的蛋糕，所以 `farmersdelight:drops_cake_slice`
  里再加原版方块不起作用；别的模组的自定义方块不用登记。
