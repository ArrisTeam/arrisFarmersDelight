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

以前 FD 自己的砧板碎屑、热浪没写这个组件：暗处的碎屑一样亮。
这里查的是本包（rp/particles）的粒子；前置包自己的那几个（气泡、破泡、水滴、水花、碎屑、蒸汽、闪光）在它那边的 tests/test_diegesis_particle_lighting.py。"""
from __future__ import print_function

import io
import json
import os

import fdtest

COMPONENT = "minecraft:particle_appearance_lighting"
LIT, BRIGHT = "跟着环境光", "满亮度"
TABLE = [
    # (文件, 该是什么, 依据)
    ("arris_board_dust.json", LIT, "砧板的碎屑放的是 DiegesisParticles.DUST（BoardBehavior.java:1411-1420），样式同上不 emissive"),
    ("arris_pan_heat.json", LIT, "HandsOnDelightClient.java:95-96 的 HEAT 没写 emissive"),
    ("arris_steam.json", LIT, "SteamParticle.java 没有覆盖 getLightColor"),
    ("arris_skillet_steam.json", LIT, "同上（煎锅和厨锅放的是同一个 SteamParticle）"),
    ("sparkle.json", BRIGHT, "SparkleParticle.java:19 覆盖了 getLightColor"),
    ("arris_board_mark.json", BRIGHT, "刀口虚线 setShape(..., WHITE, true)：BoardBehavior.java:1193，glows 为真时满亮度（SceneRenderer.java:631）"),
]


def _components(name):
    with io.open(os.path.join(fdtest.ROOT, "rp", "particles", name), encoding="utf-8-sig") as handle:
        return json.load(handle)["particle_effect"]["components"]


def testEveryParticleWeHaveCheckedAgainstJavaFollowsOrIgnoresTheAmbientLightLikeJavaDoes():
    wrong = []
    for name, want, why in TABLE:
        components = _components(name)
        if want == LIT and components.get(COMPONENT) != {}:
            wrong.append("%s 该跟着环境光（%s）" % (name, why))
        if want == BRIGHT and COMPONENT in components:
            wrong.append("%s 该满亮度（%s）" % (name, why))
    assert not wrong, "\n".join(wrong)


def testTheTableCoversBothKinds():
    assert {row[1] for row in TABLE} == {LIT, BRIGHT}
    names = [row[0] for row in TABLE]
    assert len(set(names)) == len(names), "一个文件一行"
    for name, _want, _why in TABLE:
        assert os.path.isfile(os.path.join(fdtest.ROOT, "rp", "particles", name)), name


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
