# -*- coding: utf-8 -*-
# runner: both
"""经典砧板每切一件飞的 5 颗碎屑（客户端 Client/Endpoints.PlayCrumbs，数在 Shared/Rules/BoardDust 的 CRUMB_*）。

JE：CuttingBoardBlockEntity.spawnCuttingParticles（java:148-150）在方块中心、高 0.2 处放 5 颗这件东西的物品粒子，各方向散 0.1。
基岩版没有按物品贴图碎开的粒子：用站点也用的 arris:board_dust，按这件东西的颜色（FoodColors，没有记录的用缺省色）染。
"""
from __future__ import print_function

import boardclient
import fdtest

Endpoints = fdtest.load("Client.Endpoints")
Dust = fdtest.load("Shared.Rules.BoardDust")
Colors = fdtest.load("Shared.Data.FoodColors").FoodColors
engine = boardclient.engine


def _crumbs(item="arris:cabbage", pos=(7, 64, 7), dimension=0):
    engine.reset()
    Endpoints.PlayCrumbs({"dimensionId": dimension, "blockPos": pos, "itemName": item})
    return engine.particles


def testFiveSpecksOfTheThingsColourRiseFromTheBoardCentre():
    particles = _crumbs()
    assert len(particles) == 1 and particles[0]["id"] == "arris:board_dust"
    assert particles[0]["pos"] == (7.5, 64.2, 7.5), "方块中心、高 0.2（FD 的 spawnCuttingParticles）"
    variables = particles[0]["vars"]
    color = Colors["arris:cabbage"]
    assert (variables["variable.tint_r"], variables["variable.tint_g"], variables["variable.tint_b"]) == \
        (((color >> 16) & 0xFF) / 255.0, ((color >> 8) & 0xFF) / 255.0, (color & 0xFF) / 255.0) and variables["variable.tint_set"] == 1.0
    assert variables["variable.count"] == 5.0 and variables["variable.spread"] == 0.1
    assert (variables["variable.vx"], variables["variable.vy"], variables["variable.vz"]) == (0.0, Dust.CRUMB_SPEED, 0.0)


def testAThingWithoutAColourRecordGetsTheDefaultOne():
    assert "minecraft:oak_log" not in Colors
    variables = _crumbs("minecraft:oak_log")[0]["vars"]
    color = Dust.CRUMB_COLOR
    assert variables["variable.tint_r"] == ((color >> 16) & 0xFF) / 255.0 and variables["variable.tint_b"] == (color & 0xFF) / 255.0


def testAnotherDimensionsCrumbsAreDropped():
    assert _crumbs(dimension=1) == []


def testNothingIsSetWhenTheParticleSystemIsNotReadyYet():
    """进世界头几秒粒子系统还没好：引擎回 0（不是 None），不能当编号去设变量。"""
    engine.reset()
    created = []
    engine.Create = lambda identifier, pos: created.append(identifier) or 0
    try:
        Endpoints.PlayCrumbs({"dimensionId": 0, "blockPos": (7, 64, 7), "itemName": "arris:cabbage"})
    finally:
        del engine.Create                    # 回到类里的记账版本
    assert created == ["arris:board_dust"] and engine.particles == []


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
