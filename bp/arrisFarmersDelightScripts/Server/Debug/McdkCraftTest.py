# -*- coding: utf-8 -*-
"""McdkCraftTest - 工作台合成的游戏内自检（服务端）：测试函数，仅供 MCDK-MCP 的 execute_code / 开发调试调用

不会自动运行，没有 RPC 端点。合成要客户端点结果格（mc_input 点 3×3 右边的结果格；潜行点 = 一次做完），这里摆场景、记录、判定。
工作台界面要先开着：在玩家旁边放一个工作台方块，客户端投递右键打开（mcdk_test_craft_open 不替你开：OpenWorkBench 在 2026-11-26 的 3.10 里
返回 True 但界面没开，1 秒后最上层还是 hud_screen）。投递点结果格之前先连发三步 move（间隔 120 ms），悬停才落到结果格上（只发一步时悬停
留在界面当前选中的格子上，点下去会把那一格的原料拿到鼠标上，之后结果就取不走了；2026-11-26 实机：窗口客户区 960x562、界面 480x283 时
结果格在界面坐标 (362.9, 99.5)）。服务端摆的格子，开界面后第一次摆客户端不出结果，所以摆料都摆两遍。
    from arrisFarmersDelightScripts.Server.Debug import McdkCraftTest as T

手写的几个用例（CASES：照 JE 的合成剩余物，空了的那格放回剩余物、没空就进背包；前置包在场时砧板菜被拦、切片拼回整个派不拦）：
    T.mcdk_test_craft_setup("milk")      摆好这个用例的原料、清空记录
    （客户端点结果格）
    T.mcdk_test_craft_check("milk")      核对：事件发没发 / 被没被取消、合成后格子里和背包里的剩余物
探针排在所有处理函数前面，被取消的合成也记得到。会改玩家的合成格和鼠标上拿着的东西，check 后清掉。

写了标签的工作台配方逐份真做一遍（31 份配方 62 例，用例怎么来的见 Server/Debug/CraftCaseKit）：
    T.mcdk_test_craft_cases()            用例表：每例的 grid、expect（做一份之后合成格 + 背包里该有的全部东西）、same（swap 换不了成员，可以跳过）、
                                         dish（料正好是砧板上某道菜的一条配方）、blocked（dish 而且工作台的拦截在：这一例该被拦）
    T.mcdk_test_craft_put(3)             清空合成格、鼠标上的东西和背包，把第 3 例的料一格一个摆进 3×3（行优先）
    （客户端投递 Shift 点结果格）
    T.mcdk_test_craft_check(3)           点过隔 0.3 秒再调：读合成格 + 背包和预期比（missing 少了的、extra 多了的），然后清掉合成格
量配方本身要不带前置包跑。装着前置包、砧板站点登上了时工作台拦砧板菜（Compat/Diegesis/DishCrafts）：blocked 的那些例子 check 把"被拦"当预期——
料原样留在格子里、背包里什么都没多、合成事件来过而且被取消了；别的包并进标签的东西不在砧板的菜谱表里，不拦。
put 会清空玩家整个背包：在用户的世界里跑之前先把背包存下来，跑完还原。
2026-11-26 实机（第十一轮）：不带前置包 54 例全过（另 8 例 same 跳过）；带前置包 36 例被拦，标签格换成别的包的番茄的照常做出来。
"""
from . import CraftCaseKit as Kit
from ..EventRegistry import registerHandler
from ..Helpers.Engine import compFactory, levelId, serverApi, ItemPosType
from ...Shared.Rules import Crafting

BENCH = tuple(range(32, 41))         # PlayerUISlot 的 3×3
CURSOR = 0                           # PlayerUISlot.CursorSelected：鼠标上拿着的东西
WATCH = ("minecraft:bucket", "minecraft:glass_bottle", "minecraft:bowl", "minecraft:water_bucket")
OPEN_HOW = "OpenWorkBench 在 3.10 里返回 True 但不开界面：在玩家旁边放一个工作台方块，客户端投递右键打开"
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
    """测试函数：不替你开工作台界面（OpenWorkBench 在 2026-11-26 的 3.10 里返回 True 但界面没开），只把怎么开交回去。"""
    return {"case": "craft_open", "ok": False, "error": OPEN_HOW}


def mcdk_test_craft_setup(case):
    """测试函数：摆好用例的原料（工作台界面要已经开着：放一个工作台方块、投递右键打开，隔一刻再调这个），清空记录。"""
    playerId = _player()
    del _log[:]
    _fill(playerId, CASES[case]["grid"])
    done = _fill(playerId, CASES[case]["grid"])
    return {"case": "craft_setup:" + case, "ok": bool(done) and all(done), "shift": bool(CASES[case].get("shift")),
            "grid": _grid(playerId)}


def mcdk_test_craft_check(case):
    """测试函数：点过结果格之后核对这个用例，返回结构化结果，并清掉合成格。case 是数（mcdk_test_craft_cases 的第几例）时
    读合成格 + 背包和预期比；是名字（CASES 的键）时照旧读事件记录。"""
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


def _cases():
    vetoed = Kit.vetoActive()
    found = Kit.cases()
    for case in found:
        case["blocked"] = bool(case["dish"] and vetoed)
    return found


def mcdk_test_craft_cases():
    """测试函数：写了标签的工作台配方的用例表（每份 base / swap 两例）；unresolved 非空是标签取不到成员，vetoed 是工作台拦砧板菜的拦截在不在。"""
    cases = _cases()
    return {"case": "craft_cases", "ok": bool(cases) and not [case for case in cases if case["unresolved"]], "count": len(cases),
            "vetoed": Kit.vetoActive(), "cases": cases}


def mcdk_test_craft_put(index):
    """测试函数：清空合成格、鼠标上的东西和背包，把第 index 例的料一格一个摆进 3×3（工作台界面要已经开着），清空记录。"""
    playerId, case = _player(), _cases()[index]
    del _log[:]
    _clearInventory(playerId)
    stacks = [(name, 1) if name else None for name in case["grid"]]
    _fill(playerId, stacks)
    done = _fill(playerId, stacks)
    return {"case": "craft_put:%d" % index, "ok": bool(done) and all(done), "source": case["source"], "variant": case["variant"],
            "blocked": case["blocked"], "grid": _grid(playerId), "expect": case["expect"]}


def _checkIndexed(index):
    """被拦的一例：料原样留在格子里、背包里什么都没多，而且合成事件来过、被取消了（没点到结果格时也是料都在，但没有事件，不算过）。"""
    playerId, case = _player(), _cases()[index]
    got = _inventory(playerId)
    for name, count in _grid(playerId).values():
        got[name] = got.get(name, 0) + count
    want = Kit.ingredients(case["grid"]) if case["blocked"] else case["expect"]
    missing = dict((name, count - got.get(name, 0)) for name, count in want.items() if got.get(name, 0) < count)
    extra = dict((name, count - want.get(name, 0)) for name, count in got.items() if count > want.get(name, 0))
    cancelled = any(entry.get("cancel") for entry in _log)
    _fill(playerId, [])
    return {"case": "craft_check:%d" % index, "ok": not missing and not extra and (cancelled or not case["blocked"]),
            "source": case["source"], "variant": case["variant"], "blocked": case["blocked"], "cancelled": cancelled,
            "got": got, "expect": want, "missing": missing, "extra": extra, "events": len(_log)}


def mcdk_test_craft_log():
    """测试函数：取回原始记录。"""
    return {"case": "craft_log", "ok": True, "log": list(_log)}
