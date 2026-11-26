# -*- coding: utf-8 -*-
# runner: py3
"""行为包的 netease_tags/ 和 docs/TAGS.md 里的词表（tools/gen_tags.py 从词表 Shared/Data/Tags.py 生成）与词表本身。

引擎的规矩（网易 3.10 实机，前置包工程 .planning/kaleidoscope/R4-netease-tags-engine.md）：一个文件一个标签，各模组登记的同名标签合并去重；
成员不存在时引擎一直刷 ERROR 日志（所以只写本包的和原版的，名字要真）；没有 aux（只写扁平名）；# 引用"物品 JSON 里声明的标签"展开不全，
引 netease_tags 登记的标签、原版标签都展开（第九轮实机：反查、按物品问、配方三处都认）。
锁的事：
  1. 文件和文档的词表是最新的；每个文件 type / identifier / items 三个键，文件名照 identifier，identifier 不重复，成员不重复、没有旧聚合名；
     # 只引本包登记的同类标签；文件展开后就是静态表（Tags.ITEM_TAGS / BLOCK_TAGS），JE 的标签文件用 # 引了这边也有的标签的地方，这边也用 #
  2. 成员只有 arris: 和 minecraft: 的：arris: 的在本包的物品 / 方块定义里；minecraft: 的在本机最新游戏的原版创造目录（物品）/ blocks.json（方块）里
     （本机没装游戏时这一项跳过）
  3. 词表：成员和 JE 1.3.4 的 forge / farmersdelight 标签文件对得上（.refs 里有 JE 源码时；JE 的熔岩炼药锅对到炼药锅 + 状态条件）；
     热源标签就是现在的热源方块表加上写了状态条件的方块；
     一个 JE 物品标签名只对应一个标签（JE 配方的标签名 → 这里的名字，做别名表时不能有歧义）；准备好的探针在表里；没有成员的名字不生成文件
  4. 团队烹饪原料标签的规范（森罗物语厨房网易版的 18 个，Tags.COOKING_STANDARD）：农夫乐事登记的粗标签只用 # 嵌自己的细标签，自己的配方不读粗标签；
     docs/TAGS.md 的对照表和词表一致；本机有森罗的工程时（FD_KC_DIR，或者旁边的 KaleidoscopeCookeryNetease-main）对照表和它的文件一致
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
        own = Tags.ITEM_TAG_FILES if doc["type"] == "item" else Tags.BLOCK_TAG_FILES
        for item in items:
            if item.startswith("#"):
                assert item[1:] in own and item[1:] != doc["identifier"], "%s：# 只引本包登记的同类标签 %r" % (name, item)
            else:
                assert NAME.match(item), "%s：成员只写扁平的名字（没有 aux）%r" % (name, item)
        assert not set(items) & set(LEGACY_NAMES), name


def testMembersAreOursOrVanillaAndExist():
    items = _definitions("netease_items_beh", "minecraft:item")
    blocks = _definitions("netease_blocks", "minecraft:block")
    for name, doc in _tagFiles().items():
        own = blocks if doc["type"] == "block" else items | blocks         # 方块也是物品（方块物品）
        for member in (item for item in doc["items"] if not item.startswith("#")):
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


def _alias(kind):
    """JE 的标签名 -> 这边同类的标签（JE_NAMES 反过来，只取 kind 那一类：物品 / 方块）。"""
    table = Tags.ITEM_TAG_FILES if kind == "items" else Tags.BLOCK_TAG_FILES
    return dict((name, tag) for tag, names in Tags.JE_NAMES.items() if tag in table for name in names)


def testTheFilesExpandToTheStaticTables():
    """文件里写的（ITEM_TAG_FILES，可以有 "#标签"）展开就是静态作答的表；静态表里没有 #。"""
    for files, expanded in ((Tags.ITEM_TAG_FILES, Tags.ITEM_TAGS), (Tags.BLOCK_TAG_FILES, Tags.BLOCK_TAGS)):
        assert sorted(files) == sorted(expanded)
        for tag, members in expanded.items():
            assert not [name for name in members if name.startswith("#")] and len(set(members)) == len(members), tag
            flat = [name for name in files[tag] if not name.startswith("#")]
            assert set(flat) <= set(members), tag
            for ref in (name[1:] for name in files[tag] if name.startswith("#")):
                assert set(expanded[ref]) <= set(members), (tag, ref)
    assert Tags.ITEM_TAGS[Tags.VEGETABLE] == ("minecraft:beetroot", "minecraft:carrot", "arris:onion", "minecraft:potato", "arris:tomato")
    assert "#" + Tags.TOMATO in Tags.ITEM_TAG_FILES[Tags.VEGETABLE], "别的模组的番茄进 common:tomato 就算蔬菜"
    assert "#" + Tags.TRAY_HEAT_SOURCES in Tags.BLOCK_TAG_FILES[Tags.HEAT_SOURCES]


def testNestingFollowsJava():
    """JE 1.3.4 的标签文件里用 # 引了别的标签、而那个标签这边也登记了（同一类），这边的文件也写 #：别的模组登记进小标签的东西自动进大标签。
    引的是这边没有的（#minecraft:campfires、#farmersdelight:cabinets/wooden、#forge:milk/milk……）照旧展开写成员。"""
    if not os.path.isdir(JE_DATA):
        print("跳过：没有 JE 源码（.refs/FarmersDelight）")
        return
    checked = 0
    for kind, files in (("items", Tags.ITEM_TAG_FILES), ("blocks", Tags.BLOCK_TAG_FILES)):
        alias = _alias(kind)
        for tag, written in files.items():
            for jeName in Tags.JE_NAMES.get(tag, ()):
                space, path = jeName.split(":", 1)
                source = os.path.join(JE_DATA, space, "tags", kind, *path.split("/")) + ".json"
                if not os.path.isfile(source):
                    continue
                for value in _json(source)["values"]:
                    ref = value if isinstance(value, str) else value.get("id", "")
                    target = alias.get(ref[1:]) if ref.startswith("#") else None
                    if target is not None and target != tag:
                        checked += 1
                        assert "#" + target in written, "%s：JE 的 %s 引了 %s，这边要写 #%s" % (tag, jeName, ref, target)
    assert checked >= 15, checked


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


# 农夫乐事自己的方块标签（farmersdelight:）读的地方是"名单 ∪ 标签"：标签的成员就是那张名单（离线时和原来一样）；
# 热源另有写了状态条件的方块（Cooking.HeatSourceStateDict：炼药锅），它们也在标签里，不在旧契约那张"无条件"的名单里
LISTED = {
    Tags.HEAT_SOURCES: lambda: list(Cooking.CanProvideHeatBlockList) + list(Cooking.HeatSourceStateDict),
    Tags.HEAT_CONDUCTORS: lambda: Cooking.HeatConductorList,
    Tags.TRAY_HEAT_SOURCES: lambda: _serverHeat().ShelfBlockSet,
    Tags.COMPOST_ACTIVATORS: lambda: fdtest.load("Shared.Data.Farming").COMPOST_ACTIVATORS,
    Tags.UNAFFECTED_BY_RICH_SOIL: lambda: fdtest.load("Shared.Data.Farming").UNAFFECTED_BY_RICH_SOIL,
    Tags.MUSHROOM_COLONY_GROWABLE_ON: lambda: fdtest.load("Shared.Rules.ColonyRules").GROWABLE_ON,
    Tags.DROPS_CAKE_SLICE: lambda: fdtest.load("Shared.Data.Slicing").CANDLE_CAKES,
}

# JE 标签里的方块、基岩版是"另一个方块 + 状态条件"的：熔岩炼药锅。3.10 实机里没有 minecraft:lava_cauldron 这个方块（SetBlockNew("minecraft:lava_cauldron")
# 返回 True，放出来的却是盛水、0 级的 minecraft:cauldron）；基岩版里它是炼药锅的状态 cauldron_liquid = lava（SetBlockStates 成熔岩、6 级之后 aux 14）。
# 所以 JE 的 minecraft:lava_cauldron 对到这边标签里的 minecraft:cauldron（JE_BLOCKS），盛不盛熔岩看状态条件表 Shared/Data/Cooking.HeatSourceStateDict
# （规则 Shared/Rules/HeatSources.heats）：{JE 的名字: (这边的方块, 状态条件)}
BY_STATE = {"minecraft:lava_cauldron": ("minecraft:cauldron", {"cauldron_liquid": "lava", "fill_level": {"min": 1}})}
JE_BLOCKS.update((jeName, (name,)) for jeName, (name, _conditions) in BY_STATE.items())


def testFarmersDelightsOwnBlockTagsAreTheirListsAndCoverJava():
    """farmersdelight: 的方块标签：成员就是读的地方原来的那张名单（热源再加上写了状态条件的方块）；JE 标签文件里的成员（展开 #、换成基岩版的名字，
    熔岩炼药锅换成炼药锅 + 状态条件）都在里面，别的模组的可选成员（create:chute）不写。名单改了：这里跟上，再跑 py -3 tools/gen_tags.py。"""
    own = sorted(tag for tag in Tags.BLOCK_TAGS if tag.startswith("farmersdelight:"))
    assert own == sorted(LISTED), "每个 farmersdelight: 方块标签都对着一张名单"
    for tag in own:
        assert sorted(Tags.BLOCK_TAGS[tag]) == sorted(LISTED[tag]()), "%s 和它的名单不一样" % tag
        assert Tags.JE_NAMES[tag] == (tag,), "照 JE 的名字"
    heats = fdtest.load("Shared.Rules.HeatSources").heats
    for jeName, (name, conditions) in BY_STATE.items():
        assert name in Tags.BLOCK_TAGS[Tags.HEAT_SOURCES] and Cooking.HeatSourceStateDict[name] == conditions, (jeName, name)
    assert heats("minecraft:cauldron", lambda: {"cauldron_liquid": "lava", "fill_level": 6}) is True, "熔岩炼药锅按状态认"
    assert heats("minecraft:cauldron", lambda: {"cauldron_liquid": "water", "fill_level": 6}) is False, "标签里有炼药锅，盛水的照样不热"
    if not os.path.isdir(JE_DATA):
        print("跳过：没有 JE 源码（.refs/FarmersDelight）")
        return
    optional = []
    for tag in own:
        expanded = _jeTag(tag, "blocks", optional=optional)
        assert expanded is not None, tag
        missing = sorted(set(expanded) - set(Tags.BLOCK_TAGS[tag]))
        assert not missing, "%s：JE 有、这边没有 %s" % (tag, missing)
    assert optional == ["create:chute"], optional
    written = _json(os.path.join(JE_DATA, "farmersdelight", "tags", "blocks", "heat_sources.json"))["values"]
    assert set(BY_STATE) <= set(written), "按状态认的成员 JE 的标签里得真有"


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
    """热源标签照 JE 只有一个（farmersdelight:heat_sources）= 现在的热源方块表（CanProvideHeatBlockList 导入时的样子）加上写了状态条件的方块
    （HeatSourceStateDict：炼药锅）；营火点没点着、炼药锅盛没盛熔岩看状态（HeatSources 的规则），不再单列一个标签。"""
    members = Tags.BLOCK_TAGS[Tags.HEAT_SOURCES]
    assert sorted(members) == sorted(list(Cooking.CanProvideHeatBlockList) + list(Cooking.HeatSourceStateDict))
    assert {"minecraft:campfire", "minecraft:soul_campfire", "minecraft:magma", "minecraft:cauldron"} <= set(members)
    assert "arris:stove_extinguish" not in members, "熄着的炉灶不发热"
    assert "minecraft:cauldron" not in Cooking.CanProvideHeatBlockList, "炼药锅只在盛着熔岩时热：不进旧契约那张不看状态的名单"


def testTheBriefsMembers():
    """任务书里定下的几条（A 拿它们还原厨锅格子）。"""
    expect = {
        Tags.TOMATO: ("arris:tomato",), Tags.DOUGH: ("arris:wheat_dough",), Tags.COOKED_EGG: ("arris:fried_egg",),
        Tags.RAW_BEEF: ("minecraft:beef", "arris:minced_beef"), Tags.RAW_PORK: ("minecraft:porkchop", "arris:bacon"),
        Tags.RAW_CHICKEN: ("minecraft:chicken", "arris:chicken_cuts"), Tags.RAW_MUTTON: ("minecraft:mutton", "arris:mutton_chops"),
        Tags.RAW_FISH: ("minecraft:cod", "arris:cod_slice", "minecraft:salmon", "arris:salmon_slice", "minecraft:tropical_fish"),
        Tags.VEGETABLE: ("minecraft:beetroot", "minecraft:carrot", "arris:onion", "minecraft:potato", "arris:tomato"),
        Tags.MUSHROOM: ("minecraft:brown_mushroom", "minecraft:red_mushroom"), Tags.MILK: ("minecraft:milk_bucket", "arris:milk_bottle"),
        Tags.BERRY: ("minecraft:sweet_berries", "minecraft:glow_berries"), Tags.BONE: ("minecraft:bone",),
        Tags.WATER_BUCKET: ("minecraft:water_bucket",),
    }
    for tag, members in expect.items():
        assert Tags.ITEM_TAGS[tag] == members, tag
    assert Tags.ITEM_TAGS[Tags.RAW_MEAT][0] == "minecraft:rabbit" and len(Tags.ITEM_TAGS[Tags.RAW_MEAT]) == 9
    assert "minecraft:pufferfish" not in Tags.ITEM_TAGS[Tags.RAW_FISH]
    assert Tags.VANILLA_TAGS[Tags.EGG] == ("minecraft:egg", "minecraft:blue_egg", "minecraft:brown_egg")
    assert len(Tags.ITEM_TAGS[Tags.KNIFE]) == 5 and all(name.startswith("arris:") for name in Tags.ITEM_TAGS[Tags.KNIFE])


# 团队烹饪原料标签的规范（Tags.COOKING_STANDARD，森罗物语厨房网易版的 18 个）：农夫乐事登记进去的粗标签 -> 用 # 嵌进去的细标签
# （每一条的 JE 依据写在 docs/TAGS.md「和森罗物语的标签对照」）；本来就同名的；农夫乐事不登记的
COARSE = {
    Tags.BEEF: (Tags.RAW_BEEF, Tags.COOKED_BEEF), Tags.CHICKEN: (Tags.RAW_CHICKEN, Tags.COOKED_CHICKEN),
    Tags.LAMB: (Tags.RAW_MUTTON, Tags.COOKED_MUTTON), Tags.PORK: (Tags.RAW_PORK, Tags.COOKED_PORK),
    Tags.FISH: (Tags.RAW_FISH, Tags.COOKED_FISH), Tags.NOODLE: (Tags.PASTA,), Tags.ANY_EGG: (Tags.COOKED_EGG,),
    Tags.SEED: (Tags.CABBAGE_SEEDS, Tags.RICE, Tags.TOMATO_SEEDS),
}
SAME_NAME = (Tags.DOUGH, Tags.MUSHROOM, Tags.RICE, Tags.TOMATO, Tags.VEGETABLE)
NOT_OURS = ("common:chili", "common:flour", "common:lettuce", "common:meat", "common:meatball")


def testTheTeamStandard():
    """团队烹饪原料标签的规范：18 个平铺、单数的 common: 名（照森罗的文件名排）。农夫乐事登记了 13 个：粗标签只用 # 嵌自己的细标签
    （别的模组登记进细标签的也跟着算，展开就是细标签的并集，没有 JE 名——JE 里没有对应的单个标签），同名的本来就有；没有依据的 5 个
    不登记、不进词表。农夫乐事自己的配方（厨锅的格子、砧板、工作台）不读粗标签：生 / 熟分开是 JE 配方的原意，蛋读原版的 minecraft:egg。"""
    standard = Tags.COOKING_STANDARD
    assert len(standard) == 18 == len(set(standard)) and list(standard) == sorted(standard), standard
    assert all(re.match(r"^common:[a-z]+$", tag) for tag in standard), "平铺、一个词"
    assert set(standard) == set(COARSE) | set(SAME_NAME) | set(NOT_OURS) and not set(COARSE) & set(SAME_NAME)
    for tag, parts in COARSE.items():
        assert Tags.ITEM_TAG_FILES[tag] == tuple("#" + part for part in parts), tag
        assert sorted(Tags.ITEM_TAGS[tag]) == sorted(set(member for part in parts for member in Tags.ITEM_TAGS[part])), tag
        assert tag not in Tags.JE_NAMES, tag
    for tag in SAME_NAME:
        assert tag in Tags.ITEM_TAGS, tag
    for tag in NOT_OURS:
        assert tag not in Tags.ITEM_TAGS and tag not in Tags.WITHOUT_MEMBERS and tag not in Tags.JE_NAMES, tag
    # 成员的分寸（JE 依据见 docs/TAGS.md）：培根算猪肉、火腿不算；鱼片算鱼、河豚不算；蛋只有做熟的蛋（三种鸡蛋森罗登记了，农夫乐事的配方读原版标签）
    assert {"arris:bacon", "arris:cooked_bacon"} <= set(Tags.ITEM_TAGS[Tags.PORK])
    assert not {"arris:ham", "arris:smoked_ham"} & set(Tags.ITEM_TAGS[Tags.PORK])
    assert {"arris:cod_slice", "arris:cooked_salmon_slice", "minecraft:tropical_fish"} <= set(Tags.ITEM_TAGS[Tags.FISH])
    assert "minecraft:pufferfish" not in Tags.ITEM_TAGS[Tags.FISH]
    assert Tags.ITEM_TAGS[Tags.ANY_EGG] == ("arris:fried_egg",) and Tags.ANY_EGG != Tags.EGG
    assert Tags.ITEM_TAGS[Tags.SEED] == ("arris:cabbage_seeds", "arris:rice", "arris:tomato_seeds")
    assert Tags.ITEM_TAGS[Tags.NOODLE] == ("arris:raw_pasta",)
    reads = _docReads()
    for tag in COARSE:
        assert reads[tag] == "—", "%s：农夫乐事自己的配方不读粗标签（%s）" % (tag, reads[tag])


def _codes(names):
    return "、".join("`%s`" % name for name in names) if names else "—"


def _standardRows():
    """docs/TAGS.md「和森罗物语的标签对照」开头那张表：{标签: [森罗登记的, 农夫乐事登记的, JE 里对应的标签]}（到第一个小标题为止）。"""
    with io.open(os.path.join(fdtest.ROOT, "docs", "TAGS.md"), encoding="utf-8") as handle:
        text = handle.read()
    section = text[text.index("## 和森罗物语的标签对照"):]
    section = section[:section.index("\n### ")]
    rows = [line for line in section.splitlines() if line.startswith("| `common:")]
    return dict((cells[1].strip("` "), [cell.strip() for cell in cells[2:-1]]) for cells in (row.split("|") for row in rows))


def testTheDocComparesTheStandardWithWhatWeRegister():
    """docs/TAGS.md 的对照表：18 个规范标签各一行，"农夫乐事登记的"一列就是词表里写的（ITEM_TAG_FILES，含 #），没登记的写 —。"""
    rows = _standardRows()
    assert sorted(rows) == sorted(Tags.COOKING_STANDARD), sorted(rows)
    for tag in Tags.COOKING_STANDARD:
        assert len(rows[tag]) == 3, (tag, rows[tag])
        assert rows[tag][1] == _codes(Tags.ITEM_TAG_FILES.get(tag, ())), (tag, rows[tag][1])


# 森罗物语厨房网易版的工程（只读）：FD_KC_DIR 给了就只认它（指向不存在的目录 = 当作没有），没给就找本仓库旁边的（开发机上并排放在 AddOn/ 下）
KC_DIR = os.environ.get("FD_KC_DIR") or os.path.join(os.path.dirname(fdtest.ROOT), "KaleidoscopeCookeryNetease-main")
KC_TAGS = os.path.join(KC_DIR, "kaleidoscope_cookery_bp", "netease_tags")


def testTheStandardIsKaleidoscopesOwnFiles():
    """本机有森罗的工程时：它 netease_tags 里的 common: 物品标签就是规范的 18 个，对照表"森罗登记的"一列照它的文件抄（含先后）；
    农夫乐事靠得上的一条：它的 common:meat 用 # 引了牛、鸡、羊、猪四个（农夫乐事的肉登记进那四个就算肉，所以 common:meat 不用登记）。
    森罗改了规范时这里先红：对照表、词表、这条用例跟着改。"""
    if not os.path.isdir(KC_TAGS):
        print("跳过：本机没有森罗物语厨房的工程（%s；可以用 FD_KC_DIR 指定）" % KC_DIR)
        return
    found = {}
    for name in sorted(os.listdir(KC_TAGS)):
        if name.endswith(".json"):
            doc = _json(os.path.join(KC_TAGS, name))
            if doc.get("type") == "item" and doc.get("identifier", "").startswith("common:"):
                found[doc["identifier"]] = doc["items"]
    assert sorted(found) == sorted(Tags.COOKING_STANDARD), sorted(found)
    rows = _standardRows()
    for tag, items in found.items():
        assert rows[tag][0] == _codes(items), (tag, rows[tag][0], items)
    assert {"#" + tag for tag in (Tags.BEEF, Tags.CHICKEN, Tags.LAMB, Tags.PORK)} <= set(found["common:meat"]), found["common:meat"]


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
