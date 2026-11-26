# -*- coding: utf-8 -*-
"""McdkCraftTest - 工作台合成的游戏内自检（服务端）：测试函数，仅供 MCDK-MCP 的 execute_code / 开发调试调用

不会自动运行，没有 RPC 端点。合成要客户端点结果格（mc_input 点 3×3 右边的结果格；潜行点 = 一次做完），这里摆场景、记录、判定：
    from arrisFarmersDelightScripts.Server.Debug import McdkCraftTest as T
    T.mcdk_test_craft_open()             给第一个玩家打开工作台界面（不依赖方块）
    T.mcdk_test_craft_setup("milk")      摆好这个用例的原料、清空记录（界面要已经开着）
    （客户端点结果格）
    T.mcdk_test_craft_check("milk")      核对：事件发没发 / 被没被取消、合成后格子里和背包里的剩余物
用例见 CASES：照 JE 的合成剩余物（空了的那格放回剩余物，没空就进背包）、前置包在场时砧板菜被拦而切片拼回整个派不拦。
探针排在所有处理函数前面，被取消的合成也记得到。会改玩家的合成格和鼠标上拿着的东西，check 后清掉。
用 mc_input 点的时候（实测 3.10）：服务端摆的格子，开界面后第一次摆客户端不出结果，所以 setup 摆两遍；点之前先发几步 move
把指针挪到结果格上（不挪的话点击落在界面当前选中的格子上，会把原料拿到鼠标上，之后结果就取不走了）。

写了标签的工作台配方逐份真做一遍（2026-11-26；表是 tools/gen_crafts.py 生成的 Server/Debug/CraftCases.py，31 份配方）：
    T.mcdk_test_craft_cases()            用例表：每份两例，"base" 标签格取第一个成员（农夫乐事自己的 / 原版的），"swap" 换另一个成员
                                         （引擎现在的成员，别的包并进标签的也算，挑最后一个不一样的；标签只有一个成员时 same 为真）；
                                         expect 是做一份之后合成格 + 背包里该有的全部东西（成品 + 剩下的容器）
    T.mcdk_test_craft_open()             打开工作台界面
    T.mcdk_test_craft_put(3)             清空合成格、鼠标上的东西和背包，把第 3 例的料一格一个摆进 3×3（行优先；摆两遍，同上）
    （客户端投递一次 Shift 点成品格）
    T.mcdk_test_craft_check(3)           读合成格 + 背包，和 expect 比（missing 少了的、extra 多了的），然后清掉合成格
有序配方的容器是 result 数组写的；无序配方按放进去的物品查 Remainders（Server/CraftReturns 补还），别的包并进标签的东西不在表里就不还。
"""
from . import CraftCases
from ..EventRegistry import registerHandler
from ..Helpers.Engine import compFactory, levelId, serverApi, ItemPosType
from ...Shared.Data import Remainders
from ...Shared.Rules import Crafting, ItemTags

BENCH = tuple(range(32, 41))         # PlayerUISlot 的 3×3
CURSOR = 0                           # PlayerUISlot.CursorSelected：鼠标上拿着的东西
WATCH = ("minecraft:bucket", "minecraft:glass_bottle", "minecraft:bowl", "minecraft:water_bucket")
_log = []

# 用例：grid 按 3×3 从左上起一格一叠（None 空一格）；点一次结果格（shift = 潜行点，一次做完）之后应该是：
#   cancel 被取消；after 合成格里剩下的 {第几格: (物品名, 个数)}；gain 背包里多出来的容器
CASES = {
    # 牛奶倒进瓶子：奶桶那格空了，空桶放回那格
    "milk": {"grid": [("minecraft:milk_bucket", 1)] + [("minecraft:glass_bottle", 2)] * 4, "result": "arris:milk_bottle",
             "cancel": False, "after": {0: ("minecraft:bucket", 1), 1: ("minecraft:glass_bottle", 1)}, "gain": {}},
    # 牛奶瓶倒回桶（潜行点做 2 份）：四格奶瓶都空了，各放回 2 个玻璃瓶
    "pour": {"grid": [("minecraft:bucket", 2)] + [("arris:milk_bottle", 2)] * 4, "result": "minecraft:milk_bucket",
             "shift": True, "cancel": False, "after": dict((index, ("minecraft:glass_bottle", 2)) for index in (1, 2, 3, 4)),
             "gain": {}},
    # 切片拼回整个派：一种原料，不是砧板菜，前置包在场也不拦
    "slices": {"grid": [("arris:apple_pie_slice", 1), ("arris:apple_pie_slice", 1), None,
                        ("arris:apple_pie_slice", 1), ("arris:apple_pie_slice", 1)],
               "result": "arris:apple_pie_item", "cancel": False, "after": {}, "gain": {}},
    # 以下两个要前置包在场：砧板菜在工作台被拦，格子一件不少、什么都不还
    "dough": {"grid": [("minecraft:wheat", 3), ("minecraft:water_bucket", 1)], "result": "arris:wheat_dough",
              "cancel": True, "after": {0: ("minecraft:wheat", 3), 1: ("minecraft:water_bucket", 1)}, "gain": {}},
    "sandwich": {"grid": [("minecraft:bread", 1), ("arris:fried_egg", 1), ("arris:fried_egg", 1)],
                 "result": "arris:egg_sandwich", "cancel": True,
                 "after": {0: ("minecraft:bread", 1), 1: ("arris:fried_egg", 1), 2: ("arris:fried_egg", 1)}, "gain": {}},
}


def _player():
    players = serverApi.GetPlayerList()
    return players[0] if players else None


def _grid(playerId):
    item = compFactory.CreateItem(playerId)
    found = {}
    for slot in Crafting.GRID_SLOTS:
        stack = item.GetPlayerUIItem(playerId, slot, False, False)
        if stack and stack.get("count"):
            found[slot] = (stack.get("newItemName"), stack.get("count"))
    return found


def _watch(playerId):
    items = compFactory.CreateItem(playerId).GetPlayerAllItems(ItemPosType.INVENTORY, False) or []
    counts = dict((name, 0) for name in WATCH)
    for stack in items:
        if stack and stack.get("newItemName") in counts:
            counts[stack["newItemName"]] += stack["count"]
    return counts


@registerHandler("CraftItemOutputChangeServerEvent", priority=1000)
def _record(args):
    """测试探针：排在所有处理函数前面（被取消的合成也记得到），只记录，不改事件。"""
    playerId = args.get("playerId")
    if not playerId:
        return
    item = args.get("itemDict") or {}
    entry = {"item": (item.get("newItemName") or item.get("itemName"), item.get("count")),
             "screen": args.get("screenContainerType"), "grid": _grid(playerId), "inventory": _watch(playerId)}
    _log.append(entry)

    def later():
        entry["cancel"] = bool(args.get("cancel"))
        entry["after"] = _grid(playerId)
        entry["inventoryAfter"] = _watch(playerId)
    compFactory.CreateGame(levelId).AddTimer(0.2, later)


def _fill(playerId, stacks):
    item = compFactory.CreateItem(playerId)
    done = []
    for slot in (CURSOR,) + BENCH:
        item.SetPlayerUIItem(playerId, slot, None, False, False)
    for slot, stack in zip(BENCH, stacks):
        if stack is not None:
            done.append(bool(item.SetPlayerUIItem(playerId, slot, {"itemName": stack[0], "auxValue": 0, "count": stack[1]},
                                                  False, False)))
    return done


def mcdk_test_craft_open():
    """测试函数：给第一个玩家打开工作台界面，清空记录。"""
    playerId = _player()
    del _log[:]
    if playerId is None:
        return {"case": "craft_open", "ok": False, "error": "no player"}
    return {"case": "craft_open", "ok": bool(compFactory.CreateBlockInfo(playerId).OpenWorkBench())}


def mcdk_test_craft_setup(case):
    """测试函数：摆好用例的原料（工作台界面要已经开着：先调 mcdk_test_craft_open，隔一刻再调这个），清空记录。"""
    playerId = _player()
    del _log[:]
    _fill(playerId, CASES[case]["grid"])
    done = _fill(playerId, CASES[case]["grid"])
    return {"case": "craft_setup:" + case, "ok": bool(done) and all(done), "shift": bool(CASES[case].get("shift")),
            "grid": _grid(playerId)}


def mcdk_test_craft_check(case):
    """测试函数：点过结果格之后核对这个用例，返回结构化结果，并清掉合成格。case 是数（mcdk_test_craft_cases 的第几例）时
    读合成格 + 背包和 expect 比；是名字（CASES 的键）时照旧读事件记录。"""
    if isinstance(case, int) and not isinstance(case, bool):
        return _checkIndexed(case)
    playerId, want = _player(), CASES[case]
    entry = _log[-1] if _log else None
    result = {"case": "craft:" + case, "events": len(_log), "entry": entry}
    if entry is None or "after" not in entry:
        result.update(ok=False, error="no craft event recorded (click the output slot first, then wait a moment)")
        return result
    after = dict((slot - BENCH[0], stack) for slot, stack in entry["after"].items())
    gain = dict((name, entry["inventoryAfter"][name] - entry["inventory"][name]) for name in WATCH
                if entry["inventoryAfter"][name] != entry["inventory"][name])
    checks = {"result": entry["item"][0] == want["result"], "cancel": entry["cancel"] == want["cancel"],
              "gain": gain == want["gain"],
              "after": all(after.get(index) == stack for index, stack in want["after"].items())
              and (bool(want["after"]) or not after)}
    result.update(ok=all(checks.values()), checks=checks, after=after, gain=gain)
    _fill(playerId, [])
    return result


def _members(tag):
    """标签现在的成员（引擎的，别的包并进来的也算）；引擎答不出时用生成表里抄的静态成员。"""
    return tuple(ItemTags.itemsOf(tag)) or tuple(CraftCases.MEMBERS.get(tag, ()))


def _pick(cell, avoid=None):
    """格子里放什么：物品就是它；"#标签" 取第一个成员，给了 avoid 就挑最后一个不一样的（没有就还是 avoid）。"""
    if cell is None or not cell.startswith("#"):
        return cell
    members = _members(cell[1:])
    if avoid is None:
        return members[0] if members else None
    others = [name for name in members if name != avoid]
    return others[-1] if others else avoid


def _expected(recipe, items):
    """做一份之后合成格 + 背包里该有的：成品，加上剩下的容器（有序配方是 result 数组写的；无序配方按放进去的物品查 Remainders，keeps 原样留下）。"""
    want = {recipe["result"][0]: recipe["result"][1]}
    extras = list(recipe["extras"])
    if recipe["kind"] == "shapeless":
        for cell, name in zip(recipe["grid"], items):
            left = name if name is not None and cell in recipe["keeps"] else Remainders.craftRemainderOf(name)
            if name is not None and left:
                extras.append((left, 1))
    for name, count in extras:
        want[name] = want.get(name, 0) + count
    return want


def _cases():
    found = []
    for recipe in CraftCases.RECIPES:
        base = [_pick(cell) for cell in recipe["grid"]]
        swap = [_pick(cell, chosen) for cell, chosen in zip(recipe["grid"], base)]
        for label, items in (("base", base), ("swap", swap)):
            found.append({"index": len(found), "source": recipe["source"], "variant": label, "kind": recipe["kind"],
                          "grid": items, "expect": _expected(recipe, items), "same": label == "swap" and swap == base,
                          "unresolved": [cell for cell, name in zip(recipe["grid"], items) if cell is not None and name is None]})
    return found


def _inventory(playerId):
    found = {}
    for stack in compFactory.CreateItem(playerId).GetPlayerAllItems(ItemPosType.INVENTORY, False) or []:
        if stack and stack.get("count"):
            name = stack.get("newItemName") or stack.get("itemName")
            found[name] = found.get(name, 0) + stack["count"]
    return found


def _clearInventory(playerId):
    item = compFactory.CreateItem(playerId)
    for slot, stack in enumerate(item.GetPlayerAllItems(ItemPosType.INVENTORY, False) or []):
        if stack and stack.get("count"):
            item.SetInvItemNum(slot, 0)


def mcdk_test_craft_cases():
    """测试函数：写了标签的工作台配方的用例表（每份 base / swap 两例）；unresolved 非空是标签取不到成员。"""
    cases = _cases()
    return {"case": "craft_cases", "ok": bool(cases) and not [case for case in cases if case["unresolved"]], "count": len(cases),
            "cases": cases}


def mcdk_test_craft_put(index):
    """测试函数：清空合成格、鼠标上的东西和背包，把第 index 例的料一格一个摆进 3×3（工作台界面要已经开着），清空记录。"""
    playerId, case = _player(), _cases()[index]
    del _log[:]
    _clearInventory(playerId)
    stacks = [(name, 1) if name else None for name in case["grid"]]
    _fill(playerId, stacks)
    done = _fill(playerId, stacks)
    return {"case": "craft_put:%d" % index, "ok": bool(done) and all(done), "source": case["source"], "variant": case["variant"],
            "grid": _grid(playerId), "expect": case["expect"]}


def _checkIndexed(index):
    playerId, case = _player(), _cases()[index]
    got = _inventory(playerId)
    for name, count in _grid(playerId).values():
        got[name] = got.get(name, 0) + count
    want = case["expect"]
    missing = dict((name, count - got.get(name, 0)) for name, count in want.items() if got.get(name, 0) < count)
    extra = dict((name, count - want.get(name, 0)) for name, count in got.items() if count > want.get(name, 0))
    _fill(playerId, [])
    return {"case": "craft_check:%d" % index, "ok": not missing and not extra, "source": case["source"], "variant": case["variant"],
            "got": got, "expect": want, "missing": missing, "extra": extra, "events": len(_log)}


def mcdk_test_craft_log():
    """测试函数：取回原始记录。"""
    return {"case": "craft_log", "ok": True, "log": list(_log)}
