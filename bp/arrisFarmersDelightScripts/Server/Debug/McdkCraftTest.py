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
"""
from ..EventRegistry import registerHandler
from ..Helpers.Engine import compFactory, levelId, serverApi, ItemPosType
from ...Shared.Rules import Crafting

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
    """测试函数：点过结果格之后核对这个用例，返回结构化结果，并清掉合成格。"""
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


def mcdk_test_craft_log():
    """测试函数：取回原始记录。"""
    return {"case": "craft_log", "ok": True, "log": list(_log)}
