# -*- coding: utf-8 -*-
# runner: both
"""砧板上插着的工具照 FD 的 IsItemCarved 标记认，不再靠推断（Shared/Rules/BoardStation.Env.isCarving、Server/Helpers/BoardDish.carvedOf / setCarved、
Server/CuttingBoard.py 的潜行插工具、Server/Helpers/BlockItems.PublishBoard 带着标记广播）。

JE（CuttingBoardBlockEntity / CuttingBoardBlock）：isItemCarvingBoard 只在 carveToolOnBoard 成功时为真——潜行着拿工具（有材质等级的工具、三叉戟、剪刀）对着空板使用
（ToolCarvingEvent），响 carve 那一声（block.wood.place 1.0 / 0.8），创造模式手里的留着；平常放上去的工具是躺着的。插着工具的板 canAddItem 为假、
processStoredItemUsingTool 开头就返回：放不上别的、也切不了。removeItem 把标记清掉。渲染（CuttingBoardRenderer）只看这个标记。
老存档没有这个标记：读的人照老办法推断（板上有、切不了、却是能插的工具就是）。站点那一边的在 test_board_station_logic。
"""
from __future__ import print_function

import test_classic_cutting_board as T

import fdtest

Board, world, POS, CENTER = T.Board, T.world, T.POS, T.CENTER
Rules = fdtest.load("Shared.Rules.BoardStation")
Place = fdtest.load("Shared.Rules.HandsOn.BoardPlace")
BD = fdtest.load("Shared.Rules.BlockDisplay")
Store = fdtest.load("Server.Helpers.BoardDish")
KNIFE, SWORD, CABBAGE = "arris:iron_knife", "minecraft:iron_sword", "arris:cabbage"
FLAG = Rules.CARVED_DATA


def _typeOf(item):
    return T.TYPES.get(item["newItemName"], "food")


def _isKnife(name):
    return name == KNIFE


ENV = Rules.Env(_isKnife, _typeOf)


def _sneakUse(playerId="p1"):
    """潜行着拿东西对着砧板使用：引擎只发物品使用（ServerItemUseOnEvent），不发方块使用。"""
    world.runTimers()
    world.sneaking.add(playerId)
    args = {"x": POS[0], "y": POS[1], "z": POS[2], "dimensionId": 0, "entityId": playerId, "itemDict": T._hand(), "ret": False}
    Board.OnServerCuttingBoardItemUse(args)
    return args


def _published():
    """广播给客户端的砧板载荷（最后一份）。"""
    sent = [data for target, endpoint, data in world.calls if endpoint == "OnBlockItems"]
    return sent[-1] if sent else None


# ---------------------------------------------------------------- 规则

def testTheFlagDecidesAndOnlyAnOldSaveWithoutItIsGuessed():
    knife, cabbage = T._item(KNIFE), T._item(CABBAGE, 3)
    assert ENV.isCarving(knife) and not ENV.isCarving(cabbage), "不知道（老存档）：照老办法推断——能插的工具是，食物不是"
    assert not ENV.isCarving(knife, False), "标记为假：平常放上去的工具是躺着的（JE addItem 不碰 isItemCarvingBoard）"
    assert ENV.isCarving(knife, True) and ENV.isCarving(T._item("minecraft:stick"), True), "标记为真：就是插着的"
    assert not ENV.isCarving(None, True) and not ENV.isCarving({}, True), "板空着：没有东西可插"
    lying = Rules.Env(_isKnife, _typeOf, None, lambda: False)
    assert not lying.isCarving(knife) and lying.isCarving(knife, True), "不给标记就问这块板的；给了照给的"
    assert Rules.Env(_isKnife, _typeOf, None, lambda: None).isCarving(knife), "板说不知道：还是推断"
    assert not lying.isDone(cabbage) and lying.isDone(T._item("minecraft:bread")), "isDone：切不了的东西让位；躺着的、切得了的不让"


def testOnlyCarveMarksTheNewBoardAsCarved():
    carved = Place.carve(T._item(KNIFE), None, [], ENV)
    assert carved.carved is True and carved.board["newItemName"] == KNIFE
    placed = Place.place(T._item(CABBAGE, 3), None, [], False, False, ENV)
    assert placed.carved is False and placed.board["count"] == 3
    assert Place.take(T._item(KNIFE), [], ENV).carved is False, "取回：板空了，没有什么插着"


def testTheWorldDisplayLaysAToolFlatUnlessTheFlagSaysCarved():
    sword = {"0": T._item(SWORD)}

    def shown(flag):
        return BD.layout(BD.KIND_BOARD, sword, _typeOf, (1, 64, 1), carving=lambda item: ENV.isCarving(item, flag), isBlock=ENV.isBlock)

    assert [placement.flat for placement in shown(True)] == [False], "插着的：竖着"
    assert [placement.flat for placement in shown(False)] == [True], "放上去的工具：平躺（CuttingBoardRenderer 的 renderItemLayingDown）"
    assert [placement.flat for placement in shown(None)] == [False], "老存档：照老办法当插着的"


# ---------------------------------------------------------------- 经典玩法：潜行插工具

def testSneakUsingAToolOnAnEmptyBoardCarvesItIn():
    for name in (KNIFE, SWORD, "minecraft:iron_axe", "minecraft:iron_pickaxe", "minecraft:iron_hoe", "minecraft:shears"):
        data = T._setUp(hand=T._item(name, durability=33))
        args = _sneakUse()
        assert args["ret"] is True, "物品使用照旧取消"
        assert data["cuttingDict"]["newItemName"] == name and data["cuttingDict"]["count"] == 1 and data["cuttingDict"]["durability"] == 33, name
        assert data[FLAG] == 1 and Store.carvedOf(data) is True and T._hand() is None, name
        assert _published()["items"]["0"]["newItemName"] == name and _published()["carved"] is True, "广播带着标记"
        T._near(T._heard(), [("dig.wood", 1.0, 0.8, CENTER)])


def testCreativeKeepsTheToolInTheHandWhenCarving():
    data = T._setUp(hand=T._item(KNIFE), creative=True)
    _sneakUse()
    assert data[FLAG] == 1 and T._hand()["newItemName"] == KNIFE


def testSneakUsingSomethingThatIsNotAToolOrOnAnOccupiedBoardCarvesNothing():
    data = T._setUp(hand=T._item("minecraft:stick", 3))
    _sneakUse()
    assert data["cuttingDict"] is None and data[FLAG] is None and T._hand()["count"] == 3 and world.soundArgs == [], "不是工具：不插"
    data = T._setUp(hand=T._item(KNIFE), board=T._item(CABBAGE, 2))
    _sneakUse()
    assert data["cuttingDict"]["newItemName"] == CABBAGE and data[FLAG] is None and T._hand()["newItemName"] == KNIFE, "板上有东西：不插（addItem 放不进）"
    data = T._setUp(hand=T._item(KNIFE))
    data[Store.LAYERS_KEY] = [T._item("minecraft:bread", 1)]
    _sneakUse()
    assert data["cuttingDict"] is None and data[FLAG] is None, "板上摆着菜的层：不插"


def testWithoutSneakingTheItemUseOnlyCancels():
    data = T._setUp(hand=T._item(KNIFE))
    world.runTimers()
    args = {"x": POS[0], "y": POS[1], "z": POS[2], "dimensionId": 0, "entityId": "p1", "itemDict": T._hand(), "ret": False}
    Board.OnServerCuttingBoardItemUse(args)
    assert args["ret"] is True and data["cuttingDict"] is None and T._hand()["newItemName"] == KNIFE


# ---------------------------------------------------------------- 经典玩法：标记跟着放、取、切

def testAToolPutDownWithoutSneakingLiesFlat():
    data = T._setUp(hand=T._item(SWORD))
    T._use()
    assert data["cuttingDict"]["newItemName"] == SWORD and data[FLAG] == 0 and Store.carvedOf(data) is False
    assert _published()["carved"] is False


def testACarvedBoardTakesNothingAndCutsNothingAndSaysNothing():
    data = T._setUp(hand=T._item(CABBAGE, 3), board=T._item(KNIFE))
    Store.setCarved(data, True)
    T._use()
    assert data["cuttingDict"]["newItemName"] == KNIFE and data["cuttingDict"]["count"] == 1 and T._hand()["count"] == 3
    assert T._tips() == [] and world.soundArgs == [], "JE：canAddItem 为假、processStoredItemUsingTool 开头就返回，没有提示"


def testTakingTheToolBackClearsTheFlag():
    data = T._setUp(board=T._item(KNIFE))
    Store.setCarved(data, True)
    T._use()
    assert data["cuttingDict"] is None and data[FLAG] is None and Store.carvedOf(data) is None and T._hand()["newItemName"] == KNIFE
    assert "carved" not in _published(), "板空了：不带标记"


def testCuttingTheLastOneClearsTheFlagAndTheRestKeepIt():
    data = T._setUp(hand=T._item(KNIFE), board=T._item(CABBAGE, 2))
    Store.setCarved(data, False)
    T._use()
    assert data["cuttingDict"]["count"] == 1 and data[FLAG] == 0 and _published()["carved"] is False
    T._use()
    assert data["cuttingDict"] is None and data[FLAG] is None


def testAnOldSaveWithAToolAndNoFlagBehavesAsBefore():
    data = T._setUp(hand=T._item(CABBAGE, 3), board=T._item(KNIFE))
    assert Store.carvedOf(data) is None
    T._use()
    assert T._tips() == [T.INVALID_ITEM], "没有标记：经典玩法照旧当它是板上的一件东西（没有切法）"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
