# 农夫乐事的标签（netease_tags）

农夫乐事（arrisFarmersDelight）用网易 3.10 的 `netease_tags` 把自己的物品、方块和用到的原版物品、方块登记进一套 `common:` 标签。
别的模组往同名的标签里放自己的东西，引擎会把成员合并，农夫乐事和其他模组就能认出对方的番茄、米、刀、热源。

词表以代码为准：`bp/arrisFarmersDelightScripts/Shared/Data/Tags.py`。`bp/netease_tags/` 下的文件和本文的词表都由 `py -3 tools/gen_tags.py` 从它生成，
`tests/test_netease_tags.py` 核对文件是不是最新、成员是不是真的、和 JE 的标签对不对得上。

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
- 不要用 `#` 引用"在物品 JSON 里声明的标签"。引擎展开这种引用时只拿到经 `netease_tags` 加进去的成员。农夫乐事的文件一律不用 `#`。
- 你自己的物品也可以继续在物品 JSON 的 `minecraft:tags` 里写标签，引擎两种写法都认；原版物品只能用 `netease_tags`。

### 刀

挂上 `common:knife` 就是刀。农夫乐事的老标签 `arris:knife` 照旧有效（`linkage.md` 教的是在物品 JSON 里写它）。
`linkage.md` 里往 `knifeList` 追加名字的办法也照旧有效。三样任一个说是刀，农夫乐事就当它是刀：砧板上刀切的配方、借刀、插刀，刀杀生物的额外掉落，
刀切蛋糕和派，刀收稻穗，蘑菇菌落，炉灶站点开不开。

### 热源方块

方块标签不带方块状态，所以热源分两个：

- `common:heat_source`：方块名本身就说明在发热，比如火、熔岩、岩浆块、点着的炉灶（农夫乐事点着和熄着的炉灶是两个方块名，登记的是点着的那个）。
  方块在这个标签里，放在它上面的厨锅、煎锅就会热。
- `common:heat_source_lit`：同一个方块名有点着和没点着两种，要看方块状态。农夫乐事认的"点着"是：方块状态里有名字是 `lit` 或以 `:lit` 结尾的状态，
  值为真；或者有 `extinguished` 状态，值为假。两种都没有就不算点着。营火在这个标签里。

手持煎锅"身边有没有热源"只看方块，不看点没点着（和 JE 一样），两个标签里的方块都算。
`linkage.md` 里往 `CanProvideHeatBlockList` 追加名字的办法照旧有效。

### 能煎烤什么

煎锅、炉灶、手持煎锅能煎什么，先看农夫乐事的表 `CanCookedFoodDict`（`linkage.md` 可以追加），表里没有的再问引擎的营火配方。
给你的生肉写一份营火配方（配方 JSON 的 `tags` 里带 `campfire`），它就能放到农夫乐事的煎锅、炉灶上煎，煎好是你配方里的东西。
食谱书和 JEI 里"能煎烤的东西"那几页只列表里的。

基岩版的三种蛋（鸡蛋、蓝色鸡蛋、棕色鸡蛋，原版标签 `minecraft:egg` 的成员）一视同仁：都能在煎锅上煎成煎蛋，只煎一面，炉灶站点的烤架不收，
熔炉、烟熏炉、营火也收（JE 只有一种蛋）。工作台配方里的蛋还只认鸡蛋。

## 词表

标签名是 `common:` 加小写、下划线连接的单数名词，对应 JE 的 `forge:` / `c:` 标签；物品名本身就是复数的照物品名（`tomato_seeds`、`mutton_chops`）。
团队里已经在用的名字照用，其中有复数的（`common:crops`、`common:seeds`、`common:flowers`、机械动力的 `common:leaves`、`common:buttons`）；新起的名字用单数。

- `common:mushroom` 是能吃的蘑菇（红蘑菇、棕蘑菇），和机械动力的 `common:mushroom_block`（蘑菇方块）不是一回事。
- 小麦粉用机械动力的 `common:wheat_flour`，没有 `common:flour`。
- 鸡蛋用原版自带的 `minecraft:egg`（鸡蛋、蓝色鸡蛋、棕色鸡蛋），不另起。
- 农夫乐事没有成员的名字只在下表里列着，不生成文件，别的模组可以往里登记。

<!-- gen_tags: 词表开始（tools/gen_tags.py 从 Shared/Data/Tags.py 生成，别手改） -->
| 标签 | 种类 | 意思 | 对应 JE | 农夫乐事登记的 | 农夫乐事在哪里读 |
| --- | --- | --- | --- | --- | --- |
| `common:tomato` | 物品 | 番茄 | `forge:crops/tomato`、`forge:vegetables/tomato` | `arris:tomato` | — |
| `common:tomato_seeds` | 物品 | 番茄种子 | `forge:seeds/tomato` | `arris:tomato_seeds` | — |
| `common:rice` | 物品 | 米（也是水稻的种子） | `forge:crops/rice`、`forge:grain/rice`、`forge:seeds/rice` | `arris:rice` | — |
| `common:rice_panicle` | 物品 | 稻穗 | — | `arris:rice_panicle` | — |
| `common:cooked_rice` | 物品 | 米饭 | `forge:cooked_rice` | `arris:cooked_rice` | — |
| `common:dough` | 物品 | 面团 | `forge:dough`、`forge:dough/wheat` | `arris:wheat_dough` | — |
| `common:fried_egg` | 物品 | 煎蛋 | `forge:cooked_eggs` | `arris:fried_egg` | — |
| `common:mutton_chops` | 物品 | 生羊排 | — | `arris:mutton_chops` | — |
| `common:cooked_mutton_chops` | 物品 | 熟羊排 | — | `arris:cooked_mutton_chops` | — |
| `common:knife` | 物品 | 刀 | `forge:tools/knives`、`farmersdelight:tools/knives` | `arris:flint_knife`、`arris:golden_knife`、`arris:iron_knife`、`arris:diamond_knife`、`arris:netherite_knife` | 是不是刀（Shared/Rules/Knives） |
| `arris:knife` | 物品 | 刀（农夫乐事的老标签，照旧有效） | — | `arris:flint_knife`、`arris:golden_knife`、`arris:iron_knife`、`arris:diamond_knife`、`arris:netherite_knife` | 是不是刀（Shared/Rules/Knives） |
| `common:raw_beef` | 物品 | 生牛肉（含牛肉末） | `forge:raw_beef` | `minecraft:beef`、`arris:minced_beef` | — |
| `common:raw_pork` | 物品 | 生猪肉（含培根） | `forge:raw_pork` | `minecraft:porkchop`、`arris:bacon` | — |
| `common:raw_chicken` | 物品 | 生鸡肉（含鸡块） | `forge:raw_chicken` | `minecraft:chicken`、`arris:chicken_cuts` | — |
| `common:raw_mutton` | 物品 | 生羊肉（含羊排） | `forge:raw_mutton` | `minecraft:mutton`、`arris:mutton_chops` | — |
| `common:raw_meat` | 物品 | 生肉：上面四种和生兔肉 | `forge:raw_meat` | `minecraft:rabbit`、`minecraft:beef`、`arris:minced_beef`、`minecraft:chicken`、`arris:chicken_cuts`、`minecraft:porkchop`、`arris:bacon`、`minecraft:mutton`、`arris:mutton_chops` | — |
| `common:cooked_beef` | 物品 | 熟牛肉（含牛肉饼） | `forge:cooked_beef` | `minecraft:cooked_beef`、`arris:beef_patty` | — |
| `common:cooked_pork` | 物品 | 熟猪肉（含熟培根） | `forge:cooked_pork` | `minecraft:cooked_porkchop`、`arris:cooked_bacon` | — |
| `common:cooked_chicken` | 物品 | 熟鸡肉（含熟鸡块） | `forge:cooked_chicken` | `minecraft:cooked_chicken`、`arris:cooked_chicken_cuts` | — |
| `common:cooked_mutton` | 物品 | 熟羊肉（含熟羊排） | `forge:cooked_mutton` | `minecraft:cooked_mutton`、`arris:cooked_mutton_chops` | — |
| `common:raw_fish` | 物品 | 生鱼（含鱼片，不含河豚） | `forge:raw_fishes` | `minecraft:cod`、`arris:cod_slice`、`minecraft:salmon`、`arris:salmon_slice`、`minecraft:tropical_fish` | — |
| `common:vegetable` | 物品 | 蔬菜（不含卷心菜） | `forge:vegetables` | `minecraft:beetroot`、`minecraft:carrot`、`arris:onion`、`minecraft:potato`、`arris:tomato` | — |
| `common:cabbage` | 物品 | 卷心菜（含卷心菜叶） | `forge:crops/cabbage`、`forge:salad_ingredients`、`forge:salad_ingredients/cabbage` | `arris:cabbage`、`arris:cabbage_leaf` | — |
| `common:milk` | 物品 | 奶（奶桶、奶瓶） | `forge:milk` | `minecraft:milk_bucket`、`arris:milk_bottle` | — |
| `common:mushroom` | 物品 | 能吃的蘑菇 | `forge:mushrooms` | `minecraft:brown_mushroom`、`minecraft:red_mushroom` | — |
| `common:onion` | 物品 | 洋葱 | `forge:crops/onion`、`forge:vegetables/onion` | `arris:onion` | — |
| `common:carrot` | 物品 | 胡萝卜 | `forge:crops/carrot`、`forge:vegetables/carrot` | `minecraft:carrot` | — |
| `common:potato` | 物品 | 土豆 | `forge:crops/potato`、`forge:vegetables/potato` | `minecraft:potato` | — |
| `common:beetroot` | 物品 | 甜菜根 | `forge:crops/beetroot`、`forge:vegetables/beetroot` | `minecraft:beetroot` | — |
| `common:wheat` | 物品 | 小麦 | `forge:crops/wheat`、`forge:grain/wheat` | `minecraft:wheat` | — |
| `common:bread` | 物品 | 面包 | `forge:bread`、`forge:bread/wheat` | `minecraft:bread` | — |
| `common:pasta` | 物品 | 生意面 | `forge:pasta`、`forge:pasta/raw_pasta` | `arris:raw_pasta` | — |
| `common:berry` | 物品 | 浆果 | `forge:berries` | `minecraft:sweet_berries`、`minecraft:glow_berries` | — |
| `common:bone` | 物品 | 骨头 | `forge:bones` | `minecraft:bone` | — |
| `common:raw_cod` | 物品 | 生鳕鱼（含鱼片） | `forge:raw_fishes/cod` | `minecraft:cod`、`arris:cod_slice` | — |
| `common:raw_salmon` | 物品 | 生鲑鱼（含鱼片） | `forge:raw_fishes/salmon` | `minecraft:salmon`、`arris:salmon_slice` | — |
| `common:cooked_fish` | 物品 | 熟鱼（含熟鱼片） | `forge:cooked_fishes` | `minecraft:cooked_cod`、`arris:cooked_cod_slice`、`minecraft:cooked_salmon`、`arris:cooked_salmon_slice` | — |
| `common:cooked_cod` | 物品 | 熟鳕鱼（含熟鱼片） | `forge:cooked_fishes/cod` | `minecraft:cooked_cod`、`arris:cooked_cod_slice` | — |
| `common:cooked_salmon` | 物品 | 熟鲑鱼（含熟鱼片） | `forge:cooked_fishes/salmon` | `minecraft:cooked_salmon`、`arris:cooked_salmon_slice` | — |
| `common:raw_bacon` | 物品 | 生培根 | `forge:raw_bacon` | `arris:bacon` | — |
| `common:cooked_bacon` | 物品 | 熟培根 | `forge:cooked_bacon` | `arris:cooked_bacon` | — |
| `common:cabbage_seeds` | 物品 | 卷心菜种子 | `forge:seeds/cabbage` | `arris:cabbage_seeds` | — |
| `common:water_bucket` | 物品 | 水桶 | `forge:buckets/water` | `minecraft:water_bucket` | — |
| `common:crops` | 物品 | 作物（团队已有的名字） | `forge:crops` | `arris:cabbage`、`arris:cabbage_leaf`、`arris:onion`、`arris:rice`、`arris:tomato` | — |
| `common:seeds` | 物品 | 种子（团队已有的名字） | `forge:seeds` | `arris:cabbage_seeds`、`arris:rice`、`arris:tomato_seeds` | — |
| `common:flowers` | 物品 | 花（团队已有的名字） | `minecraft:flowers` | `arris:wild_carrots`、`arris:wild_potatoes`、`arris:wild_beetroots`、`arris:wild_cabbages`、`arris:wild_tomatoes`、`arris:wild_onions`、`arris:wild_rice` | — |
| `common:heat_source` | 方块 | 热源：方块名就说明在发热 | `farmersdelight:heat_sources` | `minecraft:fire`、`minecraft:soul_fire`、`minecraft:lava`、`minecraft:flowing_lava`、`minecraft:magma`、`arris:stove` | 热源（Shared/Rules/HeatSources） |
| `common:heat_source_lit` | 方块 | 热源：要看方块状态点没点着 | `minecraft:campfires` | `minecraft:campfire`、`minecraft:soul_campfire` | 热源（Shared/Rules/HeatSources，锅底下要点着） |
| `farmersdelight:heat_conductors` | 方块 | 把热传给上面一格的方块 | `farmersdelight:heat_conductors` | `minecraft:hopper` | 锅 / 煎锅下面是它时看再下面一格（HeatSources.conducts） |
| `farmersdelight:tray_heat_sources` | 方块 | 锅 / 煎锅放在上面要画托盘的方块 | `farmersdelight:tray_heat_sources` | `minecraft:lava`、`minecraft:flowing_lava`、`minecraft:campfire`、`minecraft:soul_campfire`、`minecraft:fire`、`minecraft:soul_fire` | 锅 / 煎锅画不画托盘（Server/Helpers/Heat.RefreshHeat） |
| `farmersdelight:compost_activators` | 方块 | 有机肥周围的催化剂 | `farmersdelight:compost_activators` | `minecraft:brown_mushroom`、`minecraft:red_mushroom`、`minecraft:podzol`、`minecraft:mycelium`、`arris:organic_compost_stage0`、`arris:organic_compost_stage1`、`arris:organic_compost_stage2`、`arris:organic_compost_stage3`、`arris:rich_soil`、`arris:rich_soil_farmland`、`arris:rich_soil_farmland_moist`、`arris:brown_mushroom_colony`、`arris:red_mushroom_colony` | 有机肥堆沤的概率（Server/OrganicCompost） |
| `farmersdelight:unaffected_by_rich_soil` | 方块 | 沃土不催熟的植物 | `farmersdelight:unaffected_by_rich_soil` | `minecraft:grass_block`、`minecraft:moss_block`、`minecraft:crimson_nylium`、`minecraft:warped_nylium`、`minecraft:short_grass`、`minecraft:tall_grass`、`minecraft:fern`、`minecraft:large_fern`、`minecraft:twisting_vines`、`minecraft:big_dripleaf`、`minecraft:pink_petals`、`minecraft:sunflower`、`minecraft:lilac`、`minecraft:rose_bush`、`minecraft:peony`、`minecraft:pitcher_plant`、`arris:sandy_shrub`、`arris:brown_mushroom_colony`、`arris:red_mushroom_colony`、`arris:wild_carrots`、`arris:wild_potatoes`、`arris:wild_beetroots`、`arris:wild_cabbages`、`arris:wild_tomatoes`、`arris:wild_onions`、`arris:wild_rice` | 沃土 / 沃土耕地催不催熟上面的植物（Server/BoneMeal.BoostPlant） |
| `minecraft:egg` | 物品（原版自带，不生成文件） | 蛋（原版自带的标签） | `forge:eggs` | `minecraft:egg`、`minecraft:blue_egg`、`minecraft:brown_egg` | — |
| `common:chili` | 物品（农夫乐事没有成员，不生成文件） | 辣椒 | — | — | — |
| `common:fruit` | 物品（农夫乐事没有成员，不生成文件） | 水果 | — | — | — |
| `common:wheat_flour` | 物品（农夫乐事没有成员，不生成文件） | 小麦粉（机械动力的） | — | — | — |
<!-- gen_tags: 词表结束 -->

## 限制

- 要网易 3.10 以上。3.10 以前没有 `netease_tags`，农夫乐事只认自己的东西和物品 JSON 里声明的标签，和以前一样。
- 没有 aux：同一个物品名的不同 aux 是同一组标签。
- 客户端的标签要到进世界的过程中才全（实机：客户端脚本加载完时原版物品还查不到标签，两秒多以后才全）。农夫乐事在这之前按自己的词表答，
  别的模组的东西这时候可能还认不出来，进世界之后就认了。服务端从一开始就是全的。
- 进世界时引擎日志里会有一批 `netease_tags: apply item tag ...: item ... not found`，是引擎在原版物品注册之前先挂了一遍，之后查得到，不是名字写错了。
  名字真写错了的，这条日志会一直出现。
- 营火配方的返回值没有在游戏里核对过形状，农夫乐事解析得比较宽松；认不出来的就当没有这条配方。
- 方块的状态只有服务端读得到：客户端判断热源时不看点没点着。
