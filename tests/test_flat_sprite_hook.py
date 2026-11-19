# -*- coding: utf-8 -*-
# runner: both
"""四个站点（厨锅、砧板、煎锅、炉灶）回答前置包的 flatSprite 钩子（Compat/Diegesis/FlatSprites.py）：手上拿着的方块物品里，引擎画成一张平面图的
（花、野生作物——Shared/Data/FlatBlockItems，砧板画板上的东西用的同一张表）说是，别的方块物品（原木、石头、蘑菇丛）、不是方块的东西说不是；
老版本的前置包没有 FLAT_SPRITES：表现类不挂这个钩子，和从前一样。前置包内核和这里各带一份 raisedShift（两个包互不依赖），公式一致。
"""
from __future__ import print_function

import prereq  # noqa: F401 - 前置包不在这个仓库里：旁边没有它就跳过（tests/prereq.py）
import dgtest
import boardclient as C  # noqa: F401 - 装好假的 QuModLibs、让 HoD 算联动（站点的登记要它）
import fdtest

FlatSprites = fdtest.load("Compat.Diegesis.FlatSprites")
FlatBlockItems = fdtest.load("Shared.Data.FlatBlockItems").FlatBlockItems
ItemPose = fdtest.load("Shared.Rules.ItemPose")
PropMath = dgtest.load("Client.PropMath")
Protocol = dgtest.load("Shared.Protocol")

VIEWS = ("PotView", "BoardView", "PanView", "GrillView")
POPPY, WILD, CARROT, LOG, COLONY = "minecraft:poppy", "arris:wild_carrots", "arris:carrot", "minecraft:oak_log", "arris:red_mushroom_colony"


class Base(object):
    def __init__(self, view):
        self.view = view


class Api(object):
    """前置包客户端 Api 里四个站点登记时用得到的那几样；flat 说这一版认不认 FLAT_SPRITES。"""
    API_VERSION = 3
    FACING_HOOK = True
    StationBehavior = Base
    Schema = dgtest.load("Shared.Schema")

    def __init__(self, flat, shown=False):
        self.registered = []
        if flat:
            self.FLAT_SPRITES = True
        if shown:
            self.SHOWN_AS = True                   # 这一版还认"手上的东西画成另一件物品"（Protocol.SHOWN_AS）

    def registerBehavior(self, *args, **kwargs):
        self.registered.append((args, kwargs))


def classes(flat):
    """四个站点的表现类（登记了才有）。"""
    api = Api(flat)
    made = {}
    for name in VIEWS:
        made[name] = fdtest.load("Compat.Diegesis." + name).register(api)
    return made, api


def item(name):
    return {"newItemName": name, "newAuxValue": 0, "count": 1}


def testTheAnswerIsTheBoardsTableOfFlatBlockItems():
    for name in sorted(FlatBlockItems):
        assert FlatSprites.flatSprite(None, item(name)) is True, name
    for name in (POPPY, WILD, "minecraft:dandelion", "arris:wild_rice"):
        assert name in FlatBlockItems and FlatSprites.flatSprite(None, item(name)) is True
    for name in (CARROT, LOG, COLONY, "minecraft:stone", "minecraft:bowl"):
        assert FlatSprites.flatSprite(None, item(name)) is False, "%s 不是平面图的方块物品：蘑菇丛的掉落物是缩小的立体小蘑菇" % name
    assert FlatSprites.shownAs(None, dict(item(COLONY), count=2)) == {"newItemName": COLONY + "_look", "newAuxValue": 0, "count": 2}, "蘑菇丛：手上画成它那件平面物品"
    assert FlatSprites.shownAs(None, item(POPPY)) is None and FlatSprites.shownAs(None, item(CARROT)) is None and FlatSprites.shownAs(None, None) is None, "别的不换"
    assert FlatSprites.flatSprite(None, None) is False and FlatSprites.flatSprite(None, {}) is False


def testTheHookIsOnlyGivenToAFrontDoorThatKnowsTheFlag():
    base = {"api": 1}
    assert FlatSprites.attrs(Api(False), base) is base and "flatSprite" not in base, "老版本：属性原样，不挂钩子"
    with_hook = FlatSprites.attrs(Api(True), base)
    assert with_hook is not base and with_hook["flatSprite"] is FlatSprites.flatSprite and with_hook["api"] == 1 and "flatSprite" not in base
    assert Protocol.FLAT_SPRITES is True, "前置包这一版认它（Protocol.FLAT_SPRITES）"
    both = FlatSprites.attrs(Api(True, True), base)
    assert both["shownAs"] is FlatSprites.shownAs and both["flatSprite"] is FlatSprites.flatSprite and "shownAs" not in with_hook, "认 SHOWN_AS 的前置包才挂换物品的钩子"
    assert Protocol.SHOWN_AS is True


def testAllFourStationsAnswerTheHookOnANewFrontDoor():
    made, api = classes(True)
    assert set(made) == set(VIEWS) and all(made.values()), "四个站点都登记上了：%r" % made
    for name, cls in made.items():
        assert "flatSprite" in cls.__dict__, "%s：钩子挂在表现类自己身上（不是前置包的基类）" % name
        hook = cls.__dict__["flatSprite"]                  # 站点的构造要真的视图；钩子只看物品，直接拿函数问（Py2 的未绑定方法会查第一个参数的类型）
        assert hook(None, item(POPPY)) is True and hook(None, item(WILD)) is True, name
        assert hook(None, item(LOG)) is False and hook(None, item(COLONY)) is False and hook(None, item(CARROT)) is False, name


def testAnOlderFrontDoorWithoutTheFlagGetsStationsThatBehaveAsToday():
    made, api = classes(False)
    assert all(made.values())
    for name, cls in made.items():
        assert not hasattr(cls, "flatSprite"), "%s：老版本的前置包不会问，也就不挂" % name


def testTheKernelAndTheStationsCarryTheSameRaisedShiftFormula():
    """两个包互不依赖、各带一份：内核手上的东西（PropMath）和站点的（ItemPose）的抬高公式一致。"""
    identity = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
    lying = [[1.0, 0.0, 0.0], [0.0, 0.0, -1.0], [0.0, 1.0, 0.0]]
    tilted = [[0.8, -0.6, 0.0], [0.5, 0.4, -0.76], [0.45, 0.65, 0.6]]
    for matrix in (identity, lying, tilted):
        for scale in (0.5, 1.0, 1.25, 2.0):
            assert PropMath.raisedShift(matrix, scale) == ItemPose.raisedShift(matrix, scale), (matrix, scale)
    assert PropMath.RAISED_PIVOT == ItemPose.RAISED_PIVOT and PropMath.BLOCK_LIFT == ItemPose.BLOCK_LIFT


def main():
    return fdtest.run(globals())


if __name__ == "__main__":
    raise SystemExit(main())
