# -*- coding: utf-8 -*-
# runner: both
"""长榻榻米垫的服务端（Server/TatamiMats.py）：两格一起放、一起拆、只掉一个；用假引擎驱动（tests/fakeengine.py）。

JE 的 TatamiMatBlock：getStateForPlacement 让脚放在点到的格子、头放在玩家面朝的下一格（头那格要能放、两格下面都不是空气）；
拆哪一半另一半都跟着没（updateShape），整张垫子只掉一个（战利品表只有头给，创造模式一个也不掉）；
脚下没了方块（canSurvive）这一半碎掉。这里掉落由被拆的那一半的战利品表给，另一半静默消失；脚下没了方块时由脚本把这一半"打碎"掉落。
"""
from __future__ import print_function

import io
import os

import fakeengine
import fdtest

world = fakeengine.install()
Registry = fdtest.load("Server.EventRegistry")
Mats = fdtest.load("Server.TatamiMats")
Mat = fdtest.load("Shared.Rules.TatamiMat")

STONE = "minecraft:stone"
FLOOR_Y = 63
MAT_ITEM = {"newItemName": "arris:tatami_full_mat", "newAuxValue": 0, "count": 3}
HALF_ITEM = {"newItemName": "arris:tatami_half_mat", "newAuxValue": 0, "count": 3}
BLOCK_CALLS = []                         # SetBlockNew 的调用记录：("set", 位置, 方块名, 处理方式, 多出来的参数)
STATE = {"yaw": 0.0, "gameType": None}


def _blockInfo(target):
    def setBlockNew(pos, blockDict, handling=0, dim=0, *rest):
        BLOCK_CALLS.append(("set", tuple(pos), blockDict["name"], handling, rest))
        world.blocks[(dim,) + tuple(pos)] = {"name": blockDict["name"], "states": None, "data": None}
        return True
    return {"SetBlockNew": setBlockNew,
            "GetBlockNew": lambda pos, dim=0: {"name": world.blockName(pos[0], pos[1], pos[2], dim), "aux": 0}}


def _game(target):
    methods = dict(fakeengine.FakeWorld._Game(world, target))
    creative = methods["GetPlayerGameType"]
    methods["GetPlayerGameType"] = lambda playerId: STATE["gameType"] if STATE["gameType"] is not None else creative(playerId)
    return methods


world._BlockInfo = _blockInfo
world._Game = _game
world._Rot = lambda target: {"GetRot": lambda: (0.0, STATE["yaw"])}


def _setUp(hand=MAT_ITEM, yaw=0.0, creative=False, gameType=None, floor=True):
    del BLOCK_CALLS[:]
    world.blocks.clear()
    world.sounds[:] = []
    world.calls[:] = []
    world.players.clear()
    world.entities.clear()
    world.modAttr.clear()
    world.timers = []
    STATE.update(yaw=yaw, gameType=gameType)
    world.addPlayer("p1", hand=dict(hand), creative=creative)
    if floor:
        for x in range(0, 11):
            for z in range(0, 11):
                world.setBlock(x, FLOOR_Y, z, STONE)


def _use(blockPos=(5, FLOOR_Y, 5), face=1, item=None):
    """玩家右键 blockPos 的 face 面（手里的物品用 world.players 里的）；返回事件参数。"""
    item = item if item is not None else dict(world.players["p1"]["hand"])
    blockName = world.blockName(*blockPos)
    args = {"entityId": "p1", "x": blockPos[0], "y": blockPos[1], "z": blockPos[2], "face": face, "dimensionId": 0,
            "blockName": blockName, "itemDict": item, "ret": False}
    handled = Registry.dispatch("ServerItemUseOnEvent", args, blockName)
    world.runTimers()                      # 过了交互冷却，下一次点击才算新的一次
    return args, handled


def _states(x, y, z):
    block = world.blocks.get((0, x, y, z))
    return block["states"] if block else None


def _neighborEvent(name, pos, neighbor, toName):
    args = {"blockName": name, "posX": pos[0], "posY": pos[1], "posZ": pos[2], "dimensionId": 0,
            "neighborPosX": neighbor[0], "neighborPosY": neighbor[1], "neighborPosZ": neighbor[2],
            "toBlockName": toName, "fromBlockName": STONE, "auxValue": 0, "fromBlockAuxValue": 0, "toAuxValue": 0}
    Registry.dispatch("BlockNeighborChangedServerEvent", args, name)


def _placed(direction=2, foot=(5, 64, 5)):
    """摆好一张长垫子（脚在 foot，头在放置者面朝的方向），返回 (脚, 头)；记录清空。"""
    head = Mat.partnerPos(Mat.FOOT, foot, direction)
    world.setBlock(foot[0], foot[1], foot[2], Mat.FOOT, states={"direction": direction})
    world.setBlock(head[0], head[1], head[2], Mat.HEAD, states={"direction": direction})
    del BLOCK_CALLS[:]
    return foot, head


# ---- 放置 ----

def testPlacingPutsTheFootAtTheClickAndTheHeadWhereThePlayerLooks():
    _setUp(yaw=0.0)                                            # 朝南
    args, handled = _use()
    assert args["ret"] is True and handled is True              # 引擎自己那一格被取消
    assert world.blockName(5, 64, 5) == Mat.FOOT and world.blockName(5, 64, 6) == Mat.HEAD
    assert _states(5, 64, 5) == {"direction": 2} and _states(5, 64, 6) == {"direction": 2}
    assert world.players["p1"]["hand"]["count"] == 2
    assert world.sounds == [("dig.cloth", (5.5, 64.5, 5.5))]


def testHeadFollowsTheLookDirectionForAllFourFacings():
    for yaw, headAt, direction in ((0.0, (5, 64, 6), 2), (90.0, (4, 64, 5), 3), (180.0, (5, 64, 4), 0), (-90.0, (6, 64, 5), 1)):
        _setUp(yaw=yaw)
        _use()
        assert world.blockName(5, 64, 5) == Mat.FOOT and world.blockName(*headAt) == Mat.HEAD, yaw
        assert _states(5, 64, 5) == {"direction": direction} and _states(*headAt) == {"direction": direction}, yaw


def testFootIsPlacedBeforeTheHeadWithItsDirectionAlready():
    # 头放下去会让脚收到邻居变化，那时脚必须已经有朝向（否则读不出另一半在哪）
    _setUp(yaw=0.0)
    _use()
    assert [(call[1], call[2]) for call in BLOCK_CALLS] == [((5, 64, 5), Mat.FOOT), ((5, 64, 6), Mat.HEAD)]


def testCreativeKeepsTheItem():
    _setUp(creative=True)
    _use()
    assert world.blockName(5, 64, 6) == Mat.HEAD and world.players["p1"]["hand"]["count"] == 3


def testNothingIsPlacedWhenTheHeadHasNoGroundOrNoRoom():
    _setUp(yaw=0.0)
    world.blocks.pop((0, 5, FLOOR_Y, 6))                       # 头下面是空气
    args, handled = _use()
    assert args["ret"] is True and handled is True              # 照样取消引擎的放置，什么都不放
    assert world.blockName(5, 64, 5) == "minecraft:air" and not BLOCK_CALLS
    assert world.players["p1"]["hand"]["count"] == 3 and world.sounds == []
    _setUp(yaw=0.0)
    world.setBlock(5, 64, 6, STONE)                            # 头的位置被方块占了
    _use()
    assert world.blockName(5, 64, 5) == "minecraft:air" and not BLOCK_CALLS


def testAdventureAndSpectatorCannotPlace():
    for gameType in (2, 3):
        _setUp(gameType=gameType)
        args, handled = _use()
        assert args["ret"] is True and world.blockName(5, 64, 5) == "minecraft:air" and not BLOCK_CALLS, gameType


def testHoldingTheClickDoesNotPlaceASecondMat():
    _setUp(yaw=0.0)
    args = {"entityId": "p1", "x": 5, "y": FLOOR_Y, "z": 5, "face": 1, "dimensionId": 0, "blockName": STONE,
            "itemDict": dict(MAT_ITEM), "ret": False}
    Registry.dispatch("ServerItemUseOnEvent", args, STONE)
    placed = len(BLOCK_CALLS)
    again = dict(args, ret=False, itemDict=dict(MAT_ITEM))
    Registry.dispatch("ServerItemUseOnEvent", again, STONE)     # 还在 0.2 秒冷却里（按住右键每刻重发）
    assert len(BLOCK_CALLS) == placed and again["ret"] is True


def testTheHeadItemPlacesAWholeMatToo():
    # 创造模式中键点头方块拿到的是头方块的物品：当整张长垫子用，不会放出单独一个头
    _setUp(hand={"newItemName": "arris:tatami_full_mat_head", "newAuxValue": 0, "count": 1})
    _use()
    assert world.blockName(5, 64, 5) == Mat.FOOT and world.blockName(5, 64, 6) == Mat.HEAD


def testClickingTallGrassPlacesTheFootIntoIt():
    _setUp(yaw=0.0)
    world.setBlock(5, 64, 5, "minecraft:tall_grass")
    _use(blockPos=(5, 64, 5), face=1)
    assert world.blockName(5, 64, 5) == Mat.FOOT and world.blockName(5, 64, 6) == Mat.HEAD


# ---- 短垫子 ----

def testHalfMatNeedsGroundUnderItsCell():
    _setUp(hand=HALF_ITEM)
    world.setBlock(5, 64, 5, STONE)
    world.blocks.pop((0, 5, FLOOR_Y, 6))                        # 南边那一格下面是空气
    args, handled = _use(blockPos=(5, 64, 5), face=3)           # 点侧面放到南边悬空的格子
    assert args["ret"] is True and handled is False             # 取消放置，但不拦着别的处理函数
    args, _ = _use(blockPos=(5, FLOOR_Y, 8), face=1)            # 放在地面上：引擎照常放
    assert args["ret"] is False


# ---- 一起拆 ----

def testRemovingTheHeadSilentlyRemovesTheFoot():
    foot, head = _placed()
    world.setBlock(head[0], head[1], head[2], "minecraft:air")  # 玩家拆了头（掉落由引擎按头的战利品表给）
    _neighborEvent(Mat.FOOT, foot, head, "minecraft:air")
    assert BLOCK_CALLS == [("set", foot, "minecraft:air", 0, (False, False))]      # 不掉落、不通知邻居
    assert world.blockName(*foot) == "minecraft:air"


def testRemovingTheFootSilentlyRemovesTheHead():
    foot, head = _placed(direction=3, foot=(5, 64, 5))
    world.setBlock(foot[0], foot[1], foot[2], "minecraft:air")
    _neighborEvent(Mat.HEAD, head, foot, "minecraft:air")
    assert BLOCK_CALLS == [("set", head, "minecraft:air", 0, (False, False))]


def testPlacingTheHeadDoesNotBreakTheFoot():
    foot, head = _placed()
    _neighborEvent(Mat.FOOT, foot, head, Mat.HEAD)              # 头刚放上来
    _neighborEvent(Mat.HEAD, head, foot, Mat.FOOT)
    assert not BLOCK_CALLS


def testUnrelatedNeighborChangesAreIgnored():
    foot, head = _placed()
    _neighborEvent(Mat.FOOT, foot, (foot[0] + 1, foot[1], foot[2]), "minecraft:air")      # 不是头那一侧
    _neighborEvent(Mat.FOOT, foot, (foot[0], foot[1] + 1, foot[2]), STONE)                # 上面放了方块
    _neighborEvent(Mat.FOOT, foot, (foot[0], foot[1] - 1, foot[2]), STONE)                # 脚下换了个方块
    assert not BLOCK_CALLS


def testStaleEventForABlockThatIsAlreadyGoneDoesNothing():
    foot, head = _placed()
    world.setBlock(foot[0], foot[1], foot[2], "minecraft:air")
    world.setBlock(head[0], head[1], head[2], "minecraft:air")
    _neighborEvent(Mat.FOOT, foot, head, "minecraft:air")
    _neighborEvent(Mat.FOOT, foot, (foot[0], foot[1] - 1, foot[2]), "minecraft:air")
    assert not BLOCK_CALLS


# ---- 脚下没了方块 ----

def testLosingTheGroundBreaksTheMatAndDropsOnlyOne():
    foot, head = _placed()
    below = (foot[0], foot[1] - 1, foot[2])
    _neighborEvent(Mat.FOOT, foot, below, "minecraft:air")
    # 先让另一半静默消失，再把这一半打碎掉落（处理方式 1 = 销毁并掉落）：整张垫子只掉一个
    assert BLOCK_CALLS == [("set", head, "minecraft:air", 0, (False, False)), ("set", foot, "minecraft:air", 1, ())]


def testBothHalvesLosingTheGroundStillDropsOnlyOne():
    foot, head = _placed()
    _neighborEvent(Mat.FOOT, foot, (foot[0], foot[1] - 1, foot[2]), "minecraft:air")
    _neighborEvent(Mat.HEAD, head, (head[0], head[1] - 1, head[2]), "minecraft:air")      # 迟到的事件：头已经被清掉了
    assert [call[3] for call in BLOCK_CALLS] == [0, 1]


def testHalfMatBreaksWhenTheGroundGoesAway():
    world.setBlock(5, 64, 5, Mat.HALF, states={"direction": 0})
    del BLOCK_CALLS[:]
    _neighborEvent(Mat.HALF, (5, 64, 5), (5, 63, 5), "minecraft:air")
    assert BLOCK_CALLS == [("set", (5, 64, 5), "minecraft:air", 1, ())]
    del BLOCK_CALLS[:]
    world.setBlock(5, 64, 5, Mat.HALF, states={"direction": 0})
    _neighborEvent(Mat.HALF, (5, 64, 5), (5, 63, 5), STONE)       # 换成别的方块不碎
    _neighborEvent(Mat.HALF, (5, 64, 5), (6, 64, 5), "minecraft:air")
    assert not BLOCK_CALLS


def testServerModuleIsLoadedByTheEntryPoint():
    # 处理函数是导入即登记的：ModServer 不导入它，游戏里这些处理就不存在
    with io.open(os.path.join(fdtest.BP, fdtest.SCRIPTS, "Server", "ModServer.py"), encoding="utf-8") as f:
        assert "from . import TatamiMats" in f.read()


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
