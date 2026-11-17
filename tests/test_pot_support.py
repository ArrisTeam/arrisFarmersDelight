# -*- coding: utf-8 -*-
# runner: both
"""厨锅的支架（FD 的 CookingPotSupport：没有 / 托盘 / 吊把手）：Server/PotSupport.py、Server/Helpers/Heat.RefreshHeat、Server/CookingPotHost.use、
Server/PotLook 的 support。引擎是 potfake.py 里的假的。

JE（CookingPotBlock）：
- 放下时（getStateForPlacement :117-120）：点的是方块的下面是 HANDLE，否则正下方是托盘热源（熔岩、营火、火）是 TRAY，不是 NONE；
- 邻居变了（updateShape :128-130）：HANDLE 不动，别的按正下方重算；
- 潜行空手右键（use :71-74）：HANDLE 切回按正下方算的 TRAY / NONE，别的切成 HANDLE，LANTERN_PLACE 0.7 / 1.0；
  原版潜行时任何一只手拿着东西，方块的 use 根本不调（ServerPlayerGameMode.useItemOn），手里的东西照常用。
"""
from __future__ import print_function

import sys
import types

import dgtest
import fdtest
import potfake
import potkit as K
from potkit import BOWL, POT, SAUCE, fake

PotSupport = potfake.load("Server.PotSupport")
Registry = fdtest.load("Server.EventRegistry")
Rules = fdtest.load("Shared.Rules.PotSupport")
PotLook = K.PotLook
BELOW = (POT[0], POT[1] - 1, POT[2])
LAVA, STONE, FIRE = "minecraft:lava", "minecraft:stone", "minecraft:fire"
UNDER, TOP, SOUTH = 0, 1, 3                  # Facing.Down / Up / South（点的是方块的哪一面）


class _Type(object):
    def __init__(self, typeId, title, menu, host=None):
        self.typeId, self.host = typeId, host


def _host():
    """Server/CookingPotHost 用库的方块宿主（真的）和一个替身 Api（库的 Server.Api 要引擎）导入，返回它登记的宿主和方块宿主模块。"""
    apiName = fdtest.SCRIPTS + ".dolorContainer.Server.Api"
    registered = []
    api = types.ModuleType(apiName)
    api.ContainerType, api.registerContainerType = _Type, registered.append
    sys.modules[apiName] = api
    fdtest.load("dolorContainer.Server").Api = api
    Block = fdtest.load("dolorContainer.Std.Block.Server")
    Block._installed[0] = True                         # 不真的去监听引擎事件
    potfake.load("Server.CookingPotHost")
    assert len(registered) == 1
    return registered[0].host, Block


HOST, Block = _host()
KEY = Block.blockKey(0, POT)


def _fresh(below=None):
    """干净的假世界：玩家 a（锅北边）、b；锅的位置上是一份空的方块实体数据（还没放）；below 是锅正下方的方块。返回 K.setup() 的 manager。"""
    manager, _data = K.setup()
    del fake.calls[:]
    del fake.timers[:]
    fake.blockEntities[(0, POT)] = potfake.BEData()
    fake.world.blocks[(0, BELOW)] = below or "minecraft:air"
    return manager


def _molang():
    """推给各客户端的方块实体 molang：{变量名: 最后一次的值}（先把延迟的推送跑掉），并清掉记录。"""
    for _delay, func, args in list(fake.timers):
        if func.__name__ != "ResetPlayerUsedCD":
            func(*args)
    fake.timers[:] = [timer for timer in fake.timers if timer[1].__name__ == "ResetPlayerUsedCD"]
    pushed = dict((call[2][0]["name"], call[2][0]["molang"]) for call in fake.calls if call[1] == "SetEntityBlockMolang")
    fake.calls[:] = [call for call in fake.calls if call[1] != "SetEntityBlockMolang"]
    return pushed


def _tryPlace(face, x=POT[0]):
    Registry.dispatch("ServerEntityTryPlaceBlockEvent",
                      {"entityId": "a", "dimensionId": 0, "x": x, "y": POT[1], "z": POT[2], "fullName": "arris:cooking_pot", "face": face},
                      "arris:cooking_pot")


def _place(face, below=None):
    """玩家 a 点方块的 face 面放下一口锅：放置前事件，方块实体建好（都经真的事件注册表）；返回 (锅的方块实体数据, 推给客户端的 molang)。"""
    _fresh(below)
    _tryPlace(face)
    Registry.dispatch("ServerPlaceBlockEntityEvent", {"blockName": "arris:cooking_pot", "dimension": 0, "posX": POT[0], "posY": POT[1], "posZ": POT[2]},
                      "arris:cooking_pot")
    return fake.blockEntities[(0, POT)], _molang()


def _sneak(creative=False, hand=None, offhand=None):
    player = fake.world.players["a"]
    player["sneaking"], player["creative"] = True, creative
    player["inv"][0], player["offhand"] = hand, offhand


def _click():
    """玩家 a 对着这口锅使用一下（库在对着方块使用时先问宿主）：返回宿主的答复。上一下的交互冷却先过掉（按住右键的重复要的用例自己调 HOST.use）。"""
    for _delay, func, args in list(fake.timers):
        if func.__name__ == "ResetPlayerUsedCD":
            func(*args)
    fake.timers[:] = [timer for timer in fake.timers if timer[1].__name__ != "ResetPlayerUsedCD"]
    return HOST.use("a", "arris:cooking_pot", KEY, {})


def _sounds():
    return [call[2][0] for call in fake.calls if call[1] == "OnPlaySound"]


# ---------------------------------------------------------------- 放下时（getStateForPlacement）

def testAPotPlacedAgainstTheUndersideOfABlockHangsByItsHandle():
    data, molang = _place(UNDER)
    assert data["handleEnable"] == 1.0 and data["shelfEnable"] == 0.0
    assert molang["variable.mod_handle"] == 1.0, "各客户端的模型长出吊把手"


def testPlacedOnTheTopOrASideItHasNoHandleAndTheTrayFollowsTheBlockBelow():
    for face in (TOP, 2, SOUTH, 4, 5):
        data, molang = _place(face, below=LAVA)
        assert data["handleEnable"] == 0.0 and data["shelfEnable"] == 1.0, face
        assert molang["variable.mod_handle"] == 0.0 and molang["variable.mod_shelf"] == 1.0, face
        data, molang = _place(face, below=STONE)
        assert data["handleEnable"] == 0.0 and data["shelfEnable"] == 0.0, face


def testAHangingPotHasNoTrayWhateverIsBelowItAndStillGetsHeatFromIt():
    data, molang = _place(UNDER, below=LAVA)
    assert data["shelfEnable"] == 0.0 and data["handleEnable"] == 1.0
    assert data["heatEnable"] is True and data["heatParticleEnable"] == 1.0, "JE 的 isHeated 不看支架：挂着的锅照样被下面的热源烧热"
    assert molang["variable.mod_shelf"] == 0.0 and molang["variable.mod_handle"] == 1.0 and molang["variable.mod_heat"] == 1.0


def testTheLastPlacementAttemptAtAPositionCountsAndRecordsAreKeptPerPosition():
    _fresh()
    _tryPlace(UNDER)
    _tryPlace(TOP)                                       # 第一次没放成，换个面又放了
    data = potfake.BEData()
    PotSupport.attach(data, 0, POT)
    assert data["handleEnable"] == 0.0, "用最后一次点的面"
    _tryPlace(UNDER, x=POT[0] + 5)
    other = potfake.BEData()
    PotSupport.attach(other, 0, POT)
    assert other["handleEnable"] == 0.0, "那一笔记在别的位置上，这一口不沾"
    PotSupport.attach(other, 0, (POT[0] + 5, POT[1], POT[2]))
    assert other["handleEnable"] == 1.0
    again = potfake.BEData()
    PotSupport.attach(again, 0, (POT[0] + 5, POT[1], POT[2]))
    assert again["handleEnable"] == 0.0, "取走就没了"


def testThePlacementRecordExpiresWhenThePlacementWasCancelled():
    _fresh()
    clock, original = potfake.Clock(fake.world), PotSupport.time
    PotSupport.time = clock
    try:
        _tryPlace(UNDER)
        fake.world.time += 6.0                           # 放置被别的处理函数取消了；过了几秒用 /setblock 在同一格放一口锅
        data = potfake.BEData()
        PotSupport.attach(data, 0, POT)
    finally:
        PotSupport.time = original
    assert data["handleEnable"] == 0.0, "5 秒过期：不会把旧的放置记到这口锅上"


def testAPotWithoutAPlacementRecordKeepsItsFlagAndOneWithoutTheKeyHasNoHandle():
    data = potfake.BEData()
    data["handleEnable"] = 1.0                           # 活塞推来的：方块实体数据带着旗
    PotSupport.attach(data, 0, POT)
    assert data["handleEnable"] == 1.0
    fresh = potfake.BEData()                             # /setblock、结构放出的锅没有放置记录
    PotSupport.attach(fresh, 0, POT)
    assert fresh["handleEnable"] == 0.0


# ---------------------------------------------------------------- 邻居变了（updateShape）

def _neighbour(name):
    """正下方的方块变成 name：引擎的邻居事件（经真的事件注册表）；返回锅的方块实体数据和推给客户端的 molang。"""
    fake.world.blocks[(0, BELOW)] = name
    Registry.dispatch("BlockNeighborChangedServerEvent",
                      {"dimensionId": 0, "blockName": "arris:cooking_pot", "posX": POT[0], "posY": POT[1], "posZ": POT[2],
                       "neighborPosX": BELOW[0], "neighborPosY": BELOW[1], "neighborPosZ": BELOW[2], "toBlockName": name}, "arris:cooking_pot")
    return fake.blockEntities[(0, POT)], _molang()


def testTheHandleStaysWhateverHappensBelowAndTheTrayFollowsTheBlockBelow():
    _place(UNDER)
    for below in (LAVA, STONE, FIRE, "minecraft:air"):
        data, molang = _neighbour(below)
        assert data["handleEnable"] == 1.0 and data["shelfEnable"] == 0.0, below
        assert molang["variable.mod_handle"] == 1.0 and molang["variable.mod_shelf"] == 0.0, below
    _place(TOP)
    data, molang = _neighbour(LAVA)
    assert data["handleEnable"] == 0.0 and data["shelfEnable"] == 1.0 and molang["variable.mod_shelf"] == 1.0, "没有吊把手：支架照旧跟着下面走"
    data, molang = _neighbour(STONE)
    assert data["shelfEnable"] == 0.0 and molang["variable.mod_shelf"] == 0.0


# ---------------------------------------------------------------- 潜行空手右键（use）

def testSneakingWithEmptyHandsSwitchesTheHandleOnAndOffAndPlaysTheLantern():
    _place(TOP, below=STONE)
    _sneak()
    assert _click() == Block.BLOCK, "不开界面"
    data = fake.blockEntities[(0, POT)]
    assert data["handleEnable"] == 1.0 and data["shelfEnable"] == 0.0
    assert _molang()["variable.mod_handle"] == 1.0
    call, = _sounds()
    assert call["soundName"] == "block.lantern.place" and abs(call["volume"] - 0.7) < 1e-9, "JE 的 LANTERN_PLACE 0.7"
    assert abs(call["pitch"] - 1.0 / 1.1) < 1e-9, "JE 音调 1.0；原版这条声音每个采样自带 1.1，除掉才是 1.0"
    assert tuple(call["pos"]) == (POT[0] + 0.5, POT[1] + 0.5, POT[2] + 0.5), "方块中心"
    assert _click() == Block.BLOCK
    assert data["handleEnable"] == 0.0 and data["shelfEnable"] == 0.0, "下面不是托盘热源：切回没有"
    assert _molang()["variable.mod_handle"] == 0.0 and len(_sounds()) == 2, "切回去也响一声"


def testSwitchingTheHandleOffPutsTheTrayBackWhenThereIsAFireBelow():
    _place(UNDER, below=LAVA)
    _sneak()
    assert _click() == Block.BLOCK
    data = fake.blockEntities[(0, POT)]
    assert data["handleEnable"] == 0.0 and data["shelfEnable"] == 1.0, "HANDLE 切回按正下方算的托盘"
    assert _molang()["variable.mod_shelf"] == 1.0
    assert _click() == Block.BLOCK
    assert data["handleEnable"] == 1.0 and data["shelfEnable"] == 0.0, "再切：吊把手盖掉托盘"
    assert _molang()["variable.mod_shelf"] == 0.0


def testHoldingTheButtonSwitchesOnceAndTheNextSwitchWaitsForTheSharedCooldown():
    _place(TOP)
    _sneak()
    assert _click() == Block.BLOCK
    data = fake.blockEntities[(0, POT)]
    assert data["handleEnable"] == 1.0
    assert HOST.use("a", "arris:cooking_pot", KEY, {}) == Block.BLOCK, "按住右键时引擎每刻重发：拦下"
    assert data["handleEnable"] == 1.0 and len(_sounds()) == 1, "冷却内不重复切、不重复响"
    assert _click() == Block.BLOCK and data["handleEnable"] == 0.0, "冷却过了再切一次（JE 按住右键也是每 4 刻一次）"


def testItWorksInCreativeModeToo():
    _place(TOP)
    _sneak(creative=True)
    assert _click() == Block.BLOCK and fake.blockEntities[(0, POT)]["handleEnable"] == 1.0


def testSneakingWithSomethingInTheOffHandLeavesTheClickToTheEngine():
    _place(TOP)
    _sneak(offhand={"newItemName": "minecraft:shield", "newAuxValue": 0, "count": 1})
    assert _click() == Block.PASS, "JE：任何一只手拿着东西，方块的 use 不调；不开界面、不切"
    assert fake.blockEntities[(0, POT)]["handleEnable"] == 0.0 and _sounds() == []


def testSneakingWithSomethingInTheMainHandPassesLikeVanillaAndNeverSwitches():
    _place(TOP)
    held = {"newItemName": BOWL, "newAuxValue": 0, "count": 1}
    _sneak(hand=dict(held))
    assert HOST.passes("a", held, True) is True, "库的缺省规则：潜行并拿着东西放过（用的是手里的东西）：不盛、不开界面、不切"
    assert HOST.passes("a", held, False) is False
    assert _click() == Block.PASS and fake.blockEntities[(0, POT)]["handleEnable"] == 0.0, "就算问到宿主，手里有东西也不切"


def testWithoutSneakingNothingIsSwitchedTheClickServesOrOpensTheScreen():
    _place(TOP)
    data = fake.blockEntities[(0, POT)]
    assert _click() == Block.OPEN, "空手不潜行：开经典界面"
    assert data["handleEnable"] == 0.0 and _sounds() == []
    K.setMeal(SAUCE, 3, data)
    K.PotContainer.addUsed(data, SAUCE, 3)
    fake.give("a", 0, BOWL, 2)
    assert _click() == Block.BLOCK and fake.count("a", SAUCE) == 1, "拿着碗点有菜的锅：盛一份，不开界面"
    assert data["handleEnable"] == 0.0


def testAPotWithoutTheKeyStartsWithoutHandleAndTheFirstSwitchMakesIt():
    _fresh()
    data = fake.blockEntities[(0, POT)]
    assert data["handleEnable"] is None
    _sneak()
    assert _click() == Block.BLOCK and data["handleEnable"] == 1.0
    assert _molang()["variable.mod_handle"] == 1.0


def testWithoutTheKeyNoHandleVariableIsPushedAndTheSkilletNeverGetsOne():
    _fresh()
    data = potfake.BEData()
    potfake.load("Server.Helpers.Heat").RefreshHeat(data, POT, BELOW, 0, LAVA)
    assert "variable.mod_handle" not in _molang(), "没有 handleEnable 这个键（煎锅、/setblock 放的锅）：不推，模型缺省就没有吊把手"


# ---------------------------------------------------------------- 世界外观广播

def _looks():
    return [(players, args[0]) for players, key, args in fake.multi if key == PotLook.ENDPOINT]


def testTheWorldLookCarriesTheSupportAndAChangeOfItIsBroadcastAgain():
    manager = _fresh(LAVA)
    data = fake.blockEntities[(0, POT)]
    data["previewItemSlot"], data["timer"], data["heatEnable"], data["shelfEnable"], data["handleEnable"] = [{}], 10.0, True, 1.0, 0.0
    PotLook.enable()
    K.run(manager, 0.5)
    assert _looks()[-1][1]["support"] == Rules.TRAY and data["potLook"]["support"] == Rules.TRAY, "托盘"
    _sneak()
    assert _click() == Block.BLOCK
    count = len(_looks())
    K.run(manager, 0.5)
    last = _looks()[-1][1]
    assert len(_looks()) == count + 1 and last["support"] == Rules.HANDLE and data["potLook"]["support"] == Rules.HANDLE, "吊把手：变了就再发、再写镜像"
    assert _click() == Block.BLOCK
    K.run(manager, 0.5)
    assert _looks()[-1][1]["support"] == Rules.TRAY, "切回托盘（下面是熔岩）"
    data["handleEnable"], data["shelfEnable"] = 0.0, 0.0              # 熔岩没了（这里直接改旗）
    K.run(manager, 0.5)
    assert _looks()[-1][1]["support"] == Rules.NONE and "support" not in data["potLook"], "没有支架：镜像不写（读的人缺键当没有）"


# ---------------------------------------------------------------- 纯规则

def testTheRulesFollowJava():
    assert (Rules.NONE, Rules.TRAY, Rules.HANDLE) == (0, 1, 2) and Rules.DOWN == 0, "CookingPotSupport 的次序；Facing.Down = 0"
    assert Rules.hangs(0) is True and all(Rules.hangs(face) is False for face in (1, 2, 3, 4, 5))
    assert Rules.kindOf(True, True) == Rules.HANDLE and Rules.kindOf(False, True) == Rules.TRAY and Rules.kindOf(False, False) == Rules.NONE
    assert Rules.TOGGLE_SOUND == ("block.lantern.place", 0.7, 1.0)


def testTheKindReadFromTheNetworkIsOneOfTheThreeOrNothing():
    assert [Rules.readKind(value) for value in (0, 1, 2, 2.0)] == [0, 1, 2, 2]
    assert [Rules.readKind(value) for value in (None, True, False, 3, -1, "2", [2], float("nan"))] == [0] * 8


if __name__ == "__main__":
    raise SystemExit(dgtest.run(globals()))
