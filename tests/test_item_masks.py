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
VANILLA = fdtest.vanilla()        # 本机版本号最高的原版资源包（tools/vanilla_pack.py，工具的缺省也是它）；没有游戏目录是 None


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


def testTheFlatThingsTheBoardTakesApartAreThereToo():
    # 砧板配方里拆的船、告示牌、矿车、皮甲：平躺的物品，刀口 / 虚线要按它们自己的轮廓（原来 44 件没有掩码，按整格实心算）
    flat = ["minecraft:%s_boat" % wood for wood in ("oak", "spruce", "birch", "jungle", "acacia", "dark_oak", "mangrove", "cherry")]
    flat += ["minecraft:%s_chest_boat" % wood for wood in ("oak", "spruce", "birch", "jungle", "acacia", "dark_oak", "mangrove", "cherry")]
    flat += ["minecraft:bamboo_raft", "minecraft:bamboo_chest_raft", "minecraft:chest_minecart", "minecraft:hopper_minecart", "minecraft:tnt_minecart"]
    flat += ["minecraft:%s_sign" % wood for wood in ("oak", "spruce", "birch", "jungle", "acacia", "dark_oak", "crimson", "warped", "bamboo", "cherry", "mangrove")]
    flat += ["minecraft:%s_hanging_sign" % wood for wood in ("oak", "spruce", "birch", "jungle", "acacia", "dark_oak", "crimson", "warped", "bamboo", "cherry", "mangrove")]
    flat += ["minecraft:leather_%s" % piece for piece in ("helmet", "chestplate", "leggings", "boots")]
    assert len(flat) == 8 + 8 + 5 + 11 + 11 + 4
    for name in flat:
        assert name in Masks, name
        width, height, rows = Masks[name]
        assert not all(row == (1 << width) - 1 for row in rows), (name, "整格实心 = 没读到轮廓")


def testTheIconsTheFinishAnimationsLayThingsAlongAreThereAndTheirAxesAreWhatTheJavaAlgorithmGives():
    """串 / 冻沿着签子放、成形沿着米饭的长边放（BoardFinishPlace）：它们不是砧板要切的，也要在表里（tools/gen_item_masks.py 的 FINISH_BASES），
    轴是 ItemVoxels.Icon.axis 在这两张图上算出来的（图标 16 格画 10 像素）：签子从左下（柄）斜到右上（尖）、方向 (-√½, √½)、占 ±5.6158；米饭是个扁的一团。"""
    import math
    Icon = fdtest.load("Shared.Rules.HandsOn.BoardIcon")
    assert "minecraft:stick" in Masks and "arris:cooked_rice" in Masks
    stick = Icon.iconOf("minecraft:stick").axis(10.0)
    assert abs(stick.dirX + math.sqrt(0.5)) < 1.0e-9 and abs(stick.dirZ - math.sqrt(0.5)) < 1.0e-9, "尖朝右上：x 往屏幕左边长，右上是 (-, +)"
    assert abs(stick.start + 5.6158) < 1.0e-3 and abs(stick.end - 5.6158) < 1.0e-3 and stick.elongation > 8.0
    assert abs(stick.x + 0.3125) < 1.0e-9 and abs(stick.z + 0.3125) < 1.0e-9
    rice = Icon.iconOf("arris:cooked_rice").axis(10.0)
    assert abs(rice.dirX + 0.96305) < 1.0e-4 and abs(rice.dirZ - 0.26931) < 1.0e-4 and abs(math.degrees(rice.along()) - 164.377) < 1.0e-2
    assert 1.2 < rice.elongation < 1.3, "米饭近乎圆的一团"


def testTheTableMatchesTheTextures():
    """拿本机最新的原版资源包比（工具不带 --vanilla 用的就是它）；本机没有游戏目录（别人的机器、只有本仓库的克隆）跳过。"""
    if VANILLA is None:
        print("跳过：本机没有原版资源包")
        return
    code = subprocess.call([sys.executable, "-B", TOOL, "--check"])
    assert code == 0, "贴图变了：py -3 tools/gen_item_masks.py 重新生成 Shared/Data/ItemMasks.py"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
