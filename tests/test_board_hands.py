# -*- coding: utf-8 -*-
# runner: both
"""砧板摆盘时液体层倒、蛋层磕的规则（Shared/Rules/HandsOn/BoardHands.py，手的动作本身是厨锅也用的 PotServePour / PotServeHands）：
哪些层走手、倒在哪、磕在哪、要多久、层最后画成什么，数照 Hands-On Delight 的 BoardBehavior（常量 148-157、dress 1963-1984、arrives 1986-2027、
arrive 1583-1617、pourUntil 250 / 1526）和 KitchenMotions（Pour 93-283、Crack 394-571）、KitchenLooks（isPoured / isCracked / opened 32-49）。
"""
from __future__ import print_function

import fdtest

Hands = fdtest.load("Shared.Rules.HandsOn.BoardHands")
Sounds = fdtest.load("Shared.Rules.BoardSounds")
Scene = fdtest.load("Shared.Rules.HandsOn.BoardScene")
Motion = fdtest.load("Shared.Rules.HandsOn.BoardMotion")
Maths = fdtest.load("Shared.Rules.HandsOn.PotServeMath")
PotPour = fdtest.load("Shared.Rules.HandsOn.PotServePour")
PotHands = fdtest.load("Shared.Rules.HandsOn.PotServeHands")
Assembly = fdtest.load("Shared.Rules.HandsOn.Assembly")
EggLook = fdtest.load("Shared.Rules.EggLook")
Remainders = fdtest.load("Shared.Data.Remainders")
Dishes = fdtest.load("Shared.Data.Dishes")
Colors = fdtest.load("Shared.Data.BrothColors")

CENTER = (6.5, 8.0)
START = (9.0, 12.0, 2.0)
DT = 0.01
BUCKET, BOTTLE, SAUCE, EGG = "minecraft:milk_bucket", "arris:milk_bottle", "arris:tomato_sauce", "minecraft:egg"


def item(name, count=1):
    return {"newItemName": name, "newAuxValue": 0, "count": count}


def run(motion, seconds, dt=DT):
    """推进 seconds 秒；返回 [(时刻, pose(s), events)]。"""
    out = []
    for index in range(int(round(seconds / dt))):
        posed, events = motion.step(dt)
        out.append((round((index + 1) * dt, 6), posed, events))
    return out


def eventsOf(timeline, kind):
    return [(at, event) for at, _posed, events in timeline for event in events if event["type"] == kind]


def close(a, b, eps=1.0e-9):
    return len(a) == len(b) and all(abs(x - y) < eps for x, y in zip(a, b))


# ---------------------------------------------------------------- 哪些层走手

def testThePouredAndCrackedListsAreTheOnesJEUses():
    """poured.json：奶桶 / 水桶 / 蜂蜜瓶 / FD 的奶瓶和番茄酱 / 龙息 / 岩浆桶（别的模组的不写）；cracked.json：蛋。"""
    assert Hands.POURED == frozenset(["minecraft:milk_bucket", "minecraft:water_bucket", "minecraft:honey_bottle", "arris:milk_bottle",
                                      "arris:tomato_sauce", "minecraft:dragon_breath", "minecraft:lava_bucket"])
    assert Hands.CRACKED == frozenset(["minecraft:egg", "minecraft:blue_egg", "minecraft:brown_egg"]), "基岩版的三种蛋一视同仁"
    assert not Hands.POURED & Hands.CRACKED


def testOnlyLayersAboveTheBaseAreEverPouredButAnEggIsCrackedAnywhere():
    """arrives：倒的要 index > 0（1993），磕蛋不看层号（2011）；别的东西照旧落下。"""
    for name in sorted(Hands.POURED):
        assert Hands.kindOf(0, name) is None, "第 0 层是底座，容器照旧画：%s" % name
        assert all(Hands.kindOf(index, name) == Hands.POUR for index in range(1, Assembly.MOST_LAYERS)), name
    assert all(Hands.kindOf(index, EGG) == Hands.CRACK for index in range(Assembly.MOST_LAYERS))
    for name in ("minecraft:bread", "minecraft:sugar", "arris:fried_egg", "minecraft:bucket", "minecraft:glass_bottle", "arris:egg_look_0", ""):
        assert [Hands.kindOf(index, name) for index in range(3)] == [None] * 3, name


def testTwelveDishesUseALiquidOrAnEggLayerAndEveryOneIsRecognised():
    """审计数过：用到倒的液体或磕的蛋的菜共 12 道（派皮、面团、牛奶 / 蜂蜜的土豆……）；配方里每一个这样的配料都认得出是倒还是磕。"""
    used = {}
    for dish in Dishes.DishList:
        for name, aux in dish["ingredients"]:
            if name in Hands.POURED or name in Hands.CRACKED:
                used.setdefault(dish["result"][0], set()).add(name)
    assert sorted(used) == sorted(["arris:chocolate_pie_item", "arris:gleaming_salad_block_stage0", "arris:honey_cookie",
                                   "arris:honey_glazed_ham_block_stage0", "arris:pie_crust", "arris:roast_chicken_block_stage0",
                                   "arris:shepherds_pie_block_stage0", "arris:stuffed_potato", "arris:sweet_berry_cheesecake_item",
                                   "arris:wheat_dough", "minecraft:cake", "minecraft:pumpkin_pie"])
    assert used["minecraft:cake"] == set([BOTTLE, "minecraft:milk_bucket", EGG]), "蛋糕：奶瓶 / 奶桶和蛋"
    assert used["arris:wheat_dough"] == set(["minecraft:water_bucket", EGG]), "面团：水桶（原样留下的）和蛋两种做法"
    assert used["arris:roast_chicken_block_stage0"] == set([EGG]) and used["minecraft:pumpkin_pie"] == set([EGG])


def testNoDishStartsWithALiquidOnItsBase():
    """配方里的底座（Assembly.baseOf）从不是倒的液体，所以第 0 层照旧画容器的情形只出现在不合法的摆法上。"""
    for dish in Dishes.DishList:
        names = [name for name, _aux in dish["ingredients"]]
        base, _kind = Assembly.baseOf(names)
        assert names[base] not in Hands.POURED, dish["source"]


# ---------------------------------------------------------------- 层最后画成什么

def testALiquidLayerDrawsNothingAndAnEggDrawsAsTheOpenedEggAndTheRestAsItself():
    assert Hands.lookOf(1, item(BUCKET)) is None and Hands.lookOf(5, item(SAUCE)) is None, "倒完容器走了，掉落物画不了淋面"
    bottom = item(BUCKET)
    assert Hands.lookOf(0, bottom) is bottom, "底座照旧画容器"
    egg = Hands.lookOf(3, item(EGG, 4))
    assert egg == {"newItemName": EggLook.itemOf(0.0), "newAuxValue": 0, "count": 4} and Hands.EGG_LOOK == "arris:egg_look_0", "打开的蛋 = 刚打进来的蛋清那一档"
    assert Hands.lookOf(0, item(EGG))["newItemName"] == Hands.EGG_LOOK, "蛋哪一层都画成打开的"
    bread = item("minecraft:bread", 2)
    assert Hands.lookOf(2, bread) is bread


def testTheContainerWhatIsPouredLeavesBehindAndTheColourOfWhatRunsOut():
    """JE：容器是物品的合成剩余物，桶才慢而粗；颜色取液体的（厨锅同一张 PouredColors）。"""
    expected = {"minecraft:milk_bucket": "minecraft:bucket", "minecraft:water_bucket": "minecraft:bucket", "minecraft:lava_bucket": "minecraft:bucket",
                "minecraft:honey_bottle": "minecraft:glass_bottle", "minecraft:dragon_breath": "minecraft:glass_bottle",
                "arris:milk_bottle": "minecraft:glass_bottle", "arris:tomato_sauce": "minecraft:bowl"}
    for name in sorted(Hands.POURED):
        assert Hands.containerOf(name) == expected[name] == Remainders.craftRemainderOf(name), name
        assert Hands.isBucket(name) == name.endswith("_bucket"), name
        color = Hands.liquidColor(name)
        assert color >> 24 == 0xFF and color & 0xFFFFFF == Colors.PouredColors[name], "%s 的液色在表里" % name
    assert Hands.liquidColor("x:unknown") == 0xFF000000 | Colors.FALLBACK, "表里没有的用缺省色"


# ---------------------------------------------------------------- 倒

def testTheHandPoursFromAboveTheLayerAndTheLipLandsOnIt():
    """arrives:1998-2001：落点是这一层的中心、比层底高 0.3，容器画 5 像素、往屏幕左边倾；倾倒到位时瓶口 + 满流的抛出距离正好落在落点上，瓶口在落点上方 3.2。"""
    assert (Hands.POUR_SIZE, Hands.POUR_HEIGHT, Hands.POUR_LIFT, Hands.POUR_SIDE) == (5.0, 4.0, 0.3, -1.0)
    for index in range(1, Assembly.MOST_LAYERS):
        pose = Scene.layerPose(index)
        for name in (BUCKET, BOTTLE, SAUCE):
            pour = Hands.pourFor(index, name, pose["x"], pose["z"], CENTER, START)
            top = Scene.TOP + index * Motion.LAYER_STEP + 0.3
            assert abs(pour.landY - top) < 1.0e-9 and pour.size == 5.0 and pour.side == -1.0 and pour.yaw == 0.0, (index, name)
            assert pour.bucket == (name == BUCKET) and pour.tilt == (-105.0 if name == BUCKET else -125.0)
            assert pour.color == Hands.liquidColor(name) and pour.liquid is None and pour.start == START
            lip = Maths.tipped(pour.side * Maths.LIP_X, Maths.LIP_Y, 5.0, pour.tilt, 0.0)
            away = Maths.rotateY((-pour.side * 1.3, 0.0, 0.0), 0.0)
            landing = (pour.middle[0] + lip[0] + away[0], pour.middle[1] + lip[1], pour.middle[2] + lip[2] + away[2])
            assert close(landing, (CENTER[0] + pose["x"], top + 3.2, CENTER[1] + pose["z"])), (index, name)


def testThePourTimelineIsTheSameAsAtThePotButTheSoundAndTheStreamLandOnTheLayer():
    pose = Scene.layerPose(3)
    top = Scene.TOP + 3 * Motion.LAYER_STEP + 0.3
    for name, flow, tilt in ((BUCKET, 0.8, 105.0), (BOTTLE, 0.55, 125.0)):
        pour = Hands.pourFor(3, name, pose["x"], pose["z"], CENTER, START)
        timeline = run(pour, 2.0)
        sound = eventsOf(timeline, "sound")
        assert len(sound) == 1 and abs(sound[0][0] - Hands.flowAt()) < 0.0101 and Hands.flowAt() == 0.5, "液体开始流（0.3 + 0.2 秒）才出声"
        assert Sounds.handSound(sound[0][1]) == (Sounds.POUR_BUCKET if name == BUCKET else Sounds.POUR_BOTTLE)
        streams = [event for _at, event in eventsOf(timeline, "stream")]
        assert len(streams) in (int(flow / DT) - 1, int(flow / DT), int(flow / DT) + 1), "流 %s 秒、每帧一条" % flow
        assert all(abs(stream["to"][1] - top) < 1.0e-9 and stream["to"][0] > stream["from"][0] for stream in streams), "落在这一层的面上、从瓶口朝屏幕左边（+x）落"
        assert all(stream["color"] == Hands.liquidColor(name) and stream["liquid"] is None for stream in streams)
        drops = eventsOf(timeline, "droplets")
        assert len(drops) == 1 and drops[0][1]["count"] == 2 and drops[0][1]["rise"] == (0.0, -6.0, 0.0) and drops[0][1]["spread"] == 0.05
        assert drops[0][1]["color"] == Hands.liquidColor(name) and abs(drops[0][0] - Hands.pouredBy(name)) < 0.0101, "倒空那一刻两滴水滴"
        done = [at for at, posed, _events in timeline if not posed["visible"]][0]
        assert abs(done - pour.duration) < 0.0101 and abs(pour.duration - (Hands.pouredBy(name) + 0.5)) < 1.0e-9, "倒完再 0.2 放正、0.3 端走"
        assert abs(timeline[int(0.3 / DT) - 1][1]["rot"][2] - 12.0) < 1.0e-6, "端到位时往倾倒的反方向仰 12 度（COCK）"
        assert abs(abs(timeline[int(0.5 / DT) - 1][1]["rot"][2]) - tilt) <= 2.0 + 1.0e-6, "0.5 秒倾到 %s 度（手抖 2 度）" % tilt


def testTheHandHeightsFollowTheLayers():
    """handFrom 的高度：落点上方 4（倒的落点比层底高 0.3，蛋直接落在层底）。"""
    for index in range(0, 9):
        assert abs(Hands.layerTop(index, Hands.POUR) - (1.0 + index * 0.65 + 0.3)) < 1.0e-9
        assert abs(Hands.layerTop(index, Hands.CRACK) - (1.0 + index * 0.65)) < 1.0e-9
        assert abs(Hands.handHeight(index, Hands.POUR) - (Hands.layerTop(index, Hands.POUR) + 4.0)) < 1.0e-9
        assert abs(Hands.handHeight(index, Hands.CRACK) - (Hands.layerTop(index, Hands.CRACK) + 4.0)) < 1.0e-9


# ---------------------------------------------------------------- 磕

def testTheEggIsKnockedBesideTheFoodAndOpenedOverTheLayer():
    """arrives:2017-2020：蛋在 (cx - 5.5, 板面, cz + z) 磕（蛋最低点），蛋液落在这一层的中心（高度 = 层底 + 2.5 开、层底落地），
    蛋液躺着转这一层的角度、画这一层的大小；落在食物上，没有涟漪、水花和锅里那一声噗。"""
    assert (Hands.EGG_SIZE, Hands.KNOCK_ASIDE) == (3.6, 5.5)
    for index in (0, 1, 4, 8):
        pose = Scene.layerPose(index)
        crack = Hands.crackFor(index, pose["x"], pose["z"], CENTER, START, pose["turn"])
        top = Scene.TOP + index * Motion.LAYER_STEP
        assert close(crack.rim, (CENTER[0] - 5.5, Scene.TOP + 3.6 * 0.42, CENTER[1] + pose["z"])), index
        assert close(crack.over, (CENTER[0] + pose["x"], top + 2.5, CENTER[1] + pose["z"])), index
        assert crack.size == 3.6 and crack.insideSize == Scene.layerSize(index) and not crack.sinks and not crack.liquid
        assert crack.turn == pose["turn"] and crack.yaw == 0.0 and crack.landY == top and crack.start == START


def testTheEggTimelineGoesKnockOpenLandWithShellDustAndNothingForALiquid():
    pose = Scene.layerPose(2)
    crack = Hands.crackFor(2, pose["x"], pose["z"], CENTER, START, pose["turn"])
    timeline = run(crack, 1.2)
    dusts = eventsOf(timeline, "dust")
    assert [event["count"] for _at, event in dusts] == [5, 4] and all(event["color"] == 0xFFEAD9B8 for _at, event in dusts), "磕一下 5 颗、壳裂开 4 颗，壳的颜色"
    assert abs(dusts[0][0] - Hands.knockAt()) < 0.0101 and abs(Hands.knockAt() - 0.36) < 1.0e-9
    assert close(dusts[0][1]["pos"], (CENTER[0] - 5.5, Scene.TOP, CENTER[1] + pose["z"])), "碎屑在板沿上"
    assert dusts[0][1]["rise"] == (0.0, 3.0, 0.0) and dusts[0][1]["spread"] == 1.0 and dusts[1][1]["rise"] == (0.0, 1.0, 0.0) and dusts[1][1]["spread"] == 0.8
    sounds = [Sounds.handSound(event) for _at, event in eventsOf(timeline, "sound")]
    assert sounds == [Sounds.EGG_KNOCK], "只有磕的那一声脆响：落到食物上不再有锅里的噗（落定那一声是这一层露出来时放的）"
    assert not eventsOf(timeline, "ripple") and not eventsOf(timeline, "splash"), "落在食物上不起涟漪、不溅水花"
    assert [(event["node"], event["amount"], event["seconds"]) for _at, event in eventsOf(timeline, "shake")] == [("egg", 0.15, 0.12), ("inside", 0.12, 0.15)]
    assert crack.landed and crack.done, "落了就由这一层接手：不沉"
    landed = [at for at, event in eventsOf(timeline, "shake") if event["node"] == "inside"][0]
    assert abs(Hands.landsBy() - 0.9) < 1.0e-9 and abs(landed - 0.9) < 0.0101, "0.3 + 0.06 + 0.1 + 0.14 + 0.1 + 0.2 秒落到食物上"
    last = timeline[int(0.89 / DT) - 1][1]
    assert last["inside"]["visible"] and abs(last["inside"]["pos"][1] - (Scene.TOP + 2 * Motion.LAYER_STEP)) < 0.3, "快落到这一层的面上了"
    assert not timeline[int(0.9 / DT) - 1][1]["inside"]["visible"], "落下去那一帧蛋液收掉，由这一层的图接手"
    assert last["inside"]["rot"] == (0.0, pose["turn"], 0.0), "躺着转这一层的角度（insideTurn）"


def testThePotsEggStillMakesAMessOfTheSoup():
    """Crack 多了 liquid 开关，缺省还是厨锅的样子：落进汤里有涟漪、水花和噗。"""
    crack = PotHands.Crack(START, (3.0, 10.0, 8.8), (6.0, 0.0, 8.8), 5.0)
    timeline = run(crack, 1.0)
    assert crack.liquid and eventsOf(timeline, "ripple") and eventsOf(timeline, "splash")
    assert [event["name"] for _at, event in eventsOf(timeline, "sound")] == ["egg_crack", "plop"]


# ---------------------------------------------------------------- 要多久

def testHowLongEachLayerTakesWhenADishComesFromTheBook():
    """arrive:1594-1595：倒液体 = Pour.pouredBy（桶 1.3、瓶 1.05），磕蛋 = Crack.landsBy + 落定 0.12，别的 = 飞来 0.32 + 落定 0.12。"""
    assert abs(Hands.takes(1, BUCKET) - 1.3) < 1.0e-9 and abs(Hands.takes(2, "minecraft:water_bucket") - 1.3) < 1.0e-9
    assert abs(Hands.takes(1, BOTTLE) - 1.05) < 1.0e-9 and abs(Hands.takes(1, SAUCE) - 1.05) < 1.0e-9
    assert abs(Hands.takes(1, EGG) - (0.9 + 0.12)) < 1.0e-9 and abs(Hands.takes(0, EGG) - (0.9 + 0.12)) < 1.0e-9
    assert abs(Hands.takes(0, BUCKET) - (0.32 + 0.12)) < 1.0e-9, "第 0 层的桶是底座，照旧飞来"
    assert abs(Hands.takes(3, "minecraft:bread") - (0.32 + 0.12)) < 1.0e-9
    assert Hands.pouredBy(BUCKET) == PotPour.Pour.pouredBy(True) and Hands.pouredBy(BOTTLE) == PotPour.Pour.pouredBy(False)


def testHowLongTheHandIsBusyBeforeTheLayerIsDone():
    """pourUntil：液体倒完才算（不含放正和端走）；蛋落下才算（JE 不等蛋，这边等：蛋没落下这一层还没露出来）；别的没有手。"""
    assert abs(Hands.lasts(1, BUCKET) - 1.3) < 1.0e-9 and abs(Hands.lasts(1, BOTTLE) - 1.05) < 1.0e-9
    assert abs(Hands.lasts(2, EGG) - 0.9) < 1.0e-9
    assert Hands.lasts(0, BUCKET) == 0.0 and Hands.lasts(1, "minecraft:bread") == 0.0


def testTheSoundsTheHandMakesForABystanderAreTheOnesItsMotionMakes():
    """旁观的人没有手的动画，只听声音：handSounds 给的（延迟, 声音）和手的动作自己放的同一个时刻、同一个声音（蛋液落下那一声是这一层露出来时放的）。"""
    pose = Scene.layerPose(2)
    for name, kind in ((BUCKET, Hands.POUR), (BOTTLE, Hands.POUR), (EGG, Hands.CRACK)):
        motion = (Hands.pourFor(2, name, pose["x"], pose["z"], CENTER, START) if kind == Hands.POUR
                  else Hands.crackFor(2, pose["x"], pose["z"], CENTER, START, pose["turn"]))
        played = [(at, Sounds.handSound(event)) for at, event in eventsOf(run(motion, 2.0), "sound")]
        played += [(Hands.landsBy(), Sounds.EGG_LANDED)] if kind == Hands.CRACK else []
        wanted = Sounds.handSounds({"at": 2, "item": name})
        assert len(wanted) == len(played) and len(wanted) == (2 if kind == Hands.CRACK else 1), name
        for (at, sound), (delay, expected) in zip(played, wanted):
            assert sound == expected and abs(at - delay) < 0.0101, (name, at, delay)
    assert Sounds.handSounds({"at": 0, "item": BUCKET}) == [] and Sounds.handSounds({"at": 1, "item": "minecraft:bread"}) == [], "底座和别的东西没有手"
    for bad in ({}, {"at": 1}, {"item": BUCKET}, {"at": True, "item": BUCKET}, {"at": "1", "item": BUCKET}, {"at": 1, "item": ["x"]}, {"at": 1, "item": None}):
        assert Sounds.handSounds(bad) == [], bad


def testTheHandSoundNamesAreTheBedrockOnesAndTheValuesTheJavaOnes():
    assert Sounds.POUR_BUCKET == ("bucket.empty_water", 0.45, 1.0) and Sounds.POUR_BOTTLE == ("bottle.empty", 0.45, 1.0)
    assert Sounds.EGG_KNOCK == ("block.turtle_egg.crack", 0.35, 1.5) and Sounds.EGG_LANDED == ("dig.wood", 0.4, 1.4)
    assert Sounds.handSound({"type": "sound", "name": "bucket_empty", "volume": 0.45, "pitch": 1.0}) == Sounds.POUR_BUCKET
    assert Sounds.handSound({"type": "sound", "name": "plop", "volume": 0.35, "pitch": 1.25}) is None, "锅里的噗不是板上的声音"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
