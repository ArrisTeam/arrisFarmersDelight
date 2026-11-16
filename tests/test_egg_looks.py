# -*- coding: utf-8 -*-
# runner: both
"""煎蛋从生到熟的几档样子（Shared/Rules/EggLook.py + 三个只用来画的物品 arris:egg_look_0..2）：JE 把打开的蛋按 RAW_EGG（0xC8E6E2D8）往白渐变着色，
基岩版的掉落物没法着色，几档颜色烤进专用的小图标（tools/gen_egg_looks.py 生成）。这里守：档的分界、着色就是 JE 的、物品和贴图都登记齐了、
不进创造栏、贴图一档比一档清透。"""
from __future__ import print_function

import io
import json
import os

import fdtest
import pngkit

EggLook = fdtest.load("Shared.Rules.EggLook")
Looks = fdtest.load("Shared.Rules.HandsOn.KitchenLooks")
Layout = fdtest.load("Shared.Rules.HandsOn.PanLayout")
RP = os.path.join(fdtest.ROOT, "rp")
BEH = os.path.join(fdtest.ROOT, "bp", "netease_items_beh")


def testTheThreeStagesAreThirdsOfTheTopsDoneness():
    assert EggLook.STAGES == 3 and len(EggLook.ITEMS) == 3
    assert [EggLook.stageOf(up) for up in (-1.0, 0.0, 0.33, 0.34, 0.66, 0.67, 0.999)] == [0, 0, 0, 1, 1, 2, 2]
    assert EggLook.stageOf(1.0) is None and EggLook.stageOf(1.5) is None, "熟了没有档：画煎蛋本身"
    assert EggLook.itemOf(0.0) == EggLook.ITEMS[0] and EggLook.itemOf(0.5) == EggLook.ITEMS[1] and EggLook.itemOf(0.9) == EggLook.ITEMS[2]
    assert EggLook.itemOf(1.0) == EggLook.FRIED == "arris:fried_egg"


def testTheStageBoundariesFallOnTheStepsThePanRedrawsAt():
    """朝上那面每 1/12 才重画一次（PanLayout.look）：一档里的每个值必须在同一个重画步里，不然画出来的和当前的熟度对不上。"""
    for step in range(Layout.LOOK_STEPS):
        low, high = (step + 1.0e-6) / Layout.LOOK_STEPS, (step + 1 - 1.0e-6) / Layout.LOOK_STEPS
        assert EggLook.stageOf(low) == EggLook.stageOf(high), step


def testTheTintIsJesEggTintAtEachStage():
    """KitchenLooks.fryingTint 对蛋的那一支：mix(RAW_EGG, 白, 朝上那面煎到哪)；第 k 档是 k / STAGES 那一刻。"""
    assert EggLook.tintOf(0) == Looks.RAW_EGG == 0xC8E6E2D8, "刚打进来：半透明发灰"
    for stage in range(EggLook.STAGES):
        assert EggLook.tintOf(stage) == Looks.mix(Looks.RAW_EGG, 0xFFFFFFFF, stage / 3.0)
    assert EggLook.tintOf(1) > EggLook.tintOf(0) and (EggLook.tintOf(2) >> 24) < 0xFF, "一档比一档不透明，最后一档还没到全白（熟了才是煎蛋本身）"


def _json(*parts):
    with io.open(os.path.join(*parts), encoding="utf-8") as handle:
        return json.load(handle)


def testEveryLookItemIsRegisteredOnBothSidesAndStaysOutOfTheCreativeMenu():
    textures = _json(RP, "textures", "item_texture.json")["texture_data"]
    with io.open(os.path.join(RP, "texts", "zh_CN.lang"), encoding="utf-8") as handle:
        lang = handle.read()
    groups = io.open(os.path.join(fdtest.ROOT, "bp", "netease_group", "arris_farmers_delight_group.json"), encoding="utf-8").read()
    for name in EggLook.ITEMS:
        short = name.split(":")[1]
        for folder in (BEH, os.path.join(RP, "netease_items_res")):
            body = _json(folder, "arris_%s.json" % short)["minecraft:item"]
            assert body["description"]["identifier"] == name and body["description"]["register_to_create_menu"] is False, (folder, name)
        assert _json(RP, "netease_items_res", "arris_%s.json" % short)["minecraft:item"]["components"]["minecraft:icon"] == name
        assert textures[name]["textures"] == "textures/items/" + short, name
        assert os.path.isfile(os.path.join(RP, "textures", "items", short + ".png")), name
        assert "item.%s.name=" % name in lang, name
        assert name not in groups, "只用来画，不进创造栏"
        assert "minecraft:food" not in _json(BEH, "arris_%s.json" % short)["minecraft:item"]["components"], "不是食物"


def testTheIconsGetClearerStageByStage():
    """贴图：第 0 档的蛋清最灰最透，之后一档比一档白、不透明；形状（哪些像素有东西）和煎蛋一样。"""
    source = pngkit.read(os.path.join(RP, "textures", "items", "fried_egg.png"))[2]
    white = [(x, y) for y, row in enumerate(source) for x, px in enumerate(row) if px == (255, 255, 255, 255)]
    assert white, "煎蛋的图里有纯白的蛋清像素"
    shown = []
    for name in EggLook.ITEMS:
        rows = pngkit.read(os.path.join(RP, "textures", "items", name.split(":")[1] + ".png"))[2]
        assert [[px[3] > 0 for px in row] for row in rows] == [[px[3] > 0 for px in row] for row in source], name
        shown.append(rows[white[0][1]][white[0][0]])
    assert shown[0] < shown[1] < shown[2] < (255, 255, 255, 255), shown
    assert shown[0][:3] == (230, 226, 216) and shown[0][3] == 200, "第 0 档：纯白乘 RAW_EGG（0xC8E6E2D8）"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
