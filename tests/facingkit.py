# -*- coding: utf-8 -*-
"""facingkit - 方块 aux -> 朝向的期望值（不是测试本身，跑器只收 test_*.py）

炉灶 / 厨锅 / 煎锅 / 砧板读朝向的各处测试（站点的朝向钩子两端、场景、世界里的展示、模型数学）共用这一张表。
写死的具体值，不由被测的函数自己算（早先有一条测试拿被测函数给的答案去比被测函数的答案，永远不会失败）。
direction 状态：0 南、1 西、2 北、3 东（netease:face_directional）。普通世界方块的 aux 就是 direction（0..3）；
假日创造者实验玩法下 direction 1 / 2 / 3 的 aux 是 4 / 8 / 12。别的值一律按 0 朝南，不返回 None。
站点朝向（度）：北 0 / 东 90 / 南 180 / 西 270，站点的北面转到炉灶的正面那一侧。
"""
DIRECTION = {0: 0, 1: 1, 2: 2, 3: 3, 4: 1, 8: 2, 12: 3}                 # aux -> direction 状态
YAW = {0: 180, 1: 270, 2: 0, 3: 90, 4: 270, 8: 0, 12: 90}                # aux -> 站点朝向（度）
FACING = {0: "south", 1: "west", 2: "north", 3: "east", 4: "west", 8: "north", 12: "east"}     # aux -> PotModelMath 的朝向名
UNKNOWN = (None, -1, 5, 6, 7, 9, 10, 11, 13, 16, 100, "x", "")           # 读不到 / 越界 / 不是这两种写法
UNKNOWN_DIRECTION, UNKNOWN_YAW, UNKNOWN_FACING = 0, 180, "south"
