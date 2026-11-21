# -*- coding: utf-8 -*-
# runner: both
"""本机游戏自带的原版资源包在哪（tools/vanilla_pack.py，测试经 fdtest.vanilla 拿）：取版本号最高的那一份，谁都不写死版本。

2026-11-22 查出来：生成器的缺省和九处核对写死了 3.10.0.448891，游戏升级后那个目录删了，核对就悄悄跳过（或者只比本包的），照样是绿的。
这里守：挑版本按数字比、不是版本号的目录不算；本机装了游戏就一定找得到；fdtest.vanilla 交出的就是它；本仓库的测试和工具里不再有写死版本号的路径。
"""
from __future__ import print_function

import glob
import io
import os
import re
import shutil
import sys
import tempfile

import fdtest

sys.path.insert(0, os.path.join(fdtest.ROOT, "tools"))
import vanilla_pack  # noqa: E402

# 前置包仓库的文件（它们在同一个目录里，归另一个仓库管：CLAUDE.md 的两仓库一节）
PREREQ = re.compile(r"^(test_diegesis_.*|dg.*|gen_book_assets|book_textures)\.py$")
PINNED = re.compile(r"MinecraftPE_Netease[/\\]+[0-9]")


def testTheNewestVersionWinsByNumberNotByName():
    """逐段按数字比（3.10 比 3.9 新，按字符串比就反了）；没有原版资源包的版本目录、不是版本号的目录（PCLauncher_x64 里也有一份）不算；游戏目录不在是 None。"""
    game = tempfile.mkdtemp()
    try:
        for name, pack in (("3.9.0.401155", True), ("3.10.0.436581", True), ("3.10.0.467018", True), ("3.11.0.1", False),
                           ("PCLauncher_x64", True), ("3.12.0.x", True)):
            os.makedirs(os.path.join(game, name, "data", "resource_packs", "vanilla" if pack else "other"))
        newest = vanilla_pack.newest(game)
        assert newest == os.path.join(game, "3.10.0.467018", "data", "resource_packs", "vanilla").replace("\\", "/"), newest
        assert vanilla_pack.newest(os.path.join(game, "nowhere")) is None
    finally:
        shutil.rmtree(game)


def testThisMachinesGameIsFoundWhenItHasOne():
    """另算一遍本机游戏目录里有哪些版本带原版资源包：有的话 newest() 就是数字最大的那个，没有（别人的机器、CI）是 None。"""
    versions = []
    for path in glob.glob(vanilla_pack.GAME + "/*/data/resource_packs/vanilla"):
        name = os.path.basename(os.path.dirname(os.path.dirname(os.path.dirname(path))))
        if re.match(r"^[0-9]+(\.[0-9]+)*$", name):
            versions.append([int(part) for part in name.split(".")])
    if not versions:
        print("本机没有游戏目录：newest() 是 None")
        assert vanilla_pack.newest() is None
        return
    best = ".".join(str(part) for part in max(versions))
    assert vanilla_pack.newest() == vanilla_pack.GAME + "/" + best + "/data/resource_packs/vanilla", (vanilla_pack.newest(), best)


def testFdtestHandsOutTheSamePack():
    root = vanilla_pack.newest()
    assert fdtest.vanilla() == root
    expected = None if root is None else root + "/sounds/sound_definitions.json"
    assert fdtest.vanilla("sounds", "sound_definitions.json") == expected


def testNoTestOrToolPinsAGameVersionInAPath():
    """本仓库的测试和工具里没有写死版本号的游戏路径（注释里举例的不算）：要原版资源包的一律经 vanilla_pack / fdtest.vanilla。"""
    pinned = []
    for folder in ("tests", "tools"):
        for path in sorted(glob.glob(os.path.join(fdtest.ROOT, folder, "*.py"))):
            if PREREQ.match(os.path.basename(path)):
                continue
            with io.open(path, encoding="utf-8") as handle:
                for number, line in enumerate(handle, 1):
                    if PINNED.search(line) and not line.strip().startswith("#"):
                        pinned.append("%s/%s:%d" % (folder, os.path.basename(path), number))
    assert not pinned, "写死了游戏版本的路径：%s" % ", ".join(pinned)


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
