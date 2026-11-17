# -*- coding: utf-8 -*-
# runner: both
"""砧板各种事件的声音表（Shared/Rules/BoardSounds.py）：音量、音调、哪个工具响哪一声，照 HoD 的 BoardBehavior（1350-1490、1650）和 FD 的 playProcessingSound。
声音名都要真的存在：本包自己的在 rp/sounds/sound_definitions.json 里，别的在原版里（本机有原版资源包时查）。
"""
from __future__ import print_function

import io
import json
import os

import fdtest

Sounds = fdtest.load("Shared.Rules.BoardSounds")
Cutting = fdtest.load("Shared.Rules.HandsOn.Cutting")

VANILLA = "D:/MCStudioDownload/game/MinecraftPE_Netease/3.10.0.448891/data/resource_packs/vanilla/sounds/sound_definitions.json"
LOW, HIGH = (lambda: 0.0), (lambda: 1.0)


def _stroke(tool, item, stroke=None, done=False, block=False, yields=(), rng=LOW):
    data = {"tool": tool, "item": item, "done": done, "block": block, "yields": list(yields)}
    if stroke is not None:
        data["stroke"] = stroke
    return Sounds.chopped(data, rng)


def _near(sounds, expected):
    assert len(sounds) == len(expected), (sounds, expected)
    for got, want in zip(sounds, expected):
        assert got[0] == want[0] and abs(got[1] - want[1]) < 1.0e-9 and abs(got[2] - want[2]) < 1.0e-9, (got, want)


def testTheKnifeSoundsAtPointEightWithAPitchBetweenNinetyFiveAndOneTen():
    _near(_stroke("arris:iron_knife", "arris:cabbage"), [("ambient.cutting_board.knife", 0.8, 0.95)])
    _near(_stroke("arris:iron_knife", "arris:cabbage", rng=HIGH), [("ambient.cutting_board.knife", 0.8, 1.10)])


def testEachToolSoundsOnItsOwnBeforeTheLastStroke():
    """JE：刀 0.8、削皮 0.8、别的 0.6；斧在刀切的配方上是削皮声、锹是铲平声；剪刀剪声；镐 / 锹 / 锄 / 斧劈是被切东西的材质被敲的声音。"""
    _near(_stroke("minecraft:iron_axe", "minecraft:oak_log", Cutting.TOOL_STRIP, block=True, yields=["minecraft:stripped_oak_log"]), [("use.wood", 0.8, 0.95)])
    _near(_stroke("minecraft:iron_axe", "arris:cabbage", Cutting.TOOL_CUT), [("use.wood", 0.8, 0.95)])
    _near(_stroke("minecraft:iron_shovel", "arris:cabbage", Cutting.TOOL_CUT), [("use.grass", 0.8, 0.95)])
    _near(_stroke("minecraft:shears", "minecraft:leather_helmet", Cutting.TOOL_SNIP), [("mob.sheep.shear", 0.6, 0.95)])
    _near(_stroke("minecraft:iron_pickaxe", "minecraft:stone", Cutting.TOOL_SMASH, block=True), [("hit.stone", 0.6, 0.95)])
    _near(_stroke("minecraft:iron_shovel", "minecraft:gravel", Cutting.TOOL_DIG, block=True), [("hit.gravel", 0.6, 0.95)])
    _near(_stroke("minecraft:iron_shovel", "minecraft:clay", Cutting.TOOL_DIG, block=True), [("hit.gravel", 0.6, 0.95)])
    _near(_stroke("minecraft:iron_hoe", "minecraft:oak_chest_boat", Cutting.TOOL_PRY), [("hit.wood", 0.6, 0.95)])
    _near(_stroke("minecraft:iron_axe", "minecraft:wooden_door", Cutting.TOOL_CHOP, block=True), [("hit.wood", 0.6, 0.95)])


def testTheStrokeKindIsReadFromTheToolWhenTheEventDoesNotSayIt():
    _near(_stroke("minecraft:iron_axe", "minecraft:oak_log", yields=["minecraft:stripped_oak_log"]), [("use.wood", 0.8, 0.95)])
    _near(_stroke("minecraft:iron_pickaxe", "minecraft:stone"), [("hit.stone", 0.6, 0.95)])
    _near(_stroke("minecraft:iron_pickaxe", "x:thing"), [("hit.wood", 0.6, 0.95)])         # 认不出材质的东西按木头算：JE 的 material() 缺省


def testTheLastStrokeIsFarmersDelightsOwnCutSoundThenTheBreakThenThePickup():
    """FD 的切声一次（剪刀 1.0 / 刀 0.8 / 方块破坏声 1.0 / 0.8 / 木头破坏声）；被切的不是方块、也不是刀 / 剪 / 削皮时再来材质的破坏声 0.8；最后一声拿起 0.35 / 1.3。"""
    pickup = ("random.pop", 0.35, 1.3)
    _near(_stroke("arris:iron_knife", "arris:cabbage", done=True), [("ambient.cutting_board.knife", 0.8, 1.0), pickup])
    _near(_stroke("minecraft:shears", "minecraft:leather_helmet", Cutting.TOOL_SNIP, done=True), [("mob.sheep.shear", 1.0, 1.0), pickup])
    _near(_stroke("minecraft:iron_axe", "minecraft:oak_log", Cutting.TOOL_STRIP, done=True, block=True), [("use.wood", 1.0, 1.0), pickup])
    _near(_stroke("minecraft:iron_pickaxe", "minecraft:stone", Cutting.TOOL_SMASH, done=True, block=True), [("dig.stone", 1.0, 0.8), pickup])
    _near(_stroke("minecraft:iron_pickaxe", "minecraft:brick_block", Cutting.TOOL_SMASH, done=True, block=True), [("dig.stone", 1.0, 0.8), pickup])
    _near(_stroke("minecraft:iron_hoe", "minecraft:oak_chest_boat", Cutting.TOOL_PRY, done=True, block=False),
          [("dig.wood", 1.0, 0.8), ("dig.wood", 0.8, 0.95), pickup])
    _near(_stroke("minecraft:iron_shovel", "minecraft:clay", Cutting.TOOL_DIG, done=True, block=False),
          [("dig.wood", 1.0, 0.8), ("dig.gravel", 0.8, 0.95), pickup])
    _near(_stroke("minecraft:iron_pickaxe", "minecraft:stone", Cutting.TOOL_SMASH, done=True, block=False, rng=HIGH),
          [("dig.wood", 1.0, 0.8), ("dig.stone", 0.8, 1.05), pickup])


def testTheLastStrokeOfStrippingALogPlaysTheRecipesOwnSoundNotTheBlocksBreakSound():
    """FD 的 21 条削皮配方都写 "sound": "minecraft:item.axe.strip"，playProcessingSound 第一支就是它（1.0 / 1.0）：最后一刀响的和前几刀同一个削皮声
    （基岩版是 use.wood，采样就是 sounds/item/axe/strip1..4），不是方块（原木）的破坏声 dig.wood。每种能削的木头都一样，菌柄、菌丝体、竹块也是。"""
    for log in ("minecraft:oak_log", "minecraft:crimson_stem", "minecraft:warped_hyphae", "minecraft:bamboo_block", "minecraft:cherry_wood"):
        for block in (True, False):
            _near(_stroke("minecraft:iron_axe", log, Cutting.TOOL_STRIP, done=True, block=block, yields=["minecraft:stripped_oak_log"]),
                  [("use.wood", 1.0, 1.0), ("random.pop", 0.35, 1.3)])
    _near(_stroke("minecraft:iron_axe", "minecraft:oak_log", done=True, block=True, yields=["minecraft:stripped_oak_log", "arris:tree_bark"]),
          [("use.wood", 1.0, 1.0), ("random.pop", 0.35, 1.3)])         # 事件没写 stroke：按工具和产物认出是削皮
    assert Sounds.soundsOf("chopped", {"tool": "minecraft:iron_axe", "item": "minecraft:oak_log", "stroke": "strip", "block": True, "done": True})[0] == ("use.wood", 1.0, 1.0)
    _near(_stroke("minecraft:iron_axe", "minecraft:oak_log", Cutting.TOOL_STRIP, yields=["minecraft:stripped_oak_log"]), [("use.wood", 0.8, 0.95)])
    _near(_stroke("minecraft:iron_axe", "minecraft:oak_planks", Cutting.TOOL_CHOP, done=True, block=True), [("dig.wood", 1.0, 0.8), ("random.pop", 0.35, 1.3)])


def testTheMaterialOfWhatIsCutComesFromItsNameThenFromWhatItYields():
    expect = {"minecraft:stone": "stone", "minecraft:cobblestone": "stone", "minecraft:brick_block": "stone", "minecraft:sandstone": "stone",
              "minecraft:gravel": "gravel", "minecraft:clay": "gravel", "minecraft:sand": "sand", "minecraft:snow": "snow",
              "minecraft:leather_boots": "cloth", "minecraft:saddle": "cloth", "arris:wild_rice": "grass", "minecraft:melon_block": "grass",
              "minecraft:oak_log": "wood", "minecraft:oak_planks": "wood", "arris:basket": "wood", "minecraft:oak_chest_boat": "wood",
              "": "wood", "x:something": "wood"}
    for name, material in expect.items():
        assert Sounds.materialOf(name) == material, (name, Sounds.materialOf(name))
    assert Sounds.materialOf("x:thing", ["minecraft:gravel"]) == "gravel", "自己认不出，按切出来的东西认"
    assert Sounds.materialOf("minecraft:stone", ["minecraft:gravel"]) == "stone", "自己认得出，切出来的不管"


def testPlacedGetsHigherWithEveryLayerAndEveryoneHearsTheSameOne():
    assert Sounds.placed() == ("dig.wood", 0.7, 1.0) and Sounds.placed(None) == ("dig.wood", 0.7, 1.0)
    assert abs(Sounds.placed(0)[2] - 1.15) < 1.0e-9 and abs(Sounds.placed(4)[2] - 1.35) < 1.0e-9 and Sounds.placed(4)[1] == 0.7
    assert Sounds.placed(True)[2] == 1.0 and Sounds.placed("3")[2] == 1.0, "层号不是整数（坏数据）：按没带算"
    assert Sounds.soundsOf("placed", {"at": 2}) == [Sounds.placed(2)]


def testTakenCarvedAssembledAndTheRest():
    assert Sounds.soundsOf("taken", {"carved": False}) == [("random.pop", 0.3, 1.5)], "取走：只有拿起声，不再叠一声皮甲声"
    assert Sounds.soundsOf("taken", {"carved": True}) == [("hit.wood", 0.6, 0.9), ("random.pop", 0.3, 1.5)], "拔出插着的工具：拔出声 + 拿起声"
    assert Sounds.soundsOf("carved") == [("dig.wood", 1.0, 0.8)]
    assert Sounds.soundsOf("assembled", {}) == [("dig.wood", 0.8, 0.75), ("random.pop", 0.35, 1.4)]
    assert Sounds.soundsOf("refused", {}) == [("hit.wood", 0.4, 1.4)] == [Sounds.BOUNCE], "被拒：弹回那一声，旁观的人也听得到（JE 的效果发给所有看得见板的人）"
    assert Sounds.soundsOf("refused", {"stack": {"newItemName": "arris:tomato"}}) == [Sounds.BOUNCE] and Sounds.soundsOf("refused") == [Sounds.BOUNCE]
    assert Sounds.soundsOf("board_book") == [] and Sounds.soundsOf("nonsense", None) == []
    assert Sounds.SETTLE == ("dig.wood", 0.5, 0.8) and Sounds.KNOCK == ("hit.wood", 0.25, 1.6) and Sounds.BOUNCE == ("hit.wood", 0.4, 1.4)
    assert abs(Sounds.snipBite(LOW)[2] - 1.25) < 1.0e-9 and Sounds.snipBite(HIGH)[:2] == ("mob.sheep.shear", 0.3)


def testBadEventDataNeverRaises():
    for data in ({"tool": 5, "item": None, "yields": "x"}, {"tool": ["a"], "item": {"b": 1}, "stroke": "nonsense", "yields": [1, None]}, {"done": True}, {}):
        for done in (False, True):
            sounds = Sounds.soundsOf("chopped", dict(data, done=done))
            assert sounds and all(isinstance(sound[0], str) for sound in sounds), data
    _near(Sounds.soundsOf("chopped", {"tool": 5}, LOW), [("ambient.cutting_board.knife", 0.8, 0.95)])


def _names():
    names = set([Sounds.KNIFE_CUT, Sounds.AXE_STRIP, Sounds.SHOVEL_FLATTEN, Sounds.SHEEP_SHEAR, Sounds.BOARD_PLACE, Sounds.BOARD_CARVE,
                 Sounds.BOARD_REMOVE, Sounds.WOOD_HIT, Sounds.ITEM_PICKUP, Sounds.BUCKET_EMPTY, Sounds.BOTTLE_EMPTY, Sounds.EGG_CRACK])
    names.update(Sounds.HAND_SOUNDS.values())
    names.update(Sounds.HIT.values())
    names.update(Sounds.BREAK.values())
    return names


def testEverySoundNameExists():
    own = json.load(io.open(os.path.join(fdtest.ROOT, "rp", "sounds", "sound_definitions.json"), encoding="utf-8"))
    own = own.get("sound_definitions", own)
    assert Sounds.KNIFE_CUT in own, "刀声是本包自己的"
    if not os.path.exists(VANILLA):
        print("（本机没有原版资源包：别的声音名没查）")
        return
    vanilla = json.load(io.open(VANILLA, encoding="utf-8"))
    vanilla = vanilla.get("sound_definitions", vanilla)
    missing = sorted(name for name in _names() if name not in own and name not in vanilla)
    assert not missing, "原版和本包的 sound_definitions.json 里都没有：%r" % (missing,)


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
