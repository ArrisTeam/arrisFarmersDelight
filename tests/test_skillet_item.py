# -*- coding: utf-8 -*-
# runner: both
"""煎锅物品（Server/SkilletItem.py）：只有潜行才放成方块、方块记住那一件煎锅（耐久、附魔）、拆掉原样掉回，用假引擎驱动（tests/fakeengine.py）。

JE：SkilletItem.place（不潜行不放）、SkilletBlockEntity.skilletStack + CopySkilletFunction（拆掉掉出存着的那件，创造模式没有战利品）。
"""
from __future__ import print_function

import fakeengine
import fdtest
import skilletkit

world = fakeengine.install()
skilletkit.extend(world)
Registry = fdtest.load("Server.EventRegistry")
ItemToBlock = fdtest.load("Server.ItemToBlock")
SkilletItem = fdtest.load("Server.SkilletItem")
Skillet = fdtest.load("Server.Skillet")

SKILLET = {"newItemName": "arris:skillet_item", "newAuxValue": 0, "count": 1, "durability": 137,
           "enchantData": [(13, 2), (9, 1)], "userData": {"RepairCost": 1}, "customTips": "", "extraId": "", "showInHand": True}
GROUND = (5, 63, 5)
ABOVE = (5, 64, 5)


def _register():
    """和 ModServer 一样把处理函数登记到注册表（优先级照各模块里写的）。"""
    Registry.clearAll()
    use = Registry.registerHandler
    use("ServerItemUseOnEvent", match="arris:skillet_item", keyOf=SkilletItem._itemName, priority=98.5)(SkilletItem.OnUseSkilletItem)
    use("ServerItemUseOnEvent", match=ItemToBlock.itemChangeBlockDict, keyOf=ItemToBlock._itemName, priority=98)(ItemToBlock.OnPlaceItemAsBlock)
    use("ServerPlayerTryDestroyBlockEvent", match="arris:skillet")(SkilletItem.OnTryBreakSkillet)
    use("BlockRemoveServerEvent", match="arris:skillet")(Skillet.OnSkilletRemove)
    use("ServerPlaceBlockEntityEvent", match="arris:skillet")(Skillet.OnServerSkilletCreate)


def _setUp(creative=False, sneaking=True, hand=SKILLET):
    _register()
    world.reset()
    SkilletItem._pending.clear()
    world.addPlayer("p1", hand=dict(hand) if hand else None, creative=creative)
    if sneaking:
        world.sneaking.add("p1")
    world.setBlock(GROUND[0], GROUND[1], GROUND[2], "minecraft:stone")


def _click(face=1, target=GROUND, blockName="minecraft:stone"):
    world.runTimers()                      # 交互冷却到期
    args = {"entityId": "p1", "itemDict": dict(world.players["p1"]["hand"] or SKILLET), "x": target[0], "y": target[1], "z": target[2],
            "blockName": blockName, "face": face, "dimensionId": 0, "ret": False}
    return Registry.dispatch("ServerItemUseOnEvent", args, blockName), args


def _data(pos=ABOVE):
    return world.blocks[(0,) + pos]["data"]


def _break(pos=ABOVE, tryFirst=True):
    x, y, z = pos
    if tryFirst:
        Registry.dispatch("ServerPlayerTryDestroyBlockEvent", {"playerId": "p1", "dimensionId": 0, "x": x, "y": y, "z": z, "fullName": "arris:skillet"}, "arris:skillet")
    Registry.dispatch("BlockRemoveServerEvent", {"x": x, "y": y, "z": z, "dimension": 0, "fullName": "arris:skillet"}, "arris:skillet")


def testNotSneakingNeverPlacesTheSkillet():
    _setUp(sneaking=False)
    claimed, args = _click()
    assert claimed is True                                   # 拦下了，ItemToBlock 看不到它
    assert world.blockName(*ABOVE) == "minecraft:air"
    assert world.players["p1"]["hand"]["count"] == 1 and world.players["p1"]["hand"]["durability"] == 137
    assert args["ret"] is False                              # 不取消引擎自己对这次点击的处理（开箱子、手持烹饪都靠它）


def testSneakingPlacesTheSkilletAndRemembersTheItem():
    _setUp()
    claimed, _ = _click()
    assert claimed is True
    assert world.blockName(*ABOVE) == "arris:skillet"
    assert world.players["p1"]["hand"] is None               # 非创造模式用掉了这一件
    stored = _data()["skilletItem"]
    assert stored["durability"] == 137 and stored["count"] == 1 and stored["newItemName"] == "arris:skillet_item"
    assert stored["enchantData"] == [[13, 2], [9, 1]] and stored["userData"] == {"RepairCost": 1}


def testCreativeKeepsTheItemInHandButTheBlockStillRemembersIt():
    _setUp(creative=True)
    _click()
    assert world.blockName(*ABOVE) == "arris:skillet"
    assert world.players["p1"]["hand"]["durability"] == 137
    assert _data()["skilletItem"]["durability"] == 137


def testItemIsRememberedWhenTheBlockEntityIsBuiltLater():
    _setUp()
    world.deferBlockEntity = True                            # SetBlockNew 之后方块实体还没建好
    _click()
    assert world.blockName(*ABOVE) == "arris:skillet" and _data() is None
    world.blocks[(0,) + ABOVE]["data"] = skilletkit.EngineData()          # 引擎建好了，发放置事件
    Registry.dispatch("ServerPlaceBlockEntityEvent", {"posX": 5, "posY": 64, "posZ": 5, "dimension": 0, "blockName": "arris:skillet"}, "arris:skillet")
    assert _data()["skilletItem"]["durability"] == 137
    assert not SkilletItem._pending


def testNothingIsRememberedWhenTheTargetIsNotAir():
    _setUp()
    world.setBlock(ABOVE[0], ABOVE[1], ABOVE[2], "minecraft:water")
    _click()
    assert world.blockName(*ABOVE) == "minecraft:water" and not SkilletItem._pending
    assert world.players["p1"]["hand"]["count"] == 1


def testBreakingDropsTheSameItemBack():
    _setUp()
    _click()
    _data()["cookingDict"] = {"newItemName": "minecraft:beef", "newAuxValue": 0, "count": 3}
    _break()
    dropped = dict((item["newItemName"], item) for item, dim, pos in world.spawned)
    assert dropped["minecraft:beef"]["count"] == 3
    skillet = dropped["arris:skillet_item"]
    assert skillet["durability"] == 137 and skillet["count"] == 1
    assert skillet["enchantData"] == [(13, 2), (9, 1)] and skillet["userData"] == {"RepairCost": 1}
    assert "customTips" not in skillet and "extraId" not in skillet     # 空的 customTips 会盖掉物品自己的提示，不还
    assert len(world.spawned) == 2


def testBreakingInCreativeDropsNoSkilletButTheFoodStillComesOut():
    _setUp(creative=True)
    _click()
    _data()["cookingDict"] = {"newItemName": "minecraft:beef", "newAuxValue": 0, "count": 2}
    _break()
    assert world.spawnedNames() == [("minecraft:beef", 2)]


def testRemovalWithoutAPlayerStillDropsTheSkillet():
    # 爆炸、活塞、被别的方法拆：没有"玩家即将破坏"这一步，照样掉
    _setUp()
    _click()
    _break(tryFirst=False)
    assert world.spawnedNames() == [("arris:skillet_item", 1)] and world.spawned[0][0]["durability"] == 137


def testSkilletsWithoutARecordDropAFreshOne():
    _setUp()
    world.setBlock(7, 64, 7, "arris:skillet", data=skilletkit.EngineData())      # /setblock 或旧存档里的煎锅
    _break((7, 64, 7), tryFirst=False)
    assert world.spawned == [({"newItemName": "arris:skillet_item", "newAuxValue": 0, "count": 1}, 0, (7.5, 64.5, 7.5))]


def testLostBlockEntityStillDropsAFreshSkillet():
    _setUp()
    world.setBlock(8, 64, 8, "arris:skillet")                                     # 没有方块实体数据
    _break((8, 64, 8), tryFirst=False)
    assert world.spawnedNames() == [("arris:skillet_item", 1)]


def testOtherItemsStillPlaceWithoutSneaking():
    # 派等其它"物品放成方块"的东西不受影响（JE 里只有煎锅要潜行）
    _setUp(sneaking=False, hand={"newItemName": "arris:apple_pie_item", "newAuxValue": 0, "count": 1})
    _click()
    assert world.blockName(*ABOVE) == "arris:apple_pie"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
