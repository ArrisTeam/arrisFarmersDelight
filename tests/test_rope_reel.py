# -*- coding: utf-8 -*-
# runner: both
"""卷绳子（Server/RopeAndNet.py 的 OnUseRope + Shared/Rules/RopeReel.py）对照 JE 的 RopeBlock.use（FD 1.3.4）。

JE：手里是空的才处理；配置 enableRopeReeling（缺省 true）且玩家潜行时，从被点的绳子往下数，一路都是绳子，
拆掉**最下面那一节**（destroyBlock(pos, false)：不掉落），一根绳子进背包（创造模式不给；不能建造或背包放不下什么都不做）；
否则（没潜行，或配置关了）一路连到上方的钟（往上最多 24 格）时敲钟。
"""
from __future__ import print_function

import sys
import types

import fakeengine
import fdtest

world = fakeengine.install()
engineModule = sys.modules[fakeengine.ENGINE_MODULE]
engineModule.IsLiving = lambda entityId: True
# QuModLibs 离线导入不了（它要引擎）：RopeAndNet 只用它的两个装饰器，换成什么都不做的
quMod = types.ModuleType(fdtest.SCRIPTS + ".QuModLibs.Server")
quMod.AllowCall = lambda func: func
quMod.InjectHttpPlayerId = lambda func: func
sys.modules[quMod.__name__] = quMod
tolls = []
engineModule.System.CreateEngineEntityByTypeStr = lambda name, pos, rot, dim: tolls.append((name, pos, dim))

world.sneaking, world.cannotBuild, world.fullInventory = set(), set(), set()
_basePlayer, _baseItem = world._Player, world._Item


def _player(target):
    methods = _basePlayer(target)
    methods["isSneaking"] = lambda: target in world.sneaking
    methods["GetPlayerAbilities"] = lambda: {"build": target not in world.cannotBuild, "mine": True}
    return methods


def _item(target):
    methods = _baseItem(target)
    give = methods["SpawnItemToPlayerInv"]
    methods["SpawnItemToPlayerInv"] = lambda itemDict, playerId, slot=None: False if playerId in world.fullInventory else give(itemDict, playerId)
    return methods


world._Player, world._Item = _player, _item

Registry = fdtest.load("Server.EventRegistry")
RopeAndNet = fdtest.load("Server.RopeAndNet")
Blocks = fdtest.load("Shared.Data.Blocks")
RopeReel = fdtest.load("Shared.Rules.RopeReel")

ROPE = "arris:rope"
CLICK = (5, 70, 5)
REEL_DEFAULT = Blocks.enableRopeReeling         # 在别的用例改它之前先记下


def _setUp(hand=None, creative=False, sneaking=True):
    Registry.clearAll()
    Registry.registerHandler("ServerBlockUseEvent", match=ROPE)(RopeAndNet.OnUseRope)
    for table in (world.players, world.entities, world.blocks, world.modAttr):
        table.clear()
    world.spawned[:] = []
    world.sounds[:] = []
    world.calls[:] = []
    world.timers = []
    tolls[:] = []
    world.sneaking.clear()
    world.cannotBuild.clear()
    world.fullInventory.clear()
    Blocks.enableRopeReeling = True
    world.addPlayer("p1", hand=dict(hand) if hand else None, creative=creative)
    if sneaking:
        world.sneaking.add("p1")


def _rope(top, count):
    """从 top 往下 count 节绳子。"""
    for index in range(count):
        world.setBlock(CLICK[0], top - index, CLICK[2], ROPE)


def _use(y=70):
    args = {"x": CLICK[0], "y": y, "z": CLICK[2], "dimensionId": 0, "playerId": "p1", "blockName": ROPE, "aux": 0, "cancel": False}
    Registry.dispatch("ServerBlockUseEvent", args, ROPE)
    world.runTimers()
    return args


def _ropes():
    return [y for y in range(60, 80) if world.blockName(CLICK[0], y, CLICK[2]) == ROPE]


GIVEN = {"itemName": ROPE, "count": 1, "auxValue": 0}


# ---- 规则 ----

def testLowestRopeWalksDownTheWholeColumn():
    column = set((5, y, 5) for y in range(60, 71))
    assert RopeReel.lowestRope((5, 70, 5), column.__contains__) == (5, 60, 5)
    assert RopeReel.lowestRope((5, 65, 5), column.__contains__) == (5, 60, 5)      # 点的是中间一节，还是拆最下面的
    assert RopeReel.lowestRope((5, 60, 5), column.__contains__) == (5, 60, 5)      # 点的就是最下面一节：拆自己
    assert RopeReel.lowestRope((5, 70, 5), set().__contains__) == (5, 70, 5)


def testLowestRopeStopsAtAGapAndAtTheLimit():
    broken = set((5, y, 5) for y in range(60, 71)) - set([(5, 64, 5)])
    assert RopeReel.lowestRope((5, 70, 5), broken.__contains__) == (5, 65, 5)      # 中间断了：只算连着的那一段
    assert RopeReel.lowestRope((5, 70, 5), lambda pos: True, limit=10) == (5, 60, 5)


def testReelingIsOnByDefaultLikeJava():
    assert REEL_DEFAULT is True


# ---- 卷 ----

def testSneakingWithAnEmptyHandReelsTheBottomRopeIntoTheInventory():
    _setUp()
    _rope(70, 4)                                    # 70 69 68 67
    _use(70)
    assert _ropes() == [68, 69, 70]                 # 最下面的 67 没了，别的都在
    assert world.players["p1"]["given"] == [GIVEN]
    assert world.spawned == []                      # 没有掉落物：destroyBlock(pos, false)
    assert world.sounds and world.sounds[0][1] == (5, 67, 5)


def testClickingAMiddleRopeStillTakesTheBottomOne():
    _setUp()
    _rope(70, 4)
    _use(68)
    assert _ropes() == [68, 69, 70]


def testALoneRopeReelsItself():
    _setUp()
    _rope(70, 1)
    _use(70)
    assert _ropes() == [] and len(world.players["p1"]["given"]) == 1


def testOnlyRopeCountsAsTheColumn():
    _setUp()
    _rope(70, 2)
    world.setBlock(5, 68, 5, "arris:tomatoes_vine_stage0")
    world.setBlock(5, 67, 5, ROPE)
    _use(70)
    assert _ropes() == [67, 70]                      # 拆的是 69（它下面是番茄藤，不是绳子，JE 的 is(this) 只认绳子本身），67 那节不相干
    assert world.blockName(5, 68, 5) == "arris:tomatoes_vine_stage0"


def testCreativeModeRemovesTheRopeWithoutGivingOne():
    _setUp(creative=True)
    _rope(70, 3)
    _use(70)
    assert _ropes() == [69, 70] and world.players["p1"]["given"] == []


def testFullInventoryDoesNothing():
    _setUp()
    _rope(70, 3)
    world.fullInventory.add("p1")
    _use(70)
    assert _ropes() == [68, 69, 70] and world.players["p1"]["given"] == []


def testPlayersWhoMayNotBuildCannotReel():
    _setUp()
    _rope(70, 3)
    world.cannotBuild.add("p1")                      # 冒险 / 旁观：abilities.mayBuild 为假
    _use(70)
    assert _ropes() == [68, 69, 70] and world.players["p1"]["given"] == []
    assert tolls == []                               # 潜行那一支失败也不会转去敲钟


def testNotSneakingDoesNotReel():
    _setUp(sneaking=False)
    _rope(70, 3)
    _use(70)
    assert _ropes() == [68, 69, 70]


def testReelingCanBeSwitchedOffLikeTheJavaConfig():
    _setUp()
    _rope(70, 3)
    Blocks.enableRopeReeling = False
    _use(70)
    assert _ropes() == [68, 69, 70] and world.players["p1"]["given"] == []
    world.setBlock(5, 72, 5, "minecraft:bell")           # 配置关了：潜行时照样敲钟
    world.setBlock(5, 71, 5, ROPE)
    _use(70)
    assert len(tolls) == 1


def testAnItemInHandMeansNothingHappens():
    _setUp(hand={"newItemName": "minecraft:stick", "newAuxValue": 0, "count": 1})
    _rope(70, 3)
    _use(70)
    assert _ropes() == [68, 69, 70] and world.timers == [] and world.calls == []     # 连冷却都不认领，留给别的处理


# ---- 敲钟（没潜行） ----

def testBellRingsWhenTheRopeRunsStraightUpToIt():
    _setUp(sneaking=False)
    _rope(70, 1)
    world.setBlock(5, 71, 5, ROPE)
    world.setBlock(5, 72, 5, "minecraft:bell")
    _use(70)
    assert tolls == [("arris:toll_entity", (5.5, 72.6, 5.5), 0)]


def testBellIsFoundUpTo24BlocksAway():
    _setUp(sneaking=False)
    for y in range(70, 94):
        world.setBlock(5, y, 5, ROPE)
    world.setBlock(5, 94, 5, "minecraft:bell")        # 点的绳子往上第 24 格：JE 的 for i < 24
    _use(70)
    assert len(tolls) == 1
    tolls[:] = []
    world.timers = []
    world.modAttr.clear()
    world.setBlock(5, 94, 5, "minecraft:air")
    world.setBlock(5, 95, 5, "minecraft:bell")        # 第 25 格：够不着
    world.setBlock(5, 94, 5, ROPE)
    _use(70)
    assert tolls == []


def testNoBellWhenARopeIsMissingOnTheWay():
    _setUp(sneaking=False)
    _rope(70, 1)
    world.setBlock(5, 72, 5, "minecraft:bell")
    _use(70)
    assert tolls == []


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
