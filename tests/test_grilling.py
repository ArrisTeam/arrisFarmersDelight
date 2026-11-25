# -*- coding: utf-8 -*-
# runner: both
"""能煎烤什么、煎烤成什么（Shared/Rules/Grilling）：先查 CanCookedFoodDict（契约），表里没有的问引擎的营火配方。

锁的事：
  1. 表照旧是第一来源，下游追加的马上生效；没有引擎口时只认表（和以前一样）
  2. 口准备好了：表里没有的问营火配方（GetRecipesByInput(名字, "campfire", aux, 1)），按 (名字, aux) 缓存，没有配方的也记着；
     口没准备好（客户端进世界之前）只认表、不问；两个口用服务端的；口出错当没有
  3. 配方的形状没有实机记录：output / result、字符串 "名字" / "名字:aux"、dict 的名字键、列表、整份配方 JSON 都认；认不出来当没有配方，不抛
  4. 煎锅 / 炉灶站点（PanStation / GrillStation）、EnginePort.campfireRecipes 都走这里
"""
from __future__ import print_function

import fdtest

Cooking = fdtest.load("Shared.Data.Cooking")
Grilling = fdtest.load("Shared.Rules.Grilling")
Pan = fdtest.load("Shared.Rules.PanStation")
Grill = fdtest.load("Shared.Rules.GrillStation")
TagPort = fdtest.load("Shared.Rules.TagPort")

RAW, STEAK = "kaleidoscope_cookery:raw_cow_offal", "kaleidoscope_cookery:cooked_cow_offal"


class RecipePort(object):
    """Grilling 的口：recipes = {物品名: GetRecipesByInput 的返回}；calls 记问了几次。"""

    def __init__(self, recipes, ready=True, error=None):
        self.recipes = recipes
        self.isReady = ready
        self.error = error
        self.calls = 0

    def ready(self):
        return self.isReady

    def campfireRecipes(self, itemName, aux=0):
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.recipes.get(itemName)


def _reset():
    for side in Grilling.SIDES:
        Grilling.setPort(side, None)


def testTheTableComesFirstAndAloneWithoutAPort():
    _reset()
    assert Grilling.resultOf("minecraft:beef") == "minecraft:cooked_beef" and Grilling.canCook("arris:minced_beef")
    assert not Grilling.canCook(RAW) and Grilling.resultOf(None) is None and Grilling.resultOf("") is None
    Cooking.CanCookedFoodDict[RAW] = STEAK
    try:
        assert Grilling.resultOf(RAW) == STEAK, "下游往表里追加的马上生效"
    finally:
        del Cooking.CanCookedFoodDict[RAW]
    port = RecipePort({"minecraft:beef": [{"output": "mymod:other_steak"}]})
    Grilling.setPort("server", port)
    assert Grilling.resultOf("minecraft:beef") == "minecraft:cooked_beef" and port.calls == 0, "表里有的不问引擎"
    _reset()


def testOtherModsCampfireRecipesCookOnTheSkilletAndStove():
    _reset()
    port = RecipePort({RAW: [{"input": RAW + ":0", "output": STEAK + ":0", "tags": ["campfire", "furnace"]}],
                       "minecraft:stick": []})
    Grilling.setPort("server", port)
    assert Grilling.resultOf(RAW) == STEAK and Grilling.canCook(RAW, 0)
    assert not Grilling.canCook("minecraft:stick")
    for _ in range(3):
        Grilling.resultOf(RAW)
        Grilling.canCook("minecraft:stick")
    assert port.calls == 2, "按 (名字, aux) 缓存，没有配方的也记着"
    assert Pan.canFry(RAW) and Pan.friedOf(RAW) == STEAK and Pan.usable(RAW)
    assert Grill.hasRecipe(RAW) and Grill.canGrill(RAW) and Grill.isDone(STEAK), "烤好的那件没有再烤的配方"
    assert port.calls == 3
    Grilling.refresh()
    Grilling.resultOf(RAW)
    assert port.calls == 4
    _reset()


def testANotReadyPortIsNotAsked():
    """客户端进世界之前配方还没到（和标签同一个时候）：只认表，不问、不缓存；准备好以后才问。"""
    _reset()
    port = RecipePort({RAW: [{"output": STEAK}]}, ready=False)
    Grilling.setPort("client", port)
    assert Grilling.resultOf(RAW) is None and port.calls == 0
    assert Grilling.resultOf("minecraft:cod") == "minecraft:cooked_cod"
    port.isReady = True
    assert Grilling.resultOf(RAW) == STEAK and port.calls == 1
    _reset()


def testTheServerPortWinsAndABrokenPortIsNoRecipe():
    _reset()
    Grilling.setPort("client", RecipePort({RAW: [{"output": "client:steak"}]}))
    Grilling.setPort("server", RecipePort({RAW: [{"output": "server:steak"}]}))
    assert Grilling.resultOf(RAW) == "server:steak"
    Grilling.setPort("server", RecipePort({}, error=RuntimeError("engine")))
    assert Grilling.resultOf(RAW) is None and Grilling.resultOf("minecraft:beef") == "minecraft:cooked_beef"
    try:
        Grilling.setPort("both", None)
    except ValueError:
        pass
    else:
        raise AssertionError("端只有 server / client")
    _reset()


def testTheShapesItReads():
    shapes = [
        [{"output": "mymod:steak"}],
        [{"output": "mymod:steak:0"}],
        [{"output": {"item": "mymod:steak", "count": 2}}],
        [{"output": {"itemName": "mymod:steak", "auxValue": 0}}],
        [{"result": [{"item": "mymod:steak", "data": 0}]}],
        [{"result": {"newItemName": "mymod:steak"}}],
        [{"minecraft:recipe_furnace": {"input": {"item": RAW}, "output": {"item": "mymod:steak"}, "tags": ["campfire"]}}],
        [{"output": {"item": ["mymod:steak", "mymod:other"]}}],
        [{"output": 7}, {"output": "mymod:steak"}],
        ({"output": "mymod:steak"},),
    ]
    for recipes in shapes:
        assert Grilling.cookedOf(recipes, RAW) == "mymod:steak", recipes
    assert Grilling.cookedOf([{"output": "steak"}]) == "minecraft:steak", "没写命名空间的是原版"
    for recipes in (None, "mymod:steak", 3, [], [None], [42], [{"output": None}], [{"output": 3}], [{"tags": ["campfire"]}],
                    [{"output": ""}], [{"output": "a:b:c"}], [{"output": RAW}], {"output": "mymod:steak"}):
        assert Grilling.cookedOf(recipes, RAW) is None, recipes


class FakeRecipeComp(object):
    def __init__(self):
        self.asked = []

    def GetRecipesByInput(self, inputIdentifier, tag, aux=0, maxResultNum=-1):
        self.asked.append((inputIdentifier, tag, aux, maxResultNum))
        return [{"output": STEAK}] if inputIdentifier == RAW else []


def testTheEnginePortAsksForCampfireRecipes():
    comp = FakeRecipeComp()
    port = TagPort.EnginePort(lambda: object(), recipes=lambda: comp)
    assert port.campfireRecipes(RAW, 0) == [{"output": STEAK}] and port.campfireRecipes("minecraft:stick") == []
    assert comp.asked == [(RAW, "campfire", 0, 1), ("minecraft:stick", "campfire", 0, 1)]
    assert TagPort.EnginePort(lambda: object()).campfireRecipes(RAW) is None, "没有配方组件"

    class Odd(object):
        def GetRecipesByInput(self, *args):
            return "not a list"
    assert TagPort.EnginePort(lambda: object(), recipes=Odd).campfireRecipes(RAW) is None


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
