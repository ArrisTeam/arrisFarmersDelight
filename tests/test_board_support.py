# -*- coding: utf-8 -*-
# runner: both
"""经典砧板下面撑不撑得住（Shared/Rules/BoardSupport.py、Server/CuttingBoard.py 的 OnTryPlaceCuttingBoard / OnCuttingBoardNeighborChanged，假引擎驱动）。

JE 的 CuttingBoardBlock（java:121-135）：canSurvive = canSupportRigidBlock(下面) || canSupportCenter(下面, UP)。BlockItem.canPlace 先问它，不满足就放不下；
updateShape 在下面（facing == DOWN）变了、不满足时返回空气，Block.updateOrDestroy 走 destroyBlock(pos, 掉落)：掉板自己，onRemove 再把板上的东西从方块里散落。
两个条件看的都是下面那格贴着顶面的那一片盖没盖住正中 2x2 像素（原版 SupportType）：这边拿引擎的 GetBlockCollision（2026-11-18 实机量过它对各种方块回什么，
假引擎照样回）判，包围盒说不准的按名字另说（见 BoardSupport 的说明）；没查到碰撞盒时只认空气和液体。
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


# 实机量到的碰撞盒（相对这一格；None 是六个数全 0）
BOXES = {"minecraft:smooth_stone_slab": (0.0, 0.0, 0.0, 1.0, 0.5, 1.0), "t:top_slab": (0.0, 0.5, 0.0, 1.0, 1.0, 1.0), "minecraft:white_carpet": (0.0, 0.0, 0.0, 1.0, 0.0625, 1.0),
         "minecraft:farmland": (0.0, 0.0, 0.0, 1.0, 0.9375, 1.0), "minecraft:chest": (0.025, 0.0, 0.025, 0.975, 0.95, 0.975), "minecraft:enchanting_table": (0.0, 0.0, 0.0, 1.0, 0.75, 1.0),
         "minecraft:oak_fence": (0.375, 0.0, 0.375, 0.625, 1.5, 0.625), "minecraft:cobblestone_wall": (0.25, 0.0, 0.25, 0.75, 1.5, 0.75),
         "minecraft:glass_pane": (0.4375, 0.0, 0.4375, 0.5625, 1.0, 0.5625), "minecraft:anvil": (0.125, 0.0, 0.0, 0.875, 1.0, 1.0), "minecraft:lantern": (0.3125, 0.0, 0.3125, 0.6875, 0.5, 0.6875),
         "t:trapdoor_top": (0.0, 0.8175, 0.0, 1.0, 1.0, 1.0), "t:trapdoor_bottom": (0.0, 0.0, 0.0, 1.0, 0.1825, 1.0), "arris:cutting_board": (0.063, 0.0, 0.063, 0.938, 0.062, 0.938),
         "minecraft:soul_sand": (0.0, 0.0, 0.0, 1.0, 0.875, 1.0), "minecraft:mud": (0.0, 0.0, 0.0, 1.0, 0.875, 1.0), "minecraft:snow_layer": (0.0, 0.0, 0.0, 1.0, 0.875, 1.0),
         "minecraft:honey_block": (0.0625, 0.0, 0.0625, 0.9375, 1.0, 0.9375), "minecraft:cactus": (0.0625, 0.0, 0.0625, 0.9375, 1.0, 0.9375),
         "minecraft:short_grass": None, "minecraft:poppy": None, "minecraft:torch": None, "minecraft:scaffolding": None, "t:side_post": (0.0, 0.0, 0.0, 0.25, 1.0, 0.25)}
world.collisions.update(BOXES)
HOLDS = ("minecraft:stone", "minecraft:glass", "arris:stove", "t:top_slab", "minecraft:oak_fence", "minecraft:cobblestone_wall", "minecraft:glass_pane", "minecraft:anvil",
         "t:trapdoor_top", "minecraft:soul_sand", "minecraft:mud", "minecraft:scaffolding")
FALLS = ("minecraft:smooth_stone_slab", "minecraft:white_carpet", "minecraft:farmland", "minecraft:chest", "minecraft:enchanting_table", "minecraft:lantern", "t:trapdoor_bottom",
         "arris:cutting_board", "minecraft:honey_block", "minecraft:cactus", "minecraft:short_grass", "minecraft:poppy", "minecraft:torch", "t:side_post",
         "minecraft:oak_leaves", "minecraft:azalea_leaves_flowered")


def _stand(below, aux=0):
    """一块砧板在 POS，下面是 below（None 是空气）。"""
    world.reset()
    del DESTROYED[:]
    world.setBlock(POS[0], POS[1], POS[2], "arris:cutting_board")
    if below is not None:
        world.setBlock(BELOW[0], BELOW[1], BELOW[2], below, aux=aux)


def _placing(below, aux=0):
    """玩家要把砧板放在 POS：下面是 below，走注册表的 ServerEntityTryPlaceBlockEvent；返回事件的参数（看 cancel）。"""
    world.reset()
    args = {"entityId": "p1", "dimensionId": 0, "x": POS[0], "y": POS[1], "z": POS[2], "fullName": "arris:cutting_board", "face": 1, "cancel": False}
    if below is not None:
        world.setBlock(BELOW[0], BELOW[1], BELOW[2], below, aux=aux)
    Registry.dispatch("ServerEntityTryPlaceBlockEvent", args, "arris:cutting_board")
    return args


def _neighbor(to, pos=BELOW, aux=0, settled=True):
    """pos 那一格变成了 to：给砧板的邻居变化事件。settled：世界里那一格已经换过去了（假的话事件先到、世界里还是旧的）。"""
    if settled and pos == BELOW:
        world.setBlock(pos[0], pos[1], pos[2], to, aux=aux)
    args = {"dimensionId": 0, "posX": POS[0], "posY": POS[1], "posZ": POS[2], "blockName": "arris:cutting_board", "auxValue": 0,
            "neighborPosX": pos[0], "neighborPosY": pos[1], "neighborPosZ": pos[2], "fromBlockName": "minecraft:stone", "fromBlockAuxValue": 0,
            "toBlockName": to, "toAuxValue": aux}
    Registry.dispatch("BlockNeighborChangedServerEvent", args, "arris:cutting_board")


# ---------------------------------------------------------------- 纯规则

def testOnlyAirAndLiquidsCannotCarryABoardAndWhatIsNotLoadedIsNotJudged():
    assert Rules.survives("minecraft:air") is False
    assert all(Rules.survives(name) is False for name in LIQUIDS)
    assert all(Rules.survives(name) for name in ("minecraft:stone", "minecraft:grass", "minecraft:oak_planks", "arris:stove", "arris:oak_cabinet", "minecraft:glass"))
    assert Rules.survives(None) is True, "下面没加载：不判，不拿一格还没读到的方块拆板"
    assert Rules.survives("minecraft:white_carpet") is True, "没查到碰撞盒：只认空气和液体（判错了会让板放不下或到处掉）"


def testTheCollisionBoxTheEngineGivesIsTakenRelativeToTheBlock():
    assert Rules.boxOf({"min": [-144.0, 70.0, 12.0], "max": [-143.0, 70.5, 13.0]}, (-144, 70, 12)) == (0.0, 0.0, 0.0, 1.0, 0.5, 1.0)
    assert Rules.boxOf({"min": [0.0, 0.0, 0.0], "max": [0.0, 0.0, 0.0]}, (5, 6, 7)) == Rules.EMPTY, "没有碰撞盒：六个数全是 0"
    assert Rules.boxOf({"min": (0.0, 0.0, 0.0), "max": (1.0, 1.0, 1.0)}, (0, 0, 0)) == (0.0, 0.0, 0.0, 1.0, 1.0, 1.0), "世界原点上的整格不是没有碰撞盒"
    assert Rules.boxOf(None, (0, 0, 0)) is None and Rules.boxOf({"min": [1.0]}, (0, 0, 0)) is None and Rules.boxOf("x", (0, 0, 0)) is None


def testTheTopOfTheBlockBelowHasToCoverTheMiddleTwoPixels():
    # SupportType.CENTER：贴着顶面（y = 1）的那一片盖住正中 2x2 像素（7/16 ~ 9/16）
    full = (0.0, 0.0, 0.0, 1.0, 1.0, 1.0)
    assert Rules.survives("t:block", 0, full) is True
    assert Rules.survives("t:block", 0, Rules.EMPTY) is False, "没有碰撞盒（花草、火把）"
    assert Rules.survives("t:block", 0, (0.0, 0.0, 0.0, 1.0, 0.9375, 1.0)) is False, "顶不到 y = 1（耕地 15/16）"
    assert Rules.survives("t:block", 0, (0.0, 0.5, 0.0, 1.0, 1.0, 1.0)) is True, "上半砖"
    assert Rules.survives("t:block", 0, (0.4375, 0.0, 0.4375, 0.5625, 1.0, 0.5625)) is True, "正中 2 像素的柱子（玻璃板）正好盖住"
    assert Rules.survives("t:block", 0, (0.45, 0.0, 0.4375, 0.5625, 1.0, 0.5625)) is False, "差一点没盖住"
    assert Rules.survives("t:block", 0, (0.375, 0.0, 0.375, 0.625, 1.5, 0.625)) is True, "高出一格的柱子（栅栏 1.5）：看 y = 1 那一片"
    assert Rules.survives("t:block", 0, (0.0, 0.0, 0.0, 0.25, 1.0, 0.25)) is False, "顶到了，但在角上"
    assert Rules.survives("t:block", 0, (0.0, 1.0, 0.0, 1.0, 1.5, 1.0)) is False, "整个在这一格上面（不会有，防着）"


def testWhatTheBoxCannotTellGoesByName():
    low = (0.0, 0.0, 0.0, 1.0, 0.875, 1.0)
    assert all(Rules.survives(name, 0, low) for name in ("minecraft:soul_sand", "minecraft:mud")), "陷 2 像素，Java 的支撑形状是整格"
    assert Rules.survives("minecraft:scaffolding", 0, Rules.EMPTY) is True, "没有碰撞盒，Java 顶上是一整块板"
    assert Rules.survives("minecraft:snow_layer", 7, low) is True and Rules.survives("minecraft:snow_layer", 15, low) is True, "八层雪（aux 低三位 7）"
    assert Rules.survives("minecraft:snow_layer", 3, (0.0, 0.0, 0.0, 1.0, 0.375, 1.0)) is False and Rules.survives("minecraft:snow_layer", 0, Rules.EMPTY) is False
    full = (0.0, 0.0, 0.0, 1.0, 1.0, 1.0)
    assert all(Rules.survives(name, 0, full) is False for name in ("minecraft:oak_leaves", "minecraft:leaves2", "minecraft:azalea_leaves_flowered")), "树叶：Java 的支撑形状是空的"
    assert all(Rules.survives(name, 0, (0.0625, 0.0, 0.0625, 0.9375, 1.0, 0.9375)) is False for name in ("minecraft:honey_block", "minecraft:cactus")), "Java 只到 15/16"
    assert Rules.survives("minecraft:oak_stairs", 0, full) is False and Rules.survives("minecraft:oak_stairs", 3, full) is False, "正着放的楼梯：顶面只有一半"
    assert Rules.survives("minecraft:oak_stairs", 4, full) is True and Rules.survives("minecraft:stone_brick_stairs", 7, full) is True, "倒着放的：顶面是整块"
    assert Rules.survives("other:fancy_stairs", 0, full) is True, "别的模组的楼梯不知道 aux 怎么排：按碰撞盒"


# ---------------------------------------------------------------- 放

def testABoardCannotBePlacedWithNothingOrAFluidBelow():
    """贴着墙的侧面放（下面是空气）、放在水 / 岩浆上面：放不下，手里的东西不动。"""
    for below in [None] + list(LIQUIDS) + ["minecraft:air"]:
        assert _placing(below)["cancel"] is True, below


def testABoardCanBePlacedOnWhatCarriesItsMiddle():
    for below in ("minecraft:stone", "minecraft:grass", "arris:stove", "minecraft:oak_planks", "minecraft:glass") + HOLDS:
        assert _placing(below)["cancel"] is False, below
    assert _placing("minecraft:snow_layer", aux=7)["cancel"] is False and _placing("minecraft:oak_stairs", aux=4)["cancel"] is False


def testABoardCannotBePlacedOnWhatDoesNotReachItsMiddle():
    """地毯、下半砖、耕地、箱子、花草、火把、另一块砧板、树叶、正着放的楼梯：JE 里都放不下。"""
    for below in FALLS:
        assert _placing(below)["cancel"] is True, below
    assert _placing("minecraft:snow_layer", aux=3)["cancel"] is True and _placing("minecraft:oak_stairs", aux=1)["cancel"] is True


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


def testABoardIsTornDownWhenTheBlockBelowBecomesSomethingThatDoesNotCarryIt():
    for to in ("minecraft:white_carpet", "minecraft:smooth_stone_slab", "minecraft:farmland", "minecraft:torch", "minecraft:oak_leaves"):
        _stand("minecraft:stone")
        _neighbor(to)
        assert DESTROYED == [(POS, "minecraft:air", 1)], (to, DESTROYED)
    _stand("minecraft:stone")
    _neighbor("minecraft:white_carpet", settled=False)
    assert DESTROYED == [], "事件先到、世界里那一格还是石头：碰撞盒问不准，只按名字判（地毯不在名单里）"
    _stand("minecraft:stone")
    _neighbor("minecraft:air", settled=False)
    assert DESTROYED == [(POS, "minecraft:air", 1)], "空气按名字就知道"


def testABoardStaysWhenTheBlockBelowBecomesAnotherSolidBlockOrSomethingElseChanges():
    for to in ("minecraft:stone", "minecraft:oak_planks", "arris:stove", "t:top_slab", "minecraft:soul_sand"):
        _stand("minecraft:dirt")
        _neighbor(to)
        assert DESTROYED == [] and world.blockName(*POS) == "arris:cutting_board", to
    for side in ((POS[0] + 1, POS[1], POS[2]), (POS[0], POS[1] + 1, POS[2]), (POS[0], POS[1] - 2, POS[2])):
        _stand("minecraft:dirt")
        _neighbor("minecraft:air", side)
        assert DESTROYED == [], "只有正下面那一格变了才拆：%r" % (side,)


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
