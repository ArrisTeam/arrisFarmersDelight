# -*- coding: utf-8 -*-
# runner: both
"""种植的几张名单并上 JE 农夫乐事自己的方块标签（名单原样留着，不在名单里的再看标签；Shared/Rules/ItemTags.blockListed）。

锁的事：名单里的照旧；不在名单里、带了标签的方块也算——
  farmersdelight:compost_activators   有机肥周围的催化剂（Server/OrganicCompost）
对着假引擎跑（tests/farmengine.py），标签由假口答；概率的数和 test_farm_server_glue 里的同一套。
"""
from __future__ import print_function

import fdtest
import farmengine
from farmkit import ScriptRng

LEVEL = farmengine.Level()
farmengine.install(LEVEL)

Registry = fdtest.load("Server.EventRegistry")
OrganicCompost = fdtest.load("Server.OrganicCompost")
Tags = fdtest.load("Shared.Data.Tags")
ItemTags = fdtest.load("Shared.Rules.ItemTags")

TICK = "BlockRandomTickServerEvent"


class BlockTagPort(object):
    """只答方块标签的反查：members = {标签: [方块名]}。"""

    def __init__(self, members):
        self.members = members

    def ready(self):
        return True

    def blocksOf(self, tag):
        return self.members.get(tag)

    def blockTagsOf(self, blockName):
        return None


def _tagged(tag, *names):
    ItemTags.setPort("server", BlockTagPort({tag: list(names)}))


def _reset():
    for side in ItemTags.SIDES:
        ItemTags.setPort(side, None)


def _fresh():
    LEVEL.__init__()
    _reset()
    return LEVEL


def _tick(name, pos):
    args = {"fullName": name, "blockName": name, "posX": pos[0], "posY": pos[1], "posZ": pos[2], "dimensionId": 0,
            "brightness": 15, "auxValue": 0}
    Registry.dispatch(TICK, args, name)


def _random(value, *modules, **kwargs):
    rnd = ScriptRng(randoms=[value], ints=kwargs.get("ints", ()))
    for module in modules:
        module.random = rnd


def testATaggedBlockActivatesTheCompost():
    """JE：3×3×3 里每有一个催化剂，堆沤的概率 +2%。盖住的有机肥只有自己一个催化剂时 0.07 → 0.105，再多一个 0.09 → 0.135。"""
    for tagged, advances in ((False, False), (True, True)):
        level = _fresh().put((0, 1, 0), "arris:organic_compost_stage3")
        level.fill("minecraft:stone", (-1, 4, -1), (1, 4, 1))
        level.put((1, 1, 0), "mymod:compost_starter")
        if tagged:
            _tagged(Tags.COMPOST_ACTIVATORS, "mymod:compost_starter")
        _random(0.12, OrganicCompost)
        _tick("arris:organic_compost_stage3", (0, 1, 0))
        assert (level.nameAt((0, 1, 0)) == "arris:rich_soil") == advances, tagged
    _reset()


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
