# -*- coding: utf-8 -*-
# runner: both
"""哪些粒子跟着环境光变暗（minecraft:particle_appearance_lighting），哪些有意满亮度（粒子 JSON 里没有这个组件 = 满亮度，Strata 知识库 PARTICLE_ENGINE.md §6.2）。

JE 的 Diegesis 场景粒子画的时候（SceneParticles.java:252）：packed = style.emissive() ? FULL_BRIGHT : light，light 是站点所在方块的光照（SceneRenderer.java:308）。
样式表（DiegesisParticles.java，emissive 默认 false，只有写了 .emissive() 的满亮度）：
  气泡、破泡、水滴、水花、碎屑  不 emissive，跟着环境光
  蒸汽（:60-61）、闪光（:65-68）  .emissive()，满亮度
HoD 自己登记的样式（HandsOnDelightClient.java:80-101）：HEAT（热浪，:95-96）没写 .emissive()，跟着环境光；SCROLL_FLAME（:97-99）写了。
FD 的粒子：SteamParticle 没有覆盖 getLightColor（跟着环境光），SparkleParticle 覆盖了（:19，满亮度）。
砧板的刀口虚线是 setShape(shape, WHITE, true)（BoardBehavior.java:1193）：glows = true，画的时候满亮度（SceneRenderer.java:631）。

以前前置包的碎屑 / 水花 / 气泡 / 破泡 / 水滴和 FD 自己的砧板碎屑、热浪都没写这个组件：暗处的泡、水滴、碎屑一样亮。"""
from __future__ import print_function

import io
import json
import os

import fdtest

COMPONENT = "minecraft:particle_appearance_lighting"
LIT, BRIGHT = "跟着环境光", "满亮度"
TABLE = [
    # (哪个包, 文件, 该是什么, 依据)
    ("diegesisRp", "arris_diegesis_bubble.json", LIT, "DiegesisParticles.java:46-47 的 BUBBLE 没写 emissive"),
    ("diegesisRp", "arris_diegesis_bubble_pop.json", LIT, "DiegesisParticles.java:52 的 BUBBLE_POP 没写 emissive"),
    ("diegesisRp", "arris_diegesis_droplet.json", LIT, "DiegesisParticles.java:53-54 的 DROPLET 没写 emissive"),
    ("diegesisRp", "arris_diegesis_dust.json", LIT, "DiegesisParticles.java:69-70 的 DUST，emissive 那一项是 false"),
    ("diegesisRp", "arris_diegesis_splash.json", LIT, "DiegesisParticles.java:57-59 的 SPLASH，emissive 那一项是 false"),
    ("diegesisRp", "arris_diegesis_steam.json", BRIGHT, "DiegesisParticles.java:60-61 的 STEAM 是 .emissive()"),
    ("diegesisRp", "arris_diegesis_glint.json", BRIGHT, "DiegesisParticles.java:65-68 的 GLINT 是 .emissive()"),
    ("rp", "arris_board_dust.json", LIT, "砧板的碎屑放的是 DiegesisParticles.DUST（BoardBehavior.java:1411-1420），样式同上不 emissive"),
    ("rp", "arris_pan_heat.json", LIT, "HandsOnDelightClient.java:95-96 的 HEAT 没写 emissive"),
    ("rp", "arris_steam.json", LIT, "SteamParticle.java 没有覆盖 getLightColor"),
    ("rp", "arris_skillet_steam.json", LIT, "同上（煎锅和厨锅放的是同一个 SteamParticle）"),
    ("rp", "sparkle.json", BRIGHT, "SparkleParticle.java:19 覆盖了 getLightColor"),
    ("rp", "arris_board_mark.json", BRIGHT, "刀口虚线 setShape(..., WHITE, true)：BoardBehavior.java:1193，glows 为真时满亮度（SceneRenderer.java:631）"),
]


def _components(pack, name):
    with io.open(os.path.join(fdtest.ROOT, pack, "particles", name), encoding="utf-8-sig") as handle:
        return json.load(handle)["particle_effect"]["components"]


def testEveryParticleWeHaveCheckedAgainstJavaFollowsOrIgnoresTheAmbientLightLikeJavaDoes():
    wrong = []
    for pack, name, want, why in TABLE:
        components = _components(pack, name)
        if want == LIT and components.get(COMPONENT) != {}:
            wrong.append("%s/%s 该跟着环境光（%s）" % (pack, name, why))
        if want == BRIGHT and COMPONENT in components:
            wrong.append("%s/%s 该满亮度（%s）" % (pack, name, why))
    assert not wrong, "\n".join(wrong)


def testTheTableCoversBothPacksAndBothKinds():
    assert {row[0] for row in TABLE} == {"diegesisRp", "rp"}
    assert {row[2] for row in TABLE} == {LIT, BRIGHT}
    names = [(row[0], row[1]) for row in TABLE]
    assert len(set(names)) == len(names), "一个文件一行"
    for pack, name, _want, _why in TABLE:
        assert os.path.isfile(os.path.join(fdtest.ROOT, pack, "particles", name)), (pack, name)


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
