# -*- coding: utf-8 -*-
# runner: both
"""煎锅和炉灶的烟是同一个样式（HoD 的 HandsOnDelightClient.PAN_SMOKE，java:93-94：蒸汽的帧、染 0x58C8C6C2、大小 1.8~2.6 像素、活 1.6~2.4 秒、重力 -4、阻力 0.75、长大 3 倍、
摆动 1、渐显 0.3、不 emissive）：JE 里两处都放它，这里原来两套（煎锅大小 x3.0、活 1.6~2.4 秒的随机值，炉灶 x2.75、固定活 2 秒），后来都借前置包满亮度的蒸汽乘倍数，
现在是本包自己的粒子 arris:pan_smoke（rp/particles/arris_pan_smoke.json，数写在粒子里，tests/test_pan_smoke_particle.py 逐项对），只在 PanFx.PAN_SMOKE 定义一处。
引擎是 panclient.py 里的假的。"""
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


def testThePanAndTheStoveDrawTheSameSmokeParticleWithTheSameTint():
    (panId, pan), (stoveId, stove) = _fromThePan()[0], _fromTheStove()[0]
    assert panId == stoveId == "arris:pan_smoke", "本包自己的粒子，不是前置包的蒸汽"
    for name in ("variable.scale", "variable.tint_r", "variable.tint_g", "variable.tint_b", "variable.alpha"):
        assert pan[name] == stove[name], (name, pan[name], stove[name])
    assert pan["variable.scale"] == 1.0, "大小（1.8~2.6 像素）写在粒子里，不再乘倍数"
    assert (round(pan["variable.tint_r"] * 255), round(pan["variable.tint_g"] * 255), round(pan["variable.tint_b"] * 255)) == (0xC8, 0xC6, 0xC2)
    assert abs(pan["variable.alpha"] - 0x58 / 255.0) < 1.0e-9


def testBothLeaveTheLifeToTheParticleWhichPicksAnyTimeBetweenOnePointSixAndTwoPointFourSeconds():
    """寿命（JE 的 life(1.6F, 2.4F)）每颗各掷，写在粒子里：脚本不再给 variable.life。"""
    for draw in (_fromThePan, _fromTheStove):
        assert all("variable.life" not in vars_ for _, vars_ in draw(5)), draw.__name__


def testTheStyleIsDefinedInOnePlaceAndTheStoveHasNoCopyOfIt():
    assert PanFx.STYLES["pan_smoke"] is PanFx.PAN_SMOKE
    assert GrillFx.PAN_SMOKE is PanFx.PAN_SMOKE
    assert PanFx.PAN_SMOKE == ("arris:pan_smoke", 0x58C8C6C2, 1.0, None)
    assert [name for name in dir(GrillFx) if name.startswith("SMOKE_")] == [], "炉灶不再有自己的 SMOKE_SCALE / SMOKE_LIFE / SMOKE_COLOR / SMOKE_ALPHA"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
