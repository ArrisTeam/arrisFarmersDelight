# -*- coding: utf-8 -*-
# runner: both
"""工作台的游戏内自检（Server/Debug/McdkCraftTest.py）里写标签的配方那一组：用例表、摆料、核对，离线用假引擎跑一遍。

用例表（mcdk_test_craft_cases）：tools/gen_crafts.py 生成的 Server/Debug/CraftCases.py 里每份写标签的配方两例——base 标签格取第一个成员，
swap 换另一个成员（引擎现在的成员，别的包并进标签的也算）；expect 是做一份之后合成格 + 背包里该有的全部东西（成品 + 剩下的容器：
有序配方是 result 数组写的，无序配方按放进去的物品查 Remainders）。摆料（put）一格一个、行优先；核对（check）把合成格和背包加起来和 expect 比。
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
Cases = fdtest.load("Server.Debug.CraftCases")
ItemTags = fdtest.load("Shared.Rules.ItemTags")
PLAYER = "p1"
BUCKET, BOTTLE = "minecraft:bucket", "minecraft:glass_bottle"


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


def _case(cases, source, variant):
    return next(case for case in cases if case["source"] == source and case["variant"] == variant)


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
    _ports(TagPort({"common:tomato": ["arris:tomato", "fdprobe:tomato"]}))
    try:
        cases = T.mcdk_test_craft_cases()["cases"]
        stick = _case(cases, "arris_barbecue_stick.json", "swap")
        assert "fdprobe:tomato" in stick["grid"] and not stick["same"] and stick["expect"] == {"arris:barbecue_stick": 1}
    finally:
        _ports()


def testPutThenCheck():
    _ports()
    world.players.clear()
    world.uiOpen = True
    world.addPlayer(PLAYER)
    world.uiSlots[PLAYER] = {}
    inventory = {}
    saved = T._inventory, T._clearInventory
    T._inventory = lambda playerId: dict(inventory)
    T._clearInventory = lambda playerId: inventory.clear()
    try:
        cases = T.mcdk_test_craft_cases()["cases"]
        index = _case(cases, "arris_shepherds_pie_block.json", "base")["index"]
        inventory["minecraft:dirt"] = 3
        put = T.mcdk_test_craft_put(index)
        assert put["ok"] and inventory == {} and len(put["grid"]) == 9, put
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


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
