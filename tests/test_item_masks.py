# -*- coding: utf-8 -*-
# runner: py3
"""图标实心像素表（tools/gen_item_masks.py 按贴图生成的 Shared/Data/ItemMasks.py）：形状对、要切的食材都有、和贴图一致。"""
from __future__ import print_function

import os
import subprocess
import sys

import fdtest

Masks = fdtest.load("Shared.Data.ItemMasks").ItemMasks
TOOL = os.path.join(fdtest.ROOT, "tools", "gen_item_masks.py")
VANILLA = "D:/MCStudioDownload/game/MinecraftPE_Netease/3.10.0.448891/data/resource_packs/vanilla"


def testEveryMaskHasOneIntegerPerRowAndSomeSolidPixels():
    assert Masks
    for name, (width, height, rows) in Masks.items():
        assert len(rows) == height and width > 0, name
        assert all(isinstance(row, int) and 0 <= row < (1 << width) for row in rows), name
        assert any(rows), name


def testTheFoodsTheBoardCutsAreThere():
    for name in ("arris:cabbage", "arris:ham", "arris:wheat_dough", "arris:kelp_roll", "minecraft:beef", "minecraft:porkchop",
                 "minecraft:chicken", "minecraft:salmon", "minecraft:cod", "minecraft:cake", "minecraft:pumpkin_pie"):
        assert name in Masks, name


def testTheTableMatchesTheTextures():
    if not os.path.isdir(VANILLA):
        print("跳过：本机没有原版资源包", VANILLA)
        return
    code = subprocess.call([sys.executable, "-B", TOOL, "--check", "--vanilla", VANILLA])
    assert code == 0, "贴图变了：py -3 tools/gen_item_masks.py 重新生成 Shared/Data/ItemMasks.py"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
