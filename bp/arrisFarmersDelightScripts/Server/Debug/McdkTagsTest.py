# -*- coding: utf-8 -*-
"""McdkTagsTest - 标签、营火配方的游戏内自检（服务端）：测试函数，仅供 MCDK-MCP 的 execute_code / 开发调试调用

不会自动运行，没有 RPC 端点。问的是服务端自己的引擎口（Server/Helpers/Tags.PORT，原样的引擎答案），回答离线定不了的几件事：
1. mcdk_test_tags_members()：词表（Shared/Data/Tags）里每个标签，引擎反查到的成员和静态表比：extra 是别的包登记进来的，
   missing 是本包登记了、引擎却没有的（名字写错，或者 netease_tags 没挂上）；口准备好没有。另外看引擎日志：
   进世界 10 秒后不该再有 "netease_tags: apply ... not found"（原版成员只在加载时报一轮，名字写错的会一直报）。
2. mcdk_test_tags_knives()：五把刀和 knifeList 里每一把的 IsKnife，引擎给它们的物品标签（五把刀应带 arris:knife、common:knife）。
3. mcdk_test_tags_campfire()：GetRecipesByInput(名字, "campfire", 0, 1) 对原版牛肉、农夫乐事的牛肉末、三种蛋的原始返回值（repr）、
   Shared/Rules/Grilling 解析出来的产物、Grilling.resultOf 的答案——返回值的形状没有实机记录，看这里核 Grilling 的解析。
4. mcdk_test_tags_heat()：两个热源标签引擎反查的成员，GetBlockTags 对几种热源方块的回答。
5. mcdk_test_tags_blocks()：农夫乐事自己的方块标签（farmersdelight:，读的地方是"名单 ∪ 标签"）引擎反查的差，和每个成员按方块问
   （GetBlockTags）带不带这个标签：原版方块经 netease_tags 挂上的标签按方块问认不认，离线定不了，不认的列在 notTagged（只报，不算失败，
   反查认得就够用）。分类的物品标签（farmersdelight:meals 等，没有读的地方）在第 1 条里。
    from arrisFarmersDelightScripts.Server.Debug import McdkTagsTest as T
    return T.mcdk_test_tags_members()
"""
from ..Helpers import Tags as EngineTags
from ..Helpers.Items import IsKnife
from ...Shared.Data import Tags
from ...Shared.Data.Cutting import knifeList
from ...Shared.Rules import Grilling

RECIPE_PROBES = ("minecraft:beef", "arris:minced_beef", "minecraft:egg", "minecraft:blue_egg", "minecraft:brown_egg")
BLOCK_PROBES = ("arris:stove", "arris:stove_extinguish", "minecraft:magma", "minecraft:campfire", "minecraft:fire", "minecraft:lava")


def _diff(static, engine):
    """静态表的成员 vs 引擎反查到的：engine 是几个（答不了 None），extra 引擎多出来的，missing 静态表有、引擎没有的。"""
    if engine is None:
        return {"engine": None, "extra": [], "missing": sorted(static)}
    return {"engine": len(engine), "extra": sorted(set(engine) - set(static)), "missing": sorted(set(static) - set(engine))}


def _members(port):
    items = {}
    for table in (Tags.ITEM_TAGS, Tags.VANILLA_TAGS):
        for tag, members in table.items():
            items[tag] = _diff(members, port.itemsOf(tag))
    blocks = dict((tag, _diff(members, port.blocksOf(tag))) for tag, members in Tags.BLOCK_TAGS.items())
    return items, blocks


def mcdk_test_tags_members():
    """测试函数：每个标签引擎里的成员和静态表的差；返回结构化结果。"""
    port = EngineTags.PORT
    ready = port.ready()
    items, blocks = _members(port)
    missing = sorted(tag for tag, row in list(items.items()) + list(blocks.items()) if row["missing"])
    return {"case": "tags_members", "ok": bool(ready) and not missing, "ready": ready, "missing": missing, "items": items, "blocks": blocks}


def mcdk_test_tags_knives():
    """测试函数：五把刀和 knifeList 里的刀 IsKnife 认不认，引擎上的物品标签。"""
    own = Tags.ITEM_TAGS[Tags.KNIFE]
    rows = {}
    for name in list(own) + [name for name in knifeList if name not in own]:
        rows[name] = {"isKnife": IsKnife(name), "engineTags": sorted(EngineTags.PORT.tagsOf(name, 0) or ())}
    ok = all(rows[name]["isKnife"] and Tags.KNIFE in rows[name]["engineTags"] and Tags.LEGACY_KNIFE in rows[name]["engineTags"] for name in own)
    return {"case": "tags_knives", "ok": ok, "knives": rows}


def mcdk_test_tags_campfire():
    """测试函数：几种原料的营火配方原样返回值和解析结果。"""
    rows = {}
    for name in RECIPE_PROBES:
        raw = EngineTags.PORT.campfireRecipes(name, 0)
        rows[name] = {"raw": repr(raw)[:600], "parsed": Grilling.cookedOf(raw, name), "result": Grilling.resultOf(name)}
    ok = rows["minecraft:beef"]["parsed"] == "minecraft:cooked_beef"
    return {"case": "tags_campfire", "ok": ok, "recipes": rows}


def mcdk_test_tags_heat():
    """测试函数：两个热源标签引擎反查的成员、GetBlockTags 对几种方块的回答。"""
    port = EngineTags.PORT
    members = dict((tag, sorted(port.blocksOf(tag) or ())) for tag in Tags.BLOCK_TAGS)
    blockTags = {}
    for name in BLOCK_PROBES:
        found = port.blockTagsOf(name)
        blockTags[name] = sorted(found) if found is not None else None
    ok = all(set(Tags.BLOCK_TAGS[tag]) <= set(members[tag]) for tag in Tags.BLOCK_TAGS) \
        and Tags.HEAT_SOURCE in (blockTags["arris:stove"] or ()) and Tags.HEAT_SOURCE not in (blockTags["arris:stove_extinguish"] or ())
    return {"case": "tags_heat", "ok": ok, "members": members, "blockTags": blockTags}


def mcdk_test_tags_blocks():
    """测试函数：farmersdelight: 方块标签引擎反查的差（missing 非空算失败），每个成员按方块问带不带这个标签（notTagged，只报）。"""
    port = EngineTags.PORT
    rows = {}
    for tag in sorted(tag for tag in Tags.BLOCK_TAGS if tag.startswith("farmersdelight:")):
        members = Tags.BLOCK_TAGS[tag]
        row = _diff(members, port.blocksOf(tag))
        row["notTagged"] = sorted(name for name in members if tag not in (port.blockTagsOf(name) or ()))
        rows[tag] = row
    return {"case": "tags_blocks", "ok": not any(row["missing"] for row in rows.values()), "tags": rows}
