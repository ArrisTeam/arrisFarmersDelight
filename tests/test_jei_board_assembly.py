# -*- coding: utf-8 -*-
# runner: both
"""JEI 的"砧板摆盘"分类（Compat/Jei/BoardAssembly.py、JeiClient.py；界面定义 rp/ui/jei_farmers_delight.json 的 jeiBoardAssemblyRecipe）。

HoD 的 JEI 插件：登记摆盘分类、把这些菜的工作台配方藏起来。这里：只在场景交互前置联动上、砧板站点开着时登记（配置里 remove_crafting_recipes 关了就不藏）；
按成品、按每样配料都查得到；老版本的 arrisJei 没有 hideRecipes 时只多出分类；一条配方画出来——打底的躺在板上、提示多一行，别的层三个一排上下居中，
用不上的格子收起，成品写个数，有几种可换的那一格轮着显示。假的 JEI 注册表、假的界面控件。
"""
from __future__ import print_function

import io
import json
import os

import prereq  # noqa: F401 - 前置包不在这个仓库里：旁边没有它就跳过（tests/prereq.py）
import panclient as C

import fdtest

world = C.install()
Engine = C.load("Client.Engine")
Board = C.load("Compat.Jei.BoardAssembly")
Client = C.load("Compat.Jei.JeiClient")
Jei = C.load("Shared.Rules.DishJei")
Mode = C.load("Shared.Rules.HandsOnMode")
UI = os.path.join(fdtest.ROOT, "rp", "ui", "jei_farmers_delight.json")
C.Comp.GetItemFormattedHoverText = lambda self, name, aux=0, showCategory=False, userData=None: "name:" + name      # 假引擎补一个：物品的整份悬浮文字


class FakeRegistry(object):
    def __init__(self, hides=True):
        self.types, self.byResult, self.byInput, self.hidden = [], {}, {}, []
        if hides:
            self.HIDE_RECIPES = True
            self.hideRecipes = lambda hiderId, recipeType, predicate: self.hidden.append((hiderId, recipeType, predicate)) or True

    def registerRecipeType(self, *args):
        self.types.append(args)
        return True

    def setRecipeByResult(self, tag, item, found):
        self.byResult[(tag, item)] = found

    def setRecipeByInput(self, tag, item, found):
        self.byInput[(tag, item)] = found


def _with(registry):
    """让 Compat/Jei/Registry 找到这个假的 JEI（没装时 ImportModule 回 None）。"""
    module = C.NS(JeiRecipeRegistry=C.NS(getInstance=lambda: registry)) if registry is not None else None
    Engine.clientApi.ImportModule = lambda name: module if name == "arrisJeiScripts.api.jei" else None
    Board._done["registered"] = False


def testTheCategoryIsRegisteredWithEveryDishByItsResultAndByEachIngredient():
    registry = FakeRegistry()
    _with(registry)
    Board.RegisterBoardAssemblyRecipes(True)
    (kind,) = registry.types
    assert kind[0] == "board_assembly" and kind[1] == ("arris:cutting_board", 0) and kind[2] == "砧板摆盘", "分类名找不到语言文件时用代码里的中文"
    assert kind[3] is Board.BoardAssemblyRecipe and kind[4] == "jei_farmers_delight.jeiBoardAssemblyRecipe" and kind[5] == 56
    recipes = Jei.recipes()
    listed = [data for found in registry.byResult.values() for data in found]
    assert len(listed) == len(recipes) and all(data["recipe"] in recipes for data in listed)
    assert len(registry.byResult[("board_assembly", ("arris:barbecue_stick", 0))]) == 1
    assert registry.byInput[("board_assembly", ("minecraft:cooked_beef", 0))][0]["recipe"]["result"] == ("arris:barbecue_stick", 0), "轮着显示的那一格里的每一样也查得到"
    assert len(registry.byInput[("board_assembly", ("minecraft:bread", 0))]) > 3, "面包打底的菜不止一道"
    assert registry.hidden == [("arris_farmers_delight:board_dishes", "crafting_table", Jei.isDishCraft)], "被拦的工作台配方藏起来"
    Board.RegisterBoardAssemblyRecipes(True)
    assert len(registry.types) == 1, "只登记一次"


def testWithoutTheSwitchOrOnAnOldJeiNothingIsHiddenAndWithoutJeiNothingHappens():
    registry = FakeRegistry()
    _with(registry)
    Board.RegisterBoardAssemblyRecipes(False)
    assert registry.types and registry.hidden == [], "配置里关了 remove_crafting_recipes：工作台照样能做，不藏"
    old = FakeRegistry(hides=False)
    _with(old)
    Board.RegisterBoardAssemblyRecipes(True)
    assert old.types and not hasattr(old, "hidden") or old.hidden == [], "老版本的 arrisJei 没有 hideRecipes：只多出分类"
    _with(None)
    Board.RegisterBoardAssemblyRecipes(True)
    assert Board._done["registered"] is False, "没装 JEI：什么都不做"


def testOnlyALinkedGameWithTheBoardStationGetsTheCategory():
    calls = []
    real = Client.RegisterBoardAssemblyRecipes
    Client.RegisterBoardAssemblyRecipes = lambda hide: calls.append(hide)
    try:
        Client._whenDecided(Mode.STANDALONE)
        Client._whenDecided(Mode.OUTDATED)
        assert calls == [], "没装前置包 / 太旧：JEI 照农夫乐事原样"
        Client._whenDecided(Mode.LINKED)
        assert calls == [True], "联动上、砧板站点开着：登记，缺省的配置藏起工作台配方"
    finally:
        Client.RegisterBoardAssemblyRecipes = real


# ---------------------------------------------------------------- 一条配方画出来

class Control(object):
    def __init__(self, path):
        self.path, self.item, self.visible, self.at, self.text, self.bag = path, None, None, None, None, None

    def asItemRenderer(self):
        return self

    def asLabel(self):
        return self

    def SetUiItem(self, name, aux, *more):
        self.item = (name, aux)

    def SetVisible(self, flag):
        self.visible = bool(flag)

    def SetPosition(self, pos):
        self.at = tuple(pos)

    def SetText(self, text):
        self.text = text

    def SetPropertyBag(self, bag):
        self.bag = dict(bag)


class Panel(object):
    def __init__(self):
        self.controls = {}

    def GetChildByPath(self, path):
        return self.controls.setdefault(path, Control(path))


def _drawn(recipe):
    panel = Panel()
    page = Board.BoardAssemblyRecipe(None, panel, {"recipe": recipe}, 0, recipe["result"])
    page.OnCreate()
    return page, panel.controls


def _item(controls, name):
    return controls["/bg/area/%s/item_cell/item/item_renderer" % name].item


def _hover(controls, name):
    return controls["/bg/area/%s/button_ref/hover/hover_text" % name].bag["#hover_text"]


def testARecipeIsDrawnWithTheBaseOnTheBoardTheLayersInRowsAndTheDishWithItsCount():
    (pie,) = [recipe for recipe in Jei.recipes() if recipe["result"][0] == "arris:apple_pie_item"]
    page, controls = _drawn(pie)
    assert _item(controls, "base") == ("arris:pie_crust", 0) and "先放在砧板上" in _hover(controls, "base"), "打底的：提示多一行"
    assert [_item(controls, "layer%d" % index)[0] for index in range(8)] == ["minecraft:wheat"] * 3 + ["minecraft:apple"] * 3 + ["minecraft:sugar"] * 2
    assert [controls["/bg/area/layer%d" % index].at for index in (0, 2, 3, 6, 7)] == [(50.0, 0.0), (86.0, 0.0), (50.0, 18.0), (50.0, 36.0), (68.0, 36.0)], \
        "三个一排，三排占满 54 高"
    assert all(controls["/bg/area/layer%d" % index].visible for index in range(8))
    assert _item(controls, "result") == ("arris:apple_pie_item", 0) and controls["/bg/area/result/item_cell/item/stack_count_label"].text == ""
    assert "先放在砧板上" not in _hover(controls, "layer0")
    (dough,) = [recipe for recipe in Jei.recipes() if recipe["result"][0] == "arris:wheat_dough" and recipe["count"] == 3]
    page, controls = _drawn(dough)
    assert controls["/bg/area/result/item_cell/item/stack_count_label"].text == "3", "一份出几个写在成品上"
    assert [controls["/bg/area/layer%d" % index].visible for index in range(8)] == [True] * 3 + [False] * 5, "用不上的格子收起"
    assert controls["/bg/area/layer0"].at == (50.0, 18.0), "一排：上下居中"


def testAPlaceWithSeveralChoicesCyclesOnTheInterval():
    (stick,) = [recipe for recipe in Jei.recipes() if recipe["result"][0] == "arris:barbecue_stick"]
    page, controls = _drawn(stick)
    first = _item(controls, "layer2")
    assert first == stick["layers"][2][0]
    placed = controls["/bg/area/layer2"].at
    controls["/bg/area/layer2"].at = None
    page.OnInterval()
    assert _item(controls, "layer2") == stick["layers"][2][1] and _item(controls, "layer0") == stick["layers"][0][0], "只有那一格换下一种"
    assert controls["/bg/area/layer2"].at is None and placed is not None, "轮播只换物品，不重摆格子"
    (sandwich,) = [recipe for recipe in Jei.recipes() if recipe["result"][0] == "arris:egg_sandwich"]
    page, controls = _drawn(sandwich)
    page.OnInterval()
    assert page.indexTurns == 0, "没有可换的：不动"


def testTheScreenDefinitionHasEveryControlTheClassTouches():
    with io.open(UI, encoding="utf-8") as handle:
        definition = json.load(handle)["jeiBoardAssemblyRecipe"]
    area = definition["controls"][0]["bg"]["controls"][0]["area"]
    assert area["size"] == [154, 54], "AssemblyLayout：154 x 54"
    names = dict((key.split("@")[0], (key, body)) for entry in area["controls"] for key, body in entry.items())
    assert sorted(names) == sorted(["board", "base", "arrow", "result"] + ["layer%d" % index for index in range(Jei.MOST_LAYERS)])
    assert names["board"][1]["offset"] == [4, 29] and names["base"][1]["offset"] == [16, 27], "板和板上的那一样"
    assert names["arrow"][1]["offset"] == [109, 19] and names["result"][1]["offset"] == [136, 18]
    assert names["result"][0].endswith("jeiOutputItemRender") and all(names["layer%d" % index][0].endswith("jeiInputItemRender") for index in range(8))
    assert all(names["layer%d" % index][1]["$bgVisible"] is True and names["layer%d" % index][1]["size"] == [18, 18] for index in range(8)), "别的层放在格子里"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
