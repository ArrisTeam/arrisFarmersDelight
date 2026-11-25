# -*- coding: utf-8 -*-
"""Tags - 物品 / 方块标签的词表：标签名 → 农夫乐事登记的成员（双端，纯数据）

一张表说了算：tools/gen_tags.py 从这里生成 bp/netease_tags/ 的文件（一个标签一个文件；别的模组登记同名标签时引擎把成员合并去重），
Shared/Rules/ItemTags 在没有引擎口（离线测试、Strata 沙箱、3.10 以前的引擎）或者口还没准备好（客户端进世界之前）时按这里作答，
docs/TAGS.md 写的也是这里。

命名：common: + 小写下划线的单数名词，对应 JE 的 forge: / c: 标签；物品本名就是复数的照物品名（tomato_seeds、mutton_chops）。
团队里已经在用的名字照用、不另起（有的是复数，照旧）：common:crops、common:seeds、common:flowers（arrisCreateAdditions 用 netease_tags
登记了原版的作物、种子、花，它的生物质、种子油配方吃这几个标签）、common:dough、common:wheat_flour（机械动力的面团、小麦粉；所以没有 common:flour）。

成员的规矩（网易 3.10 实机量过的，前置包工程 .planning/kaleidoscope/R4-netease-tags-engine.md）：
- 只写农夫乐事自己的和原版的物品 / 方块：写别的模组的名字，对方没装时引擎一直刷 ERROR 日志；
- 只写扁平名（netease_tags 没有 aux），不写 minecraft:planks 这种旧聚合名；
- 不用 #（引用"物品 JSON 里声明的标签"时展开不全），每个标签把成员写全；
- 顺序：静态作答（ItemTags.itemsOf）按这里的顺序给，厨锅配方展开写法照它——和原来 CookingPotRecipes 里那几张列表（JE 标签的展开）一个顺序。
原版自带的标签（minecraft:egg）不生成文件，成员抄在 VANILLA_TAGS 里，没有引擎口时也答得出。
"""

# ---- 物品标签（common:，生成 netease_tags 文件）----
# 同一种东西（REPORT §6.2，用户 2026-11-25 认可）
TOMATO = "common:tomato"
TOMATO_SEEDS = "common:tomato_seeds"
RICE = "common:rice"
RICE_PANICLE = "common:rice_panicle"
COOKED_RICE = "common:cooked_rice"
DOUGH = "common:dough"
FRIED_EGG = "common:fried_egg"
MUTTON_CHOPS = "common:mutton_chops"
COOKED_MUTTON_CHOPS = "common:cooked_mutton_chops"
KNIFE = "common:knife"
# 一类东西（同上）
RAW_BEEF = "common:raw_beef"
RAW_PORK = "common:raw_pork"
RAW_CHICKEN = "common:raw_chicken"
RAW_MUTTON = "common:raw_mutton"
RAW_MEAT = "common:raw_meat"
COOKED_BEEF = "common:cooked_beef"
COOKED_PORK = "common:cooked_pork"
COOKED_CHICKEN = "common:cooked_chicken"
COOKED_MUTTON = "common:cooked_mutton"
RAW_FISH = "common:raw_fish"
VEGETABLE = "common:vegetable"
CABBAGE = "common:cabbage"
MILK = "common:milk"
MUSHROOM = "common:mushroom"
# JE 农夫乐事的配方（厨锅、工作台、砧板）实际用到的标签，同一条命名规则补的
ONION = "common:onion"
CARROT = "common:carrot"
POTATO = "common:potato"
BEETROOT = "common:beetroot"
WHEAT = "common:wheat"
BREAD = "common:bread"
PASTA = "common:pasta"
BERRY = "common:berry"
BONE = "common:bone"
RAW_COD = "common:raw_cod"
RAW_SALMON = "common:raw_salmon"
COOKED_FISH = "common:cooked_fish"
COOKED_COD = "common:cooked_cod"
COOKED_SALMON = "common:cooked_salmon"
RAW_BACON = "common:raw_bacon"
COOKED_BACON = "common:cooked_bacon"
CABBAGE_SEEDS = "common:cabbage_seeds"
WATER_BUCKET = "common:water_bucket"
# 团队里已有的名字（arrisCreateAdditions，它的生物质、种子油配方吃这三个）：农夫乐事的作物、种子照 JE 的 forge:crops / forge:seeds 登记进去；
# common:flowers 在它那里是"所有的花"（照 JE 的 minecraft:flowers：小花、高花、开花的杜鹃……），JE 把七种野生作物放在
# minecraft:small_flowers / tall_flowers 里，所以野生作物登记进 common:flowers
CROPS = "common:crops"
SEEDS = "common:seeds"
FLOWERS = "common:flowers"
# 农夫乐事自己的老标签：linkage.md 让下游给自己的刀挂它（Server/Helpers/Items.IsKnife 认），农夫乐事的五把刀以前没挂
LEGACY_KNIFE = "arris:knife"

# ---- 方块标签 ----
# 热源分两个，因为方块标签不带方块状态：HEAT_SOURCE 是方块名本身就说明在发热的（农夫乐事点着和熄着的炉灶是两个方块名，登记点着的那个）；
# HEAT_SOURCE_LIT 是要看点燃状态的（营火的 extinguished；别的模组一个方块 + lit 状态的炉灶）
HEAT_SOURCE = "common:heat_source"
HEAT_SOURCE_LIT = "common:heat_source_lit"
# 农夫乐事自己的方块标签，名字照 JE 的 farmersdelight:<路径>。读的地方是"名单 ∪ 标签"：原来的名单原样留着，不在名单里的再看标签；
# 这里的成员就是那张名单（测试核对两边一样，名单改了这里跟上、再跑 tools/gen_tags.py）
HEAT_CONDUCTORS = "farmersdelight:heat_conductors"         # 把热传给上面一格（锅下面是它时看再下面一格）：Cooking.HeatConductorList
TRAY_HEAT_SOURCES = "farmersdelight:tray_heat_sources"     # 锅 / 煎锅放在上面要画托盘：Server/Helpers/Heat.ShelfBlockSet

# ---- 原版自带的标签（不生成文件）----
EGG = "minecraft:egg"

# ---- 词表里有、农夫乐事没有成员的名字（不生成文件，docs/TAGS.md 列出来给别的模组用）----
CHILI = "common:chili"
FRUIT = "common:fruit"
WHEAT_FLOUR = "common:wheat_flour"      # 机械动力的小麦粉
WITHOUT_MEMBERS = (CHILI, FRUIT, WHEAT_FLOUR)

_KNIVES = ("arris:flint_knife", "arris:golden_knife", "arris:iron_knife", "arris:diamond_knife", "arris:netherite_knife")
_RAW_BEEF = ("minecraft:beef", "arris:minced_beef")
_RAW_CHICKEN = ("minecraft:chicken", "arris:chicken_cuts")
_RAW_PORK = ("minecraft:porkchop", "arris:bacon")
_RAW_MUTTON = ("minecraft:mutton", "arris:mutton_chops")
_RAW_COD = ("minecraft:cod", "arris:cod_slice")
_RAW_SALMON = ("minecraft:salmon", "arris:salmon_slice")
_COOKED_COD = ("minecraft:cooked_cod", "arris:cooked_cod_slice")
_COOKED_SALMON = ("minecraft:cooked_salmon", "arris:cooked_salmon_slice")

# 物品标签 → 农夫乐事登记的成员（照 JE 1.3.4 的 forge / farmersdelight 标签文件，换成这边的物品名）
ITEM_TAGS = {
    TOMATO: ("arris:tomato",),
    TOMATO_SEEDS: ("arris:tomato_seeds",),
    RICE: ("arris:rice",),
    RICE_PANICLE: ("arris:rice_panicle",),
    COOKED_RICE: ("arris:cooked_rice",),
    DOUGH: ("arris:wheat_dough",),
    FRIED_EGG: ("arris:fried_egg",),
    MUTTON_CHOPS: ("arris:mutton_chops",),
    COOKED_MUTTON_CHOPS: ("arris:cooked_mutton_chops",),
    KNIFE: _KNIVES,
    LEGACY_KNIFE: _KNIVES,
    RAW_BEEF: _RAW_BEEF,
    RAW_PORK: _RAW_PORK,
    RAW_CHICKEN: _RAW_CHICKEN,
    RAW_MUTTON: _RAW_MUTTON,
    RAW_MEAT: ("minecraft:rabbit",) + _RAW_BEEF + _RAW_CHICKEN + _RAW_PORK + _RAW_MUTTON,
    COOKED_BEEF: ("minecraft:cooked_beef", "arris:beef_patty"),
    COOKED_PORK: ("minecraft:cooked_porkchop", "arris:cooked_bacon"),
    COOKED_CHICKEN: ("minecraft:cooked_chicken", "arris:cooked_chicken_cuts"),
    COOKED_MUTTON: ("minecraft:cooked_mutton", "arris:cooked_mutton_chops"),
    RAW_FISH: _RAW_COD + _RAW_SALMON + ("minecraft:tropical_fish",),          # JE 的 forge:raw_fishes：不含河豚
    VEGETABLE: ("minecraft:beetroot", "minecraft:carrot", "arris:onion", "minecraft:potato", "arris:tomato"),
    CABBAGE: ("arris:cabbage", "arris:cabbage_leaf"),                           # JE 不把卷心菜算进 forge:vegetables，单列
    MILK: ("minecraft:milk_bucket", "arris:milk_bottle"),
    MUSHROOM: ("minecraft:brown_mushroom", "minecraft:red_mushroom"),
    ONION: ("arris:onion",),
    CARROT: ("minecraft:carrot",),
    POTATO: ("minecraft:potato",),
    BEETROOT: ("minecraft:beetroot",),
    WHEAT: ("minecraft:wheat",),
    BREAD: ("minecraft:bread",),
    PASTA: ("arris:raw_pasta",),
    BERRY: ("minecraft:sweet_berries", "minecraft:glow_berries"),
    BONE: ("minecraft:bone",),
    RAW_COD: _RAW_COD,
    RAW_SALMON: _RAW_SALMON,
    COOKED_FISH: _COOKED_COD + _COOKED_SALMON,
    COOKED_COD: _COOKED_COD,
    COOKED_SALMON: _COOKED_SALMON,
    RAW_BACON: ("arris:bacon",),
    COOKED_BACON: ("arris:cooked_bacon",),
    CABBAGE_SEEDS: ("arris:cabbage_seeds",),
    WATER_BUCKET: ("minecraft:water_bucket",),
    CROPS: ("arris:cabbage", "arris:cabbage_leaf", "arris:onion", "arris:rice", "arris:tomato"),
    SEEDS: ("arris:cabbage_seeds", "arris:rice", "arris:tomato_seeds"),     # JE 的 forge:seeds/rice 就是米
    FLOWERS: ("arris:wild_carrots", "arris:wild_potatoes", "arris:wild_beetroots", "arris:wild_cabbages", "arris:wild_tomatoes",
              "arris:wild_onions", "arris:wild_rice"),                       # JE：前六种在 minecraft:small_flowers，野生稻在 tall_flowers
}

# 方块标签 → 农夫乐事登记的成员
BLOCK_TAGS = {
    HEAT_SOURCE: ("minecraft:fire", "minecraft:soul_fire", "minecraft:lava", "minecraft:flowing_lava", "minecraft:magma", "arris:stove"),
    HEAT_SOURCE_LIT: ("minecraft:campfire", "minecraft:soul_campfire"),
    HEAT_CONDUCTORS: ("minecraft:hopper",),               # JE 还有可选的 create:chute：别的模组的名字不写，机械动力那边登记
    # JE：熔岩、#minecraft:campfires、#minecraft:fire（基岩版熔岩是两个方块名）
    TRAY_HEAT_SOURCES: ("minecraft:lava", "minecraft:flowing_lava", "minecraft:campfire", "minecraft:soul_campfire", "minecraft:fire",
                        "minecraft:soul_fire"),
}

# 原版自带的物品标签：引擎自己有，不生成文件；这里抄成员（3.10 实机，R4 §3）给没有引擎口时用
VANILLA_TAGS = {
    EGG: ("minecraft:egg", "minecraft:blue_egg", "minecraft:brown_egg"),
}

# 每个标签对应的 JE 标签名（docs/TAGS.md 用；也是"JE 配方里的标签名 → 这里的名字"的别名表：一个 JE 物品标签名只对应这里的一个物品标签）。
# JE 1.20 的农夫乐事用 forge:；cooked_rice 是 JE 森罗厨房定义的（它把两边的米饭都放进去）；heat_source 是 farmersdelight:heat_sources 里
# 不看状态的那部分，heat_source_lit 是里面要看点燃状态的 #minecraft:campfires（JE 的 HeatableBlockEntity：带 LIT 的看 LIT）
JE_NAMES = {
    TOMATO: ("forge:crops/tomato", "forge:vegetables/tomato"),
    TOMATO_SEEDS: ("forge:seeds/tomato",),
    RICE: ("forge:crops/rice", "forge:grain/rice", "forge:seeds/rice"),
    COOKED_RICE: ("forge:cooked_rice",),
    DOUGH: ("forge:dough", "forge:dough/wheat"),
    FRIED_EGG: ("forge:cooked_eggs",),
    KNIFE: ("forge:tools/knives", "farmersdelight:tools/knives"),
    RAW_BEEF: ("forge:raw_beef",),
    RAW_PORK: ("forge:raw_pork",),
    RAW_CHICKEN: ("forge:raw_chicken",),
    RAW_MUTTON: ("forge:raw_mutton",),
    RAW_MEAT: ("forge:raw_meat",),
    COOKED_BEEF: ("forge:cooked_beef",),
    COOKED_PORK: ("forge:cooked_pork",),
    COOKED_CHICKEN: ("forge:cooked_chicken",),
    COOKED_MUTTON: ("forge:cooked_mutton",),
    RAW_FISH: ("forge:raw_fishes",),
    VEGETABLE: ("forge:vegetables",),
    CABBAGE: ("forge:crops/cabbage", "forge:salad_ingredients", "forge:salad_ingredients/cabbage"),
    MILK: ("forge:milk",),
    MUSHROOM: ("forge:mushrooms",),
    ONION: ("forge:crops/onion", "forge:vegetables/onion"),
    CARROT: ("forge:crops/carrot", "forge:vegetables/carrot"),
    POTATO: ("forge:crops/potato", "forge:vegetables/potato"),
    BEETROOT: ("forge:crops/beetroot", "forge:vegetables/beetroot"),
    WHEAT: ("forge:crops/wheat", "forge:grain/wheat"),
    BREAD: ("forge:bread", "forge:bread/wheat"),
    PASTA: ("forge:pasta", "forge:pasta/raw_pasta"),
    BERRY: ("forge:berries",),
    BONE: ("forge:bones",),
    RAW_COD: ("forge:raw_fishes/cod",),
    RAW_SALMON: ("forge:raw_fishes/salmon",),
    COOKED_FISH: ("forge:cooked_fishes",),
    COOKED_COD: ("forge:cooked_fishes/cod",),
    COOKED_SALMON: ("forge:cooked_fishes/salmon",),
    RAW_BACON: ("forge:raw_bacon",),
    COOKED_BACON: ("forge:cooked_bacon",),
    CABBAGE_SEEDS: ("forge:seeds/cabbage",),
    WATER_BUCKET: ("forge:buckets/water",),
    CROPS: ("forge:crops",),
    SEEDS: ("forge:seeds",),
    FLOWERS: ("minecraft:flowers",),
    EGG: ("forge:eggs",),
    HEAT_SOURCE: ("farmersdelight:heat_sources",),
    HEAT_SOURCE_LIT: ("minecraft:campfires",),
    HEAT_CONDUCTORS: (HEAT_CONDUCTORS,),
    TRAY_HEAT_SOURCES: (TRAY_HEAT_SOURCES,),
}

# 引擎口什么时候算"准备好"（Shared/Rules/TagPort）：反查这个物品标签，里面出现了这件原版物品——农夫乐事自己登记的原版成员到了，
# 别的包登记的也就到了（客户端进世界之前反查不到原版成员，R4 §6 第 7 项）。这一对必须在 ITEM_TAGS 里（测试核对）
READY_PROBE = (RAW_BEEF, "minecraft:beef")
