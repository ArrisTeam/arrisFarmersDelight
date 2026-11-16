# -*- coding: utf-8 -*-
"""Slicing - 刀切派、蛋糕、南瓜的数据（双端，纯数据）

照 JE：PieBlock（4 口）、CakeBlock（7 口）、战利品修饰器 slicing_*.json 与 scavenging_pumpkin.json。
"""
PIE_BITES = 4       # 一个派 4 块（JE PieBlock.getMaxBites）
CAKE_BITES = 7      # 一整块蛋糕 7 片（JE MAX_CAKE_BITES）；基岩版蛋糕的 bite_counter 取 0 到 6

# 派方块 -> 切下来的一片
pieSliceItems = {
    "arris:apple_pie": "arris:apple_pie_slice",
    "arris:chocolate_pie": "arris:chocolate_pie_slice",
    "arris:sweet_berry_cheesecake": "arris:sweet_berry_cheesecake_slice",
    "arris:pumpkin_pie": "arris:pumpkin_pie_slice",
}

CAKE = "minecraft:cake"
CAKE_SLICE = "arris:cake_slice"
# 插了蜡烛的蛋糕：无色加 16 种颜色（JE 的 drops_cake_slice 标签）
CANDLE_CAKES = tuple(
    "minecraft:%scandle_cake" % color
    for color in ("", "white_", "orange_", "magenta_", "light_blue_", "yellow_", "lime_", "pink_", "gray_",
                  "light_gray_", "cyan_", "purple_", "blue_", "brown_", "green_", "red_", "black_"))

PUMPKIN = "minecraft:pumpkin"
PUMPKIN_SLICE = "arris:pumpkin_slice"
PUMPKIN_SLICES = 4

# 刀切的声音（砧板用的同一个）
SLICE_SOUND = "ambient.cutting_board.knife"
