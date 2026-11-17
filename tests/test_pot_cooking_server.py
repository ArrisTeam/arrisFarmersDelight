# -*- coding: utf-8 -*-
# runner: both
"""厨锅的烹饪（Server/HandCooking.py + Helpers/PotContainer.py + Compat/Diegesis/PotLogic.py）：手放的料等勺子、搅出来的整批、
星星多送的份数、FD 原样一份一份煮、不煮时进度往回掉、成品放不下、余料交给厨师、经验、两项配置。引擎是 potfake.py 里的假的。"""
from __future__ import print_function

import random as realRandom

import dgtest
import potkit as K
from optkit import Config
from potkit import BOWL, POT, SAUCE, TOMATO, fake

HandCooking = K.HandCooking
PotCooking = HandCooking.PotCooking
COCOA = ("minecraft:milk_bucket", "minecraft:sugar", "minecraft:cocoa_beans")


def _hand():
    return HandCooking.handOf(0, POT)


def _setConfig(**values):
    """改 PotCooking 里的配置值，返回改之前的（交给 _restore）。"""
    before = dict((name, getattr(PotCooking, name)) for name in values)
    for name, value in values.items():
        setattr(PotCooking, name, value)
    return before


def _restore(before):
    for name, value in before.items():
        setattr(PotCooking, name, value)


def _tomatoes(each):
    """漏斗放进来的番茄：0、1 号格各 each 个（番茄酱每份要两格各 1 个，所以是 each 份）。"""
    fake.setContainer(POT, 0, TOMATO, each)
    fake.setContainer(POT, 1, TOMATO, each)


def _cocoa(manager=None):
    """热可可的一整套料放进锅：牛奶桶、糖、两个可可豆（各占一格）；manager 有值时经站点放（算手放的），没有就直接写进容器。"""
    if manager is None:
        for index, name in enumerate(COCOA + (COCOA[2],)):
            fake.setContainer(POT, index, name, 1)
        return
    for index, name in enumerate(COCOA + (COCOA[2],)):
        K.feed(manager, name, 1, slotIndex=index)


def testFoodTheCookPutInWaitsForTheSpoonThenTheStirredBatchComesOutTogether():
    manager, data = K.setup()
    K.feed(manager, TOMATO, 16)
    K.run(manager, 20.0)
    hand = _hand()
    assert K.preview() == {} and hand.mode == PotCooking.WAITING and hand.clock.cookTime == 0.0, "没人搅：手放的料不煮"
    assert hand.batch == 8 and data["handsOnByHand"] is True, "整批 8 份在等；料是手放的随锅存档"
    K.effects()
    K.run(manager, 20.0, stir=True)
    assert K.preview()["count"] == 8, "搅着煮：整批 8 份同时出锅（一份 5 秒，批大了慢：5 / (1.5 / sqrt 8) 约 9.4 秒）"
    assert data["potUsed"] == {SAUCE: 8}, "煮了几份记下来（给经验用）"
    assert K.effects() == [("served", {"grade": 1, "bonus": 0})], "只开着 1 颗星：评 1 星，不多送"
    assert K.shape(K.cells()) == [None] * 6 and hand.served == 1 and hand.mode == PotCooking.WAITING
    assert [m for m in fake.multi if m[1] == "OnPotLook"] == [], "世界外观广播默认关着：什么也不发"


def testThreeOpenStarsLetAGoodStirBringBonusServings():
    manager, data = K.setup()
    HandCooking.addMade("a", SAUCE, 40)
    K.feed(manager, TOMATO, 16)
    K.run(manager, 20.0, stir=True)
    assert K.preview()["count"] == 12, "8 份 + 3 星多送 4 份"
    assert K.effects() == [("served", {"grade": 3, "bonus": 4})]
    assert data["potUsed"] == {SAUCE: 8}, "多送的份数不算煮出来的，不多给经验"


def testFoodThatCameInWithoutTheCookIsCookedTheOldWayOneServingEveryFiveSeconds():
    manager, data = K.setup()
    _tomatoes(8)                                 # 漏斗放进来的
    K.alone(21.0)
    hand = _hand()
    assert hand.mode == PotCooking.FD_WAY and hand.clock.byHand is False
    assert K.preview()["count"] == 4 and fake.container(POT, 0)["count"] == 8 - 4 and fake.container(POT, 1)["count"] == 8 - 4, \
        "不用搅：每 5 秒一份（番茄酱 2 个番茄出 1 份）"
    assert data["handsOnByHand"] is None, "不是手放的：不用记"


def testTheHandFedFoodCooksTheOldWayWhenTheCookHasBeenAwayForTwoSeconds():
    manager, data = K.setup()
    K.feed(manager, TOMATO, 4)
    manager.close("a")
    K.alone(1.0)
    assert _hand().mode == PotCooking.WAITING, "厨师刚走：2 秒内还等他"
    K.alone(9.0)
    assert K.preview()["count"] == 1 and _hand().mode == PotCooking.FD_WAY, "走开 2 秒后按 FD 原样自己煮：此后 5 秒出一份，共 10 秒内 1 份"


def testTheByHandMarkSurvivesAReload():
    manager, data = K.setup()
    K.feed(manager, TOMATO, 4)
    K.alone(0.5)
    assert data["handsOnByHand"] is True
    HandCooking._hands.clear()                   # 区块卸载再加载
    assert HandCooking.handOf(0, POT, data).clock.byHand is True
    HandCooking._hands.clear()
    data["handsOnByHand"] = None
    assert HandCooking.handOf(0, POT, data).clock.byHand is False


def testAPotThatDoesNotCookLosesItsProgressTwoSecondsPerSecondInsteadOfStartingOver():
    manager, data = K.setup()
    _tomatoes(1)
    K.alone(3.0)
    hand = _hand()
    assert 2.6 < hand.clock.cookTime <= 3.01, hand.clock.cookTime
    data["heatEnable"] = False                    # 熄了火
    before = hand.clock.cookTime
    K.alone(0.2)
    assert abs(hand.clock.cookTime - (before - 0.4)) < 1e-6, "一步 0.2 秒掉 0.4 秒（每刻 2 刻）"
    assert abs(data["timer"] - (hand.total - hand.clock.cookTime)) < 1e-6, "界面读的 timer 跟着掉"
    K.alone(2.0)
    assert hand.clock.cookTime == 0.0 and hand.batch == 0 and hand.mode == PotCooking.WAITING, "掉到 0 为止"
    data["heatEnable"] = True
    K.alone(2.0)
    assert 1.6 < hand.clock.cookTime <= 2.05, "再点火接着煮（不是退回一整份）"
    fake.setContainer(POT, 0, "minecraft:dirt", 3)  # 料变得凑不成菜：也往回掉
    before = hand.clock.cookTime
    K.alone(0.4)
    assert hand.clock.cookTime < before - 0.7 and hand.dish is None


def testTheMealStackCapStopsTheCookingAt64AndAnotherMealBlocksIt():
    manager, data = K.setup()
    _tomatoes(8)
    K.setMeal(SAUCE, 64, data)
    K.alone(8.0)
    assert K.preview()["count"] == 64 and _hand().batch == 0 and _hand().mode == PotCooking.WAITING, "成品放不下：不煮"
    assert fake.container(POT, 0)["count"] == 8
    K.setMeal(SAUCE, 63, data)
    K.alone(8.0)
    assert K.preview()["count"] == 64 and fake.container(POT, 0)["count"] == 7, "63 + 1 = 64：煮一份就停"
    K.setMeal("arris:cooked_rice", 3, data)
    K.alone(8.0)
    assert K.preview() == {"newItemName": "arris:cooked_rice", "newAuxValue": 0, "count": 3}, "等着盛的是别的菜：不煮"
    assert fake.container(POT, 0)["count"] == 7


def testTheEmptyContainerOfAnIngredientGoesToTheCookWhileTheyAreHere():
    manager, data = K.setup()
    _cocoa(manager)
    assert K.shape(K.cells())[:4] == [(COCOA[0], 1), (COCOA[1], 1), (COCOA[2], 1), (COCOA[2], 1)]
    K.run(manager, 15.0, stir=True)
    assert K.preview()["count"] == 1 and K.preview()["newItemName"] == "arris:hot_cocoa"
    assert fake.count("a", "minecraft:bucket") == 1, "牛奶桶剩下的空桶交给在工位的厨师"
    assert fake.spawned == [], "没掉在地上"


def testTheEmptyContainerFallsBesideThePotWhenNobodyIsHere():
    manager, data = K.setup()
    _cocoa()
    K.alone(12.0)
    assert K.preview()["count"] == 1
    assert [(item["newItemName"], where) for item, dim, where in fake.spawned] == [("minecraft:bucket", (10.5, 65.0, 10.5))], \
        fake.spawned


def testTheExperienceOfABatchIsGivenOnceToWhoeverServesFirstAtTheirFeet():
    manager, data = K.setup()
    K.PotContainer.random = K.FixedRandom(0.0)
    try:
        K.feed(manager, TOMATO, 16)
        K.run(manager, 20.0, stir=True)
        assert K.orbs() == [], "煮好时不给，盛走时才给"
        fake.give("a", 0, BOWL, 8)
        assert K.do(manager, "a", K.custom("scoop", from_inventory=True))
        assert K.orbs() == [3], "8 份 x 0.35 = 2.8：整数部分 2，零头 0.8 掷到 0.0 进一"
        orb = list(fake.orbs.values())[0]
        assert orb["pos"] == (10.5, 64.0, 8.5) and orb["dim"] == 0, "经验球在盛菜的人脚下"
        assert data["potUsed"] is None, "记着的份数清掉了"
        assert K.do(manager, "a", K.custom("scoop", from_inventory=True, all=True))
        assert K.orbs() == [3], "以后再盛不再给"
        K.PotContainer.random = K.FixedRandom(0.99)
        K.setMeal(SAUCE, 8, data)
        K.PotContainer.addUsed(data, SAUCE, 8)
        fake.give("a", 1, BOWL, 1)
        assert K.do(manager, "a", K.custom("scoop", from_inventory=True))
        assert sorted(K.orbs()) == [2, 3], "零头 0.8 没掷中（0.99）就不进一"
    finally:
        K.PotContainer.random = realRandom


def testTheClassicPathStillGivesTheExperienceWhereTheMealLandsInTheResultSlot():
    manager, data = K.setup()
    K.PotContainer.random = K.FixedRandom(0.0)
    try:
        fake.setContainer(POT, 6, BOWL, 5)
        _tomatoes(2)
        K.alone(11.0)                                      # 2 份（FD 原样：每份 5 秒），装进碗里转到产出格
        assert fake.container(POT, 7)["count"] == 2 and fake.container(POT, 6)["count"] == 3
        assert K.orbs() == [1, 1], "每份 0.35 经验：每次转到产出格时结算一次，零头掷中进一；球在锅的上方"
        assert sorted(orb["pos"] for orb in fake.orbs.values()) == [(10.5, 65, 10.5)] * 2
    finally:
        K.PotContainer.random = realRandom


def testTheCookingTimeConfigScalesEveryWayOfCooking():
    manager, data = K.setup()
    before = _setConfig(COOKING_POT_TIME=2.0)
    try:
        _tomatoes(8)
        K.alone(21.0)
        assert K.preview()["count"] == 2 and _hand().total == 10.0, "倍率 2：一份 10 秒"
        assert abs(PotCooking.bookSeconds(5.0) - 10.0 / PotCooking.batchSpeed(1)) < 1e-9
        _setConfig(COOKING_POT_TIME=100.0)
        assert PotCooking.timeFor(5.0) == 50.0, "夹进 0.1..10"
        _setConfig(COOKING_POT_TIME=0.0)
        assert abs(PotCooking.timeFor(5.0) - 0.5) < 1e-9
    finally:
        _restore(before)


def testStirringCanBeSwitchedOffAndTheFoodTheCookPutInCooksByItself():
    manager, data = K.setup()
    with Config(stirring_required=False):
        K.feed(manager, TOMATO, 8)
        K.run(manager, 11.0)
        assert K.preview()["count"] == 2 and _hand().mode == PotCooking.FD_WAY, "不用搅也煮（FD 原样每 5 秒一份）"
        assert data["handsOnByHand"] is True, "料还是记着是手放的（搅起来照样按批量、评星）"
    manager, data = K.setup()
    K.feed(manager, TOMATO, 8)
    K.run(manager, 11.0)
    assert K.preview() == {} and _hand().mode == PotCooking.WAITING, "缺省：等勺子"


def testStirringStillBringsTheWholeBatchAndTheStarsWhenItIsNotRequired():
    # HoD 配置的说明文字：关了不搅也煮，"stirring still cooks the whole pot at once and earns stars"
    with Config(stirring_required=False):
        manager, data = K.setup()
        HandCooking.addMade("a", SAUCE, 40)
        K.feed(manager, TOMATO, 16)
        K.run(manager, 20.0, stir=True)
        assert K.preview()["count"] == 12, "整批 8 份一起出锅，3 星多送 4 份"
        assert K.effects() == [("served", {"grade": 3, "bonus": 4})]


def testWithoutThePotStationThereIsNoSpoonSoNothingWaitsForIt():
    # HandsOnConfig.stirringRequired() 是 stirringRequired && cookingPot：站点关了不等勺子（站点是 K.setup 在配置还缺省时登记的，
    # 之后才把配置改成关：模拟重启之前手放的料，锅这一步按关了的配置煮）
    manager, data = K.setup()
    with Config(cooking_pot=False):
        K.feed(manager, TOMATO, 8)
        K.run(manager, 11.0)
        assert K.preview()["count"] == 2 and _hand().mode == PotCooking.FD_WAY


def testNamesThatGoIntoTheBlockEntityDataOrTheExtraDataAreAlwaysPlainStrings():
    manager, data = K.setup()
    unicodeName = u"arris:tomato_sauce"                 # py2：引擎读回来的字符串可能是 unicode，写回去引擎只打日志、不存
    K.PotContainer.addUsed(data, unicodeName, 2)
    data["potUsed"] = dict([(unicodeName, 2)])
    K.PotContainer.addUsed(data, SAUCE, 1)
    assert data["potUsed"] == {SAUCE: 3} and [type(name) for name in data["potUsed"]] == [str]
    HandCooking.addMade("a", unicodeName, 3)
    saved = fake.extra[("a", HandCooking.MADE_KEY)]
    assert saved == {SAUCE: 3} and [type(name) for name in saved] == [str]
    fake.extra[("b", HandCooking.MADE_KEY)] = {unicodeName: 5}       # 存档里读回来的
    assert HandCooking.madeOf("b", SAUCE) == 5
    HandCooking.addMade("b", SAUCE, 1)
    assert fake.extra[("b", HandCooking.MADE_KEY)] == {SAUCE: 6}
    assert [type(name) for name in fake.extra[("b", HandCooking.MADE_KEY)]] == [str], "读回来的 unicode 键写回去前也转成 str"
    assert type(K.PotContainer.plain(unicodeName)) is str and K.PotContainer.plain(SAUCE) == SAUCE


if __name__ == "__main__":
    raise SystemExit(dgtest.run(globals()))
