# -*- coding: utf-8 -*-
"""vanilla_pack - 本机游戏自带的原版资源包在哪（开发工具和测试共用的一处；py2 / py3 都能导入，只用标准库）

游戏目录 GAME 下每个版本一个目录（3.10.0.467018 ……），游戏升级后旧版本的目录会被删掉：写死版本号的核对就悄悄跳过了
（2026-11-22 查出来：写死的 3.10.0.448891 删了以后，汤色只比本包的物品，物品颜色、图标掩码、群系水色、三条声音、前置包水滴的核对整条跳过，照样是绿的）。
所以谁都别写死版本：生成器的缺省、测试要读的原版文件都从 newest() 来（测试经 tests/fdtest.vanilla）。
newest() 取目录名是版本号、带 data/resource_packs/vanilla 的里面版本号最高的那一份：逐段按数字比（3.10 比 3.9 新），
不是版本号的目录（PCLauncher_x64，里面也有一份）不算；一份都没有（别人的机器、只有本仓库的克隆、CI）返回 None，用的人照旧跳过或者只比本包的。
前置包的测试不靠这里（它的仓库里没有 tools/），自己在 tests/dgtest.py 里带一份。
"""
import os

GAME = "D:/MCStudioDownload/game/MinecraftPE_Netease"


def newest(game=GAME):
    """game 下版本号最高、带原版资源包的那一份的路径（正斜杠）；没有返回 None。"""
    found = []
    for name in os.listdir(game) if os.path.isdir(game) else ():
        parts = name.split(".")
        path = os.path.join(game, name, "data", "resource_packs", "vanilla").replace("\\", "/")
        if all(part.isdigit() for part in parts) and os.path.isdir(path):
            found.append((tuple(int(part) for part in parts), path))
    return max(found)[1] if found else None
