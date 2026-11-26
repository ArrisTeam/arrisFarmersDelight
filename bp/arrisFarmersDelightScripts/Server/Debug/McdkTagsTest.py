# -*- coding: utf-8 -*-
"""McdkTagsTest - 标签、营火配方的游戏内自检（服务端）：测试函数，仅供 MCDK-MCP 的 execute_code / 开发调试调用

不会自动运行，没有 RPC 端点。问的是服务端自己的引擎口（Server/Helpers/Tags.PORT，原样的引擎答案），回答离线定不了的几件事：
1. mcdk_test_tags_members()：词表（Shared/Data/Tags）里每个标签，引擎反查到的成员和静态表比：extra 是别的包登记进来的，
   missing 是本包登记了、引擎却没有的（名字写错，或者 netease_tags 没挂上；文件里用 # 引别的标签的那几个——生肉、蔬菜、作物……——
   missing 非空就是 # 没展开）；口准备好没有。另外看引擎日志：
   进世界 10 秒后不该再有 "netease_tags: apply ... not found"（原版成员只在加载时报一轮，名字写错的会一直报）。
2. mcdk_test_tags_knives()：五把刀和 knifeList 里每一把的 IsKnife，引擎给它们的物品标签（五把刀应带 arris:knife、common:knife）。
3. mcdk_test_tags_campfire()：GetRecipesByInput(名字, "campfire", 0, 1) 对原版牛肉、农夫乐事的牛肉末、三种蛋的原始返回值（repr）、
   Shared/Rules/Grilling 解析出来的产物、Grilling.resultOf 的答案（2026-11-26 实机：[{'input': 名字, 'output': 名字}]，解析都对；换引擎版本时再看一遍）。
4. mcdk_test_tags_heat()：方块标签引擎反查的成员（热源标签的文件里用 # 引了托盘标签：反查少了熔岩、营火、火，就是方块标签的 # 引擎没展开），
   GetBlockTags 对几种热源方块的回答。
5. mcdk_test_tags_blocks()：农夫乐事自己的方块标签（farmersdelight:，读的地方是"名单 ∪ 标签"）引擎反查的差，和每个成员按方块问
   （GetBlockTags）带不带这个标签：原版方块经 netease_tags 挂上的标签按方块问认不认，离线定不了，不认的列在 notTagged（只报，不算失败，
   反查认得就够用）。分类的物品标签（farmersdelight:meals 等，没有读的地方）在第 1 条里。
6. mcdk_test_tags_probe_grill()：探针包的番茄（fdprobe:tomato，表里没有，只靠探针包的营火配方烤成铁粒）在服务端线程里 Grilling.resultOf 给什么、
   两个口（Grilling 装着的，单机时两个都在）各自的原始答案、缓存里调之前 / 之后记着什么；没装探针包时跳过。先在客户端线程调
   Client/Debug/McdkTagsTest 的同名函数，再调这个：两边都该是 minecraft:iron_nugget（GetRecipesByInput 只在自己那一端的线程里答得出，
   2026-11-26 实机：以前客户端线程先问时把 None 记进了缓存，服务端读到的也是它）。
7. mcdk_test_tags_standard()：团队烹饪原料标签规范的 18 个标签（Tags.COOKING_STANDARD，森罗物语厨房定的）引擎里现在的成员——带着森罗物语厨房
   进游戏看两边并没并上：tags 里每个标签的 members（引擎反查到的全部）、missing（农夫乐事登记了引擎却没有）、extra（别的包登记的，森罗的东西在这里）；
   nestedLost：农夫乐事用 # 嵌的细标签，引擎里的成员（含别的包登记进细标签的）有没有漏出粗标签；meatLost：有人登记了 common:meat 时（森罗的文件
   用 # 引了牛、鸡、羊、猪），农夫乐事登记进那四个的肉有没有并进去（没人登记是 None）。装了森罗时 kaleidoscope 再报：它服务端模糊配方认料用的
   item_matches_ingredient 认不认农夫乐事登记进去的每件东西（refused 是不认的）、反例（火腿当猪肉、河豚当鱼）认没认（acceptedWrongly）、
   它按标签名缓存的成员（第一次问时建、之后不再问引擎）调之前有哪些、和引擎现在的对不上的（stale）。客户端另有同名函数报客户端引擎和森罗 JEI 的缓存。
    from arrisFarmersDelightScripts.Server.Debug import McdkTagsTest as T
    return T.mcdk_test_tags_members()
"""
from ..Helpers import Tags as EngineTags
from ..Helpers.Engine import compFactory, levelId, serverApi
from ..Helpers.Items import IsKnife
from ...Shared.Data import Tags
from ...Shared.Data.Cutting import knifeList
from ...Shared.Rules import Grilling

RECIPE_PROBES = ("minecraft:beef", "arris:minced_beef", "minecraft:egg", "minecraft:blue_egg", "minecraft:brown_egg")
PROBE_GRILL = ("fdprobe:tomato", "minecraft:iron_nugget")    # 探针包的番茄、它的营火配方的产物（同客户端那份，两端互不导入，各写一份）
BLOCK_PROBES = ("arris:stove", "arris:stove_extinguish", "minecraft:magma", "minecraft:campfire", "minecraft:fire", "minecraft:lava")
KC_MATCHER = "kcookery_scripts.server.register.recipes.cooking_tags"   # 森罗物语厨房服务端认料的模块（它的模糊配方经 item_matches_ingredient 认）
MEAT_PARTS = (Tags.BEEF, Tags.CHICKEN, Tags.LAMB, Tags.PORK)           # 森罗的 common:meat 用 # 引的四个（它的 netease_tags/meat.json）
NOT_THEIRS = (("arris:ham", Tags.PORK), ("arris:smoked_ham", Tags.PORK), ("minecraft:pufferfish", Tags.FISH))    # 不该认的


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
    """测试函数：方块标签引擎反查的成员（每个都要含词表展开后的成员）、GetBlockTags 对几种方块的回答。"""
    port = EngineTags.PORT
    members = dict((tag, sorted(port.blocksOf(tag) or ())) for tag in Tags.BLOCK_TAGS)
    blockTags = {}
    for name in BLOCK_PROBES:
        found = port.blockTagsOf(name)
        blockTags[name] = sorted(found) if found is not None else None
    ok = all(set(Tags.BLOCK_TAGS[tag]) <= set(members[tag]) for tag in Tags.BLOCK_TAGS) \
        and Tags.HEAT_SOURCES in (blockTags["arris:stove"] or ()) and Tags.HEAT_SOURCES not in (blockTags["arris:stove_extinguish"] or ())
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


def mcdk_test_tags_probe_grill():
    """测试函数：探针包的番茄在这个线程（服务端）里 Grilling.resultOf 给什么、两个口各自的原始答案、调之前 / 之后缓存里记着什么。"""
    name, expected = PROBE_GRILL
    if compFactory.CreateItem(levelId).GetItemBasicInfo(name, 0) is None:
        return {"case": "tags_probe_grill", "ok": True, "skipped": "没装探针包（%s）" % name}
    before = repr(Grilling._cache.get((name, 0), "<没记>"))
    raw = dict((side, repr(port.campfireRecipes(name, 0))[:300]) for side, port in Grilling._ports.items())
    result = Grilling.resultOf(name, 0)
    return {"case": "tags_probe_grill", "thread": "server", "ok": result == expected, "result": result, "expected": expected,
            "raw": raw, "cachedBefore": before, "cachedAfter": repr(Grilling._cache.get((name, 0), "<没记>"))}


def _standardRows(port):
    """规范的 18 个标签：引擎反查到的全部成员（members）、农夫乐事登记了引擎却没有的（missing）、别的包登记的（extra）。"""
    rows = {}
    for tag in Tags.COOKING_STANDARD:
        engine = port.itemsOf(tag)
        row = _diff(Tags.ITEM_TAGS.get(tag, ()), engine)
        row["members"] = sorted(engine) if engine is not None else None
        rows[tag] = row
    return rows


def _nestedLost(port):
    """农夫乐事在规范标签里用 # 嵌的细标签：细标签引擎里的成员有没有都进了粗标签。{"粗 <- #细": [漏掉的]}"""
    lost = {}
    for tag in Tags.COOKING_STANDARD:
        outer = set(port.itemsOf(tag) or ())
        for ref in (name[1:] for name in Tags.ITEM_TAG_FILES.get(tag, ()) if name.startswith("#")):
            missing = sorted(set(port.itemsOf(ref) or ()) - outer)
            if missing:
                lost["%s <- #%s" % (tag, ref)] = missing
    return lost


def _kaleidoscope(port):
    """装了森罗物语厨房时：它的 item_matches_ingredient 认不认农夫乐事登记进去的东西、反例认没认、它的标签缓存（调之前的）过没过时；没装 None。"""
    try:
        module = serverApi.ImportModule(KC_MATCHER)
    except Exception:  # noqa: BLE001 - 导入不了（给 None 或者抛异常）都当没装
        module = None
    if module is None or not hasattr(module, "item_matches_ingredient"):
        return None
    cache = getattr(module, "_TAG_ITEMS_CACHE", None) or {}
    before = sorted(cache)
    stale = sorted(tag for tag in before if tag in Tags.COOKING_STANDARD and set(cache[tag]) != set(port.itemsOf(tag) or ()))
    cases = [(name, tag) for tag in Tags.COOKING_STANDARD for name in Tags.ITEM_TAGS.get(tag, ())]
    cases += [(name, "common:meat") for tag in MEAT_PARTS for name in Tags.ITEM_TAGS[tag]]
    refused = sorted("%s %s" % case for case in cases if not module.item_matches_ingredient(case[0], "#" + case[1]))
    wrong = sorted("%s %s" % case for case in NOT_THEIRS if module.item_matches_ingredient(case[0], "#" + case[1]))
    return {"asked": len(cases), "refused": refused, "acceptedWrongly": wrong, "cachedBefore": before, "stale": stale}


def mcdk_test_tags_standard():
    """测试函数：团队规范的 18 个标签引擎里现在的成员、# 嵌套并没并上；装了森罗物语厨房时它的模糊配方认不认农夫乐事的东西。"""
    port = EngineTags.PORT
    rows = _standardRows(port)
    nested = _nestedLost(port)
    meat = set(port.itemsOf("common:meat") or ())
    meatLost = sorted(set(name for tag in MEAT_PARTS for name in Tags.ITEM_TAGS[tag]) - meat) if meat else None
    kc = _kaleidoscope(port)
    missing = sorted(tag for tag, row in rows.items() if row["missing"])
    ok = bool(port.ready()) and not missing and not nested and not meatLost and \
        (kc is None or not (kc["refused"] or kc["acceptedWrongly"] or kc["stale"]))
    return {"case": "tags_standard", "ok": ok, "ready": port.ready(), "missing": missing, "nestedLost": nested, "meatLost": meatLost,
            "kaleidoscope": kc if kc is not None else "没装森罗物语厨房（%s 导入不了）" % KC_MATCHER, "tags": rows}
