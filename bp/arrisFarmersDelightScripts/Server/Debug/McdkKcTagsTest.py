# -*- coding: utf-8 -*-
"""McdkKcTagsTest - 森罗物语厨房登记进农夫乐事读的标签以后，农夫乐事认不认它的东西（服务端）：测试函数，仅供 MCDK-MCP 的 execute_code / 开发调试调用

不会自动运行，没有 RPC 端点。森罗 2026-11-26 在它自己的 netease_tags 里把十样东西登记进了农夫乐事读的标签（它的提交 9ea2b05；
docs/TAGS.md「森罗已经登记了」那张表，这里的 KC_ITEMS / KC_KNIVES / KC_STOVE 和那张表一行一行对上，tests/test_netease_tags 核对）。
标签的另一个方向（农夫乐事的东西进规范的 18 个粗标签、森罗认不认）是 McdkTagsTest.mcdk_test_tags_standard。
mcdk_test_kc_tags()：两个包都装着时报"反方向"，问的是服务端引擎口的原样答案（Server/Helpers/Tags.PORT）和农夫乐事的规则：
- items：八样东西各自登记进的细标签，引擎反查到的成员里有没有它（inEngine）、ItemTags.has 认不认（rule）；词表里用 # 嵌了这个细标签的标签
  （nested：生肉、熟肉、规范的粗标签……）认不认它（nestedLost：不认的那几个，引擎没把跨包的 # 展开就会有）；
- knives：四把菜刀在不在引擎反查的 common:knife 里（inEngine）、引擎按物品给的标签（engineTags）、Knives.isKnife 认不认
  （砧板上刀切、借刀、刀杀生物的额外掉落、刀收稻穗……都问它）；
- stove：炉灶方块在不在引擎反查的 farmersdelight:heat_sources 里（inEngine）、按方块问（GetBlockTags）带的标签（blockTags）、
  ItemTags.blockHas 认不认（rule）；引擎给它的方块状态（GetBlockStatesFromAuxValue，aux 0..15）里找一个点着的（lit）、一个没点着的（unlit），
  各问一次热源规则 HeatSources.heats：放在上面的锅 / 煎锅（underPot，看点燃状态：点着的该热、没点着的不该热）、手持煎锅身边（nearHand，
  JE 不看点燃状态：都热）、客户端手持煎锅按 aux 判（clientByAux，HeatSources.heatsByAux：只看标签，都热）；
  unreadable 是读不到状态（给 None）时锅下面的答案——照规则"没有点燃状态就算热"，是真（服务端平常读得到状态，这一条只是说明）；
- pot：厨锅拿森罗的原料凑一道农夫乐事的菜（CookingPot.matchRecipe，锅自己煮的时候走的就是它）：POT_CASES 里厨锅读的四个细标签各一道，
  经 common:raw_meat 的卷心菜卷一道；made 是做成了什么。熟牛杂、熟五花肉、熟羊排、煎蛋只有工作台配方读，这里不凑，在工作台里实际做；
- apart：用户 2026-11-26 定意面和面条不是一种：森罗的生面条不在农夫乐事的 common:pasta 里、农夫乐事的生意面不在 common:noodle 里（都该是假）。
没装森罗物语厨房（引擎不认 kaleidoscope_cookery:sashimi）时说明"没装"、ok 是真；装着、引擎里却没有这些登记（森罗的包还是 9ea2b05 之前的）时 ok 是假。
    from arrisFarmersDelightScripts.Server.Debug import McdkKcTagsTest as T
    return T.mcdk_test_kc_tags()
真的摆：厨锅、煎锅放在炉灶上，点着、熄掉各看一次，读炉灶那一格用 Server/Debug/McdkHeatTest.mcdk_test_heat_probe(x, y, z)（heat_source、heated_above）。
"""
from ..Helpers import Tags as EngineTags
from ..Helpers.Engine import compFactory, levelId
from ...Shared.Data import Tags
from ...Shared.Rules import CookingPot, HeatSources, ItemTags, Knives

KC = "kaleidoscope_cookery:"
PROBE = KC + "sashimi"              # 引擎认得它就是装了森罗
# 森罗登记进农夫乐事读的物品标签的八样东西：(森罗的东西, 登记进的标签)
KC_ITEMS = ((KC + "raw_cow_offal", Tags.RAW_BEEF), (KC + "raw_pork_belly", Tags.RAW_PORK), (KC + "raw_lamb_chops", Tags.RAW_MUTTON),
            (KC + "cooked_cow_offal", Tags.COOKED_BEEF), (KC + "cooked_pork_belly", Tags.COOKED_PORK),
            (KC + "cooked_lamb_chops", Tags.COOKED_MUTTON), (KC + "sashimi", Tags.RAW_FISH), (KC + "fried_egg", Tags.COOKED_EGG))
KC_KNIVES = tuple(KC + "%s_kitchen_knife" % metal for metal in ("iron", "gold", "diamond", "netherite"))     # 登记进 common:knife
KC_STOVE = KC + "kaleidoscope_cookery_stove"                                                              # 登记进方块标签 farmersdelight:heat_sources
STATE_AUX = 16              # 炉灶的方块状态问到 aux 15：点燃（两种）× 朝向（四种）用不完
# 厨锅：(这道菜读的细标签, 锅里的东西, 该做成的菜)
POT_CASES = ((Tags.RAW_BEEF, (KC + "raw_cow_offal", "minecraft:carrot", "minecraft:potato"), "arris:cookbeef_stew"),
             (Tags.RAW_PORK, ("arris:raw_pasta", "minecraft:egg", "minecraft:dried_kelp", KC + "raw_pork_belly"), "arris:noodle_soup"),
             (Tags.RAW_MUTTON, (KC + "raw_lamb_chops", "arris:raw_pasta", "arris:tomato_sauce"), "arris:pasta_with_mutton_chop"),
             (Tags.RAW_FISH, (KC + "sashimi", "arris:tomato_sauce", "arris:onion"), "arris:fish_stew"),
             (Tags.RAW_MEAT, ("arris:cabbage", KC + "raw_lamb_chops"), "arris:cabbage_rolls"))
APART = ((KC + "raw_noodles", Tags.PASTA), ("arris:raw_pasta", "common:noodle"))       # 不该认的


def _nested(tag):
    """词表里用 # 嵌了 tag 的物品标签（一层一层往外找）：别的模组登记进 tag 的东西，引擎展开 # 以后也在它们里面。"""
    found, todo = [], [tag]
    while todo:
        inner = "#" + todo.pop()
        for outer, written in sorted(Tags.ITEM_TAG_FILES.items()):
            if inner in written and outer not in found:
                found.append(outer)
                todo.append(outer)
    return found


def _items(port):
    rows = {}
    for name, tag in KC_ITEMS:
        nested = _nested(tag)
        rows[name] = {"tag": tag, "inEngine": name in (port.itemsOf(tag) or ()), "rule": ItemTags.has(name, tag),
                      "nested": nested, "nestedLost": [outer for outer in nested if not ItemTags.has(name, outer)]}
    return rows


def _knives(port):
    inEngine = port.itemsOf(Tags.KNIFE) or ()
    return dict((name, {"inEngine": name in inEngine, "engineTags": sorted(port.tagsOf(name, 0) or ()), "isKnife": Knives.isKnife(name)})
                for name in KC_KNIVES)


def _states(aux):
    """引擎给炉灶这个 aux 的方块状态；读不到、抛异常都给 None。"""
    try:
        states = compFactory.CreateBlockState(levelId).GetBlockStatesFromAuxValue(KC_STOVE, aux)
    except Exception:  # noqa: BLE001 - 自检：读不到就当没有
        return None
    return dict(states) if isinstance(states, dict) else None


def _heats(states, lit):
    return HeatSources.heats(KC_STOVE, lambda: states, lit=lit)


def _stove(port):
    found = {"lit": None, "unlit": None}
    for aux in range(STATE_AUX):
        states = _states(aux)
        if states and HeatSources.hasLitState(states):
            key = "lit" if HeatSources.isLit(states) else "unlit"
            if found[key] is None:
                found[key] = {"aux": aux, "states": states, "underPot": _heats(states, True), "nearHand": _heats(states, False),
                              "clientByAux": HeatSources.heatsByAux(KC_STOVE, aux)}
    found.update(inEngine=KC_STOVE in (port.blocksOf(Tags.HEAT_SOURCES) or ()), blockTags=sorted(port.blockTagsOf(KC_STOVE) or ()),
                 rule=ItemTags.blockHas(KC_STOVE, Tags.HEAT_SOURCES), unreadable=_heats(None, True))
    return found


def _stoveOk(stove):
    lit, unlit = stove["lit"], stove["unlit"]
    return bool(stove["inEngine"] and stove["rule"] and lit and unlit and lit["underPot"] and not unlit["underPot"])


def _pot():
    rows = []
    for tag, names, dish in POT_CASES:
        meal = CookingPot.matchRecipe([{"newItemName": name, "newAuxValue": 0, "count": 1} for name in names])[0]
        rows.append({"tag": tag, "items": list(names), "expected": dish, "made": meal["newItemName"] if meal else None})
    return rows


def mcdk_test_kc_tags():
    """测试函数：森罗登记进农夫乐事读的标签的十样东西，引擎里在不在、农夫乐事的规则认不认（见模块说明）；没装森罗时说明没装、算通过。"""
    if compFactory.CreateItem(levelId).GetItemBasicInfo(PROBE, 0) is None:
        return {"case": "kc_tags", "ok": True, "skipped": "没装森罗物语厨房（引擎不认 %s）" % PROBE}
    port = EngineTags.PORT
    items, knives, stove, pot = _items(port), _knives(port), _stove(port), _pot()
    apart = dict(("%s %s" % pair, ItemTags.has(*pair)) for pair in APART)
    problems = sorted(name for name, row in items.items() if not (row["inEngine"] and row["rule"]) or row["nestedLost"])
    problems += sorted(name for name, row in knives.items() if not (row["inEngine"] and row["isKnife"]))
    problems += ([] if _stoveOk(stove) else [KC_STOVE]) + [row["expected"] for row in pot if row["made"] != row["expected"]]
    problems += sorted(pair for pair, wrong in apart.items() if wrong)
    return {"case": "kc_tags", "ok": bool(port.ready()) and not problems, "ready": port.ready(), "problems": problems,
            "items": items, "knives": knives, "stove": stove, "pot": pot, "apart": apart}
