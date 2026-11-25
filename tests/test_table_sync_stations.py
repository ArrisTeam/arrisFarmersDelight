# -*- coding: utf-8 -*-
# runner: both
"""下游在服务端追加的内容，四个站点的客户端认不认得（真的客户端类 + 服务端发来的差异）：默认包当客户端（砧板表现用 boardclient 的假引擎和假视图），
另一份包当服务端，下游照 Ends Delight 的写法追加之后，消息走客户端真正的端点 Client/TableSync.OnTableSync。
对着同一件东西，并表之前站点客户端说"不认"（托盘里不亮、借不到刀、点板敲一声、炉灶不开站、书里没有这一页……），之后认。
测的是站点客户端真在读的那几个函数：砧板的 Env / BoardView / BoardDraw / BoardInv，煎锅和炉灶的 PanStation / GrillStation 和前置包客户端 Registry 的方块名判断，
厨锅的 PotStation / CookingPot 索引，四个站点的书页（StationBooks）；还有手持煎锅的"煎还是吃"（Client/Input）和方块上物品的摆法（Client/BlockItems）。
"""
from __future__ import print_function

import sys

import prereq  # noqa: F401 - 前置包不在这个仓库里：旁边没有它就跳过（tests/prereq.py）
import dgtest
import boardclient as C            # 先导入：它换上假的 QuModLibs 和客户端引擎，后面才能导入 Client/ 下的模块
import fdtest
import tablekit as K

Pan = fdtest.load("Shared.Rules.PanStation")
Grill = fdtest.load("Shared.Rules.GrillStation")
PotStation = fdtest.load("Shared.Rules.PotStation")
Pot = fdtest.load("Shared.Rules.CookingPot")
Books = fdtest.load("Shared.Rules.StationBooks")
Board = fdtest.load("Shared.Rules.BoardStation")
Click = fdtest.load("Shared.Rules.BoardClick")
Cooking = fdtest.load("Shared.Data.Cooking")
Cutting = fdtest.load("Shared.Data.Cutting")
Tables = fdtest.load("Shared.Rules.SyncTables")
Endpoint = fdtest.load("Client.TableSync")
Input = fdtest.load("Client.Input")
Registry = dgtest.load("Client.Registry")

Inv = fdtest.load("Compat.Diegesis.BoardInv")
PRISTINE = K.Pristine(K.DEFAULT)
PEARL, LOG = K.CUT_KEY[0], K.CUT_AXE_KEY[0]
C.TYPES.update({K.KNIFE: "sword", "ends_delight:chorus_axe": "sword", LOG: "block", PEARL: "food", K.COOKABLE: "food"})   # 下游的斧：物品类型不是 axe，只能靠 axeList 认


def _forgetItemTypes():
    """BoardInv 按物品记着引擎说的类型（假引擎的类型表改了就要忘掉）；是不是刀不再按名字缓存（Shared/Rules/Knives，标签经 ItemTags 问）。"""
    Inv._types.clear()


class Synced(object):
    """with Synced() as sync：进去时默认包（客户端）的表是原样，服务端（另一份包，.server）上下游已经追加完；sync() 让客户端的端点收到服务端的差异
    （走一趟网络）；出来时客户端的表放回原样。"""

    def __enter__(self):
        PRISTINE.restore()
        _forgetItemTypes()
        self.server = K.Package()
        syncer = self.server.load("Shared.Rules.TableDiff").Syncer()
        K.downstream(self.server)
        assert syncer.refresh()
        self.messages = syncer.messages()
        return self

    def __call__(self):
        for message in self.messages:
            assert Endpoint.OnTableSync(K.transport(message)) is None

    def __exit__(self, *exc):
        PRISTINE.restore()
        _forgetItemTypes()
        return False


def _item(name, count=1):
    return C.item(name, count)


# ---------------------------------------------------------------- 砧板

def testTheBoardTrayLightsWhatDownstreamCanBeCutAndTheKnives():
    with Synced() as sync:
        before = C.station()[0]
        for name in (PEARL, K.KNIFE, "ends_delight:chorus_axe", LOG):
            assert not before.usable(_item(name)), name
        sync()
        after = C.station()[0]                                    # 开站时才建视图，托盘的亮不亮在这时按已经并好的表算
        for name in (PEARL, K.KNIFE, "ends_delight:chorus_axe", LOG):
            assert after.usable(_item(name)), name
        assert not after.usable(_item("minecraft:dirt")) and after.env.cuttable(_item(PEARL)) and after.env.recipeOf(_item(LOG)) is not None


def testTheKnifeInTheBagIsBorrowedForAFoodDownstreamAddedAndTheClickIsACut():
    with Synced() as sync:
        sync()
        behavior, view, _api = C.station()
        view.state.board = _item(PEARL, 2)
        C.engine.inventory[3] = _item(K.KNIFE)
        tool, borrowed = behavior.toolOf()
        assert borrowed and tool["newItemName"] == K.KNIFE, "手空着，背包里下游的刀借得到（选中格 -> 副手 -> 背包）"
        assert behavior.env.cutsWith(view.state.board, _item(K.KNIFE)) and not behavior.env.cutsWith(view.state.board, _item("minecraft:iron_axe"))
        action = Click.withStack(behavior.env, _item(K.KNIFE), 0, False, view.state.board, [], False, True)
        assert action == (Click.CHOP,), "拿着刀点在能切的东西上是落刀，不是敲一声"
        assert Click.bareHand(0, view.state.board, [], False, True, False) == (Click.CHOP,)


def testWithoutTheSyncTheKnifeIsNotBorrowedAndTheClickIsAPlaceNotACut():
    with Synced():
        behavior, view, _api = C.station()
        view.state.board = _item(PEARL, 2)
        C.engine.inventory[3] = _item(K.KNIFE)
        assert behavior.toolOf() == (None, False) and not behavior.env.cutsWith(view.state.board, _item(K.KNIFE))
        assert Click.withStack(behavior.env, _item(K.KNIFE), 0, False, view.state.board, [], False, False) == (Click.PLACE, False), "刀被当成要放的东西"


def testShiftClickOnTheTrayPlacesAFoodDownstreamAddedCanBeCut():
    with Synced() as sync:
        assert C.station()[0].onInventoryShiftClick(2, _item(PEARL, 5)) is False, "并表之前：这不是能切的东西，内核走自己的 QUICK_MOVE"
        sync()
        behavior, view, _api = C.station()
        assert behavior.onInventoryShiftClick(2, _item(PEARL, 5)) is True and view.sent == [("place", {"from": 2})]
        assert behavior.onInventoryShiftClick(3, _item(K.KNIFE)) is False, "刀不整叠放上板"


def testAToolTypedItemThatIsAlsoACuttingRecipeIsDrawnAsFoodNotAStuckTool():
    """BoardDraw.kindOf：工具类的物品插在板上是插着的工具；可是它要是某个配方的原料（下游追加的），就是等着切的东西。"""
    with Synced() as sync:
        C.TYPES[PEARL] = "axe"
        try:
            behavior, view, _api = C.station()
            view.state.board = _item(PEARL, 1)
            behavior.onOpen()
            assert behavior.draw.kindOf(_item(PEARL)) == "tool"
            sync()
            assert behavior.draw.kindOf(_item(PEARL)) == "flat"
            behavior.onClose()
        finally:
            C.TYPES[PEARL] = "food"
            _forgetItemTypes()


# ---------------------------------------------------------------- 煎锅和炉灶

def testThePanAndTheGrillTraysAndSchemasTakeWhatDownstreamCanCook():
    with Synced() as sync:
        item = _item(K.COOKABLE)
        assert not Pan.usable(K.COOKABLE) and not Pan.acceptsFryable(item) and not Grill.usable(K.COOKABLE) and not Grill.mayPlace(item)
        assert Pan.friedOf(K.COOKABLE) is None and not Grill.canGrill(K.COOKABLE) and not Grill.hasRecipe(K.COOKABLE)
        sync()
        assert Pan.usable(K.COOKABLE) and Pan.acceptsFryable(item) and Pan.mayPlace(None, item) and Pan.friedOf(K.COOKABLE) == K.COOKED
        assert Grill.usable(K.COOKABLE) and Grill.mayPlace(item) and Grill.canGrill(K.COOKABLE) and Grill.grilledOf(K.COOKABLE) == K.COOKED
        assert not Grill.isDone(K.COOKABLE) and Grill.isDone(K.COOKED), "没有营火配方的才算烤好了"


def testTheGrillOpensForADownstreamStoveAndForTheKnifeAndFoodTheyBring():
    with Synced() as sync:
        assert K.STOVE not in Grill.STOVE_BLOCKS and Grill.opens(K.KNIFE, "sword", False) is False
        Registry.registerBehavior(Grill.STATION_ID, Grill.STOVE_BLOCKS, object)         # GrillView.register 就是这样把同一个列表交给前置包
        try:
            assert Registry.behaviorOf(K.STOVE) is None, "客户端先按方块名决定这一下右键是不是站点点击：不认就不会去请求开站"
            sync()
            assert K.STOVE in Grill.STOVE_BLOCKS and K.STOVE in Cooking.StoveList, "就地追加：前置包拿着的容器每次按 StoveList（还是那个列表对象）判"
            assert Registry.behaviorOf(K.STOVE).stationId == Grill.STATION_ID
            assert Grill.opens(K.KNIFE, "sword", False) is True and Grill.opens(K.KNIFE, "sword", True) is False, "手里的刀：下游的刀也让炉灶开站（盖着东西的不开）"
            assert Grill.opens(K.COOKABLE, "", False) is True, "有营火配方的：开"
        finally:
            Registry.unregisterBehavior(Grill.STATION_ID)


def testTheItemsOnADownstreamStoveAreDrawnByTheWorldLayer():
    """Client/BlockItems：方块上的东西按方块名挑摆法，StoveList 里没有的方块客户端不摆，谁也看不到它上面的东西。"""
    with Synced() as sync:
        assert C.BlockItems.kindOf(K.STOVE) is None and C.BlockItems.kindOf("arris:stove") == "stove"
        sync()
        assert C.BlockItems.kindOf(K.STOVE) == "stove"


def testTheHandHeldSkilletOnTheClientKnowsDownstreamFoodAndHeat():
    """Client/Input 的"副手煎锅、主手原料、身边有热源时右键是煎不是吃"：不认的话客户端放任玩家吃生的（服务端那边认，所以会又煎又吃）。"""
    with Synced() as sync:
        C.engine.GetFootPos = lambda: (10.5, 64.0, 10.5)
        C.engine.block = (K.STOVE, 0)
        C.engine.offhand = _item(Input.SKILLET_ITEM)

        def tryUse():
            args = {"itemDict": {"newItemName": K.COOKABLE}}
            Input.OnClientItemTryUse(args)
            return args.get("cancel", False)

        try:
            assert tryUse() is False
            sync()
            assert tryUse() is True
            C.engine.block = ("minecraft:stone", 0)
            assert tryUse() is False, "身边没有热源"
        finally:
            del C.engine.GetFootPos
            C.engine.reset()


# ---------------------------------------------------------------- 厨锅

def testThePotTrayTakesTheNewIngredientsAndTheNewDishIsServedInItsVessel():
    with Synced() as sync:
        tea = ("ends_delight:chorus_flower", 0)
        assert not PotStation.usable(K.SUCCULENT) and not PotStation.usable(tea) and Pot.findRecipeByResult(K.SAUCE[0]) is None
        sync()
        assert PotStation.usable(K.SUCCULENT) and PotStation.usable(tea) and PotStation.isSunk(K.SUCCULENT) is False
        assert PotStation.mayPlace(_item(K.SUCCULENT[0])) and PotStation.isVessel("minecraft:glass_bottle")
        assert Pot.findRecipeByResult(K.SAUCE[0])["Vessel"] == ("minecraft:bowl", 0), "PotScenes.opensStation 读它：拿着这道菜的碗右键、锅里煮好了就直接盛"
        assert Pot.vesselOf("ends_delight:chorus_tea") == ("minecraft:glass_bottle", 0) and Pot.cookSecondsOf("ends_delight:chorus_tea") == 5.0
        assert Pot.matchRecipe([_item(K.SUCCULENT[0]), _item(K.CHORUS_FRUIT[0])])[0]["newItemName"] == K.SAUCE[0]


def testTheFourBooksListTheNewPagesAndThePotPageKeyIsTheServersIndex():
    with Synced() as sync:
        serverRows = sync.server.load("Shared.Data.CookingPotRecipes").CookingPotRecipeList
        keysBefore = [page["key"] for page in Books.potPages()]
        assert not [page for page in Books.potPages() if page["item"]["newItemName"] == K.SAUCE[0]]
        assert K.COOKABLE not in [page["key"] for page in Books.panPages()] and "c:%s:0" % PEARL not in [page["key"] for page in Books.boardPages()]
        sync()
        potPage = [page for page in Books.potPages() if page["item"]["newItemName"] == K.SAUCE[0]][0]
        serverIndex = [index for index, row in enumerate(serverRows) if row["CookResult"] == K.SAUCE][0]
        assert potPage["key"] == serverIndex and potPage["key"] not in keysBefore and Books.potRecipe(potPage["key"])["text"] == "紫颂酱"
        assert Books.potRecipe(potPage["key"]) is not None, "书里放料发的键，服务端按它查自己的表：两边的下标一一对得上"
        assert K.COOKABLE in [page["key"] for page in Books.panPages()] and K.COOKABLE in [page["key"] for page in Books.grillPages()]
        cut = [page for page in Books.boardPages() if page["key"] == "c:%s:0" % PEARL][0]
        assert cut["item"]["newItemName"] == "ends_delight:ender_pearl_grain" and cut["kind"] == "knife" and (K.KNIFE, 0) in cut["ways"][0][1]
        assert Books.boardCurrent([], _item(PEARL)) == "c:%s:0" % PEARL and Books.cookCurrent([_item(K.COOKABLE)]) == K.COOKABLE


# ---------------------------------------------------------------- 客户端的端点

class _Capture(object):
    def __init__(self):
        self.chunks = []

    def write(self, text):
        self.chunks.append(text)

    def flush(self):
        pass


def testTheEndpointIsTheOneTheServerCallsAndCountsWhatItGot():
    assert Endpoint.OnTableSync.__name__ == Tables.ENDPOINT == "OnTableSync"
    with Synced() as sync:
        before = Endpoint.status()
        sync()
        after = Endpoint.status()
        sent = after["messages"] - before["messages"]
        assert sent == 8 and after["rev"] == 1, "每张有追加的表一条"
        assert after["changed"] - before["changed"] == sent and after["problems"] == before["problems"], "每条都改了表、一个条目也没跳过"
        sync()
        again = Endpoint.status()
        assert again["messages"] - after["messages"] == sent and again["changed"] == after["changed"], "再收一遍：收到了，什么也没改"


def testABadMessageOnTheEndpointIsLoggedAndNeverRaised():
    saved, sys.stdout = sys.stdout, _Capture()
    try:
        for bad in (None, {"proto": 1, "table": "noSuchTable", "kind": "items", "ops": []}, {"proto": 1, "table": "StoveList", "kind": "items", "ops": [{"$weird": 1}]}):
            assert Endpoint.OnTableSync(bad) is None
        printed = "".join(sys.stdout.chunks)
    finally:
        sys.stdout = saved
    assert printed.count("表同步") >= 3 and "noSuchTable" in printed, printed
    assert Endpoint.status()["problems"] >= 3


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
