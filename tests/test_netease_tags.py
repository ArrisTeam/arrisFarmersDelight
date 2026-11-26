# -*- coding: utf-8 -*-
# runner: py3
"""行为包的 netease_tags/ 和 docs/TAGS.md 里的词表（tools/gen_tags.py 从词表 Shared/Data/Tags.py 生成）与词表本身。

引擎的规矩（网易 3.10 实机，前置包工程 .planning/kaleidoscope/R4-netease-tags-engine.md）：一个文件一个标签，各模组登记的同名标签合并去重；
成员不存在时引擎一直刷 ERROR 日志（所以只写本包的和原版的，名字要真）；没有 aux（只写扁平名）；# 引用"物品 JSON 里声明的标签"展开不全（这里不用 #）。
锁的事：
  1. 文件和文档的词表是最新的；每个文件 type / identifier / items 三个键，文件名照 identifier，identifier 不重复，成员不重复、没有 #、没有旧聚合名
  2. 成员只有 arris: 和 minecraft: 的：arris: 的在本包的物品 / 方块定义里；minecraft: 的在本机最新游戏的原版创造目录（物品）/ blocks.json（方块）里
     （本机没装游戏时这一项跳过）
  3. 词表：成员和 JE 1.3.4 的 forge / farmersdelight 标签文件对得上（.refs 里有 JE 源码时）；热源标签就是现在的热源方块表；
     一个 JE 物品标签名只对应一个标签（JE 配方的标签名 → 这里的名字，做别名表时不能有歧义）；准备好的探针在表里；没有成员的名字不生成文件
"""
from __future__ import print_function

import io
import json
import os
import re
import subprocess
import sys

import fdtest

Tags = fdtest.load("Shared.Data.Tags")
Cooking = fdtest.load("Shared.Data.Cooking")

TOOL = os.path.join(fdtest.ROOT, "tools", "gen_tags.py")
TAGS_DIR = os.path.join(fdtest.BP, "netease_tags")
JE_DATA = os.path.join(fdtest.ROOT, ".refs", "FarmersDelight", "src", "generated", "resources", "data")
# 旧式聚合名（引擎按 aux 换成扁平物品再取标签，写了只多一条找不到的报错）和改过名的老名字
LEGACY_NAMES = ("minecraft:planks", "minecraft:log", "minecraft:log2", "minecraft:wood", "minecraft:leaves", "minecraft:leaves2",
                "minecraft:sapling", "minecraft:wool", "minecraft:carpet", "minecraft:red_flower", "minecraft:yellow_flower",
                "minecraft:double_plant", "minecraft:tallgrass", "minecraft:dye", "minecraft:fish", "minecraft:cooked_fish",
                "minecraft:clownfish", "minecraft:muttonraw", "minecraft:muttoncooked", "minecraft:stone_slab", "minecraft:stone_block_slab",
                "minecraft:monster_egg", "minecraft:coral", "minecraft:concrete", "minecraft:stained_glass")
NAME = re.compile(r"^[a-z_]+:[a-z0-9_]+$")
IDENTIFIER = re.compile(r"^[a-z_]+:[a-z0-9_/]+$")


def _json(path):
    with io.open(path, encoding="utf-8-sig") as handle:
        return json.loads(handle.read())


def _tagFiles():
    return dict((name, _json(os.path.join(TAGS_DIR, name))) for name in sorted(os.listdir(TAGS_DIR)))


def _definitions(folder, top):
    """本包 folder 下（含子目录）定义的标识符。"""
    found = set()
    for root, _dirs, files in os.walk(os.path.join(fdtest.BP, folder)):
        for name in files:
            if name.endswith(".json"):
                body = _json(os.path.join(root, name)).get(top) or {}
                identifier = (body.get("description") or {}).get("identifier")
                if identifier:
                    found.add(identifier)
    return found


def testTheFilesAreCurrent():
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    result = subprocess.run([sys.executable, TOOL, "--check"], capture_output=True, env=env)
    assert result.returncode == 0, result.stdout.decode("utf-8", "replace") + "\n先跑 py -3 tools/gen_tags.py"


def _docReads():
    """docs/TAGS.md 词表里每个标签的"农夫乐事在哪里读"那一格。"""
    with io.open(os.path.join(fdtest.ROOT, "docs", "TAGS.md"), encoding="utf-8") as handle:
        text = handle.read()
    table = text[text.index("<!-- gen_tags: 词表开始"):text.index("<!-- gen_tags: 词表结束")]      # 文档前面另有几张小表，只看生成的词表
    rows = [line for line in table.splitlines() if line.startswith("| `")]
    return dict((cells[1].strip("` "), cells[-2].strip()) for cells in (row.split("|") for row in rows))   # 最后一列


def testTheDocSaysWhichRecipesReadEachTag():
    """词表的最后一列写着哪几道厨锅菜（每行 Slots 里的 #标签）、哪条砧板配方（CuttingTagDict）读这个标签：对着配方表重新数一遍。"""
    reads = _docReads()
    used = set()
    for row in fdtest.load("Shared.Data.CookingPotRecipes").CookingPotRecipeList:
        for option in (option for slot in row["Slots"] for option in slot):
            if isinstance(option, str) and option.startswith("#"):
                used.add(option[1:])
                assert row["text"] in reads[option[1:]], (option, row["text"], reads[option[1:]])
    cutting = fdtest.load("Shared.Data.Cutting").CuttingTagDict
    for tag in cutting:
        used.add(tag)
        assert "砧板按标签切成" in reads[tag], reads[tag]
    assert {"common:tomato", "common:raw_beef", "common:dough", Tags.EGG} <= used and "饺子" in reads[Tags.DOUGH]
    for tag in set(Tags.ITEM_TAGS) - used:
        assert "厨锅的格子" not in reads[tag] and "砧板按标签" not in reads[tag], (tag, reads[tag])


def testEachFileIsOneWellFormedTag():
    files = _tagFiles()
    assert len(files) == len(Tags.ITEM_TAGS) + len(Tags.BLOCK_TAGS), sorted(files)
    seen = set()
    for name, doc in files.items():
        assert sorted(doc) == ["identifier", "items", "type"] and doc["type"] in ("item", "block"), name
        assert IDENTIFIER.match(doc["identifier"]), name
        assert name == "%s_%s.json" % (doc["type"], doc["identifier"].replace(":", "_").replace("/", "_")), name
        assert (doc["type"], doc["identifier"]) not in seen, name
        seen.add((doc["type"], doc["identifier"]))
        items = doc["items"]
        assert isinstance(items, list) and items and len(set(items)) == len(items), name
        assert all(NAME.match(item) for item in items), "%s：成员只写扁平的名字（没有 #、没有 aux）%r" % (name, items)
        assert not set(items) & set(LEGACY_NAMES), name


def testMembersAreOursOrVanillaAndExist():
    items = _definitions("netease_items_beh", "minecraft:item")
    blocks = _definitions("netease_blocks", "minecraft:block")
    for name, doc in _tagFiles().items():
        own = blocks if doc["type"] == "block" else items | blocks         # 方块也是物品（方块物品）
        for member in doc["items"]:
            space = member.split(":")[0]
            assert space in ("arris", "minecraft"), "%s 写了别的模组的 %s（对方没装时引擎一直刷 ERROR）" % (name, member)
            assert space != "arris" or member in own, "%s 的 %s 本包里没有定义" % (name, member)


def _vanillaNames():
    """本机最新游戏的原版物品名（创造目录）和方块名（资源包 blocks.json）；没装游戏返回 None。"""
    pack = fdtest.vanilla()
    if pack is None:
        return None
    data = os.path.dirname(os.path.dirname(pack))
    catalog = os.path.join(data, "behavior_packs", "vanilla", "item_catalog", "crafting_item_catalog.json")
    with io.open(catalog, encoding="utf-8") as handle:
        itemNames = set(re.findall(r'"(minecraft:[a-z0-9_]+)"', handle.read()))        # 带 // 注释，不按 JSON 读
    blockNames = set("minecraft:" + key for key in _json(os.path.join(pack, "blocks.json")) if key != "format_version")
    return itemNames, blockNames


def testVanillaMembersAreRealNames():
    names = _vanillaNames()
    if names is None:
        print("跳过：本机没有游戏目录（原版名字留到实机读日志）")
        return
    itemNames, blockNames = names
    assert len(itemNames) > 1000 and "minecraft:beef" in itemNames and "minecraft:campfire" in blockNames
    missing = []
    for kind, table in (("item", Tags.ITEM_TAGS), ("item", Tags.VANILLA_TAGS), ("block", Tags.BLOCK_TAGS)):
        # 方块：资源包 blocks.json 的键有几个还是老名字（草方块是 grass），创造目录里的方块物品也算（minecraft:grass_block）
        known = itemNames if kind == "item" else blockNames | itemNames
        missing += ["%s %s" % (tag, member) for tag, members in table.items() for member in members
                    if member.startswith("minecraft:") and member not in known]
    assert not missing, missing


# JE 的名字 → 这边的名字：不是把 farmersdelight: 换成 arris: 就行的（R1 §B.1 末尾的例外），和基岩版原版改了名、拆成几个方块的
JE_ITEMS = {
    "farmersdelight:beef_stew": ("arris:cookbeef_stew",), "farmersdelight:apple_pie": ("arris:apple_pie_item",),
    "farmersdelight:sweet_berry_cheesecake": ("arris:sweet_berry_cheesecake_item",), "farmersdelight:chocolate_pie": ("arris:chocolate_pie_item",),
}
JE_ITEMS.update(("farmersdelight:%s_block" % feast, ("arris:%s_block_stage0" % feast,))
                for feast in ("roast_chicken", "stuffed_pumpkin", "shepherds_pie", "honey_glazed_ham", "gleaming_salad", "rice_roll_medley"))
JE_BLOCKS = {
    "minecraft:lava": ("minecraft:lava", "minecraft:flowing_lava"), "minecraft:grass": ("minecraft:short_grass",),
    "minecraft:twisting_vines_plant": ("minecraft:twisting_vines",), "minecraft:big_dripleaf_stem": ("minecraft:big_dripleaf",),
    "minecraft:magma_block": ("minecraft:magma",),
    "farmersdelight:organic_compost": tuple("arris:organic_compost_stage%d" % stage for stage in range(4)),
    "farmersdelight:rich_soil_farmland": ("arris:rich_soil_farmland", "arris:rich_soil_farmland_moist"),
}
# JE 原版自己的方块标签：.refs 里只有农夫乐事往里加的那几个，原版的成员照 1.20.1 换成基岩版的名字抄在这里；
# Forge 1.20.1 自己的物品标签里的原版部分（Forge 仓库 src/generated/resources/data/forge/tags/items/crops.json、seeds.json，
# 引的 crops/* / seeds/* 展开）：JE 里 forge:crops / forge:seeds = Forge 给的这些 + 农夫乐事文件里的
JE_VANILLA = {
    ("items", "forge:crops"): ("minecraft:beetroot", "minecraft:carrot", "minecraft:nether_wart", "minecraft:potato", "minecraft:wheat"),
    ("items", "forge:seeds"): ("minecraft:beetroot_seeds", "minecraft:melon_seeds", "minecraft:pumpkin_seeds", "minecraft:wheat_seeds"),
    ("blocks", "minecraft:campfires"): ("minecraft:campfire", "minecraft:soul_campfire"),
    ("blocks", "minecraft:fire"): ("minecraft:fire", "minecraft:soul_fire"),
    ("blocks", "minecraft:tall_flowers"): ("minecraft:sunflower", "minecraft:lilac", "minecraft:rose_bush", "minecraft:peony", "minecraft:pitcher_plant"),
}


def _jeTag(name, kind="items", seen=(), optional=None):
    """JE 的物品 / 方块标签展开成这边的名字（farmersdelight: → arris:，例外见 JE_ITEMS / JE_BLOCKS）；.refs 里没有这个标签文件、
    也不是 JE_VANILLA 里抄了成员的原版标签，返回 None。别的模组的可选成员（{"id": ..., "required": false}）不展开，收进 optional。"""
    space, path = name.split(":", 1)
    file = os.path.join(JE_DATA, space, "tags", kind, *path.split("/")) + ".json"
    vanilla = JE_VANILLA.get((kind, name))
    if (not os.path.isfile(file) and vanilla is None) or name in seen:
        return None
    found = list(vanilla or ())
    renames = JE_ITEMS if kind == "items" else JE_BLOCKS
    for value in _json(file)["values"] if os.path.isfile(file) else ():
        if isinstance(value, dict):
            if not value.get("required", True):
                if optional is not None:
                    optional.append(value["id"])
                continue
            value = value["id"]
        if value.startswith("#"):
            members = _jeTag(value[1:], kind, seen + (name,), optional)
            assert members is not None, "%s 引用的 %s 不在 .refs 里" % (name, value)
        else:
            members = renames.get(value) or (value.replace("farmersdelight:", "arris:"),)
        found += [member for member in members if member not in found]
    return found


def testMembersMatchTheJavaTags():
    if not os.path.isdir(JE_DATA):
        print("跳过：没有 JE 源码（.refs/FarmersDelight）")
        return
    checked = 0
    for tag, members in Tags.ITEM_TAGS.items():
        for jeName in Tags.JE_NAMES.get(tag, ()):
            expanded = _jeTag(jeName)
            if expanded is None:
                continue
            checked += 1
            assert sorted(expanded) == sorted(members), "%s（JE %s）：JE 是 %s，这边是 %s" % (tag, jeName, expanded, members)
    assert checked >= 40, checked
    assert _jeTag("forge:eggs") == ["minecraft:egg"] and set(Tags.VANILLA_TAGS[Tags.EGG]) >= {"minecraft:egg"}
    # common:flowers 对的是 JE 的 minecraft:flowers（原版定义，.refs 里没有它的文件）：农夫乐事放进去的是它的 small_flowers + tall_flowers
    flowers = _jeTag("minecraft:small_flowers") + _jeTag("minecraft:tall_flowers")
    assert sorted(flowers) == sorted(Tags.ITEM_TAGS[Tags.FLOWERS]), (flowers, Tags.ITEM_TAGS[Tags.FLOWERS])


def testTheVocabulary():
    itemTags, blockTags = set(Tags.ITEM_TAGS), set(Tags.BLOCK_TAGS)
    assert not itemTags & blockTags and not (itemTags | blockTags) & set(Tags.VANILLA_TAGS)
    assert all(tag.split(":")[0] in ("common", "farmersdelight") for tag in itemTags - {Tags.LEGACY_KNIFE} | blockTags)
    assert not set(Tags.WITHOUT_MEMBERS) & (itemTags | blockTags) and "common:flour" not in itemTags, "机械动力的小麦粉是 common:wheat_flour"
    for table in (Tags.ITEM_TAGS, Tags.BLOCK_TAGS, Tags.VANILLA_TAGS):
        for tag, members in table.items():
            assert isinstance(members, tuple) and members and len(set(members)) == len(members), tag
    assert set(Tags.JE_NAMES) <= itemTags | blockTags | set(Tags.VANILLA_TAGS)
    aliases = {}
    for tag, jeNames in Tags.JE_NAMES.items():
        if tag in blockTags:
            continue
        for jeName in jeNames:
            assert jeName not in aliases, "JE 的 %s 同时对应 %s 和 %s" % (jeName, aliases.get(jeName), tag)
            aliases[jeName] = tag
    probeTag, probeItem = Tags.READY_PROBE
    assert probeItem in Tags.ITEM_TAGS[probeTag] and probeItem.startswith("minecraft:"), "探针要是本包登记进去的原版物品"
    assert Tags.ITEM_TAGS[Tags.KNIFE] == Tags.ITEM_TAGS[Tags.LEGACY_KNIFE]


def _serverHeat():
    """Server/Helpers/Heat（托盘的名单 ShelfBlockSet 在它里面）：换上假引擎再导入。"""
    import fakeengine
    fakeengine.install()
    return fdtest.load("Server.Helpers.Heat")


# 农夫乐事自己的方块标签（farmersdelight:）读的地方是"名单 ∪ 标签"：标签的成员就是那张名单（离线时和原来一样）
LISTED = {
    Tags.HEAT_SOURCES: lambda: Cooking.CanProvideHeatBlockList,
    Tags.HEAT_CONDUCTORS: lambda: Cooking.HeatConductorList,
    Tags.TRAY_HEAT_SOURCES: lambda: _serverHeat().ShelfBlockSet,
    Tags.COMPOST_ACTIVATORS: lambda: fdtest.load("Shared.Data.Farming").COMPOST_ACTIVATORS,
    Tags.UNAFFECTED_BY_RICH_SOIL: lambda: fdtest.load("Shared.Data.Farming").UNAFFECTED_BY_RICH_SOIL,
    Tags.MUSHROOM_COLONY_GROWABLE_ON: lambda: fdtest.load("Shared.Rules.ColonyRules").GROWABLE_ON,
    Tags.DROPS_CAKE_SLICE: lambda: fdtest.load("Shared.Data.Slicing").CANDLE_CAKES,
}

# JE 有、这边还没登记的成员（等实机）：熔岩炼药锅在基岩版是炼药锅（minecraft:cauldron）的 cauldron_liquid 状态，Server/Helpers/Heat 另认；
# 引擎里有没有 lava_cauldron 这个方块名没核实
PENDING = {Tags.HEAT_SOURCES: ("minecraft:lava_cauldron",)}


def testFarmersDelightsOwnBlockTagsAreTheirListsAndCoverJava():
    """farmersdelight: 的方块标签：成员就是读的地方原来的那张名单；JE 标签文件里的成员（展开 #、换成基岩版的名字）都在里面，
    别的模组的可选成员（create:chute）不写。名单改了：这里跟上，再跑 py -3 tools/gen_tags.py。"""
    own = sorted(tag for tag in Tags.BLOCK_TAGS if tag.startswith("farmersdelight:"))
    assert own == sorted(LISTED), "每个 farmersdelight: 方块标签都对着一张名单"
    for tag in own:
        assert sorted(Tags.BLOCK_TAGS[tag]) == sorted(LISTED[tag]()), "%s 和它的名单不一样" % tag
        assert Tags.JE_NAMES[tag] == (tag,), "照 JE 的名字"
    if not os.path.isdir(JE_DATA):
        print("跳过：没有 JE 源码（.refs/FarmersDelight）")
        return
    optional = []
    for tag in own:
        expanded = _jeTag(tag, "blocks", optional=optional)
        assert expanded is not None, tag
        missing = sorted(set(expanded) - set(Tags.BLOCK_TAGS[tag]) - set(PENDING.get(tag, ())))
        assert not missing, "%s：JE 有、这边没有 %s" % (tag, missing)
    assert optional == ["create:chute"], optional


CATEGORIES = ("meals", "snacks", "sweets", "drinks", "feasts", "pies", "wild_crops", "mushroom_colonies", "cabinets", "serving_containers")


def testFarmersDelightsCategoryItemTagsAreJavasFiles():
    """JE 农夫乐事自己的分类物品标签（farmersdelight:meals 等十个，农夫乐事自己不读）：照 JE 的名字，成员就是 JE 标签文件展开、换成这边的名字
    （炖牛肉 cookbeef_stew、派的物品 *_item、大餐的物品 *_block_stage0；原版物品照收）。上面 testMembersMatchTheJavaTags 逐个比，这里锁住十个都在、都比过。"""
    own = sorted(tag for tag in Tags.ITEM_TAGS if tag.startswith("farmersdelight:"))
    assert own == sorted("farmersdelight:" + name for name in CATEGORIES), own
    for tag in own:
        assert Tags.JE_NAMES[tag] == (tag,), tag
    assert Tags.ITEM_TAGS[Tags.WILD_CROPS] == Tags.ITEM_TAGS[Tags.FLOWERS], "野生作物也是花（JE 放在 minecraft:small_flowers / tall_flowers）"
    if not os.path.isdir(JE_DATA):
        print("跳过：没有 JE 源码（.refs/FarmersDelight）")
        return
    for tag in own:
        expanded = _jeTag(tag)
        assert expanded is not None and sorted(expanded) == sorted(Tags.ITEM_TAGS[tag]), (tag, expanded)
    assert len(Tags.ITEM_TAGS[Tags.CABINETS]) == 11 and "minecraft:pumpkin_pie" in Tags.ITEM_TAGS[Tags.PIES]


def testTheHeatTagIsTodaysHeatSources():
    """热源标签照 JE 只有一个（farmersdelight:heat_sources）= 现在的热源方块表（CanProvideHeatBlockList 导入时的样子）；营火点没点着看状态
    （HeatSources 的规则），不再单列一个标签。"""
    members = Tags.BLOCK_TAGS[Tags.HEAT_SOURCES]
    assert sorted(members) == sorted(Cooking.CanProvideHeatBlockList)
    assert {"minecraft:campfire", "minecraft:soul_campfire", "minecraft:magma"} <= set(members)
    assert "arris:stove_extinguish" not in members, "熄着的炉灶不发热"


def testTheBriefsMembers():
    """任务书里定下的几条（A 拿它们还原厨锅格子）。"""
    expect = {
        Tags.TOMATO: ("arris:tomato",), Tags.DOUGH: ("arris:wheat_dough",), Tags.COOKED_EGG: ("arris:fried_egg",),
        Tags.RAW_BEEF: ("minecraft:beef", "arris:minced_beef"), Tags.RAW_PORK: ("minecraft:porkchop", "arris:bacon"),
        Tags.RAW_CHICKEN: ("minecraft:chicken", "arris:chicken_cuts"), Tags.RAW_MUTTON: ("minecraft:mutton", "arris:mutton_chops"),
        Tags.RAW_FISH: ("minecraft:cod", "arris:cod_slice", "minecraft:salmon", "arris:salmon_slice", "minecraft:tropical_fish"),
        Tags.VEGETABLE: ("minecraft:beetroot", "minecraft:carrot", "arris:onion", "minecraft:potato", "arris:tomato"),
        Tags.MUSHROOMS: ("minecraft:brown_mushroom", "minecraft:red_mushroom"), Tags.MILK: ("minecraft:milk_bucket", "arris:milk_bottle"),
        Tags.BERRY: ("minecraft:sweet_berries", "minecraft:glow_berries"), Tags.BONES: ("minecraft:bone",),
        Tags.WATER_BUCKET: ("minecraft:water_bucket",),
    }
    for tag, members in expect.items():
        assert Tags.ITEM_TAGS[tag] == members, tag
    assert Tags.ITEM_TAGS[Tags.RAW_MEAT][0] == "minecraft:rabbit" and len(Tags.ITEM_TAGS[Tags.RAW_MEAT]) == 9
    assert "minecraft:pufferfish" not in Tags.ITEM_TAGS[Tags.RAW_FISH]
    assert Tags.VANILLA_TAGS[Tags.EGG] == ("minecraft:egg", "minecraft:blue_egg", "minecraft:brown_egg")
    assert len(Tags.ITEM_TAGS[Tags.KNIFE]) == 5 and all(name.startswith("arris:") for name in Tags.ITEM_TAGS[Tags.KNIFE])


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
