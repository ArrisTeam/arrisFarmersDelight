# -*- coding: utf-8 -*-
# runner: both
"""厨锅里的料各是什么颜色、倒进去的液体什么时候染水（Shared/Rules/PotTint.py，HoD 的 FoodColors.of 和 PotBehavior.colour 的 waiting）。"""
from __future__ import print_function

import fdtest

Tint = fdtest.load("Shared.Rules.PotTint")
Brothy = fdtest.load("Shared.Data.BrothColors")
Food = fdtest.load("Shared.Data.FoodColors").FoodColors


def item(name, count=1):
    return {"newItemName": name, "newAuxValue": 0, "count": count}


def channels(rgb):
    return (rgb >> 16) & 0xFF, (rgb >> 8) & 0xFF, rgb & 0xFF


def testALiquidTakesItsContainersColourAnEggYolkAndWhiteTheRestTheirIcon():
    # FoodColors.java:41-46：poured 取 liquidColor，cracked 取 EGG，其余取图标的加权平均
    assert min(channels(Tint.colorOf("minecraft:milk_bucket"))) >= 0xF0, "牛奶是白的，不是桶的灰"
    assert Tint.colorOf("arris:tomato_sauce") == Brothy.PouredColors["arris:tomato_sauce"] != Food["arris:tomato_sauce"], "番茄酱是液色，不是瓶的图标平均"
    assert Tint.colorOf("arris:milk_bottle") == Brothy.PouredColors["arris:milk_bottle"] != Food["arris:milk_bottle"]
    assert Tint.colorOf("minecraft:egg") == 0xF2DC9A == Brothy.RAW_EGG != Food["minecraft:egg"], "蛋是蛋黄加蛋白，不是整只蛋的图标平均"
    assert Tint.colorOf("minecraft:carrot") == Food["minecraft:carrot"]
    assert Tint.colorOf("mod:nothing_like_it") == Brothy.FALLBACK == 0xB0A070


def testOnlyAPouredLiquidTintsTheWaterAnEggDoesNot():
    tint = Tint.Tint()
    items = [item("minecraft:carrot"), item("minecraft:milk_bucket"), item("minecraft:egg"), None, None, None]
    assert tint.liquids(items, frozenset([1, 2])) == [Brothy.PouredColors["minecraft:milk_bucket"]], "蛋不染水"
    assert tint.liquids(items, frozenset([2])) == []


def testALiquidThatIsStillBeingCarriedWaitsForItsPourToFlow():
    tint = Tint.Tint()
    items = [None, item("minecraft:milk_bucket"), item("minecraft:egg"), None, None, None]
    tint.put(1, "minecraft:milk_bucket")
    tint.put(2, "minecraft:egg")
    assert tint.waiting == set([1]), "蛋没有倒的过程，不等"
    assert tint.liquids(items, frozenset([1, 2])) == [], "手还端着、没开始流：不染"
    assert tint.release(1) is True, "开始流了：要重算汤色"
    assert tint.liquids(items, frozenset([1, 2])) == [Brothy.PouredColors["minecraft:milk_bucket"]]
    assert tint.release(1) is False and tint.release(2) is False, "已经不等了：没有变化"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
