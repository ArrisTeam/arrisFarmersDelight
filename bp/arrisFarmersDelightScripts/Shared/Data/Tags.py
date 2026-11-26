# -*- coding: utf-8 -*-
"""Tags - 物品 / 方块标签的词表：标签名 → 农夫乐事登记的成员（双端，纯数据）

一张表说了算：tools/gen_tags.py 从 ITEM_TAG_FILES / BLOCK_TAG_FILES 生成 bp/netease_tags/ 的文件（一个标签一个文件；别的模组登记同名标签时
引擎把成员合并去重），Shared/Rules/ItemTags 在没有引擎口（离线测试、Strata 沙箱、3.10 以前的引擎）或者口还没准备好（客户端进世界之前）时
按展开后的 ITEM_TAGS / BLOCK_TAGS 作答，docs/TAGS.md 写的也是这里。

团队的烹饪原料标签以森罗物语厨房网易版的 18 个为准（它 2026-11-26 的提交 2df8e1c，COOKING_STANDARD）：平铺、单数的 common: 名，
是"粗"的类（生的熟的都算，蛋里有煎蛋）。同一个概念用规范的名字；农夫乐事的东西照 JE 登记进对应的粗标签（BEEF……SEED，用 # 嵌自己的细标签，
依据见 docs/TAGS.md「和森罗物语的标签对照」），农夫乐事自己的配方不读粗标签：厨锅、工作台、砧板照旧读下面的细标签（生 / 熟分开是 JE 配方的原意），
蛋照旧读原版的 minecraft:egg。

细标签的命名（主会话 2026-11-26 定的，docs/TAGS.md 开头）：名字照 JE 1.21、成员照 JE 1.20.1（移植的基线 FD 1.3.4）。
- common: + JE 1.21 的 c: 名的最后一段（c:crops/tomato -> tomato、c:foods/raw_beef -> raw_beef、c:tools/knife -> knife），一律单数：
  只有一层的类目名 JE 写复数，这边照团队烹饪原料标签的规范（森罗物语厨房定的，平铺、单数）写单数：c:bones -> bone、c:mushrooms -> mushroom；
  团队里已经在用的复数名照旧（下面的 crops、seeds、flowers）；
- 最后一段只是材料名的，照机械动力把类目的单数接在后面（c:buckets/water -> water_bucket；机械动力的 c:plates/iron -> iron_plate、
  c:flours/wheat -> wheat_flour）；JE 没有对应 c: 名的照物品名（rice_panicle、mutton_chops、tomato_seeds）；
- JE 农夫乐事自己的标签照 JE 原名 farmersdelight:<路径>；不用 / 分层。
团队里已经在用的名字照用（都和上面对得上）：common:crops、common:seeds、common:flowers（arrisCreateAdditions 用 netease_tags 登记了原版的作物、
种子、花，它的生物质、种子油配方吃这几个标签）、common:dough、common:wheat_flour（机械动力的面团、小麦粉；规范里的面粉是 common:flour，
农夫乐事没有面粉，两个都不登记）。

成员的规矩（网易 3.10 实机量过的，前置包工程 .planning/kaleidoscope/R4-netease-tags-engine.md）：
- 只写农夫乐事自己的和原版的物品 / 方块：写别的模组的名字，对方没装时引擎一直刷 ERROR 日志；
- 只写扁平名（netease_tags 没有 aux），不写 minecraft:planks 这种旧聚合名；
- 嵌套照 JE 用 #：JE 的标签文件里用 # 引别的标签、那个标签这边也登记的地方，文件里也写 "#common:xxx"（主会话 2026-11-26 定的），
  别的模组把番茄登记进 common:tomato，它就自动算蔬菜、算作物，和 JE 一样；1.21 的 c: 文件多引的几处（生 / 熟猪肉引培根、熟肉引四种熟肉、
  叶菜引卷心菜）也照写。# 只引这里登记的同类标签（引擎展开；3.10 实机：反查、按物品问、配方三处都认）。JE 引的是这边没有的标签
  （#minecraft:campfires、#farmersdelight:cabinets/wooden……）就展开写成员；
- 静态作答用展开后的成员（ITEM_TAGS / BLOCK_TAGS，_expanded 按文件的先后展开、重复的去掉）：顺序就是 ItemTags.itemsOf 给的顺序，
  厨锅配方展开写法照它——和原来 CookingPotRecipes 里那几张列表（JE 标签的展开）一个顺序。
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
COOKED_EGG = "common:cooked_egg"
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
# JE 1.21 才有名字、主会话 2026-11-26 定了补上的：熟肉（c:foods/cooked_meat，烤串那一格：JE 1.20.1 写的是熟牛 / 猪 / 鸡 / 羊 / 鱼 / 熟兔肉任一）；
# 沙拉用的叶菜（c:foods/leafy_green = JE 1.20.1 的 forge:salad_ingredients：三明治、沙拉、四道汤读它，和卷心菜卷、饺子读的"卷心菜"分开）
COOKED_MEAT = "common:cooked_meat"
LEAFY_GREEN = "common:leafy_green"
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
# 团队里已有的名字（arrisCreateAdditions，它的生物质、种子油配方吃这三个）：农夫乐事的作物、种子照 JE 的 forge:crops / forge:seeds 登记进去，
# 原版的那部分（JE 里是 Forge 自己给的：甜菜根、胡萝卜、地狱疣、土豆、小麦；四种原版种子）也登记，农夫乐事单独在场时这两个标签也是全的；
# common:flowers 在它那里是"所有的花"（照 JE 的 minecraft:flowers：小花、高花、开花的杜鹃……），JE 把七种野生作物放在
# minecraft:small_flowers / tall_flowers 里，所以野生作物登记进 common:flowers
CROPS = "common:crops"
SEEDS = "common:seeds"
FLOWERS = "common:flowers"
# 团队烹饪原料标签的规范（森罗物语厨房网易版的 18 个，COOKING_STANDARD）里的粗标签：生的熟的都算。农夫乐事的东西照 JE 登记进去（依据：
# docs/TAGS.md「和森罗物语的标签对照」），用 # 嵌自己的细标签：别的模组登记进细标签的东西也跟着算。农夫乐事自己的配方不读这几个
BEEF = "common:beef"
CHICKEN = "common:chicken"
LAMB = "common:lamb"
PORK = "common:pork"
FISH = "common:fish"
ANY_EGG = "common:egg"          # 规范的"蛋"（森罗登记了三种鸡蛋、海龟蛋、嗅探兽蛋、煎蛋）；原版的 minecraft:egg 是 EGG，农夫乐事的配方读那个
SEED = "common:seed"            # 规范的"种子"；机械动力附属在用的复数名 common:seeds 照旧另外登记
# 农夫乐事自己的老标签：linkage.md 让下游给自己的刀挂它（Server/Helpers/Items.IsKnife 认），农夫乐事的五把刀以前没挂
LEGACY_KNIFE = "arris:knife"
# JE 农夫乐事自己的分类物品标签，名字照 JE 的 farmersdelight:<路径>：给别的模组认"哪些是饭菜、小吃、甜食……"，农夫乐事自己不读。
# 成员照 JE 的标签文件（# 展开），换成这边的物品名，原版物品照收
MEALS = "farmersdelight:meals"
SNACKS = "farmersdelight:snacks"
SWEETS = "farmersdelight:sweets"
DRINKS = "farmersdelight:drinks"
FEASTS = "farmersdelight:feasts"
PIES = "farmersdelight:pies"
WILD_CROPS = "farmersdelight:wild_crops"
MUSHROOM_COLONIES = "farmersdelight:mushroom_colonies"
CABINETS = "farmersdelight:cabinets"
SERVING_CONTAINERS = "farmersdelight:serving_containers"

# ---- 方块标签 ----
# 农夫乐事自己的方块标签，名字照 JE 的 farmersdelight:<路径>。读的地方是"名单 ∪ 标签"：原来的名单原样留着，不在名单里的再看标签；
# 这里的成员就是那张名单（测试核对两边一样，名单改了这里跟上、再跑 tools/gen_tags.py）
# 热源照 JE 只有一个标签：在里面就算热，方块有"点没点着"这类状态（lit、*:lit、extinguished）的要点着（JE 的 HeatableBlockEntity：带 LIT 的看 LIT；
# 规则在 Shared/Rules/HeatSources）；写了状态条件的方块（Cooking.HeatSourceStateDict：炼药锅要盛着熔岩）只按条件判。
# 农夫乐事点着和熄着的炉灶是两个方块名，登记的是点着的那个
HEAT_SOURCES = "farmersdelight:heat_sources"               # 给上面的锅 / 煎锅加热：Cooking.CanProvideHeatBlockList + HeatSourceStateDict 里的方块
HEAT_CONDUCTORS = "farmersdelight:heat_conductors"         # 把热传给上面一格（锅下面是它时看再下面一格）：Cooking.HeatConductorList
TRAY_HEAT_SOURCES = "farmersdelight:tray_heat_sources"     # 锅 / 煎锅放在上面要画托盘：Server/Helpers/Heat.ShelfBlockSet
COMPOST_ACTIVATORS = "farmersdelight:compost_activators"   # 有机肥堆沤的催化剂：Farming.COMPOST_ACTIVATORS
UNAFFECTED_BY_RICH_SOIL = "farmersdelight:unaffected_by_rich_soil"     # 沃土不催熟的植物：Farming.UNAFFECTED_BY_RICH_SOIL
MUSHROOM_COLONY_GROWABLE_ON = "farmersdelight:mushroom_colony_growable_on"     # 蘑菇菌落在上面才长：ColonyRules.GROWABLE_ON
DROPS_CAKE_SLICE = "farmersdelight:drops_cake_slice"       # 拿刀右键切下一片蛋糕（JE 的 KnifeItem.onCakeInteraction）：Slicing.CANDLE_CAKES

# ---- 原版自带的标签（不生成文件）----
EGG = "minecraft:egg"

# ---- 词表里有、农夫乐事没有成员的名字（不生成文件，docs/TAGS.md 列出来给别的模组用）----
FRUIT = "common:fruit"
WHEAT_FLOUR = "common:wheat_flour"      # 机械动力的小麦粉
WITHOUT_MEMBERS = (FRUIT, WHEAT_FLOUR)

# ---- 团队烹饪原料标签的规范（森罗物语厨房网易版 2026-11-26 的提交 2df8e1c：它 netease_tags 下的 18 个文件，照名字排）----
# 农夫乐事登记了其中 12 个（上面的常量）。剩下 6 个农夫乐事不登记、不进词表、没有名字常量：辣椒、面粉、生菜、肉丸（农夫乐事没有这些东西，
# JE 里也没有把农夫乐事的东西算进去的依据），肉（common:meat：森罗自己的文件用 # 引了牛、鸡、羊、猪四个，农夫乐事的肉登记进那四个就跟着进去了），
# 面条（common:noodle：用户 2026-11-26 定，意面和面条不是一种，农夫乐事的生意面不进去；JE 里两个模组也是两样）
COOKING_STANDARD = (BEEF, CHICKEN, "common:chili", DOUGH, ANY_EGG, FISH, "common:flour", LAMB, "common:lettuce", "common:meat",
                    "common:meatball", MUSHROOM, "common:noodle", PORK, RICE, SEED, TOMATO, VEGETABLE)

_KNIVES = ("arris:flint_knife", "arris:golden_knife", "arris:iron_knife", "arris:diamond_knife", "arris:netherite_knife")
_RAW_BEEF = ("minecraft:beef", "arris:minced_beef")
_RAW_CHICKEN = ("minecraft:chicken", "arris:chicken_cuts")
_RAW_MUTTON = ("minecraft:mutton", "arris:mutton_chops")
_RAW_COD = ("minecraft:cod", "arris:cod_slice")
_RAW_SALMON = ("minecraft:salmon", "arris:salmon_slice")
_COOKED_COD = ("minecraft:cooked_cod", "arris:cooked_cod_slice")
_COOKED_SALMON = ("minecraft:cooked_salmon", "arris:cooked_salmon_slice")
_WILD_CROPS = ("arris:wild_carrots", "arris:wild_potatoes", "arris:wild_beetroots", "arris:wild_cabbages", "arris:wild_tomatoes",
               "arris:wild_onions", "arris:wild_rice")

# 物品标签 → netease_tags 文件里写的成员（照 JE 1.3.4 的 forge / farmersdelight 标签文件，换成这边的物品名；"#标签" 引这张表里的别的标签）
ITEM_TAG_FILES = {
    TOMATO: ("arris:tomato",),
    TOMATO_SEEDS: ("arris:tomato_seeds",),
    RICE: ("arris:rice",),
    RICE_PANICLE: ("arris:rice_panicle",),
    COOKED_RICE: ("arris:cooked_rice",),
    DOUGH: ("arris:wheat_dough",),
    COOKED_EGG: ("arris:fried_egg",),
    MUTTON_CHOPS: ("arris:mutton_chops",),
    COOKED_MUTTON_CHOPS: ("arris:cooked_mutton_chops",),
    KNIFE: _KNIVES,
    LEGACY_KNIFE: _KNIVES,
    RAW_BEEF: _RAW_BEEF,
    RAW_PORK: ("minecraft:porkchop", "#" + RAW_BACON),                      # 1.21 引培根（1.20.1 直接写培根）
    RAW_CHICKEN: _RAW_CHICKEN,
    RAW_MUTTON: _RAW_MUTTON,
    RAW_MEAT: ("minecraft:rabbit", "#" + RAW_BEEF, "#" + RAW_CHICKEN, "#" + RAW_PORK, "#" + RAW_MUTTON),
    COOKED_BEEF: ("minecraft:cooked_beef", "arris:beef_patty"),
    COOKED_PORK: ("minecraft:cooked_porkchop", "#" + COOKED_BACON),
    COOKED_CHICKEN: ("minecraft:cooked_chicken", "arris:cooked_chicken_cuts"),
    COOKED_MUTTON: ("minecraft:cooked_mutton", "arris:cooked_mutton_chops"),
    COOKED_MEAT: ("minecraft:cooked_rabbit", "#" + COOKED_BEEF, "#" + COOKED_CHICKEN, "#" + COOKED_PORK, "#" + COOKED_MUTTON),
    RAW_FISH: ("#" + RAW_COD, "#" + RAW_SALMON, "minecraft:tropical_fish"),     # JE 的 forge:raw_fishes：不含河豚
    VEGETABLE: ("#" + BEETROOT, "#" + CARROT, "#" + ONION, "#" + POTATO, "#" + TOMATO),
    CABBAGE: ("arris:cabbage", "arris:cabbage_leaf"),                           # JE 不把卷心菜算进 forge:vegetables，单列
    LEAFY_GREEN: ("#" + CABBAGE,),
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
    COOKED_FISH: ("#" + COOKED_COD, "#" + COOKED_SALMON),
    COOKED_COD: _COOKED_COD,
    COOKED_SALMON: _COOKED_SALMON,
    RAW_BACON: ("arris:bacon",),
    COOKED_BACON: ("arris:cooked_bacon",),
    CABBAGE_SEEDS: ("arris:cabbage_seeds",),
    WATER_BUCKET: ("minecraft:water_bucket",),
    CROPS: ("#" + CABBAGE, "#" + ONION, "#" + RICE, "#" + TOMATO,
            "#" + BEETROOT, "#" + CARROT, "minecraft:nether_wart", "#" + POTATO, "#" + WHEAT),
    SEEDS: ("#" + CABBAGE_SEEDS, "#" + RICE, "#" + TOMATO_SEEDS,          # JE 的 forge:seeds/rice 就是米
            "minecraft:beetroot_seeds", "minecraft:melon_seeds", "minecraft:pumpkin_seeds", "minecraft:wheat_seeds"),
    FLOWERS: _WILD_CROPS,                       # JE：前六种野生作物在 minecraft:small_flowers，野生稻在 tall_flowers
    # 团队规范的粗标签：嵌 JE 的生、熟两个细标签（JE 的 forge:raw_* / forge:cooked_*：JE 森罗把自己的生 / 熟牛杂、五花肉、羊排也登记在这两个里，
    # 网易版森罗的粗标签就是两个的合并）。培根算猪肉（JE 的 forge:raw_pork / cooked_pork 有培根），火腿不算（JE 没把火腿放进任何肉的标签）
    BEEF: ("#" + RAW_BEEF, "#" + COOKED_BEEF),
    CHICKEN: ("#" + RAW_CHICKEN, "#" + COOKED_CHICKEN),
    LAMB: ("#" + RAW_MUTTON, "#" + COOKED_MUTTON),
    PORK: ("#" + RAW_PORK, "#" + COOKED_PORK),
    FISH: ("#" + RAW_FISH, "#" + COOKED_FISH),              # 含鱼片（JE 的 forge:raw_fishes/cod 等有鱼片）、热带鱼，不含河豚
    ANY_EGG: ("#" + COOKED_EGG,),                           # 煎蛋：规范把森罗的煎蛋算进蛋里，JE 的合并表把两边的煎蛋当成一种东西
    SEED: ("#" + CABBAGE_SEEDS, "#" + RICE, "#" + TOMATO_SEEDS),     # JE 的 forge:seeds 里农夫乐事的三样；原版的种子森罗登记了
    # 分类（JE 的 farmersdelight: 物品标签）。炖牛肉这边叫 cookbeef_stew；派的物品是 *_item（方块名是派本身）；
    # 大餐的物品是第 0 阶段的方块（*_block_stage0）
    MEALS: ("minecraft:mushroom_stew", "minecraft:beetroot_soup", "minecraft:rabbit_stew", "arris:mixed_salad", "arris:cooked_rice",
            "arris:bone_broth", "arris:cookbeef_stew", "arris:vegetable_soup", "arris:fish_stew", "arris:chicken_soup", "arris:fried_rice",
            "arris:pumpkin_soup", "arris:baked_cod_stew", "arris:noodle_soup", "arris:onion_soup", "arris:bacon_and_eggs",
            "arris:ratatouille", "arris:steak_and_potatoes", "arris:pasta_with_meatballs", "arris:pasta_with_mutton_chop",
            "arris:mushroom_rice", "arris:roasted_mutton_chops", "arris:vegetable_noodles", "arris:squid_ink_pasta",
            "arris:grilled_salmon", "arris:roast_chicken", "arris:stuffed_pumpkin", "arris:honey_glazed_ham", "arris:shepherds_pie",
            "arris:gleaming_salad"),
    SNACKS: ("arris:barbecue_stick", "arris:egg_sandwich", "arris:chicken_sandwich", "arris:hamburger", "arris:bacon_sandwich",
             "arris:mutton_wrap", "arris:dumplings", "arris:stuffed_potato", "arris:cabbage_rolls", "arris:salmon_roll", "arris:cod_roll",
             "arris:kelp_roll", "arris:kelp_roll_slice"),
    SWEETS: ("minecraft:cake", "minecraft:cookie", "arris:cake_slice", "arris:apple_pie_slice", "arris:sweet_berry_cheesecake_slice",
             "arris:chocolate_pie_slice", "arris:pumpkin_pie_slice", "arris:sweet_berry_cookie", "arris:honey_cookie",
             "arris:melon_popsicle", "arris:glow_berry_custard", "arris:fruit_salad"),
    DRINKS: ("arris:milk_bottle", "arris:apple_cider", "arris:melon_juice", "arris:hot_cocoa"),
    FEASTS: tuple("arris:%s_block_stage0" % feast for feast in (
        "roast_chicken", "stuffed_pumpkin", "shepherds_pie", "honey_glazed_ham", "gleaming_salad", "rice_roll_medley")),
    PIES: ("minecraft:pumpkin_pie", "arris:apple_pie_item", "arris:sweet_berry_cheesecake_item", "arris:chocolate_pie_item"),
    WILD_CROPS: _WILD_CROPS,
    MUSHROOM_COLONIES: ("arris:brown_mushroom_colony", "arris:red_mushroom_colony"),
    # JE：#farmersdelight:cabinets/wooden（展开）
    CABINETS: tuple("arris:%s_cabinet" % wood for wood in (
        "oak", "spruce", "birch", "jungle", "acacia", "dark_oak", "mangrove", "cherry", "bamboo", "crimson", "warped")),
    SERVING_CONTAINERS: ("minecraft:bowl", "minecraft:glass_bottle", "minecraft:bucket"),
}

# 方块标签 → netease_tags 文件里写的成员
BLOCK_TAG_FILES = {
    # JE：岩浆块、熔岩炼药锅、炉灶、#tray_heat_sources。基岩版没有熔岩炼药锅这个方块名，它是炼药锅盛着熔岩的状态（cauldron_liquid = lava）：
    # 这里写炼药锅，盛不盛熔岩按状态条件判（Cooking.HeatSourceStateDict；空的、盛水的炼药锅不热）
    HEAT_SOURCES: ("minecraft:magma", "minecraft:cauldron", "arris:stove", "#" + TRAY_HEAT_SOURCES),
    HEAT_CONDUCTORS: ("minecraft:hopper",),               # JE 还有可选的 create:chute：别的模组的名字不写，机械动力那边登记
    # JE：熔岩、#minecraft:campfires、#minecraft:fire（基岩版熔岩是两个方块名）
    TRAY_HEAT_SOURCES: ("minecraft:lava", "minecraft:flowing_lava", "minecraft:campfire", "minecraft:soul_campfire", "minecraft:fire",
                        "minecraft:soul_fire"),
    # JE：两种蘑菇、灰化土、菌丝、有机肥（基岩版按阶段是四个方块）、沃土、沃土耕地（干、湿两个方块）、#mushroom_colonies
    COMPOST_ACTIVATORS: ("minecraft:brown_mushroom", "minecraft:red_mushroom", "minecraft:podzol", "minecraft:mycelium",
                         "arris:organic_compost_stage0", "arris:organic_compost_stage1", "arris:organic_compost_stage2",
                         "arris:organic_compost_stage3", "arris:rich_soil", "arris:rich_soil_farmland", "arris:rich_soil_farmland_moist",
                         "arris:brown_mushroom_colony", "arris:red_mushroom_colony"),
    # JE：草方块、苔藓块、两种菌岩、草（基岩版 short_grass）、蕨、缠怨藤、大垂滴叶、粉红花簇、沙地灌木、两种菌落、#wild_crops、
    # #minecraft:tall_flowers（展开）；这边的名单另外多了高草丛、大型蕨
    UNAFFECTED_BY_RICH_SOIL: ("minecraft:grass_block", "minecraft:moss_block", "minecraft:crimson_nylium", "minecraft:warped_nylium",
                              "minecraft:short_grass", "minecraft:tall_grass", "minecraft:fern", "minecraft:large_fern",
                              "minecraft:twisting_vines", "minecraft:big_dripleaf", "minecraft:pink_petals",
                              "minecraft:sunflower", "minecraft:lilac", "minecraft:rose_bush", "minecraft:peony", "minecraft:pitcher_plant",
                              "arris:sandy_shrub", "arris:brown_mushroom_colony", "arris:red_mushroom_colony",
                              "arris:wild_carrots", "arris:wild_potatoes", "arris:wild_beetroots", "arris:wild_cabbages",
                              "arris:wild_tomatoes", "arris:wild_onions", "arris:wild_rice"),
    MUSHROOM_COLONY_GROWABLE_ON: ("arris:rich_soil",),
    DROPS_CAKE_SLICE: tuple("minecraft:%scandle_cake" % color for color in (
        "", "white_", "orange_", "magenta_", "light_blue_", "yellow_", "lime_", "pink_", "gray_", "light_gray_", "cyan_", "purple_",
        "blue_", "brown_", "green_", "red_", "black_")),                   # 插了蜡烛的蛋糕：无色加 16 种颜色
}



def _expanded(files):
    """{标签: 文件里写的成员（"#标签" 引同一张表里的标签）} -> {标签: 展开后的成员元组}：按写的先后展开、重复的去掉；引了表里没有的、
    转圈引用的，导入时就报错（测试里就红）。"""
    def members(tag, seen):
        if tag in seen:
            raise ValueError("标签转圈引用：%s" % " -> ".join(seen + (tag,)))
        found = []
        for name in files[tag]:
            for member in (members(name[1:], seen + (tag,)) if name.startswith("#") else (name,)):
                if member not in found:
                    found.append(member)
        return found
    return dict((tag, tuple(members(tag, ()))) for tag in files)


# 静态作答用的展开表（Shared/Rules/ItemTags、厨锅的旧写法展开、测试都读这两张）
ITEM_TAGS = _expanded(ITEM_TAG_FILES)
BLOCK_TAGS = _expanded(BLOCK_TAG_FILES)

# 原版自带的物品标签：引擎自己有，不生成文件；这里抄成员（3.10 实机，R4 §3）给没有引擎口时用
VANILLA_TAGS = {
    EGG: ("minecraft:egg", "minecraft:blue_egg", "minecraft:brown_egg"),
}

# 每个标签对应的 JE 标签名（docs/TAGS.md 分两列：forge: 是 1.20.1 的，c: 是 1.21 的，别的命名空间两边一样）；也是"JE 配方里的标签名 → 这里的名字"
# 的别名表（Shared/Rules/RecipeJson：行为包里照 JE 写的配方 JSON 用这两种名字都认）：一个 JE 物品标签名只对应这里的一个物品标签。
# cooked_rice 是 JE 森罗厨房（1.20.1）和它的兼容包（1.21）定义的；c:foods/raw_fish 在 1.21 含河豚，这边的 raw_fish 不含（= c:foods/safe_raw_fish），
# 照 JE 写的配方里写 raw_fish 的也换成它；cooked_meat、leafy_green 照 1.21 的名字补的（1.20.1 的烤串那一格、forge:salad_ingredients）
JE_NAMES = {
    TOMATO: ("forge:crops/tomato", "forge:vegetables/tomato", "c:crops/tomato", "c:foods/tomato"),
    TOMATO_SEEDS: ("forge:seeds/tomato",),
    RICE: ("forge:crops/rice", "forge:grain/rice", "forge:seeds/rice", "c:crops/rice"),
    COOKED_RICE: ("forge:cooked_rice", "c:foods/cooked_rice"),
    DOUGH: ("forge:dough", "forge:dough/wheat", "c:foods/dough", "c:foods/dough/wheat"),
    COOKED_EGG: ("forge:cooked_eggs", "c:foods/cooked_egg"),
    KNIFE: ("forge:tools/knives", "farmersdelight:tools/knives", "c:tools/knife"),
    RAW_BEEF: ("forge:raw_beef", "c:foods/raw_beef"),
    RAW_PORK: ("forge:raw_pork", "c:foods/raw_pork"),
    RAW_CHICKEN: ("forge:raw_chicken", "c:foods/raw_chicken"),
    RAW_MUTTON: ("forge:raw_mutton", "c:foods/raw_mutton"),
    RAW_MEAT: ("forge:raw_meat", "c:foods/raw_meat"),
    COOKED_BEEF: ("forge:cooked_beef", "c:foods/cooked_beef"),
    COOKED_PORK: ("forge:cooked_pork", "c:foods/cooked_pork"),
    COOKED_CHICKEN: ("forge:cooked_chicken", "c:foods/cooked_chicken"),
    COOKED_MUTTON: ("forge:cooked_mutton", "c:foods/cooked_mutton"),
    COOKED_MEAT: ("c:foods/cooked_meat",),
    RAW_FISH: ("forge:raw_fishes", "c:foods/safe_raw_fish", "c:foods/raw_fish"),
    VEGETABLE: ("forge:vegetables", "c:foods/vegetable"),
    CABBAGE: ("forge:crops/cabbage", "c:crops/cabbage", "c:foods/cabbage"),
    LEAFY_GREEN: ("forge:salad_ingredients", "forge:salad_ingredients/cabbage", "c:foods/leafy_green"),
    MILK: ("forge:milk", "c:drinks/milk"),
    MUSHROOM: ("forge:mushrooms", "c:mushrooms"),
    ONION: ("forge:crops/onion", "forge:vegetables/onion", "c:crops/onion", "c:foods/onion"),
    CARROT: ("forge:crops/carrot", "forge:vegetables/carrot", "c:crops/carrot"),
    POTATO: ("forge:crops/potato", "forge:vegetables/potato", "c:crops/potato"),
    BEETROOT: ("forge:crops/beetroot", "forge:vegetables/beetroot", "c:crops/beetroot"),
    WHEAT: ("forge:crops/wheat", "forge:grain/wheat", "c:crops/wheat"),
    BREAD: ("forge:bread", "forge:bread/wheat", "c:foods/bread"),
    PASTA: ("forge:pasta", "forge:pasta/raw_pasta", "c:foods/pasta"),
    BERRY: ("forge:berries", "c:foods/berry"),
    BONE: ("forge:bones", "c:bones"),
    RAW_COD: ("forge:raw_fishes/cod", "c:foods/raw_cod"),
    RAW_SALMON: ("forge:raw_fishes/salmon", "c:foods/raw_salmon"),
    COOKED_FISH: ("forge:cooked_fishes", "c:foods/cooked_fish"),
    COOKED_COD: ("forge:cooked_fishes/cod", "c:foods/cooked_cod"),
    COOKED_SALMON: ("forge:cooked_fishes/salmon", "c:foods/cooked_salmon"),
    RAW_BACON: ("forge:raw_bacon", "c:foods/raw_bacon"),
    COOKED_BACON: ("forge:cooked_bacon", "c:foods/cooked_bacon"),
    CABBAGE_SEEDS: ("forge:seeds/cabbage",),
    WATER_BUCKET: ("forge:buckets/water", "c:buckets/water"),
    CROPS: ("forge:crops", "c:crops"),
    SEEDS: ("forge:seeds", "c:seeds"),
    FLOWERS: ("minecraft:flowers",),
    MEALS: (MEALS,),
    SNACKS: (SNACKS,),
    SWEETS: (SWEETS,),
    DRINKS: (DRINKS,),
    FEASTS: (FEASTS,),
    PIES: (PIES,),
    WILD_CROPS: (WILD_CROPS,),
    MUSHROOM_COLONIES: (MUSHROOM_COLONIES,),
    CABINETS: (CABINETS,),
    SERVING_CONTAINERS: (SERVING_CONTAINERS,),
    EGG: ("forge:eggs", "c:eggs"),
    HEAT_SOURCES: (HEAT_SOURCES,),
    HEAT_CONDUCTORS: (HEAT_CONDUCTORS,),
    TRAY_HEAT_SOURCES: (TRAY_HEAT_SOURCES,),
    COMPOST_ACTIVATORS: (COMPOST_ACTIVATORS,),
    UNAFFECTED_BY_RICH_SOIL: (UNAFFECTED_BY_RICH_SOIL,),
    MUSHROOM_COLONY_GROWABLE_ON: (MUSHROOM_COLONY_GROWABLE_ON,),
    DROPS_CAKE_SLICE: (DROPS_CAKE_SLICE,),
}

# 引擎口什么时候算"准备好"（Shared/Rules/TagPort）：反查这个物品标签，里面出现了这件原版物品——农夫乐事自己登记的原版成员到了，
# 别的包登记的也就到了（客户端进世界之前反查不到原版成员，R4 §6 第 7 项）。这一对必须在 ITEM_TAGS 里（测试核对）
READY_PROBE = (RAW_BEEF, "minecraft:beef")
