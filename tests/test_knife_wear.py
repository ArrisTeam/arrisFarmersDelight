# -*- coding: utf-8 -*-
# runner: both
"""刀的磨损（Server/Tools.OnKnifeDurability）：实机 2026-11-26（INGAME-FACTS-1 §3）铁刀打猪一下掉 1 点（和 JE 一样），
拆一块羊毛掉 2 点（JE 的刀是 DiggerItem.mineBlock：拆方块掉 1 点），割硬度 0 的草不掉（和 JE 一样）。
多出来的那 1 点退回去，规则和煎锅同一条（SkilletRules.wearAfter）。
"""
from __future__ import print_function

import fakeengine
import fdtest

world = fakeengine.install()

Registry = fdtest.load("Server.EventRegistry")
Tools = fdtest.load("Server.Tools")
Items = fdtest.load("Server.Helpers.Items")


def _durability(name, before, after, canChange=True):
    Registry.clearAll()
    Registry.registerHandler("ItemDurabilityChangedServerEvent", match=Items.IsKnife)(Tools.OnKnifeDurability)
    args = {"entityId": "p1", "itemDict": {"newItemName": name, "newAuxValue": 0, "count": 1}, "durabilityBefore": before,
            "durability": after, "canChange": canChange}
    Registry.dispatch("ItemDurabilityChangedServerEvent", args, name)
    return args["durability"]


def testBreakingABlockWearsOneLikeJava():
    for knife in ("arris:flint_knife", "arris:iron_knife", "arris:golden_knife", "arris:diamond_knife", "arris:netherite_knife"):
        assert _durability(knife, 250, 248) == 249, knife                 # 拆羊毛：引擎 2 点 → 1 点
    assert _durability("arris:iron_knife", 250, 249) == 249                # 打生物：引擎本来就是 1 点
    assert _durability("arris:iron_knife", 100, 180) == 180                # 修复不动
    assert _durability("arris:iron_knife", 1, -1) == 0                     # 最后一下照样能坏（0 再磨就坏）


def testLeftAloneWhenTheEngineSaysItCannotChangeOrForOtherItems():
    assert _durability("arris:iron_knife", 250, 248, canChange=False) == 248
    assert _durability("minecraft:iron_sword", 250, 248) == 248


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
