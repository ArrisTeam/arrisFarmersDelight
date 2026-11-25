# -*- coding: utf-8 -*-
# runner: both
"""标签的游戏内自检（Server/Debug/McdkTagsTest.py、Client/Debug/McdkTagsTest.py）离线能跑通、报得出差：引擎口换成假的（答的是静态表，
外加别的包登记的一件），全部 ok；口少了本包登记的成员时 ok 是假、报出是哪个标签。真正的数在游戏里跑（见两个文件的说明）。"""
from __future__ import print_function

import sys
import types

import fakeengine
import fdtest

fakeengine.install()
Tags = fdtest.load("Shared.Data.Tags")
ItemTags = fdtest.load("Shared.Rules.ItemTags")
Grilling = fdtest.load("Shared.Rules.Grilling")
ServerTest = fdtest.load("Server.Debug.McdkTagsTest")
ServerPort = fdtest.load("Server.Helpers.Tags")


def _loadClient():
    engine = types.ModuleType(fdtest.SCRIPTS + ".Client.Engine")
    engine.compFactory, engine.levelId = object(), "level"
    saved = sys.modules.get(engine.__name__)
    sys.modules[engine.__name__] = engine
    try:
        return fdtest.load("Client.Debug.McdkTagsTest"), fdtest.load("Client.Tags")
    finally:
        if saved is not None:
            sys.modules[engine.__name__] = saved
        else:
            sys.modules.pop(engine.__name__, None)


ClientTest, ClientPort = _loadClient()


class FullPort(object):
    """引擎口：答的是静态表（番茄里多一件别的包的），drop = (标签, 成员) 时少答那一件。"""

    def __init__(self, drop=None):
        self.drop = drop
        self.probes, self.firstProbeAt, self.readyAt = 1, 10.0, 12.5

    def ready(self):
        return True

    def itemsOf(self, tag):
        members = [name for name in (Tags.ITEM_TAGS.get(tag) or Tags.VANILLA_TAGS.get(tag) or ()) if (tag, name) != self.drop]
        return tuple(members) + (("mymod:tomato",) if tag == Tags.TOMATO else ())

    def blocksOf(self, tag):
        return tuple(Tags.BLOCK_TAGS.get(tag, ()))

    def tagsOf(self, itemName, aux=0):
        return tuple(tag for tag, members in Tags.ITEM_TAGS.items() if itemName in members)

    def blockTagsOf(self, blockName):
        return tuple(tag for tag, members in Tags.BLOCK_TAGS.items() if blockName in members)

    def campfireRecipes(self, itemName, aux=0):
        return [{"output": "minecraft:cooked_beef:0"}] if itemName == "minecraft:beef" else []


def _reset():
    for side in ItemTags.SIDES:
        ItemTags.setPort(side, None)
        Grilling.setPort(side, None)


def testTheServerSelfTestsPassOnAFullEngine():
    saved = ServerPort.PORT
    ServerPort.PORT = FullPort()
    try:
        members = ServerTest.mcdk_test_tags_members()
        assert members["ok"] and members["items"][Tags.TOMATO]["extra"] == ["mymod:tomato"], members["missing"]
        assert ServerTest.mcdk_test_tags_knives()["ok"]
        campfire = ServerTest.mcdk_test_tags_campfire()
        assert campfire["ok"] and campfire["recipes"]["minecraft:beef"]["parsed"] == "minecraft:cooked_beef"
        assert campfire["recipes"]["arris:minced_beef"]["result"] == "arris:beef_patty", "表里有的照表"
        assert ServerTest.mcdk_test_tags_heat()["ok"]
        ServerPort.PORT = FullPort(drop=(Tags.RAW_BEEF, "minecraft:beef"))
        members = ServerTest.mcdk_test_tags_members()
        assert not members["ok"] and members["missing"] == [Tags.RAW_BEEF], members["missing"]
        assert members["items"][Tags.RAW_BEEF]["missing"] == ["minecraft:beef"]
    finally:
        ServerPort.PORT = saved
        _reset()


def testTheClientSelfTestReportsItsTimeline():
    saved = ClientPort.PORT
    ClientPort.PORT = FullPort()
    try:
        result = ClientTest.mcdk_test_tags_client()
        assert result["ok"], result["missing"]
        assert result["timing"]["probes"] == 1 and result["timing"]["secondsAfterLoad"] == 12.5 - ClientPort.LOADED_AT
        assert result["beefCampfire"]["parsed"] == "minecraft:cooked_beef" and all(result["knives"].values())
    finally:
        ClientPort.PORT = saved
        _reset()


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
