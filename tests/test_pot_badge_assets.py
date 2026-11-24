# -*- coding: utf-8 -*-
# runner: py3
"""厨锅徽章的贴图和界面（rp/textures/ui/pot_badge/、内核的 arris_diegesis_focus.json 的 plate）：
贴图和 PotBadgeGlyphs.PATTERNS 的字符画一致（tools/gen_pot_badge.py 生成）、徽章用到的每张贴图都在、
界面里的图片控件够用、弹一下的动画在界面 JSON 里有定义。"""
from __future__ import print_function

import io
import json
import os
import re
import subprocess
import sys

import prereq  # 徽章要对着前置包的界面和牌子的源码：它不在这个仓库里，找不到就跳过
import fdtest

Glyphs = fdtest.load("Shared.Rules.HandsOn.PotBadgeGlyphs")
TOOL = os.path.join(fdtest.ROOT, "tools", "gen_pot_badge.py")
RP = os.path.join(fdtest.ROOT, "rp")
FOCUS = os.path.join(prereq.RP, "ui", "arris_diegesis_focus.json")
WIDGET = os.path.join(prereq.SCRIPTS, "Client", "Ui", "PlateWidget.py")
LAYOUT = os.path.join(prereq.SCRIPTS, "Shared", "PlateLayout.py")


def focus():
    with io.open(FOCUS, encoding="utf-8") as handle:
        return json.loads(re.sub(r"^\s*//.*$", "", handle.read(), flags=re.M))


def constant(path, name):
    with io.open(path, encoding="utf-8") as handle:
        return int(re.search(r"^%s = (\d+)" % name, handle.read(), re.M).group(1))


def testTheTexturesAreWhatTheGeneratorDraws():
    code = subprocess.call([sys.executable, "-B", TOOL, "--check"])
    assert code == 0, "贴图不是最新：py -3 tools/gen_pot_badge.py 重新生成"


def testEverySpriteTheBadgeCanShowHasItsTexture():
    seen = set()
    for added in (0, 7, 45, 99):
        for cold in (False, True):
            for sprite in Glyphs.sprites(3, cold, 14, 15, added):
                if sprite is not None:
                    seen.add(sprite["texture"])
    for digit in range(10):
        seen.add(Glyphs.TEXTURES + "digit_%d" % digit)
    assert len(seen) == len(Glyphs.PATTERNS)
    for texture in sorted(seen):
        assert os.path.isfile(os.path.join(RP, texture + ".png")), texture


def testTheFocusScreenHasEnoughSpriteSlotsAndTheAnimations():
    ui = focus()
    pool, over = constant(LAYOUT, "POOL"), constant(LAYOUT, "OVER_ITEM")
    assert Glyphs.SLOTS <= pool and Glyphs.SLOT_COUNT >= over > Glyphs.SLOT_BAR, "数字那几格在物品上面，别的在下面"
    controls = dict((list(entry)[0].split("@")[0], list(entry.values())[0]) for entry in ui["plate"]["controls"])
    slots = ["s%d" % index for index in range(pool)]
    probes = dict((name, body) for name, body in controls.items() if name.startswith("probe_"))
    assert sorted(name for name in controls if name != "item" and name not in probes) == sorted(slots)
    assert dict((name, body["clip_direction"]) for name, body in probes.items()) == {
        "probe_left": "left", "probe_right": "right", "probe_top": "up", "probe_bottom": "down"}, "界面类开界面时靠它们学裁切方向的接口名"
    item = controls["item"]["layer"]
    assert all(controls["s%d" % index]["layer"] < item for index in range(over)), "前面的格子画在物品下面"
    assert all(controls["s%d" % index]["layer"] > item for index in range(over, pool)), "后面的格子画在物品上面"
    image = ui["plate_sprite"]["controls"][0]["image"]
    assert image["type"] == "image" and image["size"] == ["100%", "100%"], "图撑满外面的框：位置和大小摆在框上"
    assert ui["plate_pop"]["anim_type"] == "size" and ui["plate_pop"]["to"] == ["100%", "100%"], "弹完回到原大"
    assert ui["plate_flash"]["anim_type"] == "alpha" and ui["plate_flash"]["to"] == 1.0
    with io.open(WIDGET, encoding="utf-8") as handle:
        widget = handle.read()
    assert '"plate_pop"' in widget and '"plate_flash"' in widget and ui["namespace"] in widget, "界面类放的就是这两段动画"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
