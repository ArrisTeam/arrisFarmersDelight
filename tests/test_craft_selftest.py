# -*- coding: utf-8 -*-
# runner: both
"""工作台的游戏内自检（Server/Debug/McdkCraftTest.py、用例 Server/Debug/CraftCaseKit.py）里写标签的配方那一组：用例表、摆料、核对，离线用假引擎跑一遍。

用例表（mcdk_test_craft_cases）：tools/gen_crafts.py 生成的 Server/Debug/CraftCases.py 里每份写标签的配方两例——base 标签格取第一个成员，
swap 换另一个成员（引擎现在的成员，别的包并进标签的也算）；expect 是做一份之后合成格 + 背包里该有的全部东西（成品 + 剩下的容器：
有序配方是 result 数组写的，无序配方按放进去的物品查 Remainders）。摆料（put）一格一个、行优先；核对（check）把合成格和背包加起来和预期比。
dish 是砧板上某道菜的一条配方：工作台拦砧板菜的处理函数（前置包的 DishCrafts）登记着时，这一例该被拦——料原样留着、事件被取消。
2026-11-26 第十一轮实机（探针包往 common:tomato、minecraft:egg 里并了一个番茄）：不带前置包 54 例全过、8 例 same 跳过；带前置包 36 例被拦。
"""
from __future__ import print_function

import sys

import fakeengine
import fdtest


class ItemPosType(object):
    INVENTORY, OFFHAND, CARRIED, ARMOR = 0, 1, 2, 3


world = fakeengine.install()
sys.modules[fakeengine.ENGINE_MODULE].ItemPosType = ItemPosType     # 假引擎没有这个枚举（自检模块读背包要用）
T = fdtest.load("Server.Debug.McdkCraftTest")
Kit = fdtest.load("Server.Debug.CraftCaseKit")
Cases = fdtest.load("Server.Debug.CraftCases")
ItemTags = fdtest.load("Shared.Rules.ItemTags")
Tags = fdtest.load("Shared.Data.Tags")
EventRegistry = fdtest.load("Server.EventRegistry")
PLAYER = "p1"
BUCKET, BOTTLE = "minecraft:bucket", "minecraft:glass_bottle"
PROBE = "fdprobe:tomato"


class TagPort(object):
    def __init__(self, members):
        self.members = members

    def ready(self):
        return True

    def itemsOf(self, tag):
        return self.members.get(tag, [])

    def tagsOf(self, itemName, aux=0):
        return [tag for tag, names in self.members.items() if itemName in names]


def _ports(port=None):
    for side in ItemTags.SIDES:
        ItemTags.setPort(side, port if side == "server" else None)


def _probePort():
    """第十一轮的探针包：番茄登记进 common:tomato（经 # 嵌套也就在蔬菜、作物里），又往原版的 minecraft:egg 里并了它。"""
    members = dict((tag, list(names)) for tag, names in Tags.ITEM_TAGS.items())
    for tag in (Tags.TOMATO, Tags.VEGETABLE, Tags.CROP):
        members[tag].append(PROBE)
    members[Tags.EGG] = list(Tags.VANILLA_TAGS[Tags.EGG]) + [PROBE]
    return TagPort(members)


def _case(cases, source, variant):
    return next(case for case in cases if case["source"] == source and case["variant"] == variant)


def _veto():
    """登记一个模块名是 ...DishCrafts 的处理函数，当作前置包的拦截（返回撤掉它的函数）。"""
    def onCraft(args):
        return None
    onCraft.__module__ = fdtest.SCRIPTS + ".Compat.Diegesis.DishCrafts"
    EventRegistry.registerHandler(Kit.CRAFT_EVENT, priority=50)(onCraft)

    def undo():
        EventRegistry._handlers[Kit.CRAFT_EVENT] = [entry for entry in EventRegistry._handlers[Kit.CRAFT_EVENT]
                                                    if entry.ident != (onCraft.__module__, "onCraft")]
    return undo


def testEveryTagRecipeHasABaseAndASwapCase():
    _ports()
    result = T.mcdk_test_craft_cases()
    assert result["ok"] and result["count"] == 2 * len(Cases.RECIPES) == 62, result["count"]
    cases = result["cases"]
    assert [case["index"] for case in cases] == list(range(len(cases)))
    potato = _case(cases, "arris_stuffed_potato.json", "base")
    assert "minecraft:milk_bucket" in potato["grid"] and potato["expect"] == {"arris:stuffed_potato": 1, BUCKET: 1}
    swap = _case(cases, "arris_stuffed_potato.json", "swap")
    assert "arris:milk_bottle" in swap["grid"] and "arris:beef_patty" in swap["grid"] and swap["expect"] == {"arris:stuffed_potato": 1, BOTTLE: 1}
    cake = _case(cases, "arris_cake_from_milk_bottle2.json", "swap")
    assert "minecraft:brown_egg" in cake["grid"] and cake["expect"] == {"minecraft:cake": 1, BUCKET: 2, BOTTLE: 1}, "有序：result 数组写的容器"
    board = _case(cases, "arris_cutting_board.json", "swap")
    assert board["grid"][:3] == ["minecraft:stick", "minecraft:warped_planks", "minecraft:warped_planks"] and not board["same"]
    assert _case(cases, "arris_honey_cookie.json", "swap")["same"], "小麦标签只有一个成员：换不了"


def testTheSwapCaseTakesWhatOtherPacksPutInTheTag():
    _ports(TagPort({"common:tomato": ["arris:tomato", PROBE]}))
    try:
        cases = T.mcdk_test_craft_cases()["cases"]
        stick = _case(cases, "arris_barbecue_stick.json", "swap")
        assert PROBE in stick["grid"] and not stick["same"] and stick["expect"] == {"arris:barbecue_stick": 1}
    finally:
        _ports()


def testBoardDishesAreMarkedAndOnlyBlockedWhileTheBoardVetoIsRegistered():
    """dish：料正好是砧板上某道菜的一条配方（DishList 按词表的静态成员展开，所以别的包的番茄不算）；blocked 还要拦截在。
    探针包那样并了番茄时：不是 same 的 54 例里 36 例是砧板菜——和第十一轮带前置包实测被拦的一样多。"""
    _ports(_probePort())
    try:
        result = T.mcdk_test_craft_cases()
        cases = result["cases"]
        live = [case for case in cases if not case["same"]]
        assert len(live) == 54 and len([case for case in live if case["dish"]]) == 36, (len(live), len([c for c in live if c["dish"]]))
        assert _case(cases, "arris_hamburger.json", "base")["dish"] and not _case(cases, "arris_hamburger.json", "swap")["dish"]
        assert not _case(cases, "arris_cutting_board.json", "base")["dish"], "砧板本身不是菜"
        assert result["vetoed"] is False and not [case for case in cases if case["blocked"]], "没装前置包：哪一例都不该被拦"
        undo = _veto()
        try:
            result = T.mcdk_test_craft_cases()
            assert result["vetoed"] is True and [case["blocked"] for case in result["cases"]] == [case["dish"] for case in result["cases"]]
        finally:
            undo()
        assert T.mcdk_test_craft_cases()["vetoed"] is False
    finally:
        _ports()


def _setUpPlayer(inventory):
    world.players.clear()
    world.uiOpen = True
    world.addPlayer(PLAYER)
    world.uiSlots[PLAYER] = {}
    saved = T._inventory, T._clearInventory
    T._inventory = lambda playerId: dict(inventory)
    T._clearInventory = lambda playerId: inventory.clear()
    return saved


def testPutThenCheck():
    _ports()
    inventory = {}
    saved = _setUpPlayer(inventory)
    try:
        cases = T.mcdk_test_craft_cases()["cases"]
        index = _case(cases, "arris_shepherds_pie_block.json", "base")["index"]
        inventory["minecraft:dirt"] = 3
        put = T.mcdk_test_craft_put(index)
        assert put["ok"] and inventory == {} and len(put["grid"]) == 9 and put["blocked"] is False, put
        world.uiSlots[PLAYER] = {32 + 3: {"newItemName": BUCKET, "newAuxValue": 0, "count": 1}}      # 奶桶那格放回空桶
        inventory["arris:shepherds_pie_block_stage0"] = 1
        checked = T.mcdk_test_craft_check(index)
        assert checked["ok"] and checked["missing"] == {} and checked["extra"] == {}, checked
        assert world.uiSlots[PLAYER] == {}, "核对完清掉合成格"
        world.uiSlots[PLAYER] = {32: {"newItemName": BUCKET, "newAuxValue": 0, "count": 2}}
        checked = T.mcdk_test_craft_check(index)
        assert not checked["ok"] and checked["extra"] == {BUCKET: 1}, "多还了一个桶"
        inventory.clear()
        checked = T.mcdk_test_craft_check(index)
        assert not checked["ok"] and checked["missing"] == {"arris:shepherds_pie_block_stage0": 1, BUCKET: 1}
    finally:
        T._inventory, T._clearInventory = saved


def testABlockedCaseWantsTheIngredientsBackAndACancelledCraftEvent():
    """前置包在场时砧板菜被拦：料原样留在格子里、背包里什么都没多，还要有一次被取消的合成事件（没点到结果格时料也都在，但没有事件）。"""
    _ports()
    inventory = {}
    saved = _setUpPlayer(inventory)
    undo = _veto()
    try:
        cases = T.mcdk_test_craft_cases()["cases"]
        sandwich = _case(cases, "arris_egg_sandwich.json", "base")
        assert sandwich["blocked"] is True
        T.mcdk_test_craft_put(sandwich["index"])
        placed = dict(world.uiSlots[PLAYER])
        checked = T.mcdk_test_craft_check(sandwich["index"])
        assert not checked["ok"] and checked["missing"] == {} and checked["extra"] == {} and checked["cancelled"] is False, "没有事件：没点到"
        world.uiSlots[PLAYER] = dict(placed)
        T._log.append({"cancel": True})
        checked = T.mcdk_test_craft_check(sandwich["index"])
        assert checked["ok"] and checked["expect"] == {"minecraft:bread": 1, "arris:fried_egg": 2}, checked
        world.uiSlots[PLAYER] = {}
        inventory["arris:egg_sandwich"] = 1
        checked = T.mcdk_test_craft_check(sandwich["index"])
        assert not checked["ok"] and checked["extra"] == {"arris:egg_sandwich": 1}, "该拦的做出来了"
        board = _case(cases, "arris_cutting_board.json", "base")
        assert board["blocked"] is False and board["expect"] == {"arris:cutting_board": 1}, "不是菜：照常做"
    finally:
        undo()
        del T._log[:]
        T._inventory, T._clearInventory = saved


def testOpenSaysHowInsteadOfPretending():
    """OpenWorkBench 在 2026-11-26 的 3.10 里返回 True 但界面没开：这个函数不再调它，只说怎么开。"""
    result = T.mcdk_test_craft_open()
    assert result["ok"] is False and "右键" in result["error"]


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
