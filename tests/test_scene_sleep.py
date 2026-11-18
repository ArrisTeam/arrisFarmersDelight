# -*- coding: utf-8 -*-
# runner: both
"""煎锅和厨锅的场景歇着、没变的道具不碰引擎（Compat/Diegesis 的 PanScene / PotScene / PotProps，假引擎数引擎调用）

32 格内每口加载着的锅，每个渲染帧都过一遍 frame。静着的锅（食物躺着不动、凉的、没人开站点）要歇着：掉落物原样留在世界里，
一帧只做一次便宜的核对，一次引擎也不碰；叫得醒（广播、一次性的表现、方块实体重建、模型上的值丢了、开站点……）；
不歇的（烧着、熟好的食物在鼓、开着站点、手在演）照旧每帧演，摆出来的样子一点没变，只是没变的道具不再每帧调 SetDropItemTransform。
"""
from __future__ import print_function

import math

import copy

import panclient as C
import potclient as P

world = C.install()
PanScenes = C.load("Compat.Diegesis.PanScenes")
PotScenes = C.load("Compat.Diegesis.PotScenes")
BlockItems = C.load("Client.BlockItems")
BrothColors = C.load("Shared.Data.BrothColors")
ItemPose = C.load("Shared.Rules.ItemPose")
PanPose = C.load("Shared.Rules.PanPose")
POS = C.POS
DT = 1.0 / 60.0
CHECK = "GetBlockEntityMolangValue"         # 场景每 0.5 秒读回一个模型变量，核对方块实体有没有重建：歇着时唯一还碰引擎的一件事


def run(scene, seconds, near=True):
    for _ in range(int(round(seconds / DT))):
        scene.frame(DT, near)


def engineCalls(scene, seconds, near=True):
    """跑 seconds 秒（每帧一次），返回这期间每个引擎接口被调了几次。"""
    world.counts.clear()
    run(scene, seconds, near)
    return dict(world.counts)


def onlyTheCheck(calls, seconds):
    """歇着的锅这段时间只做了核对（每 0.5 秒一次，差一次是帧数取整）。"""
    assert set(calls) <= set([CHECK]), calls
    assert abs(calls.get(CHECK, 0) - seconds / 0.5) <= 1, calls


def snapshot():
    return copy.deepcopy(world.drops)


# ---------------------------------------------------------------- 煎锅

def panSetup():
    world.reset()
    PanScenes._scenes.clear()
    PanScenes.enable()
    BlockItems._hidden.clear()
    return PanScenes.ensure(0, POS)


def panLook(name="minecraft:beef", count=2, **changes):
    data = {"dimensionId": 0, "pos": list(POS), "item": {"newItemName": name, "newAuxValue": 0, "count": count} if name else {},
            "batch": count if name else 0, "byHand": True, "heated": False, "down": 0.0, "up": 0.0, "rate": 0.0, "both": False}
    data.update(changes)
    return data


def sleepingPan(**changes):
    """凉锅里躺着两块生肉、什么也没发生：落完、歇着。"""
    scene = panSetup()
    PanScenes.OnPanLook(panLook(**changes))
    run(scene, 6.0)
    assert scene.frame(DT) is False and not scene.busy(), "歇着了"
    return scene


def testAColdPanWithFoodLyingStillSleepsKeepsTheFoodAndDoesNotTouchTheEngine():
    scene = sleepingPan()
    assert len(world.drops) == 2, "歇着不是把食物收起来"
    before = snapshot()
    onlyTheCheck(engineCalls(scene, 5.0), 5.0)
    assert world.drops == before, "食物原样留在原来摆的地方"
    assert world.deleted == []


def testAnEmptyColdPanSleepsToo():
    scene = panSetup()
    PanScenes.OnPanLook(panLook(name=None))
    run(scene, 6.0)
    assert scene.frame(DT) is False
    onlyTheCheck(engineCalls(scene, 3.0), 3.0)


def testAHotPanWithFoodLyingStillKeepsItsParticlesButSendsNoTransforms():
    """等着翻面的锅：烟、油星、滋滋声每帧都在攒，所以不歇；食物躺着不动，一个掉落物也不重摆。"""
    scene = panSetup()
    PanScenes.OnPanLook(panLook(heated=True, down=1.0, up=0.0))
    run(scene, 4.0)
    assert scene.frame(DT) is True and scene.busy()
    del world.particles[:]
    calls = engineCalls(scene, 3.0)
    assert not calls.get("SetDropItemTransform"), calls
    assert not calls.get("DeleteClientDropItemEntity") and not calls.get("AddDropItemToWorld"), calls
    assert world.particles, "烟和油星照放"
    assert len(world.drops) == 2


def testFinishedFoodKeepsPulsingInAColdPanAndOnlyItsSizeChanges():
    """熟好的食物一直鼓着、闪着、冒汽（HoD 的 readyGlow），凉锅也一样：不歇；每块每帧只有缩放在变。"""
    scene = panSetup()
    PanScenes.OnPanLook(panLook(name="minecraft:cooked_beef", down=1.0, up=1.0))
    run(scene, 8.0)
    assert scene.frame(DT) is True and scene.show.heat.glows()
    first = sorted(world.drops)[0]
    positions = world.drops[first]["pivot"]
    scales = set()
    world.counts.clear()
    for _ in range(80):                                     # 一鼓 1.3 秒，80 帧一整拍
        scene.frame(DT, False)
        scales.add(world.drops[first]["scale"])
    calls = dict(world.counts)
    assert calls.get("SetDropItemTransform") == 2 * 80, "两块，每帧各调一次：鼓着，缩放每帧都变：%r" % (calls,)
    assert max(scales) / min(scales) > 1.045 and max(scales) / min(scales) < 1.0501, "READY_SWELL 0.05：%r" % (sorted(scales)[::20],)
    assert all(abs(a - b) < 0.02 for a, b in zip(world.drops[first]["pivot"], positions)), "位置没挪，只是鼓大缩小"


def testTheSameColdPanSleepsWithRawFoodAndPulsesWithFinishedFood():
    """歇着判的是"还有什么在随时间变"，不是"锅里有没有东西"：同一口锅，生肉躺着歇着，换成熟肉（鼓着）就不歇。"""
    scene = sleepingPan()
    PanScenes.OnPanLook(panLook(name="minecraft:cooked_beef", down=1.0, up=1.0))
    assert scene.frame(DT) is True, "广播一来就醒"
    run(scene, 8.0)
    assert scene.frame(DT) is True, "熟肉在鼓：不歇"
    PanScenes.OnPanLook(panLook(name="minecraft:beef"))
    run(scene, 6.0)
    assert scene.frame(DT) is False, "换回生肉：鼓的收了，歇"
    assert abs(world.drops[sorted(world.drops)[0]]["scale"] - 7.5 / 8.0) < 1e-9, "收了鼓：食物回到原来的大小"


def testABroadcastWakesASleepingPanAndTheNewFoodIsDrawn():
    scene = sleepingPan()
    PanScenes.OnPanLook(panLook(count=3))
    assert scene.frame(DT) is True
    run(scene, 0.5)
    assert len(world.drops) == 3, "三块"
    run(scene, 6.0)
    assert scene.frame(DT) is False


def testAnEventWakesASleepingPan():
    scene = sleepingPan()
    before = snapshot()
    PanScenes.OnPanLook({"dimensionId": 0, "pos": list(POS), "event": "tossed", "strength": 1.0})
    assert scene.frame(DT) is True
    moved = 0
    for _ in range(30):
        scene.frame(DT)
        moved += world.drops != before
    assert moved, "颠了：食物飞起来"
    run(scene, 6.0)
    assert scene.frame(DT) is False
    assert max(abs(a - b) for key in before for a, b in zip(centerOf(world.drops[key]), centerOf(before[key]))) < 0.02, "落回来了：每块的中心回到原处"
    # 翻了一回：贴图在自己的平面里倒了过来，底边上的轴心在对面那一边（场景接着上一帧的姿态画，翻到顶点换向时轴心不跳，ItemPose.steadied）
    assert all(max(abs(a - b) for a, b in zip(world.drops[key]["pivot"], before[key]["pivot"])) > 0.2 for key in before)


def testHeatWakesASleepingPan():
    scene = sleepingPan()
    del world.particles[:]
    PanScenes.OnPanLook(panLook(heated=True, down=0.5, rate=0.2))
    assert scene.frame(DT) is True
    run(scene, 2.0)
    assert world.particles and scene.busy(), "热了：热浪、油星"
    PanScenes.OnPanLook(panLook(heated=False))
    run(scene, 7.0)
    assert scene.frame(DT) is False, "又凉了：油收干、歇"
    assert world.molang[(POS, "variable.mod_oil_a")] == 0.0


def testOpeningTheStationWakesASleepingPanAndTheHandleGlowsUnderTheCursor():
    scene = sleepingPan()
    scene.show.focused = True                              # PanView.onOpen 只改这一个字段
    assert scene.frame(DT) is True, "开站点：不歇"
    scene.hovered = True
    run(scene, 0.05)
    assert world.molang[(POS, "variable.mod_handle_lit")] == 1.0
    scene.show.close()
    scene.show.focused = scene.hovered = False
    run(scene, 6.0)
    assert scene.frame(DT) is False and world.molang[(POS, "variable.mod_handle_lit")] == 0.0


def testARebuiltBlockEntityWakesASleepingPanAndEverythingIsPushedAgain():
    scene = sleepingPan()
    world.molang.clear()                                   # 方块实体在本端重建：引擎那边的变量全丢了，没有事件
    awake = [scene.frame(DT) for _ in range(40)]           # 0.67 秒：核对在 0.5 秒时发现
    assert world.molang[(POS, "variable.mod_scene")] == 1.0, "整份重推"
    assert any(awake), "发现了就醒、推完再歇"
    run(scene, 6.0)
    assert scene.frame(DT) is False
    world.molang.clear()
    scene.rebuilt()                                        # 加载事件来了（区块重载）
    assert scene.frame(DT) is True and world.molang[(POS, "variable.mod_scene")] == 1.0


def testAPanEmptiedWhileAsleepGivesItsFoodBack():
    scene = sleepingPan()
    PanScenes.OnPanLook(panLook(name=None))
    run(scene, 1.0)
    assert not world.drops, "锅空了：掉落物收了"
    run(scene, 6.0)
    assert scene.frame(DT) is False


def testWhatTheEngineRefusesIsSentAgainNextFrame():
    """引擎没收下（返回假）就不能当"和引擎里一样"：下一帧再来，和原来每帧都调时一样。"""
    scene = panSetup()
    comp, real, refused = C.Comp, C.Comp.SetDropItemTransform, [True]

    def maybe(self, entityId, pivot, euler, scale):
        if refused:
            return False
        return real(self, entityId, pivot, euler, scale)

    comp.SetDropItemTransform = maybe
    try:
        PanScenes.OnPanLook(panLook(count=1))
        run(scene, 0.5)
        assert all(drop["pivot"] is None for drop in world.drops.values()), "引擎一直没收下"
        del refused[:]
        run(scene, 0.1)
    finally:
        comp.SetDropItemTransform = real
    assert all(drop["pivot"] is not None for drop in world.drops.values()), "收得下了：摆好"


def centerOf(drop):
    """掉落物的视觉中心：轴心 + 贴图的"上"方向 * 半边长（R = Rz·Rx·Ry，第二列是 (-sin z cos x, cos z cos x, sin x)）。"""
    x, y, z = [math.radians(angle) for angle in drop["euler"]]
    half = 8.0 / 16.0 * drop["scale"] * 0.5
    up = (-math.sin(z) * math.cos(x), math.cos(z) * math.cos(x), math.sin(x))
    return tuple(drop["pivot"][axis] + up[axis] * half for axis in range(3))


def referencePose(scene, name, node, turned=False):
    """原来每帧都这么算（不缓存）：节点此刻的样子 -> SetDropItemTransform 的三个参数。turned：贴图在自己的平面里转了半圈的那个姿态
    （占同一块地方，轴心在对面那一边）——翻过奇数次的那一块画的是它（ItemPose.steadied）。"""
    pan = scene.show.nodes["pan"]
    center, matrix = scene._placed(name, pan.pos, pan.rot, node)
    world_ = PanPose.toWorld(scene.facing, matrix)
    if turned:
        world_ = [[-row[0], -row[1], row[2]] for row in world_]
    scale = max(0.01, node.size * node.scale / ItemPose.ITEM_SPAN)
    return ItemPose.pivotFor(scene.world(center), world_, scale), ItemPose.engineEuler(world_), scale


def testTheCachedPoseIsTheSameNumbersTheOldPerFrameMathGave():
    """颠一下、再落下、再鼓着：每一帧、每一块掉落物在引擎里的位置转角缩放，和不缓存时现算的一模一样——
    翻到顶点之前是节点的姿态原样，之后是贴图在自己平面里转了半圈的那个（轴心不跳），一块只换这一回。"""
    scene = panSetup()
    PanScenes.OnPanLook(panLook(name="minecraft:cooked_beef", count=5, down=1.0, up=1.0))
    run(scene, 1.0)
    scene.event("tossed", {"strength": 0.7})
    turned = {}
    for _ in range(90):
        scene.frame(DT, False)
        for name, prop in scene.props.items():
            drop = world.drops[prop.entityId]
            got = (drop["pivot"], drop["euler"], drop["scale"])
            plain, other = [(tuple(pose[0]), tuple(pose[1]), pose[2]) for pose in (referencePose(scene, name, scene.show.nodes[name]),
                                                                                   referencePose(scene, name, scene.show.nodes[name], True))]
            assert got in (plain, other), name
            if got != plain:
                turned[name] = True
            assert got == (other if turned.get(name) else plain), "%s：换过去之后一直是那一个，不来回跳" % name
    assert len(scene.props) == 5 and len(turned) == 5, "五块都翻了一回"


# ---------------------------------------------------------------- 厨锅

ITEMS = [("minecraft:carrot", 1), ("minecraft:potato", 2), ("minecraft:beef", 1), ("minecraft:egg", 1), ("minecraft:bowl", 1), ("minecraft:apple", 3)]


def potSetup():
    P.reset()
    PotScenes._scenes.clear()
    PotScenes.enable(BrothColors.BrothColors.get)
    return PotScenes.ensure(0, POS)


def sleepingPot(**changes):
    scene = potSetup()
    scene.apply(P.look(ITEMS, **changes))
    run(scene, 8.0)
    assert scene.frame(DT) is False and not scene.busy(), "歇着了"
    return scene


def testAColdPotSleepsWithItsFloatingItemsStillInThePotAndDoesNotTouchTheEngine():
    scene = sleepingPot()
    assert len(world.drops) == 6
    before = snapshot()
    onlyTheCheck(engineCalls(scene, 5.0), 5.0)
    assert world.drops == before and world.deleted == []


def testABroadcastAnEventAHandAndAnotherSpoonWakeASleepingPot():
    scene = sleepingPot()
    scene.apply(P.look(ITEMS[:5], heated=False))
    assert scene.frame(DT) is True, "广播来了"
    run(scene, 8.0)
    assert scene.frame(DT) is False
    scene.event("scooped", {})
    assert scene.frame(DT) is True, "一次性的表现来了"
    run(scene, 8.0)
    assert scene.frame(DT) is False
    scene.hand = True
    assert scene.frame(DT) is True, "本人拿着勺子"
    scene.hand = False
    run(scene, 8.0)
    assert scene.frame(DT) is False
    scene.lift.target = 0
    assert scene.frame(DT) is True, "光标指着一件料"
    scene.lift.target = None
    run(scene, 8.0)
    assert scene.frame(DT) is False


def testHeatAndStirringAndCookingProgressKeepAPotAwake():
    for changes in ({"heated": True}, {"stirring": True}, {"rate": 0.05}):
        scene = sleepingPot()
        scene.apply(P.look(ITEMS, **changes))
        run(scene, 8.0)
        assert scene.frame(DT) is True, changes
        scene.apply(P.look(ITEMS))
        run(scene, 8.0)
        assert scene.frame(DT) is False, changes


def testARebuiltBlockEntityWakesASleepingPotAndEverythingIsPushedAgain():
    scene = sleepingPot()
    world.molang.clear()
    world.uniforms.clear()
    awake = [scene.frame(DT) for _ in range(40)]
    assert world.molang[(POS, "variable.mod_open")] == 1.0 and world.uniforms, "整份重推（盖子、液面、着色器的数）"
    assert any(awake)
    run(scene, 8.0)
    assert scene.frame(DT) is False
    world.molang.clear()
    scene.rebuilt()
    assert scene.frame(DT) is True and world.molang[(POS, "variable.mod_open")] == 1.0


class SlowHand(object):
    """一只演得很久的手（倒一大批、磕好几个蛋排着队）：不出姿态、不出事件，过了 12 秒才算演完。"""

    def __init__(self):
        self.age = 0.0

    @property
    def done(self):
        return self.age >= 12.0

    def step(self, dt, surface):
        self.age += dt
        return {}, []


def testAHandStillAtWorkKeepsAColdPotAwakeUntilItIsDone():
    """原来凉锅只靠"最后一次广播后 4 秒"，手演得比这久（排队的蛋、一次放好几件）就中途歇了，手和手里的东西停在半空。"""
    scene = sleepingPot()
    scene.apply(P.look(ITEMS[:5], heated=False))
    scene.hands.going[1] = {"motion": SlowHand(), "kind": "cracked", "name": "minecraft:egg", "props": {}, "rings": 0.0, "slot": 1,
                            "frame": scene.hands._frame()}
    run(scene, 10.0)
    assert scene.frame(DT) is True and 1 in scene.hands.going, "10 秒了，手还没演完：锅不歇"
    run(scene, 3.0)
    assert scene.hands.going == {}, "演完了"
    run(scene, 6.0)
    assert scene.frame(DT) is False, "手走了，锅歇"


def settledHeatedPot(items, **changes):
    scene = potSetup()
    scene.apply(P.look(items, heated=True, **changes))
    run(scene, 20.0)                                       # 水位、汤色都追到头了，剩下的只有料自己的起伏
    return scene


def testAHeatedPotKeepsAnimatingItsFloatingItemsEveryFrame():
    """烧着的锅里漂着的料：圈着转、起伏、摇晃，每帧都变，每帧每件都照旧送给引擎（姿态一点没变）。"""
    scene = settledHeatedPot(ITEMS)
    calls = engineCalls(scene, 2.0)
    assert calls["SetDropItemTransform"] == 6 * 120, calls
    assert scene.frame(DT) is True


def testTheServedDishOfAHeatedPotIsNotSentToTheEngineAgainEveryFrame():
    """装好的那碗菜浮在锅心，液面落定之后什么都不变：烧着的锅不歇（沸腾的气泡、蒸汽、水波），但它不再每帧调一次 SetDropItemTransform。"""
    scene = settledHeatedPot([], served=P.item("arris:pumpkin_soup"), meal=P.item("arris:pumpkin_soup", 3))
    assert scene.props[6] is not None and world.drops[scene.props[6][0]]["pivot"] is not None, "碗菜摆出来了"
    before = snapshot()
    calls = engineCalls(scene, 3.0)
    assert not calls.get("SetDropItemTransform"), calls
    assert scene.frame(DT) is True and world.drops == before


def testPlacingAPropTwiceTheSameWayTouchesTheEngineOnceAndRemovingForgetsIt():
    scene = potSetup()
    item = {"newItemName": "minecraft:carrot", "newAuxValue": 0, "count": 1}
    entityId = C.Comp(None).AddDropItemToWorld(item, 0, POS)
    world.counts.clear()
    scene.placeProp(entityId, 8.0, 5.0, 8.0, 10.0, 2.0, 3.0)
    scene.placeProp(entityId, 8.0, 5.0, 8.0, 10.0, 2.0, 3.0)
    assert world.counts["SetDropItemTransform"] == 1, "一模一样：只送一次"
    scene.placeProp(entityId, 8.0, 5.0, 8.0, 10.0, 2.0, 3.0, 1.5)
    assert world.counts["SetDropItemTransform"] == 2, "大小变了：再送"
    pivot = world.drops[entityId]["pivot"]
    scene.removeProp(entityId)
    assert entityId not in world.drops and entityId not in scene.drops.posed, "删了的不留记录"
    again = C.Comp(None).AddDropItemToWorld(item, 0, POS)
    scene.placeProp(again, 8.0, 5.0, 8.0, 10.0, 2.0, 3.0, 1.5)
    assert world.counts["SetDropItemTransform"] == 3 and world.drops[again]["pivot"] == pivot, "新的掉落物照样摆"


def testAnItemThatIsSwappedForAnotherInTheSameSlotIsPosedAfresh():
    scene = settledHeatedPot([("minecraft:carrot", 1)])
    old = scene.props[0][0]
    scene.apply(P.look([("minecraft:potato", 1)], heated=True))
    run(scene, 0.2)
    new = scene.props[0][0]
    assert new != old and old in world.deleted and old not in world.drops
    assert world.drops[new]["item"]["newItemName"] == "minecraft:potato" and world.drops[new]["pivot"] is not None


def testWhatTheEngineRefusesInAPotIsSentAgainNextFrame():
    scene = potSetup()
    comp, real, refused = C.Comp, C.Comp.SetDropItemTransform, [True]

    def maybe(self, entityId, pivot, euler, scale):
        return False if refused else real(self, entityId, pivot, euler, scale)

    comp.SetDropItemTransform = maybe
    try:
        scene.apply(P.look([("minecraft:carrot", 1)]))
        run(scene, 0.3)
        assert all(drop["pivot"] is None for drop in world.drops.values())
        del refused[:]
        run(scene, 0.1)
    finally:
        comp.SetDropItemTransform = real
    assert all(drop["pivot"] is not None for drop in world.drops.values())


def testTheSpoonThatRestsInAHeatedPotIsNotRecomputedEveryFrame():
    """烧着的锅每帧都过一遍 frame，勺子靠着不动时骨骼的位移和欧拉角（要连乘矩阵）每帧都一样：不重算，也不碰引擎；动起来照常算；方块实体重建之后整份重推。"""
    PotModelMath = C.load("Shared.Rules.PotModelMath")
    ladleBone = PotModelMath.ladleBone
    counted = [0]

    def counting(tip, turn=None):
        counted[0] += 1
        return ladleBone(tip, turn) if turn is not None else ladleBone(tip)

    PotModelMath.ladleBone = counting
    try:
        scene = settledHeatedPot([("minecraft:carrot", 1)])
        counted[0] = 0
        run(scene, 2.0)
        assert counted[0] == 0, "靠着不动：一次也没算（%d）" % counted[0]
        world.molang.clear()                                                # 方块实体在本端重建
        scene.model.reset()
        run(scene, 0.1)
        assert counted[0] == 1 and (POS, "variable.mod_spoon_rz") in world.molang, "整份重推：重算一次、变量回来（%d）" % counted[0]
        counted[0] = 0
        scene.hand, scene.aim = True, (9.0, 9.0)
        run(scene, 0.5)
        assert counted[0] > 10, "勺子在动：每帧照算（%d）" % counted[0]
    finally:
        PotModelMath.ladleBone = ladleBone


def testASpoonPoseTheEngineDidNotTakeIsPushedAgainNextFrame():
    scene = settledHeatedPot([("minecraft:carrot", 1)])
    comp, real, refuse = C.Comp, C.Comp.SetBlockEntityMolangValue, [True]

    def maybe(self, pos, name, value):
        return False if refuse and name == "variable.mod_spoon_rz" else real(self, pos, name, value)

    scene.model.reset()
    world.molang.clear()
    comp.SetBlockEntityMolangValue = maybe
    try:
        run(scene, 0.2)
        assert (POS, "variable.mod_spoon_rz") not in world.molang and (POS, "variable.mod_spoon_x") in world.molang, "有一个没收下，别的都推上了"
        del refuse[:]
        run(scene, 0.1)
    finally:
        comp.SetBlockEntityMolangValue = real
    assert (POS, "variable.mod_spoon_rz") in world.molang, "收得下了：靠着不动也补上了"


if __name__ == "__main__":
    raise SystemExit(C.fdtest.run(globals()))
