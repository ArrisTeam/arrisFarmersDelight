# -*- coding: utf-8 -*-
# runner: both
"""砧板站点里放液体层、蛋层的那只手（Compat/Diegesis/BoardHandDraw + BoardDraw + BoardDrawEvents + BoardThing，假引擎见 boardclient.py）：
液体层不是落下来的，是一只手端着容器过来倒、倒完容器走了、这一层什么也不画；蛋层是手端着蛋在板沿磕、到食物上方打开、蛋液落下，落稳了这一层才露出来（打开的蛋）；
开站时就在板上的这样的层不演、只有最后的样子；书里点的菜里的这样的层从玩家那边来；同一时刻只有一只手。对应 HoD 的 BoardBehavior.arrives / dress / arrive（1583-2042）。
"""
from __future__ import print_function

import dgtest  # noqa: F401 - 把 diegesisBp 放进 sys.path（boardclient 要它的 Geometry / Schema）
import boardclient as C
import fdtest

Hands = fdtest.load("Shared.Rules.HandsOn.BoardHands")
Motion = fdtest.load("Shared.Rules.HandsOn.BoardMotion")
Scene = fdtest.load("Shared.Rules.HandsOn.BoardScene")
Sounds = fdtest.load("Shared.Rules.BoardSounds")
Remainders = fdtest.load("Shared.Data.Remainders")
SAME = type("Changes", (), {"hasSlot": lambda self, ref: False})()
CHANGED = type("Changes", (), {"hasSlot": lambda self, ref: True})()
BREAD, WHEAT, SUGAR, BUCKET, BOTTLE, EGG = "minecraft:bread", "minecraft:wheat", "minecraft:sugar", "minecraft:milk_bucket", "arris:milk_bottle", "minecraft:egg"
EGG_LOOK = Hands.EGG_LOOK
DROPLET, DUST = "arris_diegesis:droplet", "arris:board_dust"


def _open(board=None, layers=(), data=None):
    behavior, view, api = C.station()
    view.state.board, view.state.layers = board, list(layers)
    view.data, view.hand = dict(data or {}), None
    behavior.onOpen()
    C.engine.played[:] = []
    C.engine.particles[:] = []
    return behavior, view


def _frames(behavior, seconds, dt=1.0 / 60.0):
    for _ in range(int(round(seconds / dt))):
        behavior.frame(dt)


def _lay(behavior, view, layers):
    view.state.layers = list(layers)
    behavior.onState(SAME)


def _named(view, name):
    return [prop for prop in view.props.live() if prop.item["newItemName"] == name]


def _near(a, b, eps=1.0e-6):
    return len(a) == len(b) and all(abs(x - y) < eps for x, y in zip(a, b))


def _home(index):
    pose = Scene.layerPose(index)
    return (pose["x"], pose["y"], pose["z"])


def _particles(identifier):
    return [p for p in C.engine.particles if p["id"] == identifier]


def _counts(identifier):
    return [int(p["vars"]["variable.count"]) for p in _particles(identifier)]


def _hand(behavior):
    return behavior.draw.hand


# ---------------------------------------------------------------- 倒

def testALiquidLayerIsPouredByAHandAndNothingIsLeftInTheDish():
    behavior, view = _open(layers=[C.item(BREAD)])
    draw = behavior.draw
    _lay(behavior, view, [C.item(BREAD), C.item(BUCKET)])
    held = _named(view, BUCKET)
    assert len(held) == 1 and not held[0].flat and held[0].matrix is not None, "手里的桶：立着、仰着、在贴图平面里倾"
    height = Hands.handHeight(1, Hands.POUR)
    home = _home(1)
    assert _near(held[0].center, (draw.cx + home[0], height + 2.0, draw.cz + home[2])), "没有光标：从落点正上方 2 像素的地方来（handFrom）"
    assert abs(held[0].scale - Hands.POUR_SIZE / 8.0 * 0.5) < 1.0e-9, "从手里来，先小一半"
    assert draw.layers[1].prop is None and draw.layers[1].item is None, "这一层本身不画"
    _frames(behavior, 0.3)
    middle = _hand(behavior).motion.middle
    assert _near(held[0].center, middle, 0.01) and abs(held[0].scale - 5.0 / 8.0) < 0.01, "0.3 秒到位、长到原大"
    assert C.engine.played == [], "还没倒：液体开始流（0.5 秒）才出声"
    _frames(behavior, 0.22)
    assert C.engine.played == [Sounds.POUR_BUCKET], "液体开始流：倒桶的声音一次"
    assert _counts(DROPLET), "从瓶口朝落点撒染了色的水滴"
    first = _particles(DROPLET)[0]["vars"]
    assert (first["variable.tint_r"], first["variable.tint_g"], first["variable.tint_b"]) == (1.0, 1.0, 1.0), "奶是白的"
    assert first["variable.speed_set"] == 1.0 and first["variable.vy"] < 0.0, "有初速、往下落"


def testTheContainerIsEmptiedAndTakenAwayAndTheLayerStaysEmpty():
    behavior, view = _open(layers=[C.item(BREAD)])
    _lay(behavior, view, [C.item(BREAD), C.item(BUCKET)])
    _frames(behavior, 1.4)
    assert not _named(view, BUCKET) and len(_named(view, "minecraft:bucket")) == 1, "倒空了换成空桶"
    assert _counts(DROPLET)[-2:] != [], "倒空那一刻瓶口再落两滴"
    assert 2 in _counts(DROPLET)
    _frames(behavior, 0.6)
    assert [prop.item["newItemName"] for prop in view.props.live()] == [BREAD], "端走之后板上只有面包：这一层什么也不画"
    assert behavior.draw.layers[1].prop is None and _hand(behavior).motion is None
    assert len(C.engine.played) == 1, "倒的过程只响一次"


def testEveryLiquidPoursFromItsOwnContainerAtItsOwnPace():
    for name in sorted(Hands.POURED):
        behavior, view = _open(layers=[C.item(BREAD)])
        _lay(behavior, view, [C.item(BREAD), C.item(name)])
        assert len(_named(view, name)) == 1, name
        _frames(behavior, 0.55)
        assert C.engine.played == [Sounds.POUR_BUCKET if Hands.isBucket(name) else Sounds.POUR_BOTTLE], name
        _frames(behavior, 0.9)
        assert len(_named(view, Remainders.craftRemainderOf(name))) == 1 and not _named(view, name), "%s 倒空了留下 %s" % (name, Remainders.craftRemainderOf(name))
        color = Hands.liquidColor(name)
        tint = _particles(DROPLET)[0]["vars"]
        assert [round(tint["variable.tint_%s" % c] * 255) for c in "rgb"] == [(color >> 16) & 255, (color >> 8) & 255, color & 255], "水滴是 %s 的颜色" % name
        _frames(behavior, 0.6)
        assert not _hand(behavior).props and _hand(behavior).motion is None, name


def testALiquidAtTheBottomIsAnOrdinaryIconThatLandsLikeAnythingElse():
    behavior, view = _open()
    _lay(behavior, view, [C.item(BUCKET)])
    assert _hand(behavior).motion is None, "第 0 层是底座：不倒"
    assert len(_named(view, BUCKET)) == 1 and _named(view, BUCKET)[0].flat
    _frames(behavior, 0.6)
    assert _near(_named(view, BUCKET)[0].center[::2], (behavior.draw.cx + _home(0)[0], behavior.draw.cz + _home(0)[2]), 1.0e-6)


# ---------------------------------------------------------------- 磕

def testAnEggIsKnockedOnTheBoardBesideTheFoodOpenedAndLandsOnIt():
    behavior, view = _open(layers=[C.item(BREAD)])
    draw = behavior.draw
    _lay(behavior, view, [C.item(BREAD), C.item(EGG)])
    egg = _named(view, EGG)
    assert len(egg) == 1 and not egg[0].flat and draw.layers[1].prop is None, "手里的蛋；这一层先不露出来"
    assert abs(egg[0].scale - Hands.EGG_SIZE / 8.0 * 0.5) < 1.0e-9
    _frames(behavior, 0.37)
    assert C.engine.played == [Sounds.EGG_KNOCK], "磕在板沿上：脆响"
    assert _counts(DUST) == [5], "碎壳 5 颗"
    shell = _particles(DUST)[0]["vars"]
    assert [round(shell["variable.tint_%s" % c] * 255) for c in "rgb"] == [0xEA, 0xD9, 0xB8], "壳的颜色"
    assert shell["variable.vy"] > 0.0, "往上溅"
    _frames(behavior, 0.25)
    assert _counts(DUST) == [5, 4], "壳裂开：再 4 颗"
    inside = _hand(behavior).props.get("inside")
    assert inside is not None and inside[0].flat and inside[0].item["newItemName"] == EGG_LOOK, "蛋液：平躺的打开的蛋"
    assert draw.layers[1].prop is None, "还没落稳"
    _frames(behavior, 0.2)
    assert draw.layers[1].prop is None and C.engine.played == [Sounds.EGG_KNOCK]
    _frames(behavior, 0.15)
    assert C.engine.played == [Sounds.EGG_KNOCK, Sounds.EGG_LANDED], "落到食物上：这一层露出来，响一声落定"
    layer = draw.layers[1].prop
    home = _home(1)
    assert layer is not None and layer.flat and layer.item["newItemName"] == EGG_LOOK, "这一层画成打开的蛋"
    assert _near(layer.center, (draw.cx + home[0], Scene.TOP + home[1] + Scene.FLAT_LIFT, draw.cz + home[2])), "躺在自己的位置上"
    assert not _hand(behavior).props and _hand(behavior).motion is None and not _named(view, EGG), "手和蛋液都收了，板上没有蛋壳也没有鸡蛋"
    assert len(_named(view, EGG_LOOK)) == 1


def testTheEggIsKnockedAtTheRightOfTheFoodWhereTheHandPutsItFirst():
    behavior, view = _open(layers=[C.item(BREAD)])
    draw = behavior.draw
    _lay(behavior, view, [C.item(BREAD), C.item(EGG)])
    knock = _hand(behavior).motion.rim
    assert abs(knock[0] - (draw.cx - Hands.KNOCK_ASIDE)) < 1.0e-9 and abs(knock[2] - (draw.cz + _home(1)[2])) < 1.0e-9, "板沿：食物屏幕右侧 5.5 像素（x 减）"
    _frames(behavior, 0.37)
    station = view.toStation(*_particles(DUST)[0]["pos"])               # 粒子位置是世界坐标：换算成站点坐标核对
    assert _near(station, (draw.cx - Hands.KNOCK_ASIDE, Scene.TOP, draw.cz + _home(1)[2]), 0.01), "碎壳从磕的地方溅出来"


# ---------------------------------------------------------------- 开站时已经在板上的

def testOpeningTheStationWithSuchLayersAlreadyThereShowsOnlyTheFinalLook():
    behavior, view = _open(layers=[C.item(BREAD), C.item(EGG), C.item(BUCKET), C.item(SUGAR)])
    assert _hand(behavior).motion is None and not C.engine.played and not C.engine.particles, "不演：没有手、没有声音、没有粒子"
    names = sorted(prop.item["newItemName"] for prop in view.props.live())
    assert names == sorted([BREAD, EGG_LOOK, SUGAR]), "面包、打开的蛋、糖；奶桶那一层什么也不画"
    assert behavior.draw.layers[2].prop is None


def testLaterStateChangesThatAddNoNewLayerPlayNoHandEither():
    behavior, view = _open(layers=[C.item(BREAD), C.item(EGG), C.item(BUCKET)])
    _lay(behavior, view, [C.item(BREAD), C.item(EGG), C.item(BUCKET), C.item(SUGAR)])
    assert _hand(behavior).motion is None, "新来的是糖：从光标上方落下，手不动"
    _frames(behavior, 0.5)
    assert not C.engine.played and len(_named(view, EGG_LOOK)) == 1


# ---------------------------------------------------------------- 一只手

def testALaterHandTakesOverAndTheInterruptedEggShowsAtOnce():
    behavior, view = _open(layers=[C.item(BREAD)])
    draw = behavior.draw
    _lay(behavior, view, [C.item(BREAD), C.item(EGG)])
    _frames(behavior, 0.2)
    assert draw.layers[1].prop is None
    _lay(behavior, view, [C.item(BREAD), C.item(EGG), C.item(BUCKET)])
    assert draw.layers[1].prop is not None and draw.layers[1].prop.item["newItemName"] == EGG_LOOK, "被打断的蛋这一层马上露出来"
    assert _hand(behavior).kind == Hands.POUR and len(_named(view, BUCKET)) == 1 and not _named(view, EGG), "手去倒桶了、蛋收了"
    assert C.engine.played == [], "被打断的不响落定"
    _frames(behavior, 2.0)
    assert Sounds.EGG_LANDED not in C.engine.played and Sounds.POUR_BUCKET in C.engine.played, "蛋没磕完就换了手：只有倒的声音"


def testTakingALayerWhileItsEggIsInTheAirDoesNotBringItBack():
    behavior, view = _open(layers=[C.item(BREAD)])
    draw = behavior.draw
    _lay(behavior, view, [C.item(BREAD), C.item(EGG)])
    _frames(behavior, 0.3)
    _lay(behavior, view, [C.item(BREAD)])
    _frames(behavior, 1.5)
    assert draw.layers[1].prop is None and not draw.layers[1].mover.visible, "取走了的蛋，手磕完它也不再露出来"
    assert Sounds.EGG_LANDED not in C.engine.played and not _hand(behavior).props


def testClosingTheStationInTheMiddleOfAPourDropsEveryProp():
    behavior, view = _open(layers=[C.item(BREAD)])
    _lay(behavior, view, [C.item(BREAD), C.item(BUCKET)])
    _frames(behavior, 0.7)
    assert _named(view, BUCKET)
    hand = _hand(behavior)
    behavior.onClose()
    assert not view.props.live() and hand.motion is None and not hand.props


def testTheHandStartsFromTheCursorWhenThereIsOne():
    behavior, view = _open(layers=[C.item(BREAD)])
    draw = behavior.draw
    height = Hands.handHeight(1, Hands.POUR)
    draw.cursor = C.rayTo((draw.cx + 3.0, height - 5.0, draw.cz - 4.0))
    _lay(behavior, view, [C.item(BREAD), C.item(BUCKET)])
    point = _named(view, BUCKET)[0].center
    assert abs(point[1] - height) < 1.0e-6, "光标落在手来的那一层平面上"
    ray = draw.cursor
    t = (height - ray[1]) / ray[4]
    assert _near(point, (ray[0] + ray[3] * t, height, ray[2] + ray[5] * t), 1.0e-6)


# ---------------------------------------------------------------- 书里点的菜、做成

def _book(behavior, view, made, finish="knead"):
    """书里点的菜：状态先到（层是空的、菜躺在板上），assembled 效果随后。"""
    view.state.board, view.state.layers = C.item("arris:wheat_dough", 1), []
    behavior.onState(CHANGED)
    behavior.onEffect("assembled", {"layers": made, "finish": finish, "block": False})


def testADishFromTheBookPoursItsLiquidFromThePlayerAndWaitsForItBeforeItMelts():
    behavior, view = _open()
    draw = behavior.draw
    made = [C.item(WHEAT), C.item(BUCKET), C.item(SUGAR)]
    _book(behavior, view, made)
    arrive = max(Hands.takes(0, WHEAT), 1 * Motion.LAYER_STAGGER + Hands.takes(1, BUCKET), 2 * Motion.LAYER_STAGGER + Hands.takes(2, SUGAR))
    assert abs(arrive - (Motion.LAYER_STAGGER + 1.3)) < 1.0e-9
    assert abs(draw.melting - (arrive + Motion.MELT_TIME + 0.05)) < 1.0e-9, "倒完才开始沉"
    assert not _named(view, BUCKET), "桶要等 0.16 秒才出发"
    _frames(behavior, 0.2)
    held = _named(view, BUCKET)
    assert len(held) == 1 and not held[0].flat, "手端着桶来了"
    assert draw.layers[1].prop is None, "这一层不画"
    _frames(behavior, arrive - 0.2 - 0.05)
    assert C.engine.played.count(Sounds.POUR_BUCKET) == 1
    assert Sounds.ASSEMBLED[0] not in C.engine.played, "做成的声音等液体倒完"
    _frames(behavior, 0.1)
    assert Sounds.ASSEMBLED[0] in C.engine.played, "倒完了：做成的声音"


def testTheHandInTheBookPathComesFromTheBottomOfTheScreen():
    behavior, view = _open()
    draw = behavior.draw
    _book(behavior, view, [C.item(WHEAT), C.item(BUCKET)])
    _frames(behavior, Motion.LAYER_STAGGER + 0.001)
    height = Hands.handHeight(1, Hands.POUR)
    off = draw.fromPlayer(height)
    home = _home(1)
    start = _hand(behavior).motion.start
    assert _near(start, (draw.cx + home[0] + off[0], height, draw.cz + home[2] + off[1])), "屏幕底边投到手来的那一层平面上的点、减去屏幕正中投到同一个面上的点（FromPlayer.offset）"


def testAnEggInTheBookPathIsKnockedAndTheLayerAppearsWhenItLands():
    behavior, view = _open()
    draw = behavior.draw
    _book(behavior, view, [C.item(WHEAT), C.item(EGG), C.item(SUGAR)])
    _frames(behavior, 0.16 + 0.9 - 0.05)
    assert draw.layers[1].prop is None and _hand(behavior).props.get("inside") is not None, "蛋液还在落"
    _frames(behavior, 0.1)
    assert draw.layers[1].prop is not None and Sounds.EGG_LANDED in C.engine.played, "落到了：这一层露出来"
    assert draw.melting > 0.0, "还没沉：要等 Crack.landsBy + 落定"


def testAPourStillRunningWhenTheDishIsMadeHoldsTheFinishBackUntilTheLiquidIsOut():
    behavior, view = _open(layers=[C.item(WHEAT)])
    draw = behavior.draw
    _lay(behavior, view, [C.item(WHEAT), C.item(BUCKET)])
    _frames(behavior, 0.2)
    assert _hand(behavior).remaining() > 1.0
    _book(behavior, view, [C.item(WHEAT), C.item(BUCKET)])
    left = 1.3 - 0.2
    assert draw.melting > left + Motion.MELT_TIME, "手还在倒：做成等它倒完（pourUntil）"
    assert draw.melting < left + Motion.MELT_TIME + 0.2
    _frames(behavior, left - 0.05)
    assert not C.engine.played.count(Sounds.ASSEMBLED[0]), "倒完之前不做成"


def testAnEggStillInTheHandWhenTheDishIsMadeIsNotShownBeforeItLands():
    behavior, view = _open(layers=[C.item(WHEAT)])
    draw = behavior.draw
    _lay(behavior, view, [C.item(WHEAT), C.item(EGG)])
    _frames(behavior, 0.2)
    _book(behavior, view, [C.item(WHEAT), C.item(EGG)])
    assert draw.layers[1].prop is None, "蛋还在手上：这一层等它落下才露出来"
    assert draw.melting > 0.7 + Motion.MELT_TIME, "要等蛋落下（0.9 秒）才开始沉"
    _frames(behavior, 0.75)
    assert draw.layers[1].prop is not None, "蛋落了露出来"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
