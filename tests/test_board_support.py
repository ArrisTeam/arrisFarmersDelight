# -*- coding: utf-8 -*-
# runner: both
"""经典砧板下面撑不撑得住（Shared/Rules/BoardSupport.py、Server/CuttingBoard.py 的 OnTryPlaceCuttingBoard / OnCuttingBoardNeighborChanged，假引擎驱动）。

JE 的 CuttingBoardBlock（java:121-135）：canSurvive = canSupportRigidBlock(下面) || canSupportCenter(下面, UP)。BlockItem.canPlace 先问它，不满足就放不下；
updateShape 在下面（facing == DOWN）变了、不满足时返回空气，Block.updateOrDestroy 走 destroyBlock(pos, 掉落)：掉板自己，onRemove 再把板上的东西从方块里散落。
这边只认引擎说得准的两样：下面是空气、下面是液体（其余方块的形状引擎没有查询，见 BoardSupport 的说明），其余照旧当撑得住。
"""
from __future__ import print_function

import fakeengine
import fdtest
import skilletkit

world = fakeengine.install()
skilletkit.extend(world)
Rules = fdtest.load("Shared.Rules.BoardSupport")
Registry = fdtest.load("Server.EventRegistry")
Board = fdtest.load("Server.CuttingBoard")

POS = (7, 64, 7)
BELOW = (POS[0], POS[1] - 1, POS[2])
LIQUIDS = ("minecraft:water", "minecraft:flowing_water", "minecraft:lava", "minecraft:flowing_lava")
DESTROYED = []                   # [(位置, 方块名, oldBlockHandling)]：SetBlockNew 的调用


def _install():
    base = world._BlockInfo

    def _BlockInfo(target):
        methods = dict(base(target))
        setBlock = methods["SetBlockNew"]

        def recording(pos, blockDict, handling=0, *rest):
            DESTROYED.append((tuple(pos), blockDict["name"], handling))
            return setBlock(pos, blockDict, handling, *rest)

        methods["SetBlockNew"] = recording
        return methods

    world._BlockInfo = _BlockInfo


_install()


def _stand(below):
    """一块砧板在 POS，下面是 below（None 是空气）。"""
    world.reset()
    del DESTROYED[:]
    world.setBlock(POS[0], POS[1], POS[2], "arris:cutting_board")
    if below is not None:
        world.setBlock(BELOW[0], BELOW[1], BELOW[2], below)


def _placing(below):
    """玩家要把砧板放在 POS：下面是 below，走注册表的 ServerEntityTryPlaceBlockEvent；返回事件的参数（看 cancel）。"""
    world.reset()
    args = {"entityId": "p1", "dimensionId": 0, "x": POS[0], "y": POS[1], "z": POS[2], "fullName": "arris:cutting_board", "face": 1, "cancel": False}
    if below is not None:
        world.setBlock(BELOW[0], BELOW[1], BELOW[2], below)
    Registry.dispatch("ServerEntityTryPlaceBlockEvent", args, "arris:cutting_board")
    return args


def _neighbor(to, pos=BELOW):
    """pos 那一格变成了 to：给砧板的邻居变化事件。"""
    args = {"dimensionId": 0, "posX": POS[0], "posY": POS[1], "posZ": POS[2], "blockName": "arris:cutting_board", "auxValue": 0,
            "neighborPosX": pos[0], "neighborPosY": pos[1], "neighborPosZ": pos[2], "fromBlockName": "minecraft:stone", "fromBlockAuxValue": 0,
            "toBlockName": to, "toAuxValue": 0}
    Registry.dispatch("BlockNeighborChangedServerEvent", args, "arris:cutting_board")


# ---------------------------------------------------------------- 纯规则

def testOnlyAirAndLiquidsCannotCarryABoardAndWhatIsNotLoadedIsNotJudged():
    assert Rules.survives("minecraft:air") is False
    assert all(Rules.survives(name) is False for name in LIQUIDS)
    assert all(Rules.survives(name) for name in ("minecraft:stone", "minecraft:grass", "minecraft:oak_planks", "arris:stove", "arris:oak_cabinet", "minecraft:glass"))
    assert Rules.survives(None) is True, "下面没加载：不判，不拿一格还没读到的方块拆板"


# ---------------------------------------------------------------- 放

def testABoardCannotBePlacedWithNothingOrAFluidBelow():
    """贴着墙的侧面放（下面是空气）、放在水 / 岩浆上面：放不下，手里的东西不动。"""
    for below in [None] + list(LIQUIDS) + ["minecraft:air"]:
        assert _placing(below)["cancel"] is True, below


def testABoardCanBePlacedOnAnyBlock():
    for below in ("minecraft:stone", "minecraft:grass", "arris:stove", "minecraft:oak_planks", "minecraft:glass"):
        assert _placing(below)["cancel"] is False, below


def testABoardIsLeftAloneWhenTheCellBelowIsNotLoadedYet():
    world.reset()
    base = world._BlockInfo

    def _BlockInfo(target):
        methods = dict(base(target))
        methods["GetBlockNew"] = lambda pos, dim=0: None
        return methods

    world._BlockInfo = _BlockInfo
    try:
        args = {"entityId": "p1", "dimensionId": 0, "x": POS[0], "y": POS[1], "z": POS[2], "fullName": "arris:cutting_board", "face": 1, "cancel": False}
        Registry.dispatch("ServerEntityTryPlaceBlockEvent", args, "arris:cutting_board")
        assert args["cancel"] is False
    finally:
        world._BlockInfo = base


# ---------------------------------------------------------------- 掉

def testABoardIsTornDownLikeAMinedOneWhenTheBlockBelowBecomesAirOrALiquid():
    """像被挖掉一样拆（oldBlockHandling 1 = 销毁：掉板自己，BlockRemoveServerEvent 里板上的东西散落）。"""
    for to in ("minecraft:air",) + LIQUIDS:
        _stand("minecraft:stone")
        _neighbor(to)
        assert DESTROYED == [(POS, "minecraft:air", 1)], (to, DESTROYED)
        assert world.blockName(*POS) == "minecraft:air", to


def testABoardStaysWhenTheBlockBelowBecomesAnotherSolidBlockOrSomethingElseChanges():
    for to in ("minecraft:stone", "minecraft:oak_planks", "arris:stove"):
        _stand("minecraft:dirt")
        _neighbor(to)
        assert DESTROYED == [] and world.blockName(*POS) == "arris:cutting_board", to
    for side in ((POS[0] + 1, POS[1], POS[2]), (POS[0], POS[1] + 1, POS[2]), (POS[0], POS[1] - 2, POS[2])):
        _stand("minecraft:dirt")
        _neighbor("minecraft:air", side)
        assert DESTROYED == [], "只有正下面那一格变了才拆：%r" % (side,)


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
