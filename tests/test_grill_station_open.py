# -*- coding: utf-8 -*-
# runner: both
"""炉灶站点开不开的服务端复查（Compat/Diegesis/GrillOpen.py，站点登记时的 canOpen）。

客户端那一遍（GrillView.opensStation）只是预判：上面盖着锅 / 煎锅、手里拿着炉灶自己用得上的东西时不开，方块原本的用法照常走。
改过的客户端可以不管它直接发开站请求，所以服务端也照同一份纯规则（Shared/Rules/GrillStation.opens）再问一遍，读的是服务端的引擎。
"""
from __future__ import print_function

import potfake
import stovekit as K

fake = K.fake
Rules = K.Rules
Protocol = K.Protocol
Api = K.Api
GrillOpen = potfake.load("Compat.Diegesis.GrillOpen")

# 引擎给的物品类型（假引擎对什么都答 food，这里换成一张表；表里没有的物品引擎不认识，答 None）
TYPES = {"minecraft:beef": "food", "minecraft:bread": "food", "minecraft:flint_and_steel": "item", "minecraft:iron_shovel": "shovel",
         "minecraft:water_bucket": "bucket", "minecraft:oak_planks": "block", "arris:iron_knife": "sword",
         "minecraft:iron_axe": "axe", "minecraft:bowl": "item", "minecraft:glass_bottle": "item", "minecraft:stick": "item",
         "minecraft:shears": "item"}


def _basicInfo(self, name, aux=0):
    return {"itemType": TYPES[name], "maxStackSize": 64, "itemName": "name:" + name} if name in TYPES else None


potfake.Comp.GetItemBasicInfo = _basicInfo


def _tryOpen(held=None, covered=None):
    """一位玩家手里拿着 held（None 空手）、炉灶上面是 covered（None 是空气）开站；返回 (开成没有, Denied 的原因或 None, Manager)。"""
    manager, data = K.setup(covered=covered)
    if held is not None:
        fake.give("a", 0, held, 1)
    fake.world.take()
    opened = manager.open("a", list(K.STOVE))
    denied = fake.world.take("a", Protocol.EP_DENIED)
    return opened, (denied[0][2]["reason"] if denied else None), manager


def testAnEmptyHandOpensAnUncoveredStove():
    opened, reason, manager = _tryOpen()
    assert opened and reason is None and "a" in manager.sessions


def testAPotOrASkilletOnTopRefusesTheOpenOnTheServer():
    for cover in ("arris:cooking_pot", "arris:skillet", "minecraft:stone"):
        opened, reason, manager = _tryOpen(covered=cover)
        assert not opened and reason == "not allowed", cover
        assert not manager.stations and not manager.sessions, "被拒的开站不留站点实例"


def testWhatTheClientRuleRefusesInTheHandIsRefusedOnTheServerToo():
    for held in ("minecraft:flint_and_steel", "minecraft:iron_shovel", "minecraft:water_bucket", "minecraft:oak_planks",
                 "minecraft:stick"):
        opened, reason, _ = _tryOpen(held=held)
        assert not opened and reason == "not allowed", held


def testFoodKnivesToolsBowlsAndBottlesOpenIt():
    for held in ("minecraft:beef", "minecraft:bread", "arris:iron_knife", "minecraft:iron_axe", "minecraft:bowl",
                 "minecraft:glass_bottle"):
        opened, reason, _ = _tryOpen(held=held)
        assert opened and reason is None, held


def testTheServerAnswersWhatTheSharedRuleSaysForEveryHeldItemAndCover():
    for held, kind in sorted(TYPES.items()):
        for covered in (None, "arris:cooking_pot"):
            opened, _, _ = _tryOpen(held=held, covered=covered)
            assert opened == Rules.opens(held, kind, covered is not None), (held, covered)
    assert _tryOpen()[0] == Rules.opens(None, "", False)


def testAnItemTheEngineDoesNotKnowIsJudgedByItsNameAndItsRecipeOnly():
    """GetItemBasicInfo 答 None（拆掉的附属包留下的物品）：没有类型，不抛；有营火配方的照样开，别的不开。"""
    opened, reason, _ = _tryOpen(held="gone:addon_item")
    assert not opened and reason == "not allowed"
    TYPES.pop("minecraft:beef")
    try:
        assert _tryOpen(held="minecraft:beef")[0], "牛肉有营火配方：不看类型也开"
    finally:
        TYPES["minecraft:beef"] = "food"


def testTheStoveOpensOnceTheCoverIsGone():
    manager, data = K.setup(covered="arris:cooking_pot")
    assert not manager.open("a", list(K.STOVE))
    del fake.world.blocks[(0, (K.STOVE[0], K.STOVE[1] + 1, K.STOVE[2]))]
    assert manager.open("a", list(K.STOVE)) and "a" in manager.sessions


def testReopeningTheStationTheCookAlreadyUsesAsksNothingAgain():
    manager, data = K.setup()
    assert manager.open("a", list(K.STOVE))
    fake.give("a", 0, "minecraft:flint_and_steel", 1)       # 开着站点的人手里换成了打火石：再发一次开站只是重发整份状态
    assert manager.open("a", list(K.STOVE)) and "a" in manager.sessions


def testTheHookIsTheSameFunctionTheStoveIsRegisteredWith():
    manager, data = K.setup()
    stationType = Api.getStationType(Rules.STATION_ID)
    assert stationType.canOpen is GrillOpen.opensStation


def testALogicThatCoversIsTheSameAnswerAsTheHook():
    manager, data = K.setup(covered="arris:cooking_pot")
    assert GrillOpen.isCovered(0, K.STOVE) is True
    assert GrillOpen.isCovered(0, (K.STOVE[0] + 5, K.STOVE[1], K.STOVE[2])) is False


# ---------------------------------------------------------------- 站点朝哪（JE 的 Orientation.BLOCK）

YAW_OF_AUX = {0: 180, 1: 270, 2: 0, 3: 90}      # direction 状态 0 南 1 西 2 北 3 东：站点的北面转到炉灶的正面那一侧


def testTheStationIsRegisteredWithTheBlockFacingHook():
    K.setup()
    assert Api.getStationType(Rules.STATION_ID).facing is GrillOpen.facingOf


def testTheStationFacesTheStovesFrontWhicheverSideTheCookOpensFrom():
    """Opened 里的 yaw 就是炉灶朝哪：厨师 a 在炉灶北面、b 在东面，炉灶朝哪都是同一个答案（站点的北面是方块的正面）。"""
    for aux, yaw in sorted(YAW_OF_AUX.items()):
        manager, data = K.setup()
        fake.blockAux[(0, K.STOVE)] = aux
        assert [K.opened(manager, player)["yaw"] for player in ("a", "b")] == [yaw, yaw], aux
        assert manager.sessions["a"].yaw == manager.sessions["b"].yaw == yaw
        assert GrillOpen.facingOf(0, K.STOVE) == yaw


def testTheServerHookReadsTheBlocksAuxFromTheEngineAndGivesTheSameAnswerAsTheClientsRule():
    StoveFacing = K.fdtest.load("Shared.Rules.StoveFacing")
    manager, data = K.setup()
    for aux in range(4):
        fake.blockAux[(0, K.STOVE)] = aux
        assert GrillOpen.facingOf(0, K.STOVE) == StoveFacing.yawOfAux(aux) == YAW_OF_AUX[aux]
    del fake.blockAux[(0, K.STOVE)]
    assert GrillOpen.facingOf(0, K.STOVE) == 180, "读不到 aux 按 0：引擎的缺省状态朝南"


def testAnOlderKernelWhoseStationTypeKnowsNoCanOpenStillGetsTheStove():
    """前置包是老版本（StationType 没有 canOpen 参数、也不读它）：登记照常成功，炉灶照旧只靠客户端预判。"""
    registered = []

    class OldStationType(object):
        def __init__(self, stationId, blocks, logicFactory=None, schema=None, reach=6.0, exclusive=False):
            self.stationId = stationId

    class OldApi(object):
        API_VERSION = 3
        StationLogic = Api.StationLogic
        SlotRules = Api.SlotRules
        StationSchema = Api.StationSchema
        StationType = OldStationType
        registerStation = staticmethod(registered.append)

    logicClass = K.GrillLogic.register(OldApi)
    assert logicClass is not None and len(registered) == 1 and registered[0].stationId == Rules.STATION_ID


if __name__ == "__main__":
    import fdtest
    raise SystemExit(fdtest.run(globals()))
