# -*- coding: utf-8 -*-
# runner: py3
"""原版文件的覆盖版（tools/gen_vanilla_overrides.py 生成）：猫。

引擎里附加包的同路径文件整份替换原版，所以这些文件是"原版整份拷来 + 只在列表末尾追加本模组内容"。这里守两件事：
1. 追加的内容对（照 JE：猫被鳕鱼片 / 鲑鱼片吸引、驯服、繁殖、长大、治疗）、用到的物品都存在；
2. 找得到本机的原版行为包时，重新生成一遍和提交的文件逐字比对：原版随游戏升级变了就失败，提醒重新生成
   （找不到原版目录就跳过这一条；FD_VANILLA_BP 环境变量可以指定目录）。
"""
from __future__ import print_function

import glob
import io
import json
import os
import sys

import fdtest

sys.path.insert(0, os.path.join(fdtest.ROOT, "tools"))
import gen_vanilla_overrides as gen  # noqa: E402

SLICES = ["arris:cod_slice", "arris:salmon_slice"]


def _read(relPath):
    with io.open(os.path.join(fdtest.BP, *relPath.split("/")), encoding="utf-8") as f:
        return json.load(f)


def _items():
    names = set()
    for path in glob.glob(os.path.join(fdtest.BP, "netease_items_beh", "*.json")):
        with io.open(path, encoding="utf-8") as f:
            names.add(json.load(f)["minecraft:item"]["description"]["identifier"])
    return names


# ---- 猫 ----

def testCatKeepsItsIdentityAndGainsTheSlicesWhereverItUsesFishAndSalmon():
    cat = _read("entities/cat.json")["minecraft:entity"]
    assert cat["description"]["identifier"] == "minecraft:cat"
    fishLists = []

    def walk(node):
        if isinstance(node, dict):
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            if "fish" in node and "salmon" in node:
                fishLists.append(node)
            for value in node:
                walk(value)

    walk(cat)
    # 幼崽长大、成年繁殖、野猫驯服、野猫 / 驯服猫被吸引，共 5 张字符串列表
    assert len(fishLists) == 5, len(fishLists)
    for names in fishLists:
        assert names[-2:] == SLICES, names
    healable = cat["components"]["minecraft:healable"]["items"]
    assert [entry["item"] for entry in healable] == ["fish", "salmon"] + SLICES
    assert [entry["heal_amount"] for entry in healable[2:]] == [1, 1], "JE 按食物的营养值回血，鱼片都是 1"


# ---- 物品 ----

def testEveryModItemTheOverridesMentionExists():
    items = _items()
    missing = sorted(name for name in SLICES if name not in items)
    assert not missing, "物品 JSON 里找不到: %s" % missing


# ---- 与本机原版逐字比对 ----

def testOverridesAreCurrentAgainstTheLocalVanillaPack():
    vanilla = gen.find_vanilla()
    if vanilla is None:
        print("跳过：找不到本机原版行为包（FD_VANILLA_BP 可以指定）")
        return
    for out, text in gen.generate(vanilla).items():
        with io.open(os.path.join(fdtest.BP, *out.split("/")), encoding="utf-8", newline="") as f:
            current = f.read().replace("\r\n", "\n")
        assert current == text, "%s 和原版（%s）不一致：py -3 tools/gen_vanilla_overrides.py 重新生成" % (out, vanilla)


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
