# -*- coding: utf-8 -*-
# runner: py3
"""行为包的 netease_tags/（tools/gen_tags.py 从词表 Shared/Data/Tags.py 生成）与词表本身。

引擎的规矩（网易 3.10 实机，前置包工程 .planning/kaleidoscope/R4-netease-tags-engine.md）：一个文件一个标签，各模组登记的同名标签合并去重；
成员不存在时引擎一直刷 ERROR 日志（所以只写本包的和原版的，名字要真）；没有 aux（只写扁平名）；# 引用"物品 JSON 里声明的标签"展开不全（这里不用 #）。
锁的事：
  1. 文件是最新的；每个文件 type / identifier / items 三个键，文件名照 identifier，identifier 不重复，成员不重复、没有 #、没有旧聚合名
  2. 成员只有 arris: 和 minecraft: 的：arris: 的在本包的物品 / 方块定义里；minecraft: 的在本机最新游戏的原版创造目录（物品）/ blocks.json（方块）里
     （本机没装游戏时这一项跳过）
  3. 词表：成员和 JE 1.3.4 的 forge / farmersdelight 标签文件对得上（.refs 里有 JE 源码时）；热源两个标签合起来就是现在的热源方块表；
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
        known = itemNames if kind == "item" else blockNames
        missing += ["%s %s" % (tag, member) for tag, members in table.items() for member in members
                    if member.startswith("minecraft:") and member not in known]
    assert not missing, missing


def _jeTag(name, seen=()):
    """JE 物品标签展开成这边的名字（farmersdelight: → arris:）；.refs 里没有这个标签文件（Forge / 原版自己定义的）返回 None。"""
    space, path = name.split(":", 1)
    file = os.path.join(JE_DATA, space, "tags", "items", *path.split("/")) + ".json"
    if not os.path.isfile(file) or name in seen:
        return None
    found = []
    for value in _json(file)["values"]:
        value = value["id"] if isinstance(value, dict) else value
        members = _jeTag(value[1:], seen + (name,)) if value.startswith("#") else [value.replace("farmersdelight:", "arris:")]
        assert members is not None, "%s 引用的 %s 不在 .refs 里" % (name, value)
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
    assert all(tag.startswith("common:") for tag in itemTags - {Tags.LEGACY_KNIFE} | blockTags)
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


def testTheHeatTagsAreTodaysHeatSources():
    """两个热源标签合起来 = 现在的热源方块表（CanProvideHeatBlockList 导入时的样子）；营火要看点燃状态，单列。"""
    both = Tags.BLOCK_TAGS[Tags.HEAT_SOURCE] + Tags.BLOCK_TAGS[Tags.HEAT_SOURCE_LIT]
    assert sorted(both) == sorted(Cooking.CanProvideHeatBlockList)
    assert set(Tags.BLOCK_TAGS[Tags.HEAT_SOURCE_LIT]) == {"minecraft:campfire", "minecraft:soul_campfire"}
    assert "arris:stove_extinguish" not in both, "熄着的炉灶不发热"


def testTheBriefsMembers():
    """任务书里定下的几条（A 拿它们还原厨锅格子）。"""
    expect = {
        Tags.TOMATO: ("arris:tomato",), Tags.DOUGH: ("arris:wheat_dough",), Tags.FRIED_EGG: ("arris:fried_egg",),
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


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
