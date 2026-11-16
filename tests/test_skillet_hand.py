# -*- coding: utf-8 -*-
# runner: both
"""手持煎锅烹饪（Server/SkilletHand.py）对 JE 的 SkilletItem.use / finishUsingItem / releaseUsing，用假引擎和假时钟驱动。

JE：主手煎锅、副手食物，玩家着火或脚下 3x3x3 里有热源；按住 6 秒（火焰附加 I 4 秒、II 起 3 秒）做好一件；松手什么都不发生；
副手没有食物提示"用另一只手拿着原料！"，头泡在水里提示"在水里可没法煎啊……"。
JE 两只手都认；基岩版生肉放不进副手（实测），常用的是反过来拿：煎锅放副手、原料拿主手——文件末尾几个用例测这种拿法。
"""
from __future__ import print_function

import fakeengine
import fdtest
import skilletkit

world = fakeengine.install()
skilletkit.extend(world)
SkilletHand = fdtest.load("Server.SkilletHand")

SKILLET = {"newItemName": "arris:skillet_item", "newAuxValue": 0, "count": 1, "durability": 200}
BEEF = {"newItemName": "minecraft:beef", "newAuxValue": 0, "count": 3}
clock = [1000.0]


class _Dice(object):
    """滋滋声的随机数：测试里定死。"""
    value = 0.99

    def random(self):
        return self.value


dice = _Dice()
SkilletHand._now = lambda: clock[0]
SkilletHand.random = dice


def _setUp(skillet=SKILLET, food=BEEF, heat=True, creative=False, fireAspect=0):
    world.reset()
    SkilletHand._sessions.clear()
    SkilletHand._holds._beat.clear()
    dice.value = 0.99
    clock[0] = 1000.0
    main = dict(skillet)
    if fireAspect:
        main["enchantData"] = [(13, fireAspect)]
    world.addPlayer("p1", hand=main, creative=creative)          # 站在 (0.5, 64, 0.5)
    world.offhand["p1"] = dict(food) if food else None
    if heat:
        world.setBlock(1, 64, 0, "minecraft:campfire")


def _press():
    SkilletHand.onHeld("p1")


def _advance(steps, beat=True):
    """过 steps 步（每步 0.25 秒）：客户端报"按着"，再跑到期的计时器。"""
    for _ in range(steps):
        clock[0] += 0.25
        if beat:
            SkilletHand.onHeld("p1")
        world.runTimers()


def _tips():
    return [text for target, endpoint, text in world.calls if endpoint == "ShowTip"]


def _cooked():
    return [(item["itemName"], item["count"]) for item in world.players["p1"]["given"]]


def testSixSecondsOfHoldingCooksOneItem():
    _setUp()
    _press()
    assert "p1" in SkilletHand._sessions and _tips() == []
    _advance(23)
    assert _cooked() == [] and world.offhand["p1"]["count"] == 3                    # 5.75 秒：食物还在副手
    _advance(1)
    assert _cooked() == [("minecraft:cooked_beef", 1)]
    assert world.offhand["p1"]["count"] == 2 and "p1" not in SkilletHand._sessions
    assert world.players["p1"]["hand"]["durability"] == 200                         # JE：手持烹饪不磨损煎锅


def testKeepHoldingCooksTheWholeStackOneByOne():
    _setUp()
    _press()
    _advance(24 * 3 + 3)
    assert _cooked() == [("minecraft:cooked_beef", 1)] * 3
    assert world.offhand["p1"] is None                                              # 最后一件拿走后副手空了
    assert _tips() == ["用另一只手拿着原料！"]                                          # 还按着、副手空了：JE 同样提示


def testReleasingEarlyChangesNothing():
    _setUp()
    _press()
    _advance(12)
    SkilletHand.onRelease("p1")
    _advance(40, beat=False)
    assert _cooked() == [] and world.offhand["p1"]["count"] == 3 and not SkilletHand._sessions


def testLosingTheHoldReportsCountsAsReleasing():
    # 客户端掉线 / 开了界面没发松开：超过 HOLD_TIMEOUT 没有"按着"就当松手
    _setUp()
    _press()
    _advance(4)
    _advance(40, beat=False)
    assert _cooked() == [] and world.offhand["p1"]["count"] == 3 and not SkilletHand._sessions


def testFireAspectShortensTheHeldCooking():
    for level, steps in ((1, 16), (2, 12), (4, 12)):                                # 4 秒 / 3 秒 / 下限 3 秒
        _setUp(fireAspect=level)
        _press()
        _advance(steps - 1)
        assert _cooked() == [], level
        _advance(1)
        assert _cooked() == [("minecraft:cooked_beef", 1)], level


def testNothingHappensWithoutAHeatSourceNearby():
    _setUp(heat=False)
    _press()
    assert not SkilletHand._sessions and _tips() == []                              # JE：没热源什么提示都没有
    world.setBlock(2, 64, 0, "minecraft:campfire")                                  # 玩家站在格 (0, 64, 0)，x 差 2 格在 3x3x3 之外
    world.setBlock(0, 66, 0, "minecraft:campfire")                                  # y 差 2 格也在外面
    _press()
    assert not SkilletHand._sessions and _tips() == []
    world.setBlock(-1, 63, 1, "minecraft:soul_campfire")                            # 斜下方一格：在里面
    _press()
    assert "p1" in SkilletHand._sessions


def testBurningPlayerNeedsNoHeatSource():
    _setUp(heat=False)
    world.entities["p1"]["fire"] = True
    _press()
    assert "p1" in SkilletHand._sessions


def testExtinguishedCampfireStillCountsLikeInJe():
    _setUp(heat=False)
    world.setBlock(1, 64, 0, "minecraft:campfire", states={"extinguished": True})
    _press()
    assert "p1" in SkilletHand._sessions


def testHeatButNoFoodInTheOtherHandShowsTheHowToCookTip():
    for food in (None, {"newItemName": "minecraft:stick", "newAuxValue": 0, "count": 1}):
        _setUp(food=food)
        _press()
        assert _tips() == ["用另一只手拿着原料！"] and not SkilletHand._sessions


def testSneakingStaysQuietBecauseThatClickPlacesTheSkillet():
    # 潜行右键方块是放煎锅：站在炉灶边放煎锅，手里没食物也不该每次都冒一句提示；有食物和热源时照样能开始
    _setUp(food=None)
    world.sneaking.add("p1")
    _press()
    assert _tips() == [] and not SkilletHand._sessions
    world.water.add((0, 0, 65, 0))
    world.offhand["p1"] = dict(BEEF)
    _press()
    assert _tips() == [] and not SkilletHand._sessions                              # 在水里也不提示
    world.water.clear()
    _press()
    assert "p1" in SkilletHand._sessions


def testUnderwaterShowsTheUnderwaterTipAndDoesNotStart():
    _setUp()
    world.water.add((0, 0, 65, 0))                                                   # 眼睛（脚 64 + 1.62）所在的格
    _press()
    assert _tips() == ["在水里可没法煎啊……"] and not SkilletHand._sessions
    world.reset()
    _setUp()
    world.water.add((0, 0, 64, 0))                                                   # 水只到胸口：不算
    _press()
    assert "p1" in SkilletHand._sessions


def testNoSkilletInEitherHandDoesNothing():
    _setUp(skillet={"newItemName": "minecraft:stick", "newAuxValue": 0, "count": 1})
    _press()
    assert not SkilletHand._sessions and _tips() == []


def testSwitchingTheMainHandItemStopsIt():
    _setUp()
    _press()
    _advance(8)
    world.players["p1"]["hand"] = {"newItemName": "minecraft:stick", "newAuxValue": 0, "count": 1}
    _advance(40)
    assert _cooked() == [] and world.offhand["p1"]["count"] == 3 and not SkilletHand._sessions


def testSwappingTheFoodAtTheLastMomentTakesNothing():
    _setUp()
    _press()
    _advance(20)
    world.offhand["p1"] = {"newItemName": "minecraft:chicken", "newAuxValue": 0, "count": 4}
    _advance(4)
    assert _cooked() == [] and world.offhand["p1"]["count"] == 4 and not SkilletHand._sessions


def testCreativeModeStillConsumesTheFood():
    # JE use() 不看创造模式，照样把那一件分到煎锅上
    _setUp(creative=True)
    _press()
    _advance(24)
    assert _cooked() == [("minecraft:cooked_beef", 1)] and world.offhand["p1"]["count"] == 2


def testFullInventoryDropsTheResultAtTheFeet():
    _setUp()
    original = world._Item

    def noRoom(target):
        methods = dict(original(target))
        methods["SpawnItemToPlayerInv"] = lambda itemDict, playerId: False
        return methods

    world._Item = noRoom
    try:
        _press()
        _advance(24)
    finally:
        world._Item = original
    assert world.spawnedNames() == [("minecraft:cooked_beef", 1)] and world.spawned[0][2] == (0.5, 64.0, 0.5)


def testSizzleSoundIsPlayedOnlyToTheCook():
    # JE onUseTick 的 playLocalSound 只有自己听得到：不用 Call("*") 广播，只发给这个玩家
    _setUp()
    heard = []
    original = SkilletHand.Call
    SkilletHand.Call = lambda target, endpoint, data=None: heard.append((target, endpoint, data["soundName"]))
    dice.value = 0.0
    try:
        _press()
        _advance(1)
    finally:
        SkilletHand.Call = original
    assert heard == [("p1", "OnPlaySound", "ambient.skillet.sizzle")]
    dice.value = 0.99
    _setUp()
    _press()
    _advance(10)
    assert world.sounds == []


def testEveryCampfireRecipeCanBeCookedInHand():
    cases = {"minecraft:kelp": "minecraft:dried_kelp", "arris:minced_beef": "arris:beef_patty", "minecraft:egg": "arris:fried_egg"}
    for raw, cooked in sorted(cases.items()):
        _setUp(food={"newItemName": raw, "newAuxValue": 0, "count": 1})
        _press()
        _advance(24)
        assert _cooked() == [(cooked, 1)], raw
        assert world.offhand["p1"] is None


# ---- 反过来拿：煎锅在副手、原料在主手（基岩版的常用拿法） ----

def _setUpMirrored(food=BEEF, fireAspect=0):
    _setUp(skillet=food if food else {"newItemName": "minecraft:air", "newAuxValue": 0, "count": 0}, food=SKILLET)
    if not food:
        world.players["p1"]["hand"] = None
    if fireAspect:
        world.offhand["p1"]["enchantData"] = [(13, fireAspect)]


def testSkilletInTheOffHandCooksWhatTheMainHandHolds():
    _setUpMirrored()
    _press()
    assert "p1" in SkilletHand._sessions and _tips() == []
    _advance(23)
    assert _cooked() == [] and world.players["p1"]["hand"]["count"] == 3
    _advance(1)
    assert _cooked() == [("minecraft:cooked_beef", 1)]
    assert world.players["p1"]["hand"] == dict(BEEF, count=2), "原料从主手拿走一件"
    assert world.offhand["p1"]["newItemName"] == "arris:skillet_item" and world.offhand["p1"]["durability"] == 200


def testTheOffHandSkilletsFireAspectCounts():
    _setUpMirrored(fireAspect=2)
    _press()
    _advance(11)
    assert _cooked() == []
    _advance(1)
    assert _cooked() == [("minecraft:cooked_beef", 1)], "副手那把煎锅的火焰附加 II：3 秒"


def testTheLastPieceEmptiesTheMainHand():
    _setUpMirrored(food={"newItemName": "minecraft:chicken", "newAuxValue": 0, "count": 1})
    _press()
    _advance(24)
    assert _cooked() == [("minecraft:cooked_chicken", 1)] and world.players["p1"]["hand"] is None
    assert world.offhand["p1"]["newItemName"] == "arris:skillet_item"


def testOffHandSkilletWithNothingToCookShowsTheTip():
    _setUpMirrored(food={"newItemName": "minecraft:stick", "newAuxValue": 0, "count": 1})
    _press()
    assert _tips() == ["用另一只手拿着原料！"] and not SkilletHand._sessions
    _setUpMirrored(food=None)
    _press()
    assert _tips() == ["用另一只手拿着原料！"] and not SkilletHand._sessions


def testPuttingTheOffHandSkilletAwayStopsIt():
    _setUpMirrored()
    _press()
    _advance(8)
    world.offhand["p1"] = None
    _advance(40)
    assert _cooked() == [] and world.players["p1"]["hand"]["count"] == 3 and not SkilletHand._sessions


def testTheMainHandSkilletWinsWhenBothHandsHoldOne():
    _setUp(food=SKILLET)                     # 两只手都是煎锅：按 JE 先试主手，另一只手（副手的煎锅）不是原料
    _press()
    assert _tips() == ["用另一只手拿着原料！"] and not SkilletHand._sessions


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
