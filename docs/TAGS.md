# 农夫乐事的标签（netease_tags）

农夫乐事（arrisFarmersDelight）用网易 3.10 的 `netease_tags` 把自己的物品、方块和用到的原版物品、方块登记进一套 `common:` 标签，
JE 农夫乐事自己定义的标签照 JE 的名字登记成 `farmersdelight:` 标签。
别的模组往同名的标签里放自己的东西，引擎会把成员合并，农夫乐事和其他模组就能认出对方的番茄、米、刀、热源。

词表以代码为准：`bp/arrisFarmersDelightScripts/Shared/Data/Tags.py`。`bp/netease_tags/` 下的文件和本文的词表都由 `py -3 tools/gen_tags.py` 从它生成，
`tests/test_netease_tags.py` 核对文件是不是最新、成员是不是真的、和 JE 的标签对不对得上。

## 名字和成员照什么定

**团队的烹饪原料标签以森罗物语厨房定的 18 个为准。** 森罗物语厨房网易版 2026-11-26 的提交 `2df8e1c` 在它的行为包里登记了 18 个物品标签，
名字平铺、单数：`common:beef`、`chicken`、`chili`、`dough`、`egg`、`fish`、`flour`、`lamb`、`lettuce`、`meat`、`meatball`、`mushroom`、`noodle`、
`pork`、`rice`、`seed`、`tomato`、`vegetable`，它的汤锅、炒锅的模糊配方按这些标签收料。这些是"粗"的类：生的熟的都算（`common:beef` 里有生牛肉、
熟牛肉、生熟牛杂），`common:egg` 里有三种鸡蛋、海龟蛋、嗅探兽蛋和煎蛋。同一个概念用规范的名字；农夫乐事的东西照 JE 登记进对应的粗标签，
两个模组就能用对方的原料（下面「和森罗物语的标签对照」）。

**农夫乐事另有按 JE 配方需要的细标签：名字照 JE 1.21，成员照 JE 1.20.1。** JE 农夫乐事的配方把生的熟的分开、牛猪鸡羊分开，
这边的厨锅、工作台、砧板照 JE 读这些细标签，不读粗标签；鸡蛋格子照旧读原版的 `minecraft:egg`（规范的 `common:egg` 里有海龟蛋和煎蛋，不能拿来做蛋糕）。
细标签的名字跟着 NeoForge 和 Fabric 从 1.21 起统一的 `c:` 标签走；成员跟着这边移植的版本走（Farmer's Delight 1.3.4 / Minecraft 1.20.1，`forge:` 标签）。

- **`common:` 物品标签一律单数**（团队 2026-11-26 定：模组的 `common:` 物品标签都用单数）。例外只有照 JE 原名的 `farmersdelight:` 标签
  （`farmersdelight:heat_sources`、`farmersdelight:meals`……是 JE 的标识符，照抄才对得上 JE 的数据）；物品名、方块名本身不改（`arris:cabbage_seeds` 还是这个名字）。
- 名字是 `common:` 加 `c:` 名的最后一段。`c:` 的写法是"复数的类目 / 单数的名字"：`c:crops/tomato` → `common:tomato`、
  `c:foods/raw_beef` → `common:raw_beef`、`c:tools/knife` → `common:knife`；只有一层的类目名在 JE 里是复数，这边写单数：
  `c:bones` → `common:bone`、`c:mushrooms` → `common:mushroom`、`c:crops` → `common:crop`、`c:seeds` → `common:seed`。
- 最后一段只是材料名、单拿出来说不清是什么的，照机械动力的写法把类目的单数接在后面：`c:buckets/water` → `common:water_bucket`
  （机械动力的 `c:plates/iron` → `common:iron_plate`、`c:flours/wheat` → `common:wheat_flour` 也是这样来的）。
- JE 没有对应 `c:` 名的，照物品名，也写单数：`common:rice_panicle`、`common:mutton_chop`（物品 `arris:mutton_chops`）、`common:tomato_seed`（物品 `arris:tomato_seeds`）。
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
  算作物，和 JE 一样（3.10 实机：别的包登记进 `common:tomato` 的番茄，反查 `common:vegetable`、作物标签都有它；量的时候作物标签用的还是复数名，现在是 `common:crop`）。
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
刀切蛋糕和派，刀收稻穗，蘑菇菌落，炉灶站点开不开；还有刀掉耐久：一次掉的多于 1 点时只扣 1 点（`Server/Tools.OnKnifeDurability`，
为的是农夫乐事的刀：它们是剑类的自定义武器，拆一块方块引擎扣 2 点，JE 的刀只扣 1 点；别的模组的刀是刀，也照这一条）。
反过来，装了森罗物语厨房时，`common:knife` 里的刀也是森罗的菜刀：能在它的砧板上切、杀猪掉油（见下面「森罗也认农夫乐事的东西」）。

### 热源方块

热源照 JE 用农夫乐事自己的方块标签 `farmersdelight:heat_sources`（JE 的森罗物语也把炉灶登记进这个名字，网易版的森罗也登记了，见下面「森罗已经登记了」）。方块在这个标签里，放在它上面的厨锅、煎锅就会热；
方块有"点没点着"这类状态的要点着才算，和 JE 一样（JE 是"带 LIT 状态的看 LIT"）：状态里有名字是 `lit` 或以 `:lit` 结尾的状态，值为真；
或者有 `extinguished` 状态，值为假。没有这类状态的方块在标签里就算热，比如火、熔岩、岩浆块、农夫乐事点着的炉灶（点着和熄着是两个方块名，登记的是点着的那个）。

JE 的这个标签里还有熔岩炼药锅（`minecraft:lava_cauldron`）。基岩版没有这个方块（3.10 实机：`minecraft:lava_cauldron` 放出来的是盛水、0 级的
`minecraft:cauldron`），熔岩炼药锅是炼药锅盛着熔岩的状态（`cauldron_liquid` = `lava`）。所以这边的标签里写的是炼药锅 `minecraft:cauldron`，
另带一条**状态条件**：`cauldron_liquid` 是 `lava`、`fill_level` 至少是 1。盛着熔岩的炼药锅上面的锅、煎锅会热，站在它旁边能手持煎锅，
空的、盛水的、盛粉雪的炼药锅都不热，和 JE 一样（3.10 实机：厨锅放在熔岩 6 级的炼药锅上热、放在盛水的上面不热，把熔岩改成 0 级后凉了）。
别的模组按这个标签认热源时，炼药锅也要看这两个状态。
往这个标签里写 `minecraft:lava_cauldron` 不起作用：世界里没有叫这个名字的方块（方块标签的成员名引擎不校验，3.10 实机；会不会往日志里记一条没量过）。

状态条件（农夫乐事的表 `Shared/Data/Cooking.HeatSourceStateDict`）：一个方块的几条条件都满足才算热，每条写一个值（相等）、一组值（是其中之一）
或 `{"min": n}` / `{"max": n}`（数值范围）。写了条件的方块处处按条件判：放在上面的锅、煎锅，手持煎锅身边，都判；方块在这个标签里、
在 `CanProvideHeatBlockList` 里也一样；状态读不到、没有这个状态都算不满足。
你自己的"一个方块 + 某个状态"的热源，用新联动接口登记条件：`ext.registerHeatSource("mymod:brazier", states={"mymod:coals": {"min": 1}})`
（[EXTENSION-API.md](EXTENSION-API.md) §6.1）；登记了条件的方块不用再进这个标签。只看点燃状态（`lit` / `*:lit` / `extinguished`）的方块不用登记条件，进标签就行。

手持煎锅"身边有没有热源"只看方块，不看点没点着（和 JE 一样）；写了状态条件的照样按条件判。
`linkage.md` 里往 `CanProvideHeatBlockList` 追加名字的办法照旧有效。

### 能煎烤什么

煎锅、炉灶、手持煎锅能煎什么，先看农夫乐事的表 `CanCookedFoodDict`（`linkage.md` 可以追加），表里没有的再问引擎的营火配方。
给你的生肉写一份营火配方（配方 JSON 的 `tags` 里带 `campfire`），它就能放到农夫乐事的煎锅、炉灶上煎，煎好是你配方里的东西。
食谱书和 JEI 里"能煎烤的东西"那几页只列表里的。

基岩版的三种蛋（鸡蛋、蓝色鸡蛋、棕色鸡蛋，原版标签 `minecraft:egg` 的成员）一视同仁：都能在煎锅上煎成煎蛋，只煎一面，炉灶站点的烤架不收，
熔炉、烟熏炉、营火也收（JE 只有一种蛋）。工作台配方里 JE 写 `#forge:eggs` 的四样（蛋糕、南瓜派、烤鸡、鸡蛋面团）写的是 `minecraft:egg` 标签，三种蛋都收。

## 和森罗物语的标签对照

团队的烹饪原料标签规范是森罗物语厨房网易版（下面简称森罗）2026-11-26 的提交 `2df8e1c` 登记的 18 个标签。下表是两边各登记了什么：
两个模组都装着时，引擎把同名标签两边的成员并起来，`#` 引的标签再展开（3.10 实机量过的是"两个包登记同一个标签会合并"和"别的包登记进被 `#` 引的标签，
引它的标签里也有"；两个包都往同一个标签里写 `#`、各引各的时并出来什么样，还没在游戏里量过）。"森罗登记的"照它 `kaleidoscope_cookery_bp/netease_tags/`
的文件抄，"农夫乐事登记的"就是词表（测试核对这一列）。`common:vegetable` 末尾的 `#common:cabbage` 是森罗 2026-11-26 晚上的提交 `4be4319` 加的
（见下面「森罗也认农夫乐事的东西」）；测试对着还没有这个提交的森罗 main 也认，那时这一格少这一项。

| 标签 | 森罗登记的 | 农夫乐事登记的 | JE 里对应的标签 |
| --- | --- | --- | --- |
| `common:beef` | `minecraft:beef`、`minecraft:cooked_beef`、`kaleidoscope_cookery:raw_cow_offal`、`kaleidoscope_cookery:cooked_cow_offal` | `#common:raw_beef`、`#common:cooked_beef` | `forge:raw_beef` 和 `forge:cooked_beef` 合起来（JE 森罗的配方只收生的） |
| `common:chicken` | `minecraft:chicken`、`minecraft:cooked_chicken` | `#common:raw_chicken`、`#common:cooked_chicken` | `forge:raw_chicken` 和 `forge:cooked_chicken` |
| `common:chili` | `kaleidoscope_cookery:red_chili`、`kaleidoscope_cookery:green_chili` | — | `forge:crops/chilipepper` |
| `common:dough` | `kaleidoscope_cookery:raw_dough` | `arris:wheat_dough` | `forge:dough` |
| `common:egg` | `minecraft:egg`、`minecraft:blue_egg`、`minecraft:brown_egg`、`minecraft:turtle_egg`、`minecraft:sniffer_egg`、`kaleidoscope_cookery:fried_egg` | `#common:cooked_egg` | JE 森罗的 `forge:eggs`（它把自己的煎蛋放了进去） |
| `common:fish` | `minecraft:cod`、`minecraft:salmon`、`minecraft:cooked_cod`、`minecraft:cooked_salmon`、`minecraft:tropical_fish`、`kaleidoscope_cookery:sashimi` | `#common:raw_fish`、`#common:cooked_fish` | `forge:raw_fishes` 和 `forge:cooked_fishes` |
| `common:flour` | `kaleidoscope_cookery:flour` | — | `forge:flour` |
| `common:lamb` | `minecraft:mutton`、`minecraft:cooked_mutton`、`kaleidoscope_cookery:raw_lamb_chops`、`kaleidoscope_cookery:cooked_lamb_chops` | `#common:raw_mutton`、`#common:cooked_mutton` | `forge:raw_mutton` 和 `forge:cooked_mutton` |
| `common:lettuce` | `kaleidoscope_cookery:lettuce` | — | `forge:crops/lettuce` |
| `common:meat` | `#common:beef`、`#common:chicken`、`#common:lamb`、`#common:pork`、`minecraft:rabbit`、`kaleidoscope_cookery:raw_cut_small_meats` | — | 没有单个对应的（JE 森罗的 `forge:raw_meats` 还含鱼） |
| `common:meatball` | `kaleidoscope_cookery:raw_meatball`、`kaleidoscope_cookery:cooked_meatball` | — | 没有（JE 森罗的配方写物品） |
| `common:mushroom` | `minecraft:red_mushroom`、`minecraft:brown_mushroom` | `minecraft:brown_mushroom`、`minecraft:red_mushroom` | `forge:mushrooms` |
| `common:noodle` | `kaleidoscope_cookery:raw_noodles` | — | 没有（JE 森罗的配方写物品） |
| `common:pork` | `minecraft:porkchop`、`minecraft:cooked_porkchop`、`kaleidoscope_cookery:raw_pork_belly`、`kaleidoscope_cookery:cooked_pork_belly` | `#common:raw_pork`、`#common:cooked_pork` | `forge:raw_pork` 和 `forge:cooked_pork` |
| `common:rice` | `kaleidoscope_cookery:rice` | `arris:rice` | `forge:crops/rice`、`forge:grain/rice` |
| `common:seed` | `minecraft:wheat_seeds`、`minecraft:pumpkin_seeds`、`minecraft:melon_seeds`、`minecraft:beetroot_seeds`、`minecraft:torchflower_seeds`、`minecraft:pitcher_pod`、`kaleidoscope_cookery:rice` | `#common:cabbage_seed`、`#common:rice`、`#common:tomato_seed`、`minecraft:beetroot_seeds`、`minecraft:melon_seeds`、`minecraft:pumpkin_seeds`、`minecraft:wheat_seeds` | `forge:seeds` |
| `common:tomato` | `kaleidoscope_cookery:tomato` | `arris:tomato` | `forge:crops/tomato` |
| `common:vegetable` | `#common:tomato`、`#common:lettuce`、`#common:chili`、`minecraft:carrot`、`minecraft:potato`、`minecraft:beetroot`、`#common:cabbage` | `#common:beetroot`、`#common:carrot`、`#common:onion`、`#common:potato`、`#common:tomato` | `forge:vegetables` |

### 农夫乐事登记进去的依据

依据都在 JE 的源码里：JE 农夫乐事 1.3.4 的 `data/ItemTags.java`（`src/main/java/vectorwing/farmersdelight/` 下），JE 森罗物语厨房（1.20.1，
源码快照 `1d935a2c`）的 `datagen/tag/TagItem.java`（`src/main/java/com/github/ysbbbbbb/kaleidoscopecookery/` 下）和它生成的配方
（`src/generated/resources/data/kaleidoscope_cookery/recipes/`），以及两个 JE 兼容模组 Kaleidoscope Compat 2.9.7、Kaledelights Compat 1.3.9 的数据。

- **牛、鸡、羊、猪、鱼**：JE 森罗的模糊配方收 `#forge:raw_beef`、`#forge:raw_chicken`、`#forge:raw_mutton`、`#forge:raw_pork`、`#forge:raw_fishes`
  （如 `flex_pot/braised_beef.json:8`、`flex_pot/spicy_chicken.json:8`、`flex_pot/crystal_lamb_chop.json:11`、`flex_pot/sweet_and_sour_pork.json:8`、
  `flex_pot/oil_splashed_fish.json:8`），JE 农夫乐事把牛肉末、鸡块、羊排、培根、鳕鱼片、鲑鱼片登记在同样的标签里（`ItemTags.java:227-235`），
  所以 JE 里森罗的这些菜本来就收农夫乐事的生肉、生鱼片。网易版森罗把熟的也算了进来（它的 `common:beef` 里有熟牛肉、熟牛杂，就是 JE 森罗登记在
  `forge:cooked_beef` 的那两样，`TagItem.java:186`），农夫乐事就把 JE 里同在 `forge:cooked_*` 的熟的也放进来：牛肉饼、熟鸡块、熟猪排、熟培根、熟羊排
  （`ItemTags.java:187-190`），熟鳕鱼片、熟鲑鱼片（`ItemTags.java:193-195`）。写法是 `#` 嵌生、熟两个细标签，别的模组登记进细标签的东西也跟着算。
  - 培根算猪肉，火腿不算：JE 的 `forge:raw_pork` 是猪排和培根（`ItemTags.java:229`），`forge:cooked_pork` 是熟猪排和熟培根（`ItemTags.java:189`），
    火腿、熏火腿 JE 没放进任何肉的标签。
  - 鱼片、热带鱼算鱼，河豚不算：`forge:raw_fishes` 是鳕鱼和鳕鱼片、鲑鱼和鲑鱼片、热带鱼（`ItemTags.java:232-235`），没有河豚；森罗的 `common:fish` 也没有。
- **蛋**（`#common:cooked_egg`，就是煎蛋）：JE 森罗把自己的煎蛋放进 `forge:eggs`（`TagItem.java:159`），它的番茄炒蛋、蛋炒饭这些收 `#forge:eggs`
  （`flex_pot/scramble_egg_with_tomatoes.json:8`）；两个模组的煎蛋是同一种东西：Kaleidoscope Compat 的合并表里有农夫乐事的煎蛋
  （`packs/unite_farmersdelight/data/kaleidoscope_cookery/tags/item/united.json:4`）。JE 农夫乐事的煎蛋在 `forge:cooked_eggs`（`ItemTags.java:191`），
  所以这边嵌的是"做熟的蛋"这个细标签，别的模组登记进 `common:cooked_egg` 的也跟着算蛋。农夫乐事自己的鸡蛋格子照旧读 `minecraft:egg`。
- **种子**（`common:seed` 就是 JE 的 `forge:seeds`）：JE 森罗的腊八粥收 `#forge:seeds`（`flex_stockpot/laba_congee.json:12`），JE 农夫乐事往
  `forge:seeds` 里放的是卷心菜种子、米、番茄种子这三样（`ItemTags.java:240-243`），原版的四种种子（甜菜、西瓜、南瓜、小麦的种子）是 Forge 自己给的。
  这边两样都写：`#` 嵌三个细标签，原版的四种照写，农夫乐事单独在场时这个标签照样是全的；森罗也登记了的原版种子，引擎合并时去重。
  机械动力附属读的种子标签原来是另一个复数名，团队 2026-11-26 定了 `common:` 物品标签一律单数，它并进了 `common:seed`
  （机械动力附属同一天的提交 `aa8fc45` 改读 `common:seed`；改名的对照见 [API-CHANGELOG.md](API-CHANGELOG.md)）。
- **蘑菇、番茄、米、面团、蔬菜**：本来就同名，两边的成员引擎合并。JE 里这几样也是两个模组共用同一个 `forge:` 标签
  （`forge:mushrooms`、`forge:crops/tomato`、`forge:crops/rice`、`forge:dough`、`forge:vegetables`）。
- **卷心菜算蔬菜**（森罗那边登记的，农夫乐事这边没改）：JE 森罗的 `forge:vegetables` 可选地含 `#forge:crops/cabbage`（`TagItem.java:174-177`，
  注释写的是兼容农夫乐事卷心菜），JE 农夫乐事读的是同一个标签，所以两个模组都装时农夫乐事的蔬菜格也收卷心菜。网易版森罗在 `common:vegetable`
  末尾写了 `#common:cabbage`（森罗提交 `4be4319`）：两个包都装着时农夫乐事的卷心菜、卷心菜叶算蔬菜，农夫乐事读 `common:vegetable` 的格子也收它们
  （厨锅的蔬菜面、蔬菜杂烩、填馅南瓜、卷心菜卷、鸡肉汤，工作台的海带卷），和 JE 两个都装时一样；农夫乐事自己登记的 `common:vegetable` 照旧不含卷心菜。
  只装森罗时这个 `#` 引的是没人登记的标签：3.10 实机（2026-11-26，两端各量一遍）被引的标签只要还有别的真成员，标签照常登记、成员就是那些真成员，
  加载时不记日志。两个包都装着时整条链（`#` 引 → 引擎展开 → 厨锅的蔬菜格收卷心菜）还没在游戏里走过。
- **面条不登记**（用户 2026-11-26 定：意面和面条不是同一种东西）：农夫乐事的生意面只在 `common:pasta` 里，不进 `common:noodle`；
  森罗的生面条也不进 `common:pasta`，两边互不认。JE 里本来也是两样：JE 森罗的牛肉面、羊肉烩面、热干面、乌冬面写的是物品
  `kaleidoscope_cookery:raw_noodles`（如 `flex_stockpot/beef_noodle.json:15`），不是标签；两个兼容模组也没把农夫乐事的生意面和森罗的生面条当成一种
  （Kaledelights Compat 给农夫乐事厨锅写的乌冬面照样写 `kaleidoscope_cookery:raw_noodles`：`data/farmersdelight/recipe/cooking/kk_udon_noodle_cooked_eggs.json:22`）。
- **没登记的六个**：面条见上一条。辣椒、面粉、生菜、肉丸农夫乐事没有，JE 里也没有把农夫乐事的东西算进去的依据：JE 森罗的 `forge:crops/lettuce` 只有生菜
  （`TagItem.java:164`），Kaleidoscope Compat 的 `c:crops/lettuce` 只加了 Farm & Charm 的生菜（`packs/compat/data/c/tags/item/crops/lettuce.json:4`），
  Kaledelights Compat 的配方里生菜写 `c:crops/lettuce`（如 `data/farmersdelight/recipe/cooking/kk_beef_meatball_soup.json:19`）、
  卷心菜写 `c:crops/cabbage`（如 `data/kaleidoscope_cookery/recipe/stockpot/dumplings.json:15`），卷心菜不当生菜用；`forge:flour` 只有森罗的面粉（`TagItem.java:216`）；肉丸 JE 森罗写物品。肉（`common:meat`）森罗自己的文件用 `#` 引了牛、鸡、羊、猪四个，
  农夫乐事的肉登记进那四个就跟着进去了，不用再登记。

### 森罗已经登记了：森罗的东西进农夫乐事的配方

农夫乐事的配方读的是细标签。森罗 2026-11-26 在它自己的行为包里把下面十样东西登记进了这些标签（用户定的；森罗的提交 `9ea2b05`：
`kaleidoscope_cookery_bp/netease_tags/` 下九个物品标签文件、一个方块标签文件，只写森罗自己的东西）。农夫乐事这边一行配方没改：
两个模组都装着时引擎把同名标签两边的成员并起来，农夫乐事按标签认的地方就认得它们，农夫乐事用 `#` 嵌了这些细标签的标签（生肉、熟肉、粗标签）里也有它们。
"农夫乐事哪里因此能用上它"照现在的配方数（厨锅每道菜的 `Slots`、`bp/recipes` 里写标签的工作台配方，`tests/test_netease_tags.py` 照配方重新数一遍）；
依据是 JE 森罗把它放进的 `forge:` 标签，就是农夫乐事读的那个（`TagItem.java` 的行号）。表里最后一行（米饭）是同一天晚些时候森罗的另一个提交（`6287898`）
登记的：农夫乐事自己不读 `common:cooked_rice`，用处在森罗那边（下一节）。

| 森罗的东西 | 登记进 | 农夫乐事哪里因此能用上它 | JE 依据 |
| --- | --- | --- | --- |
| `kaleidoscope_cookery:raw_cow_offal`（生牛杂） | `common:raw_beef` | 厨锅：饺子、牛肉炖；经 `common:raw_meat`：卷心菜卷、狗粮 | `forge:raw_beef`（`:194`） |
| `kaleidoscope_cookery:raw_pork_belly`（生五花肉） | `common:raw_pork` | 厨锅：饺子、南瓜汤、面条汤；经 `common:raw_meat`：卷心菜卷、狗粮 | `forge:raw_pork`（`:196`） |
| `kaleidoscope_cookery:raw_lamb_chops`（生羊排） | `common:raw_mutton` | 厨锅：羊排意面；经 `common:raw_meat`：卷心菜卷、狗粮 | `forge:raw_mutton`（`:197`） |
| `kaleidoscope_cookery:cooked_cow_offal`（熟牛杂） | `common:cooked_beef` | 工作台：填馅马铃薯；经 `common:cooked_meat`：烧烤串 | `forge:cooked_beef`（`:186`） |
| `kaleidoscope_cookery:cooked_pork_belly`（熟五花肉） | `common:cooked_pork` | 经 `common:cooked_meat`：烧烤串 | `forge:cooked_pork`（`:187`） |
| `kaleidoscope_cookery:cooked_lamb_chops`（熟羊排） | `common:cooked_mutton` | 工作台：羊肉卷饼、牧羊人派；经 `common:cooked_meat`：烧烤串 | `forge:cooked_mutton`（`:188`） |
| `kaleidoscope_cookery:sashimi`（刺身） | `common:raw_fish` | 厨锅：鱿鱼墨面、卷心菜卷、鱼肉炖 | `forge:raw_fishes/tropical_fish`，引进 `forge:raw_fishes`（`:199`、`:203-205`） |
| `kaleidoscope_cookery:fried_egg`（煎蛋） | `common:cooked_egg` | 工作台：培根蛋、夹蛋三明治 | `forge:cooked_eggs`（`:189`） |
| `kaleidoscope_cookery:iron_kitchen_knife`、`kaleidoscope_cookery:gold_kitchen_knife`、`kaleidoscope_cookery:diamond_kitchen_knife`、`kaleidoscope_cookery:netherite_kitchen_knife`（四把菜刀） | `common:knife` | 认作刀的地方都认（见上面「刀」） | `forge:tools/knives`、`farmersdelight:tools/knives`（`:53-62`） |
| `kaleidoscope_cookery:kaleidoscope_cookery_stove`（炉灶） | 方块标签 `farmersdelight:heat_sources` | 放在上面的厨锅、煎锅会热，点着才算（它的 `kaleidoscope_cookery:lit` 是点燃状态）；手持煎锅站在它旁边也算身边有热源（和 JE 一样不看点没点着） | JE 森罗生成的 `data/farmersdelight/tags/blocks/heat_sources.json:3` |
| `kaleidoscope_cookery:cooked_rice`（米饭） | `common:cooked_rice` | 农夫乐事不读这个标签，用处在森罗自己的盖饭配方（下一节） | `forge:cooked_rice`（`:190`） |

- 工作台那几样（填馅马铃薯、羊肉卷饼、牧羊人派、烧烤串、培根蛋、夹蛋三明治）都是砧板菜。装了沉浸式交互前置、砧板站点开着时，工作台不出砧板菜、要在砧板上拼；
  砧板的菜谱按词表里农夫乐事登记的成员展开（`DishList`），认不出森罗的东西：格子里有森罗的东西时工作台拦不住、照样做得出，砧板上却拼不了
  （已知的口子，见 ARCHITECTURE.md「和 JE 的出入」里"工作台配方按标签"那一条）。没装前置包时就是工作台照常做。
- 森罗的炉灶只登记方块名就够了：农夫乐事看"点没点着"认的是名字是 `lit` 或以 `:lit` 结尾的状态（上面「热源方块」）。
- 游戏内自检：`Server/Debug/McdkKcTagsTest.mcdk_test_kc_tags()`（两个包都装着时报前十样在不在引擎的标签里、农夫乐事的规则认不认、厨锅凑不凑得出菜；米饭那一行它还没问）。

### 森罗也认农夫乐事的东西

反方向：森罗 2026-11-26 晚上又加了三处（用户定的："森罗切菜认农夫乐事的刀……盖饭认农夫乐事的米饭、卷心菜算蔬菜"），都只动了它的数据，农夫乐事这边没改。
两个包都装着时：

- **刀**（森罗提交 `c254893`）：森罗的 `netease_tags/kitchen_knife.json` 给 `kaleidoscope_cookery:kitchen_knife` 写了四把菜刀，再用 `#` 引 `common:knife`。
  农夫乐事的五把刀和别的模组登记进 `common:knife` 的刀，能在森罗的砧板上切菜、杀猪 / 猪灵 / 疣猪兽时掉油；沉浸式交互前置的森罗砧板站点也认
  （这几处问的是同一个标签 `kaleidoscope_cookery:kitchen_knife`）。JE 依据：JE 森罗的 `kitchen_knife` 可选地含 `#farmersdelight:tools/knives`（`TagItem.java:43-47`），
  网易版对应的是 `common:knife`。四把菜刀还在各自物品 JSON 的 `minecraft:tags` 里声明着，这个文件里又写了一遍：同一个包里两种写法声明同一个标签时会不会都算，
  还没在游戏里量过，写全了两种结果都对。
- **盖饭**（`6287898`）：森罗的 `netease_tags/cooked_rice.json` 把 `kaleidoscope_cookery:cooked_rice` 登记进 `common:cooked_rice`（农夫乐事的 `arris:cooked_rice` 在同一个标签里），
  五条盖饭的工作台配方（番茄炒蛋盖饭、红烧牛肉盖饭、青椒炒肉盖饭、糖醋里脊盖饭、鱼香肉丝盖饭）里米饭那一格写成 `{"tag": "common:cooked_rice"}`。
  农夫乐事的米饭能做这五种盖饭；只装森罗时靠它自己的文件，配方照样做得出。JE 依据：`forge:cooked_rice` 可选地含农夫乐事的米饭（`TagItem.java:190-192`），
  盖饭配方收 `#forge:cooked_rice`（`RiceBowlRecipe.java`）。
- **卷心菜**（`4be4319`）：森罗的 `common:vegetable` 末尾加了 `#common:cabbage`，农夫乐事的卷心菜、卷心菜叶算蔬菜，依据见「农夫乐事登记进去的依据」里"卷心菜算蔬菜"一条。

这三处都只是数据，离线核过名字和写法（测试 `testKaleidoscopeAlsoReadsOurKnivesAndRice` 对着森罗的文件核，没有这三个提交的森罗 main 也认），
还没在游戏里整条走过：农夫乐事的刀在森罗砧板上真切一次、只装森罗时盖饭做得出、两个包都装着时厨锅的蔬菜格收卷心菜。

和 JE 不一样的一处：农夫乐事的米饭做森罗的盖饭**不还碗**。JE 里米饭自带合成剩余物（碗，`ModItems` 里的 `bowlFoodItem`），做完盖饭碗还给玩家；
这边的碗由农夫乐事自己的脚本还（`Server/CraftReturns.py`，只认本包生成的工作台配方表 `Shared/Data/CraftReturns.py`，按成品名查），森罗的盖饭不在表里，所以不还。
这是照代码读出来的，没在游戏里做过；记在 ARCHITECTURE.md「和 JE 的出入」。

### 给森罗那边的建议

下面这些还是建议，森罗定要不要登记；农夫乐事这边照旧一行不用改。

| 森罗的东西 | 登记进 | 农夫乐事哪里因此能用上它 | JE 依据 |
| --- | --- | --- | --- |
| `kaleidoscope_cookery:tomato_seed` | `common:tomato_seed` | 不读 | `forge:seeds/tomato`（`:180`） |
| `kaleidoscope_cookery:rice_panicle`、`raw_lamb_chops`、`cooked_lamb_chops` | `common:rice_panicle`、`common:mutton_chop`、`common:cooked_mutton_chop` | 不读 | 同一种东西：Kaleidoscope Compat 的合并表（上面那个 `united.json`） |
| 番茄、两种辣椒、生菜、米；番茄、辣椒、生菜的种子，野生稻种子 | `common:crop`；`common:seed` | 农夫乐事不读（机械动力附属读） | `forge:crops`（`:162-169`）、`forge:seeds`（`:152-158`） |

森罗自己的 `common:seed` 现在只有原版种子和米；JE 森罗的 `forge:seeds` 还有它的番茄、辣椒、生菜种子和野生稻（`TagItem.java:152-158`，上表最后一行），要不要补由森罗定。

JE 有、这边不建议的：

- 森罗的煎蛋、海龟蛋进原版的 `minecraft:egg`：JE 森罗把它们放进 `forge:eggs`（`TagItem.java:159`、`:198`），而 JE 农夫乐事的蛋糕、南瓜派、烤鸡、
  鸡蛋面团、炒饭这些按 `forge:eggs` 收蛋，于是 JE 里能拿煎蛋做蛋糕。这边的鸡蛋格子只收三种鸡蛋，不建议。
- 森罗的碎肉 `raw_cut_small_meats` 进 `common:raw_meat`：JE 里它在森罗的 `forge:raw_meats`（复数，`TagItem.java:207-214`），农夫乐事读的是
  `forge:raw_meat`（单数，`ItemTags.java:219-224`），是两个标签，JE 里农夫乐事的卷心菜卷、狗粮不收它。
- 生菜进 `common:leafy_green`（沙拉、三明治和几道汤用的叶菜）：JE 里没有依据（JE 森罗没把生菜放进 `forge:salad_ingredients`），要不要由团队定。
- 生面条进 `common:pasta`：不进（用户 2026-11-26 定：意面和面条不是同一种东西，见上面「面条不登记」；JE 里生面条也不在 `forge:pasta`）。

JE 森罗另外还认农夫乐事的东西，网易版要森罗那边改（农夫乐事不用动）。原来列的五条，加上网易版独有的炒锅盛饭一条，现在的进度（2026-11-26 晚）：

- 菜刀：**已做**（森罗提交 `c254893`）。JE 森罗的 `kaleidoscope_cookery:kitchen_knife` 可选地含 `#farmersdelight:tools/knives`（`TagItem.java:43-47`），
  网易版的 `kitchen_knife` 引了 `common:knife`，农夫乐事的刀能当菜刀用（见上面「森罗也认农夫乐事的东西」）。
- 盖饭认农夫乐事的米饭：**已做**（`6287898`）。`forge:cooked_rice` 可选地含农夫乐事的米饭（`TagItem.java:190-192`）；网易版五条工作台盖饭配方读 `common:cooked_rice`，农夫乐事的米饭在里面。
- 卷心菜算蔬菜：**已做**（`4be4319`）。`forge:vegetables` 可选地含 `#forge:crops/cabbage`（`TagItem.java:177`，注释"兼容农夫乐事卷心菜"）；网易版森罗的 `common:vegetable`
  写了 `#common:cabbage`，农夫乐事的蔬菜格子也收卷心菜，和 JE 两个模组都装时一样。只装森罗时这个 `#` 引的是没人登记的标签，3.10 实机量过：标签里还有别的真成员时照常、不记日志（见上面「农夫乐事登记进去的依据」）。
- 热源：要改森罗的代码，森罗那边另外在做。JE 森罗"没有点燃状态的热源"含 `#farmersdelight:heat_sources`（生成的 `data/kaleidoscope_cookery/tags/blocks/heat_source_blocks_without_lit.json:7`）；
  网易版森罗的锅现在认的是写死的名单（火、熔岩、岩浆块，炉灶、营火另外判），不读标签，要改成也按方块标签 `farmersdelight:heat_sources` 认（见上面「热源方块」）。
- 水稻种在农夫乐事的沃土耕地上：不做。JE 的 `rice_plantable` 含农夫乐事的沃土耕地（生成的 `data/kaleidoscope_cookery/tags/blocks/rice_plantable.json:4`），
  网易版的沃土耕地是 `arris:rich_soil_farmland`、`arris:rich_soil_farmland_moist` 两个方块。
- 炒锅里用米饭盛成盖饭（森罗 `pot_action.py` 里的 `RICE_BOWL_MAPPING`）：网易版独有，JE 没有，不做，还是只认森罗自己的米饭。

## JE 农夫乐事自己的标签（farmersdelight:）

JE 农夫乐事自己定义的标签，这边照 JE 的名字登记成 `farmersdelight:<路径>`。成员照 JE 的标签文件换成这边的名字；JE 用 `#` 引的标签这边也登记的
照写 `#`（`farmersdelight:heat_sources` 引 `#farmersdelight:tray_heat_sources`；方块标签里的 `#` 引擎也展开，3.10 实机：反查 `heat_sources`
是炉灶、营火、灵魂营火、火、灵魂火、熔岩、流动的熔岩、岩浆块 8 个——这是加炼药锅之前量的，加了以后没反查过——营火按方块问同时带 `heat_sources` 和 `tray_heat_sources`），引的是这边没有的（`#minecraft:campfires`、`#farmersdelight:cabinets/wooden`……）展开写成员；只写农夫乐事自己的和原版的东西，JE 里别的模组的可选成员不写（`heat_conductors` 里机械动力的溜槽由机械动力自己登记）。

方块标签有七个。农夫乐事读它们的地方都是"原来的名单 ∪ 标签"：名单原样留着，不在名单里、带了标签的方块也算。
热源的名单 `CanProvideHeatBlockList` 在 `linkage.md` 的接口里，另外六张不在，别的模组要加进来就用标签。

| 标签 | 方块在这个标签里时 | 农夫乐事登记的 |
| --- | --- | --- |
| `farmersdelight:heat_sources` | 放在它上面的厨锅、煎锅会热（有点燃状态的要点着；写了状态条件的按条件，见上一节） | 岩浆块、炼药锅（盛着熔岩时：JE 的熔岩炼药锅）、炉灶、熔岩、营火、火 |
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

名字怎么来的见开头「名字和成员照什么定」。团队里别的模组在用的名字照用：`common:crop`、`common:seed`、`common:flower`（机械动力附属读；
2026-11-26 和这边一起从复数名改成了单数）、`common:dough`、`common:wheat_flour`（机械动力），都和那条规则对得上。团队烹饪原料规范里农夫乐事登记的 12 个也在下表里
（粗标签的"意思"一列写着"团队规范的粗标签"），没登记的 6 个见「和森罗物语的标签对照」。

- `common:mushroom` 是能吃的蘑菇（红蘑菇、棕蘑菇），和机械动力的 `common:mushroom_block`（蘑菇方块）不是一回事。
- 小麦粉：机械动力登记的是 `common:wheat_flour`，规范里的面粉是 `common:flour`（森罗物语的面粉），两个名字；农夫乐事没有面粉，两个都不登记。
- 农夫乐事的鸡蛋格子用原版自带的 `minecraft:egg`（鸡蛋、蓝色鸡蛋、棕色鸡蛋）。规范的 `common:egg` 是更粗的"蛋"，农夫乐事只把煎蛋登记进去、自己不读它。
  别的模组的鸡蛋登记进 `minecraft:egg` 就行：`netease_tags` 的 `identifier` 写
  `minecraft:egg`（3.10 实机：引擎把它并进原版标签，反查、按物品问都有它；工作台自检里蛋那一格放它，蛋糕、南瓜派、烤鸡、鸡蛋面团都做出来了）。
- 农夫乐事没有成员的名字只在下表里列着，不生成文件，别的模组可以往里登记。

<!-- gen_tags: 词表开始（tools/gen_tags.py 从 Shared/Data/Tags.py 生成，别手改） -->
| 标签 | 种类 | 意思 | JE 1.20.1（forge:） | JE 1.21（c:） | 农夫乐事登记的 | 农夫乐事在哪里读 |
| --- | --- | --- | --- | --- | --- | --- |
| `common:tomato` | 物品 | 番茄 | `forge:crops/tomato`、`forge:vegetables/tomato` | `c:crops/tomato`、`c:foods/tomato` | `arris:tomato` | 厨锅的格子：番茄酱、蔬菜杂烩、鱿鱼墨面、烘焙鳕鱼炖（Shared/Data/CookingPotRecipes 的 Slots）；工作台：`arris:bacon_sandwich`、`arris:barbecue_stick`、`arris:gleaming_salad_block_stage0`、`arris:hamburger`、`arris:mixed_salad`、`arris:roasted_mutton_chops`（bp/recipes） |
| `common:tomato_seed` | 物品 | 番茄种子 | `forge:seeds/tomato` | — | `arris:tomato_seeds` | — |
| `common:rice` | 物品 | 米（也是水稻的种子） | `forge:crops/rice`、`forge:grain/rice`、`forge:seeds/rice` | `c:crops/rice` | `arris:rice` | 厨锅的格子：米饭、炒饭、蘑菇饭、填馅南瓜、狗粮（Shared/Data/CookingPotRecipes 的 Slots） |
| `common:rice_panicle` | 物品 | 稻穗 | — | — | `arris:rice_panicle` | — |
| `common:cooked_rice` | 物品 | 米饭 | `forge:cooked_rice` | `c:foods/cooked_rice` | `arris:cooked_rice` | — |
| `common:dough` | 物品 | 面团 | `forge:dough`、`forge:dough/wheat` | `c:foods/dough`、`c:foods/dough/wheat` | `arris:wheat_dough` | 厨锅的格子：饺子（Shared/Data/CookingPotRecipes 的 Slots）；砧板按标签切成 `arris:raw_pasta`（Shared/Data/Cutting.CuttingTagDict，Shared/Rules/CuttingStation.recipeOf） |
| `common:cooked_egg` | 物品 | 做熟的蛋（煎蛋） | `forge:cooked_eggs` | `c:foods/cooked_egg` | `arris:fried_egg` | 工作台：`arris:bacon_and_eggs`、`arris:egg_sandwich`（bp/recipes） |
| `common:mutton_chop` | 物品 | 生羊排 | — | — | `arris:mutton_chops` | — |
| `common:cooked_mutton_chop` | 物品 | 熟羊排 | — | — | `arris:cooked_mutton_chops` | — |
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
| `common:mushroom` | 物品 | 能吃的蘑菇 | `forge:mushrooms` | `c:mushrooms` | `minecraft:brown_mushroom`、`minecraft:red_mushroom` | 厨锅的格子：蔬菜面、卷心菜卷、大骨汤（Shared/Data/CookingPotRecipes 的 Slots） |
| `common:onion` | 物品 | 洋葱 | `forge:crops/onion`、`forge:vegetables/onion` | `c:crops/onion`、`c:foods/onion` | `arris:onion` | 厨锅的格子：炒饭、饺子、蔬菜杂烩、填馅南瓜、鱼肉炖、洋葱汤（Shared/Data/CookingPotRecipes 的 Slots）；工作台：`arris:barbecue_stick`、`arris:grilled_salmon`、`arris:hamburger`、`arris:mutton_wrap`、`arris:roast_chicken_block_stage0`、`arris:shepherds_pie_block_stage0`、`arris:steak_and_potatoes`（bp/recipes） |
| `common:carrot` | 物品 | 胡萝卜 | `forge:crops/carrot`、`forge:vegetables/carrot` | `c:crops/carrot` | `minecraft:carrot` | 厨锅的格子：兔肉煲、炒饭、蔬菜面、牛肉炖、鸡肉汤、蔬菜汤（Shared/Data/CookingPotRecipes 的 Slots）；工作台：`arris:chicken_sandwich`、`arris:roast_chicken_block_stage0`（bp/recipes） |
| `common:potato` | 物品 | 土豆 | `forge:crops/potato`、`forge:vegetables/potato` | `c:crops/potato` | `minecraft:potato` | 厨锅的格子：兔肉煲、填馅南瓜、牛肉炖、蔬菜汤、烘焙鳕鱼炖（Shared/Data/CookingPotRecipes 的 Slots） |
| `common:beetroot` | 物品 | 甜菜根 | `forge:crops/beetroot`、`forge:vegetables/beetroot` | `c:crops/beetroot` | `minecraft:beetroot` | 厨锅的格子：甜菜汤、蔬菜杂烩、蔬菜汤（Shared/Data/CookingPotRecipes 的 Slots）；工作台：`arris:gleaming_salad_block_stage0`、`arris:mixed_salad`、`arris:roasted_mutton_chops`（bp/recipes） |
| `common:wheat` | 物品 | 小麦 | `forge:crops/wheat`、`forge:grain/wheat` | `c:crops/wheat` | `minecraft:wheat` | 工作台：`arris:apple_pie_item`、`minecraft:cake`、`arris:honey_cookie`、`arris:pie_crust`、`arris:sweet_berry_cookie`、`arris:wheat_dough`（bp/recipes） |
| `common:bread` | 物品 | 面包 | `forge:bread`、`forge:bread/wheat` | `c:foods/bread` | `minecraft:bread` | 厨锅的格子：洋葱汤（Shared/Data/CookingPotRecipes 的 Slots）；工作台：`arris:bacon_sandwich`、`arris:chicken_sandwich`、`arris:egg_sandwich`、`arris:hamburger`、`arris:mutton_wrap`（bp/recipes） |
| `common:pasta` | 物品 | 生意面 | `forge:pasta`、`forge:pasta/raw_pasta` | `c:foods/pasta` | `arris:raw_pasta` | 厨锅的格子：肉丸意面、羊排意面、蔬菜面、鱿鱼墨面、面条汤（Shared/Data/CookingPotRecipes 的 Slots） |
| `common:berry` | 物品 | 浆果 | `forge:berries` | `c:foods/berry` | `minecraft:sweet_berries`、`minecraft:glow_berries` | 厨锅的格子：填馅南瓜（Shared/Data/CookingPotRecipes 的 Slots）；工作台：`arris:fruit_salad`（bp/recipes） |
| `common:bone` | 物品 | 骨头 | `forge:bones` | `c:bones` | `minecraft:bone` | 厨锅的格子：大骨汤（Shared/Data/CookingPotRecipes 的 Slots） |
| `common:raw_cod` | 物品 | 生鳕鱼（含鱼片） | `forge:raw_fishes/cod` | `c:foods/raw_cod` | `minecraft:cod`、`arris:cod_slice` | 厨锅的格子：烘焙鳕鱼炖（Shared/Data/CookingPotRecipes 的 Slots） |
| `common:raw_salmon` | 物品 | 生鲑鱼（含鱼片） | `forge:raw_fishes/salmon` | `c:foods/raw_salmon` | `minecraft:salmon`、`arris:salmon_slice` | — |
| `common:cooked_fish` | 物品 | 熟鱼（含熟鱼片） | `forge:cooked_fishes` | `c:foods/cooked_fish` | `#common:cooked_cod`、`#common:cooked_salmon` | 工作台：`arris:barbecue_stick`（bp/recipes） |
| `common:cooked_cod` | 物品 | 熟鳕鱼（含熟鱼片） | `forge:cooked_fishes/cod` | `c:foods/cooked_cod` | `minecraft:cooked_cod`、`arris:cooked_cod_slice` | — |
| `common:cooked_salmon` | 物品 | 熟鲑鱼（含熟鱼片） | `forge:cooked_fishes/salmon` | `c:foods/cooked_salmon` | `minecraft:cooked_salmon`、`arris:cooked_salmon_slice` | 工作台：`arris:grilled_salmon`（bp/recipes） |
| `common:raw_bacon` | 物品 | 生培根 | `forge:raw_bacon` | `c:foods/raw_bacon` | `arris:bacon` | — |
| `common:cooked_bacon` | 物品 | 熟培根 | `forge:cooked_bacon` | `c:foods/cooked_bacon` | `arris:cooked_bacon` | 工作台：`arris:bacon_sandwich`（bp/recipes） |
| `common:cabbage_seed` | 物品 | 卷心菜种子 | `forge:seeds/cabbage` | — | `arris:cabbage_seeds` | — |
| `common:water_bucket` | 物品 | 水桶 | `forge:buckets/water` | `c:buckets/water` | `minecraft:water_bucket` | — |
| `common:crop` | 物品 | 作物（机械动力附属也读；原版的那部分 JE 里是 Forge 给的，这边也登记） | `forge:crops` | `c:crops` | `#common:cabbage`、`#common:onion`、`#common:rice`、`#common:tomato`、`#common:beetroot`、`#common:carrot`、`minecraft:nether_wart`、`#common:potato`、`#common:wheat` | — |
| `common:seed` | 物品 | 种子（团队规范的名字，机械动力附属也读；原版的那部分 JE 里是 Forge 给的，这边也登记） | `forge:seeds` | `c:seeds` | `#common:cabbage_seed`、`#common:rice`、`#common:tomato_seed`、`minecraft:beetroot_seeds`、`minecraft:melon_seeds`、`minecraft:pumpkin_seeds`、`minecraft:wheat_seeds` | — |
| `common:flower` | 物品 | 花（机械动力附属也读） | `minecraft:flowers` | `minecraft:flowers` | `arris:wild_carrots`、`arris:wild_potatoes`、`arris:wild_beetroots`、`arris:wild_cabbages`、`arris:wild_tomatoes`、`arris:wild_onions`、`arris:wild_rice` | — |
| `common:beef` | 物品 | 牛肉，生的熟的都算（团队规范的粗标签，见「和森罗物语的标签对照」） | — | — | `#common:raw_beef`、`#common:cooked_beef` | — |
| `common:chicken` | 物品 | 鸡肉，生的熟的都算（团队规范的粗标签） | — | — | `#common:raw_chicken`、`#common:cooked_chicken` | — |
| `common:lamb` | 物品 | 羊肉，生的熟的都算（团队规范的粗标签） | — | — | `#common:raw_mutton`、`#common:cooked_mutton` | — |
| `common:pork` | 物品 | 猪肉，生的熟的都算，含培根（团队规范的粗标签） | — | — | `#common:raw_pork`、`#common:cooked_pork` | — |
| `common:fish` | 物品 | 鱼，生的熟的都算，含鱼片，不含河豚（团队规范的粗标签） | — | — | `#common:raw_fish`、`#common:cooked_fish` | — |
| `common:egg` | 物品 | 蛋，做熟的也算（团队规范的粗标签；农夫乐事的鸡蛋格子读的是原版的 minecraft:egg） | — | — | `#common:cooked_egg` | — |
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
| `farmersdelight:heat_sources` | 方块 | 热源：给上面的锅 / 煎锅加热（有点燃状态的要点着；炼药锅要盛着熔岩） | `farmersdelight:heat_sources` | `farmersdelight:heat_sources` | `minecraft:magma`、`minecraft:cauldron`、`arris:stove`、`#farmersdelight:tray_heat_sources` | 热源（Shared/Rules/HeatSources；锅底下的有点燃状态要点着，手持煎锅身边的不看；写了状态条件的——炼药锅——处处按条件判，Shared/Data/Cooking.HeatSourceStateDict） |
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
- 方块的状态只有服务端读得到：客户端判断热源时不看点没点着；写了状态条件的方块（炼药锅）客户端只读得到方块附加值（aux），
  按服务端照条件算好、随表同步发来的 aux 判，还没发到时当不热。3.10 实机：空的、盛水 6 级、熔岩 1 级、熔岩 6 级的炼药锅，客户端 `GetBlock`
  读到的 aux 是 0 / 6 / 9 / 14，和服务端一样，两端判得一样；`GetBlockStatesFromAuxValue` 对没有方块的 aux（空号、越界）给的是缺省状态
  （盛水、0 级），不是 None，农夫乐事把和前面重复的状态当没有方块，算出熔岩 1–6 级 = aux 9–14。
- 原版方块要先登记右键事件，拿刀右键时才切得到。农夫乐事只登记了蛋糕和插蜡烛的蛋糕，所以 `farmersdelight:drops_cake_slice`
  里再加原版方块不起作用；别的模组的自定义方块不用登记。
