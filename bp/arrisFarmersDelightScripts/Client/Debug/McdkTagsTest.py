# -*- coding: utf-8 -*-
"""McdkTagsTest - 标签的游戏内自检（客户端）：测试函数，仅供 MCDK-MCP 的 execute_code（is_client 为 true）/ 开发调试调用

不会自动运行，没有 RPC 端点。问的是客户端自己的引擎口（Client/Tags.PORT），不经 ItemTags——单机时 ItemTags 用的是服务端的口。回答：
- 口准备好没有、什么时候好的：timing 里 loadedAt 是 Client/Tags 导入的时刻，firstProbeAt / readyAt 是第一次被问、探到准备好的时刻，
  probes 探了几次（单机时客户端的口平时没人问，第一次探可能就是这个自检；联机的客户端有人问，readyAt - loadedAt 就是标签晚多久才全）；
- 每个标签客户端引擎反查到的成员和静态表比（extra / missing，同服务端的 mcdk_test_tags_members）；
- 五把刀按 Shared/Rules/Knives 认不认（客户端 BlockItems.isKnife 就是它）；原版牛肉的营火配方原样返回值和解析结果。
    from arrisFarmersDelightScripts.Client.Debug import McdkTagsTest as T
    return T.mcdk_test_tags_client()
mcdk_test_tags_probe_grill()：探针包的番茄（fdprobe:tomato，表里没有，只靠探针包的营火配方烤成铁粒）在客户端线程里 Grilling.resultOf 给什么、
两个口（Grilling 装着的，单机时两个都在）各自的原始答案、缓存里调之前 / 之后记着什么；没装探针包时跳过。先在客户端线程调这个，再在服务端线程调
Server/Debug/McdkTagsTest 的同名函数：两边都该是 minecraft:iron_nugget（GetRecipesByInput 只在自己那一端的线程里答得出，2026-11-26 实机）。
mcdk_test_tags_standard()：团队烹饪原料标签规范的 18 个标签（Tags.COOKING_STANDARD）客户端引擎里现在的成员（members / missing / extra，
同服务端的同名函数）；装了森罗物语厨房时报它客户端 JEI 按标签名缓存的成员（第一次问时建、之后不再问引擎）调之前有哪些、和客户端引擎现在的
对不上的（stale：客户端的标签进世界后才全，太早问过的会一直缺东西）。只读它的缓存，不替它问。
"""
from .. import Tags as EngineTags
from ..Engine import clientApi, compFactory, levelId
from ...Shared.Data import Tags
from ...Shared.Rules import Grilling, Knives

PROBE_GRILL = ("fdprobe:tomato", "minecraft:iron_nugget")    # 探针包的番茄、它的营火配方的产物（同服务端那份，两端互不导入，各写一份）
KC_JEI = "kcookery_scripts.client.compat.jei.jei"           # 森罗物语厨房客户端 JEI 的模块：_ITEM_TAG_CACHE 是它按标签名记的成员


def _diff(static, engine):
    """静态表的成员 vs 引擎反查到的（同服务端 Server/Debug/McdkTagsTest 的那份，两端互不导入，各写一份）。"""
    if engine is None:
        return {"engine": None, "extra": [], "missing": sorted(static)}
    return {"engine": len(engine), "extra": sorted(set(engine) - set(static)), "missing": sorted(set(static) - set(engine))}


def mcdk_test_tags_client():
    """测试函数：客户端口的时间线、每个标签的差、五把刀、牛肉的营火配方；返回结构化结果。"""
    port = EngineTags.PORT
    ready = port.ready()
    items = {}
    for table in (Tags.ITEM_TAGS, Tags.VANILLA_TAGS):
        for tag, members in table.items():
            items[tag] = _diff(members, port.itemsOf(tag))
    blocks = dict((tag, _diff(members, port.blocksOf(tag))) for tag, members in Tags.BLOCK_TAGS.items())
    missing = sorted(tag for tag, row in list(items.items()) + list(blocks.items()) if row["missing"])
    knives = dict((name, Knives.isKnife(name)) for name in Tags.ITEM_TAGS[Tags.KNIFE])
    raw = port.campfireRecipes("minecraft:beef", 0)
    timing = {"loadedAt": EngineTags.LOADED_AT, "firstProbeAt": port.firstProbeAt, "readyAt": port.readyAt, "probes": port.probes,
              "secondsAfterLoad": None if port.readyAt is None else port.readyAt - EngineTags.LOADED_AT}
    return {"case": "tags_client", "ok": bool(ready) and not missing and all(knives.values()), "ready": ready, "timing": timing,
            "missing": missing, "items": items, "blocks": blocks, "knives": knives,
            "beefCampfire": {"raw": repr(raw)[:600], "parsed": Grilling.cookedOf(raw, "minecraft:beef")}}


def mcdk_test_tags_probe_grill():
    """测试函数：探针包的番茄在这个线程（客户端）里 Grilling.resultOf 给什么、两个口各自的原始答案、调之前 / 之后缓存里记着什么。"""
    name, expected = PROBE_GRILL
    if compFactory.CreateItem(levelId).GetItemBasicInfo(name, 0) is None:
        return {"case": "tags_probe_grill", "ok": True, "skipped": "没装探针包（%s）" % name}
    before = repr(Grilling._cache.get((name, 0), "<没记>"))
    raw = dict((side, repr(port.campfireRecipes(name, 0))[:300]) for side, port in Grilling._ports.items())
    result = Grilling.resultOf(name, 0)
    return {"case": "tags_probe_grill", "thread": "client", "ok": result == expected, "result": result, "expected": expected,
            "raw": raw, "cachedBefore": before, "cachedAfter": repr(Grilling._cache.get((name, 0), "<没记>"))}


def _kaleidoscopeJei(port):
    """森罗物语厨房客户端 JEI 的标签缓存：记着哪些标签、哪些和客户端引擎现在的对不上；没装（导入不了、没有这个缓存）是 None。"""
    try:
        module = clientApi.ImportModule(KC_JEI)
    except Exception:  # noqa: BLE001 - 导入不了（给 None 或者抛异常）都当没装
        module = None
    cache = getattr(module, "_ITEM_TAG_CACHE", None) if module is not None else None
    if cache is None:
        return None
    stale = sorted(tag for tag in cache if tag in Tags.COOKING_STANDARD and set(cache[tag]) != set(port.itemsOf(tag) or ()))
    return {"cached": sorted(cache), "stale": stale}


def mcdk_test_tags_standard():
    """测试函数：团队规范的 18 个标签客户端引擎里的成员；装了森罗物语厨房时它 JEI 的标签缓存过没过时。"""
    port = EngineTags.PORT
    rows = {}
    for tag in Tags.COOKING_STANDARD:
        engine = port.itemsOf(tag)
        row = _diff(Tags.ITEM_TAGS.get(tag, ()), engine)
        row["members"] = sorted(engine) if engine is not None else None
        rows[tag] = row
    jei = _kaleidoscopeJei(port)
    missing = sorted(tag for tag, row in rows.items() if row["missing"])
    ok = bool(port.ready()) and not missing and not (jei and jei["stale"])
    return {"case": "tags_standard_client", "ok": ok, "ready": port.ready(), "missing": missing,
            "kaleidoscopeJei": jei if jei is not None else "没装森罗物语厨房（%s 导入不了）" % KC_JEI, "tags": rows}
