# -*- coding: utf-8 -*-
# runner: both
"""工作台合成后补还剩余物：纯规则（Shared/Rules/Crafting.py）和服务端处理（Server/CraftReturns.py，假引擎驱动）。

照 JE 的 ResultSlot.onTake：每格原料用掉一件，剩余物放回原来那格（空了才放得回），否则进背包。
实机核对过的引擎事实（3.10，Server/Debug/McdkCraftTest.py）：事件一次请求发一次、这时格子还没扣、
潜行做多份时 itemDict.count 是总数——测试按这个喂。
"""
from __future__ import print_function

import fakeengine
import fdtest

world = fakeengine.install()
Rules = fdtest.load("Shared.Rules.Crafting")
ItemTags = fdtest.load("Shared.Rules.ItemTags")
Table = fdtest.load("Shared.Data.CraftReturns").CraftReturns
Food = fdtest.load("Shared.Data.Food")
Registry = fdtest.load("Server.EventRegistry")
Server = fdtest.load("Server.CraftReturns")

PLAYER = "p1"
BUCKET, BOTTLE, BOWL = "minecraft:bucket", "minecraft:glass_bottle", "minecraft:bowl"


def _fill(*stacks):
    """从 3×3 的第一格（槽位 32）起摆：(物品名, 个数)，None 空一格。"""
    world.players.clear()
    world.spawned[:] = []
    world.timers[:] = []
    world.uiOpen = True
    player = world.addPlayer(PLAYER)
    world.uiSlots[PLAYER] = dict((32 + index, {"newItemName": stack[0], "newAuxValue": 0, "count": stack[1]})
                                 for index, stack in enumerate(stacks) if stack)
    return player


def _craft(result, count, crafts=1, cancel=False):
    """取一次结果：派发事件，再像引擎那样每格扣 crafts 件，然后跑下一刻的定时器。"""
    args = {"playerId": PLAYER, "itemDict": {"newItemName": result, "newAuxValue": 0, "count": count},
            "screenContainerType": 1, "cancel": cancel}
    Registry.dispatch("CraftItemOutputChangeServerEvent", args, result)
    slots = world.uiSlots[PLAYER]
    for slot in list(slots):
        slots[slot]["count"] -= 0 if cancel else crafts
        if slots[slot]["count"] <= 0:
            del slots[slot]
    world.runTimers()


def _grid():
    return dict((slot, (stack["newItemName"], stack["count"])) for slot, stack in world.uiSlots[PLAYER].items())


def _given(player):
    return sorted((item.get("newItemName"), item["count"]) for item in player["given"])


# ---------------------------------------------------------------- 纯规则

def testTheGridNamesOneRecipe():
    potato = Table["arris:stuffed_potato"]
    grid = {32: ("minecraft:baked_potato", 5), 36: ("minecraft:milk_bucket", 1), 40: ("arris:beef_patty", 2)}
    assert Rules.namesOf(grid) == ("arris:beef_patty", "minecraft:baked_potato", "minecraft:milk_bucket")
    assert Rules.returnsOf(Rules.entryFor(potato, grid), grid, 1) == [(36, BUCKET, 1)]
    grid[36] = ("arris:milk_bottle", 3)
    assert Rules.returnsOf(Rules.entryFor(potato, grid), grid, 1) == [(36, BOTTLE, 1)], "同一成品按格子里实际的料还"
    grid[33] = ("minecraft:dirt", 1)
    assert Rules.entryFor(potato, grid) is None and Rules.entryFor(potato, {}) is None
    assert Rules.returnsOf(None, grid, 1) == [], "认不出配方：什么都不还"


class TagPort(object):
    """只答物品标签的假口：members = {标签: [物品名]}。"""

    def __init__(self, members):
        self.members = members

    def ready(self):
        return True

    def itemsOf(self, tag):
        return self.members.get(tag, [])

    def tagsOf(self, itemName, aux=0):
        return [tag for tag, names in self.members.items() if itemName in names]


def _ports(port):
    for side in ItemTags.SIDES:
        ItemTags.setPort(side, port if side == "server" else None)


def testTagSlotsTakeWhatOtherModsPutInTheTag():
    """标签格按标签认（ItemTags 现问）：别的模组并进 common:milk 的奶也认得出是这条配方，但它不在 Remainders 里，不还东西。"""
    entries = [{"slots": ("minecraft:baked_potato", "#common:cooked_beef", "#common:milk"), "count": 1, "keeps": (), "source": "a"}]
    grid = {32: ("minecraft:baked_potato", 1), 33: ("mymod:goat_milk", 1), 34: ("minecraft:cooked_beef", 1)}
    _ports(None)
    assert Rules.entryFor(entries, grid) is None, "没登记进标签：对不上"
    _ports(TagPort({"common:milk": ["mymod:goat_milk"]}))
    try:
        entry = Rules.entryFor(entries, grid)
        assert entry is entries[0]
        assert Rules.returnsOf(entry, grid, 1) == [], "Remainders 里没有的物品不留东西"
        grid[33] = ("arris:milk_bottle", 1)
        assert Rules.returnsOf(Rules.entryFor(entries, grid), grid, 2) == [(33, BOTTLE, 2)], "自带的奶瓶照还，两份还两个"
    finally:
        _ports(None)


def testTwoMatchingRecipesMeanNoReturns():
    """格子同时对得上两条：认不出是哪条，什么都不还（一次合成最多还一次的另一面）。"""
    entries = [{"slots": ("#common:milk", "minecraft:sugar"), "count": 1, "keeps": (), "source": "a"},
               {"slots": ("minecraft:milk_bucket", "minecraft:sugar"), "count": 1, "keeps": (), "source": "b"}]
    grid = {32: ("minecraft:milk_bucket", 1), 33: ("minecraft:sugar", 1)}
    assert Rules.entryFor(entries, grid) is None
    grid[32] = ("arris:milk_bottle", 1)
    assert Rules.entryFor(entries, grid) is entries[0]
    assert Rules.entryFor(entries, {32: ("minecraft:sugar", 1)}) is None, "少一格对不上"


def testKeptOptionsStay():
    entry = {"slots": ("#common:wheat", "#common:water_bucket"), "count": 1, "keeps": ("#common:water_bucket",), "source": "d"}
    grid = {32: ("minecraft:wheat", 3), 34: ("minecraft:water_bucket", 1)}
    assert Rules.entryFor([entry], grid) is entry
    assert Rules.returnsOf(entry, grid, 1) == [(34, "minecraft:water_bucket", 1)], "水桶原样留下，不换成空桶"


def testCraftsAreCountedFromWhatTheGridLost():
    before = {32: ("a", 5), 33: ("b", 3)}
    assert Rules.craftsDone(before, {32: ("a", 4), 33: ("b", 2)}) == 1
    assert Rules.craftsDone(before, {32: ("a", 2)}) == 3, "格子空了 = 全用掉了"
    assert Rules.craftsDone(before, before) == 0, "取消了、请求被拒：一件没少"
    assert Rules.craftsDone(before, {32: ("a", 1), 33: ("b", 2)}) == 1, "同一刻又挪走别的：按少得最少的那格"
    assert Rules.craftsDone(before, {}, most=1) == 1, "界面关了格子全空：不超过取出的份数"
    assert Rules.craftsDone(before, {32: ("x", 9), 33: ("b", 2)}) == 1, "那格换成了别的东西算全用掉"
    assert Rules.craftsDone({}, {}) == 0
    assert Rules.mostCrafts(8, 8) == 1 and Rules.mostCrafts(24, 8) == 3 and Rules.mostCrafts(None, 0) == 1


def testRemaindersGoBackToTheirSlotWhenItIsEmpty():
    assert Rules.settle(None, BUCKET, 1, 16) == ((BUCKET, 1), 0)
    assert Rules.settle(("arris:milk_bottle", 2), BOTTLE, 1, 64) == (None, 1), "那格还有料：进背包"
    assert Rules.settle((BOTTLE, 63), BOTTLE, 3, 64) == ((BOTTLE, 64), 2), "同一种就叠上去，叠不下的进背包"
    assert Rules.settle(None, "minecraft:water_bucket", 3, 1) == (("minecraft:water_bucket", 1), 2)
    entry = Table["arris:honey_glazed_ham_block_stage0"][0]
    before = {32: ("arris:cooked_rice", 1), 33: ("minecraft:honey_bottle", 1), 34: ("arris:cooked_rice", 2),
              35: ("minecraft:bowl", 4)}
    assert Rules.returnsOf(entry, before, 1) == [(32, BOWL, 1), (33, BOTTLE, 1), (34, BOWL, 1)], "碗本身不是剩余物"
    assert Rules.returnsOf(entry, before, 0) == []


# ---------------------------------------------------------------- 服务端

def testMilkBucketLeavesItsBucketInTheGrid():
    player = _fill(("minecraft:milk_bucket", 1), ("minecraft:glass_bottle", 2), ("minecraft:glass_bottle", 2),
                   ("minecraft:glass_bottle", 2), ("minecraft:glass_bottle", 2))
    _craft("arris:milk_bottle", 4)
    assert _grid()[32] == (BUCKET, 1), "奶桶那格空了：空桶放回那格（JE）"
    assert _given(player) == [] and world.spawned == []


def testRiceLeavesBowlsInTheInventoryWhenTheSlotIsBusy():
    player = _fill(("arris:cod_slice", 6), ("arris:cod_slice", 6), ("arris:cooked_rice", 6))
    _craft("arris:cod_roll", 6, crafts=3)                    # 潜行一次做 3 份：count 是总数
    assert _grid()[34] == ("arris:cooked_rice", 3)
    assert _given(player) == [(BOWL, 3)], "米饭那格还有米饭：3 只碗进背包"


def testDoughKeepsItsWaterBucket():
    player = _fill(("minecraft:wheat", 5), None, ("minecraft:water_bucket", 1))
    _craft("arris:wheat_dough", 1)
    assert _grid() == {32: ("minecraft:wheat", 4), 34: ("minecraft:water_bucket", 1)}, "JE 的 DoughRecipe：水桶原样留下"
    assert _given(player) == []


def testShepherdsPieGivesBackWhatItsMilkCameIn():
    stacks = [("minecraft:baked_potato", 1), ("minecraft:baked_potato", 1), ("arris:onion", 1), ("arris:onion", 1),
              ("minecraft:bowl", 1), ("arris:cooked_mutton_chops", 1), ("minecraft:cooked_mutton", 1),
              ("minecraft:cooked_mutton", 1)]
    _fill(*(stacks + [("minecraft:milk_bucket", 1)]))
    _craft("arris:shepherds_pie_block_stage0", 1)
    assert _grid() == {40: (BUCKET, 1)}, "熟羊肉和熟羊排混着放也认（JE 的标签）"
    _fill(*(stacks + [("arris:milk_bottle", 1)]))
    _craft("arris:shepherds_pie_block_stage0", 1)
    assert _grid() == {40: (BOTTLE, 1)}


def testNothingComesBackWithoutACraft():
    player = _fill(("minecraft:milk_bucket", 1), ("minecraft:baked_potato", 1), ("arris:beef_patty", 1))
    _craft("arris:stuffed_potato", 1, cancel=True)           # 被取消：格子一件没少
    assert _given(player) == [] and _grid()[32] == ("minecraft:milk_bucket", 1)
    player = _fill()                                         # 创造模式从物品栏拿：合成格是空的
    _craft("arris:stuffed_potato", 1)
    assert _given(player) == [] and _grid() == {}
    player = _fill(("arris:milk_bottle", 1), ("minecraft:dirt", 1))
    _craft("arris:stuffed_potato", 1)
    assert _given(player) == [], "格子对不上本包的配方：不还"


def testAClosedScreenSendsRemaindersToTheInventory():
    player = _fill(("minecraft:milk_bucket", 1), ("minecraft:baked_potato", 1), ("minecraft:cooked_beef", 1))
    args = {"playerId": PLAYER, "itemDict": {"newItemName": "arris:stuffed_potato", "newAuxValue": 0, "count": 1}}
    Registry.dispatch("CraftItemOutputChangeServerEvent", args, "arris:stuffed_potato")
    world.uiSlots[PLAYER] = {}
    world.uiOpen = False
    world.runTimers()
    assert _given(player) == [(BUCKET, 1)]


def testDownstreamContainerDictStillWorksByResult():
    player = _fill(("test:jam", 2))
    Food.shapedRecipeContainerDict["test:toast"] = {"itemName": BOTTLE, "auxValue": 0, "perCraft": 2}
    try:
        _craft("test:toast", 6, crafts=2)
    finally:
        del Food.shapedRecipeContainerDict["test:toast"]
    assert _given(player) == [(BOTTLE, 3)], "下游包登记的成品：一次取出 6 个、一份 2 个 = 3 份"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
