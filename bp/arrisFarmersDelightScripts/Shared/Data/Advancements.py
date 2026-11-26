# -*- coding: utf-8 -*-
"""Advancements - JE 农夫乐事的 21 条进度：交给成就系统（arrisAdvancements）的节点，和每条怎么算做到（双端，纯数据）

节点照 JE 的 data/farmersdelight/advancements/main/*.json（FDAdvancementGenerator 生成）：ID 用 JE 的（farmersdelight:main/<名字>），
父子、框（task / goal / challenge）、隐藏、弹窗（show_toast）、全服播报（announce）、经验奖励（xp）都照 JE；标题和描述照抄 JE 官方中文翻译
（zh_cn.json 的 advancements.farmersdelight.<名字>.title / .description，英文客户端里也是中文）；图标换成本包的物品名。
根节点的背景 JE 是砖块贴图（minecraft:textures/block/bricks.png），这里用基岩原版资源包里的 textures/blocks/brick（16x16，和成就系统自带的背景一样大）。
tests/test_advancements.py 对着 .refs 里的 21 个 JSON 复算父子、框、开关、经验、标题、条件个数。

CRITERIA：进度名 -> (要求, [(子条件名, 种类, 键)])。要求 any = JE 的 OR（做到任何一个就完成，setFinish），
all = AND（每个子条件各记一次，goal = 子条件数，addProgressUnique 的子键是子条件名）。子条件名照 JE 的 criteria 名。种类：
    ready      玩家的进度装好了（JE 根节点：背包有任何变化就给，等于进游戏就给）
    obtain     背包里有了这些物品之一（JE inventory_changed）
    placed     玩家放下了这些方块之一（JE placed_block）：引擎放的、种子种下去的，和脚本替玩家放的（Server/Helpers/Deeds.PLACED_BLOCK）
    cut        在砧板上切开了一件（JE 自定义的 use_cutting_board）：经典右键和砧板站点都报 Deeds.CUT_ON_BOARD
    skillet    手持煎锅煎好了一件（JE consume_item 煎锅：用完一次手持的煎锅）：Deeds.SKILLET_COOKED
    harvested  右键采摘了这些方块之一（JE item_used_on_block，番茄藤在绳子上、采完那一格回到 0 级）：Deeds.HARVESTED
    effect     身上有了这个效果（JE effects_changed）
    eaten      吃了这个（JE consume_item）
    hit        这些实体被玩家扔的烂番茄打中（JE player_hurt_entity：直接来源是烂番茄的弹射物伤害，受伤的在 raiders 实体标签里）
"""
NAMESPACE = "farmersdelight:main/"
BACKGROUND = "textures/blocks/brick"

KNIVES = ("arris:flint_knife", "arris:iron_knife", "arris:diamond_knife", "arris:golden_knife", "arris:netherite_knife")
# JE 的 raiders 实体标签：唤魔者、幻术师、掠夺者、劫掠兽、卫道士、女巫。基岩版没有幻术师
RAIDERS = ("minecraft:evocation_illager", "minecraft:pillager", "minecraft:ravager", "minecraft:vindicator", "minecraft:witch")
# 种下去以后那一格是什么方块：原版的、本包的作物，沃土耕地上的原版作物（Server/RichSoil 换成的那几个），蘑菇放在有机肥 / 沃土上直接长成的菌落
CROPS = (
    ("wheat", ("minecraft:wheat", "arris:rich_soil_wheat0")),
    ("beetroot", ("minecraft:beetroot", "arris:rich_soil_beetroot0")),
    ("carrot", ("minecraft:carrots", "arris:rich_soil_carrots0")),
    ("potato", ("minecraft:potatoes", "arris:rich_soil_potatoes0")),
    ("cabbage", ("arris:cabbages_stage0",)),
    ("tomato", ("arris:budding_tomatoes_stage0",)),
    ("onion", ("arris:onions_stage0",)),
    ("rice", ("arris:rice_stage0",)),
    ("melon", ("minecraft:melon_stem",)),
    ("pumpkin", ("minecraft:pumpkin_stem",)),
    ("sweet_berries", ("minecraft:sweet_berry_bush",)),
    ("sugar_cane", ("minecraft:reeds",)),
    ("kelp", ("minecraft:kelp",)),
    ("cocoa", ("minecraft:cocoa",)),
    ("nether_wart", ("minecraft:nether_wart",)),
    ("chorus_flower", ("minecraft:chorus_flower",)),
    ("brown_mushroom", ("minecraft:brown_mushroom", "arris:brown_mushroom_colony")),
    ("red_mushroom", ("minecraft:red_mushroom", "arris:red_mushroom_colony")),
    ("glow_berries", ("minecraft:cave_vines", "minecraft:cave_vines_head_with_berries", "minecraft:cave_vines_body_with_berries")),
)
# 拿着这些东西对方块用、点的那一面外面那一格变成了这些方块，就算种下去了（种子类放方块时引擎报不报放置事件没核实，两条路都认）
PLANTERS = {
    "minecraft:wheat_seeds": ("minecraft:wheat",), "minecraft:beetroot_seeds": ("minecraft:beetroot",),
    "minecraft:carrot": ("minecraft:carrots",), "minecraft:potato": ("minecraft:potatoes",),
    "arris:cabbage_seeds": ("arris:cabbages_stage0",), "arris:tomato_seeds": ("arris:budding_tomatoes_stage0",),
    "arris:onion": ("arris:onions_stage0",), "minecraft:melon_seeds": ("minecraft:melon_stem",),
    "minecraft:pumpkin_seeds": ("minecraft:pumpkin_stem",), "minecraft:sweet_berries": ("minecraft:sweet_berry_bush",),
    "minecraft:sugar_cane": ("minecraft:reeds",), "minecraft:kelp": ("minecraft:kelp",), "minecraft:cocoa_beans": ("minecraft:cocoa",),
    "minecraft:nether_wart": ("minecraft:nether_wart",), "minecraft:chorus_flower": ("minecraft:chorus_flower",),
    "minecraft:brown_mushroom": ("minecraft:brown_mushroom",), "minecraft:red_mushroom": ("minecraft:red_mushroom",),
    "minecraft:glow_berries": ("minecraft:cave_vines", "minecraft:cave_vines_head_with_berries", "minecraft:cave_vines_body_with_berries"),
}
# 厨神当道：JE 的 27 道菜（子条件名是 JE 的物品名，本包的物品名多半一样，牛肉炖菜是 arris:cookbeef_stew）
DISHES = ("mixed_salad", "cooked_rice", "bone_broth", "beef_stew", "vegetable_soup", "fish_stew", "chicken_soup", "fried_rice", "pumpkin_soup",
          "baked_cod_stew", "noodle_soup", "onion_soup", "bacon_and_eggs", "ratatouille", "steak_and_potatoes", "pasta_with_meatballs",
          "pasta_with_mutton_chop", "mushroom_rice", "roasted_mutton_chops", "vegetable_noodles", "squid_ink_pasta", "grilled_salmon",
          "roast_chicken", "stuffed_pumpkin", "honey_glazed_ham", "shepherds_pie", "gleaming_salad")
OUR_NAMES = {"beef_stew": "cookbeef_stew"}
FEASTS = ("roast_chicken", "stuffed_pumpkin", "honey_glazed_ham", "shepherds_pie", "gleaming_salad", "rice_roll_medley")


def _ours(name):
    return "arris:" + OUR_NAMES.get(name, name)


def _each(kind, pairs):
    return [(sub, kind, keys) for sub, keys in pairs]


CRITERIA = {
    "root": ("any", [("seeds", "ready", ())]),
    "craft_knife": ("any", _each("obtain", [(name.split(":")[1], (name,)) for name in KNIVES])),
    "harvest_straw": ("any", [("harvest_straw", "obtain", ("arris:straw",))]),
    "place_organic_compost": ("any", [("place_organic_compost", "placed", ("arris:organic_compost_stage0",))]),
    "get_rich_soil": ("any", [("get_rich_soil", "obtain", ("arris:rich_soil",))]),
    "get_ham": ("any", [("ham", "obtain", ("arris:ham",)), ("smoked_ham", "obtain", ("arris:smoked_ham",))]),
    "use_cutting_board": ("any", [("cutting_board", "cut", ())]),
    "obtain_netherite_knife": ("any", [("obtain_netherite_knife", "obtain", ("arris:netherite_knife",))]),
    "get_fd_seed": ("any", _each("obtain", [(name, ("arris:" + name,)) for name in ("cabbage_seeds", "tomato_seeds", "onion", "rice")])),
    "get_mushroom_colony": ("any", _each("obtain", [(name, ("arris:" + name,)) for name in ("brown_mushroom_colony", "red_mushroom_colony")])),
    "plant_rice": ("any", [("plant_rice", "placed", ("arris:rice_stage0",))]),
    "harvest_ropelogged_tomato": ("any", [("harvest_ropelogged_tomato", "harvested", ("arris:tomatoes_vine_stage3",))]),
    "hit_raider_with_rotten_tomato": ("any", [("hit_raider_with_rotten_tomato", "hit", RAIDERS)]),
    "plant_all_crops": ("all", _each("placed", CROPS)),
    "place_campfire": ("any", [("campfire", "placed", ("minecraft:campfire",)), ("soul_campfire", "placed", ("minecraft:soul_campfire",))]),
    "use_skillet": ("any", [("skillet", "skillet", ())]),
    "place_skillet": ("any", [("skillet", "placed", ("arris:skillet",))]),
    "place_cooking_pot": ("any", [("cooking_pot", "placed", ("arris:cooking_pot",))]),
    "eat_nourishing_food": ("any", [("nourishment", "effect", ("arris:nourishment",))]),
    "place_feast": ("any", _each("placed", [(name, ("arris:%s_block_stage0" % name,)) for name in FEASTS])),
    "master_chef": ("all", _each("eaten", [(name, (_ours(name),)) for name in DISHES])),
}


def _node(name, parent, frame, icon, toast, announce, xp=None):
    """JE 的 getAdvancement(parent, display, name, frame, showToast, announceToChat, hidden)：21 条都不隐藏。"""
    requirement, subs = CRITERIA[name]
    node = {"id": NAMESPACE + name, "title": TEXTS[name][0], "description": TEXTS[name][1], "frame": frame,
            "goal": len(subs) if requirement == "all" else 1, "icon": {"item": icon, "aux": 0},
            "hidden": False, "show_toast": toast, "announce": announce}
    if parent:
        node["parent"] = NAMESPACE + parent
    else:
        node["background"] = BACKGROUND
    if xp:
        node["xp"] = xp
    return node


# JE 官方中文翻译（assets/farmersdelight/lang/zh_cn.json），照抄
TEXTS = {
    "root": ("农夫乐事", "美味的世界在等着你！"),
    "craft_knife": ("刀耕火种", "合成一把刀来从植物和动物上获取更多资源！"),
    "harvest_straw": ("救命稻草", "使用刀割下长草的植物以获取一些草秆"),
    "place_organic_compost": ("先进堆肥", "放置一些有机堆肥。要是有阳光、水和蘑菇就更好了!"),
    "get_rich_soil": ("植物肥料", "有机堆肥会慢慢分解最终变成沃土，为你的农场增光添彩！"),
    "get_ham": ("狂野屠夫", "刀可以更精准仔细地切开动物的肉。刀劈有时候能产出更大的肉块！"),
    "use_cutting_board": ("当心伤手……", "工具到手，在砧板上切开一些东西"),
    "obtain_netherite_knife": ("没这金刚钻的话……", "要么在你的刀上花一整块下界合金锭，要么从厨房里出去"),
    "get_fd_seed": ("野生作物", "有四种新的作物在野外等待着你，你需要跨越山和大海……或者只需要翻翻箱子。"),
    "plant_rice": ("倾斜稻根", "在浅水洼里种一些稻米"),
    "harvest_ropelogged_tomato": ("采田艹加", "在番茄顶上挂些绳子，让它长得更高"),
    "hit_raider_with_rotten_tomato": ("嘘！去！", "向那些讨厌的入侵者扔一个烂番茄！"),
    "get_mushroom_colony": ("我们当中出了内“菌”", "在暗处的沃土上种点蘑菇，看着菌落长出来，然后剪掉它！"),
    "plant_all_crops": ("轮作", "种植所有你找得到的水果、蔬菜，或是菌类！"),
    "place_campfire": ("点燃营火", "放置一个营火，让夜晚不再寒冷"),
    "use_skillet": ("移动厨房", "煎锅能让你轻松烹饪食物。在另一只手上把食物拿好，然后离热源近些！"),
    "place_skillet": ("滋滋火热！", "潜行时把煎锅作为方块放置下来"),
    "place_cooking_pot": ("晚餐上桌喽！", "放置一个厨锅，准备做饭！"),
    "eat_nourishing_food": ("服务周到", "一盘丰盛的食物会让你获得滋养很长一段时间！"),
    "place_feast": ("一顿盛宴", "有些食物最好拿到台面上分享给朋友。准备好盛饭的餐具吧！"),
    "master_chef": ("厨神当道", "把全部菜肴都品尝一遍！"),
}

# 父先子后（成就系统一次注册整棵时要这样）；图标：JE 的物品换成本包的名字
NODES = [
    _node("root", None, "task", "arris:cooking_pot", False, False),
    _node("craft_knife", "root", "task", "arris:flint_knife", True, True),
    _node("harvest_straw", "craft_knife", "task", "arris:straw", True, False),
    _node("place_organic_compost", "harvest_straw", "task", "arris:organic_compost_stage0", True, False),
    _node("get_rich_soil", "place_organic_compost", "goal", "arris:rich_soil", True, True),
    _node("get_ham", "craft_knife", "task", "arris:ham", True, False),
    _node("use_cutting_board", "craft_knife", "task", "arris:cutting_board", True, False),
    _node("obtain_netherite_knife", "use_cutting_board", "challenge", "arris:netherite_knife", True, True, xp=200),
    _node("get_fd_seed", "root", "task", "arris:wild_onions", True, True),
    _node("get_mushroom_colony", "get_fd_seed", "task", "arris:red_mushroom_colony", True, False),
    _node("plant_rice", "get_fd_seed", "task", "arris:rice", True, False),
    _node("harvest_ropelogged_tomato", "get_fd_seed", "task", "arris:tomato", True, False),
    _node("hit_raider_with_rotten_tomato", "harvest_ropelogged_tomato", "task", "arris:rotten_tomato", True, True),
    _node("plant_all_crops", "plant_rice", "challenge", "arris:cabbage", True, True, xp=100),
    _node("place_campfire", "root", "task", "minecraft:campfire", True, True),
    _node("use_skillet", "place_campfire", "task", "arris:skillet_item", True, False),
    _node("place_skillet", "use_skillet", "task", "arris:skillet_item", True, False),
    _node("place_cooking_pot", "place_campfire", "goal", "arris:cooking_pot", True, True),
    _node("eat_nourishing_food", "place_cooking_pot", "task", "arris:steak_and_potatoes", True, False),
    _node("place_feast", "eat_nourishing_food", "task", "arris:roast_chicken_block_stage0", True, True),
    _node("master_chef", "place_feast", "challenge", "arris:honey_glazed_ham", True, True, xp=200),
]
