# -*- coding: utf-8 -*-
# runner: both
"""煎锅和炉灶的烟是同一个样式（HoD 的 HandsOnDelightClient.PAN_SMOKE，java:93-94：蒸汽的帧、染 0x58C8C6C2、大小 1.8~2.6 像素、活 1.6~2.4 秒）：
JE 里两处都放它，这里原来两套（煎锅大小 x3.0、活 1.6~2.4 秒的随机值，炉灶 x2.75、固定活 2 秒），现在只在 PanFx.PAN_SMOKE 定义一处。
前置包的蒸汽是 0.6~1.0 像素，所以大小倍数取两个区间中点的比 2.2 / 0.8。引擎是 panclient.py 里的假的。"""
from __future__ import print_function

import fdtest
import panclient as C

world = C.install()
PanFx = C.load("Compat.Diegesis.PanFx")
GrillFx = C.load("Compat.Diegesis.GrillFx")
StoveFx = C.load("Shared.Rules.HandsOn.StoveFx")
PanModelMath = fdtest.load("Shared.Rules.PanModelMath")
WHERE = (10.5, 65.0, 10.5)


def _fromThePan(times=1):
    world.reset()
    fx = PanFx.PanFx(C.POS, PanModelMath.facingOf(0))
    for _ in range(times):
        fx.play([{"type": "particle", "style": "pan_smoke", "pos": (8.0, 2.0, 8.0), "vel": (0.0, 4.0, 0.0), "spread": 0.0, "count": 1, "color": 0}])
    return [(p["id"], p["vars"]) for p in world.particles]


def _fromTheStove(times=1):
    world.reset()
    for _ in range(times):
        GrillFx.play([StoveFx.Spawn("smoke", 0, (0.0, 0.0, 0.0), (0.0, 4.0, 0.0), 0.0, 1, 0)], lambda place, offset: WHERE)
    return [(p["id"], p["vars"]) for p in world.particles]


def testThePanAndTheStoveDrawTheSameSmokeParticleWithTheSameSizeAndTint():
    (panId, pan), (stoveId, stove) = _fromThePan()[0], _fromTheStove()[0]
    assert panId == stoveId == "arris_diegesis:steam"
    for name in ("variable.scale", "variable.tint_r", "variable.tint_g", "variable.tint_b", "variable.alpha"):
        assert pan[name] == stove[name], (name, pan[name], stove[name])
    assert abs(pan["variable.scale"] - 2.2 / 0.8) < 1.0e-9, "JE 的烟（1.8~2.6）和前置包蒸汽（0.6~1.0）两个区间中点的比"
    assert (round(pan["variable.tint_r"] * 255), round(pan["variable.tint_g"] * 255), round(pan["variable.tint_b"] * 255)) == (0xC8, 0xC6, 0xC2)
    assert abs(pan["variable.alpha"] - 0x58 / 255.0) < 1.0e-9


def testBothLiveAnyTimeBetweenOnePointSixAndTwoPointFourSecondsNotAFixedTwo():
    for draw in (_fromThePan, _fromTheStove):
        lives = [vars_["variable.life"] for _, vars_ in draw(40)]
        assert all(1.6 <= life <= 2.4 for life in lives), draw.__name__
        assert len(set(round(life, 6) for life in lives)) > 10, draw.__name__ + "：每次的寿命是随机的（JE 的 life(1.6F, 2.4F)）"


def testTheStyleIsDefinedInOnePlaceAndTheStoveHasNoCopyOfIt():
    assert PanFx.STYLES["pan_smoke"] is PanFx.PAN_SMOKE
    assert GrillFx.PAN_SMOKE is PanFx.PAN_SMOKE
    assert [name for name in dir(GrillFx) if name.startswith("SMOKE_")] == [], "炉灶不再有自己的 SMOKE_SCALE / SMOKE_LIFE / SMOKE_COLOR / SMOKE_ALPHA"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
