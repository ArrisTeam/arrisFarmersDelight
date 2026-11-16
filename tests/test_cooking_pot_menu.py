# -*- coding: utf-8 -*-
# runner: both
"""厨锅的 dolorContainer 界面模型（Shared/Menus/CookingPot.py）：用库的纯逻辑部分在内存里跑，不碰引擎。

两端各建一份界面模型；格子类型、Shift 点击的去向、界面数据、动作（搜索、选食谱、换变体、添加食材）都照服务端的写法执行。
"""
from __future__ import print_function

import fdtest

Book = fdtest.load("Shared.Rules.CookingPotBook")
PotMenu = fdtest.load("Shared.Menus.CookingPot")
Recipes = fdtest.load("Shared.Data.CookingPotRecipes")
Actions = fdtest.load("dolorContainer.Common.Actions")
Collections = fdtest.load("dolorContainer.Common.Collections")
Items = fdtest.load("dolorContainer.Common.Items")
Libs = fdtest.load("dolorContainer.Common.Menus")
Rules = fdtest.load("dolorContainer.Common.Rules")
BlockCommon = fdtest.load("dolorContainer.Std.Block.Common")
Operations = fdtest.load("dolorContainer.Std.Operations")
fdtest.load("dolorContainer.Std.Defaults")   # 库的缺省实现（标准交互、操作）随之登记，与游戏里一样

RULES = Items.ItemRules(lambda name, aux: 64)
HOTBAR, INVENTORY, COMBINED = Collections.HOTBAR, Collections.INVENTORY, Collections.COMBINED
STEW = Recipes.CookingPotRecipeList[0]   # 蘑菇煲：红蘑菇 ×2 / 棕蘑菇 ×2 / 红 + 棕，碗盛


def _menu(side=Libs.SERVER):
    return Libs.create(PotMenu.MENU, {}, side, RULES)


def _item(name, count=1, aux=0):
    return {"newItemName": name, "newAuxValue": aux, "count": count}


class State(Rules.SlotState):
    """界面模型的全部容器放在一张字典里：{容器格: 物品堆}。"""

    def __init__(self, menu, data=None):
        self.menu = menu
        self.structure = menu.structure
        self.slots = {}
        self._data = data or {}

    def put(self, ref, stack):
        self.slots[self.structure.locate(ref)] = Items.normalize(stack)

    def read(self, key):
        return self.slots.get(key)

    def dataValue(self, name):
        return self._data.get(name)

    def get(self, ref):
        return Rules.Workspace(self, RULES).get(ref)

    def apply(self, workspace):
        for key, stack in workspace.changes.items():
            if stack is None:
                self.slots.pop(key, None)
            else:
                self.slots[key] = stack


class Ctx(object):
    """动作拿到的上下文（服务端会话的 ActionContext 的最小替身）。"""

    def __init__(self, state, viewer):
        self.ws = Rules.Workspace(state, RULES)
        self.viewer = viewer


def _viewer(menu):
    viewer = dict((name, field.empty) for name, field in menu.viewerState.items())
    viewer.update(menu.allViewerInitial(None, "p"))
    return viewer


def _call(menu, state, viewer, name, *args):
    """执行动作并提交（成了返回 True）；被拒返回错误码。"""
    action = menu.actions[name]
    ctx = Ctx(state, viewer)
    try:
        action.handler(menu, ctx, *args)
    except Actions.Refused as refused:
        return refused.code
    state.apply(ctx.ws)
    return True


def _pickStew(menu, viewer, variant=0):
    state = State(menu)
    assert _call(menu, state, viewer, "search", "蘑菇") is True
    shown = Book.visibleRecipes("蘑菇")
    assert _call(menu, state, viewer, "pick", shown.index(0)) is True
    viewer["variant"] = variant


# ---------------------------------------------------------------- 结构

def testBuildsOnBothSidesWithTheEightEngineSlots():
    for side in (Libs.SERVER, Libs.CLIENT):
        menu = _menu(side)
        structure = menu.structure
        pot = structure.containers["pot"]
        assert (pot.kind, pot.size) == (BlockCommon.ENGINE_CONTAINER, Book.POT_SLOTS)
        assert structure.locate(("ingredients", 5)) == ("pot", 5)
        assert structure.locate(("vessel", 0)) == ("pot", Book.VESSEL_SLOT)
        assert structure.locate(("output", 0)) == ("pot", Book.RESULT_SLOT)
        assert [structure.get(name).size for name in ("ingredients", "vessel", "output", "book")] == [6, 1, 1, 8]
        assert set(menu.actions) == {"search", "pick", "nextVariant", "addFood"}
        assert menu.dataEvery == PotMenu.DATA_EVERY and menu.layout == PotMenu.MENU


def testOutputTakesNothingAndOtherSlotsTakeAnything():
    state = State(_menu())
    ws = Rules.Workspace(state, RULES)
    carrot = Items.normalize(_item("minecraft:carrot"))
    assert not ws.canPlace(("output", 0), carrot)
    assert ws.canPlace(("ingredients", 0), carrot)
    assert ws.canPlace(("vessel", 0), carrot)   # 手动放什么都收（与旧界面一致），Shift 点击才挑
    assert not ws.canPlace(("book", 0), carrot)   # 食谱书的详情格只看，不能放


# ---------------------------------------------------------------- Shift 点击

def _shiftClick(state, ref, profile=Collections.PROFILE_CLASSIC):
    ws = Rules.Workspace(state, RULES)
    moved = Operations.routeQuickMove(ws, ref, profile)
    state.apply(ws)
    return moved


def testShiftClickPutsAKnownVesselInTheVesselSlotAndFoodInTheIngredientSlots():
    state = State(_menu())
    state.put((HOTBAR, 0), _item("minecraft:bowl", 4))
    state.put((HOTBAR, 1), _item("minecraft:carrot", 5))
    assert _shiftClick(state, (HOTBAR, 0))
    assert state.get(("vessel", 0))["count"] == 4 and state.get((HOTBAR, 0)) is None
    assert _shiftClick(state, (HOTBAR, 1))
    assert state.get(("vessel", 0))["newItemName"] == "minecraft:bowl"   # 胡萝卜没有被塞进容器格
    assert state.get(("ingredients", 0))["newItemName"] == "minecraft:carrot"


def testShiftClickNeverFillsTheVesselSlotWithFood():
    state = State(_menu())
    for index in range(6):   # 食材格全占满
        state.put(("ingredients", index), _item("minecraft:potato"))
    state.put((HOTBAR, 0), _item("minecraft:carrot", 3))
    assert _shiftClick(state, (HOTBAR, 0))
    assert state.get(("vessel", 0)) is None   # 食材格满了也不会往容器格里塞，余下的换到背包的另一半（与箱子一样）
    assert state.get((HOTBAR, 0)) is None and state.get((INVENTORY, 0))["count"] == 3


def testShiftClickTakesTheOutputBackToTheInventory():
    state = State(_menu())
    state.put(("output", 0), _item("minecraft:mushroom_stew", 3))
    assert _shiftClick(state, ("output", 0))
    assert state.get(("output", 0)) is None
    assert state.get((HOTBAR, 0))["newItemName"] == "minecraft:mushroom_stew"


def testShiftClickInThePocketProfileUsesTheCombinedInventory():
    state = State(_menu())
    state.put((COMBINED, 20), _item("minecraft:bowl", 2))
    assert _shiftClick(state, (COMBINED, 20), Collections.PROFILE_POCKET)
    assert state.get(("vessel", 0))["count"] == 2


# ---------------------------------------------------------------- 界面数据

class _Instance(object):
    key = "0:1:2:3"


def testDataValuesComeFromTheRegisteredStateReader():
    menu = _menu()
    seen = []
    sample = {"heated": True, "progress": 0.5, "preview": _item("minecraft:mushroom_stew", 2)}
    PotMenu.setStateReader(lambda key: seen.append(key) or sample)
    try:
        values = menu.dataValues(_Instance())
    finally:
        PotMenu.setStateReader(None)
    assert seen == ["0:1:2:3"] and values == sample
    for name, value in values.items():
        assert menu.data[name].encode(value) is not None   # 声明过、编码得出来
    assert menu.dataValues(_Instance()) == {}   # 没登记读数函数（客户端）时什么都不给


def testViewerStartsWithNothingSelectedAndTheWholeList():
    menu = _menu()
    viewer = _viewer(menu)
    assert viewer == {"picked": -1, "variant": 0, "search": ""}
    values = menu.viewerValues(_Instance(), viewer)
    assert len(values["recipes"]) == len(Recipes.CookingPotRecipeList)
    assert values["book"] == {} and values["bookTitle"] == "请选择食谱" and values["bookVariant"] == ""
    for name, value in values.items():
        assert menu.data[name].scope == "viewer"
        assert menu.data[name].encode(value) is not None


def testViewerValuesShowTheSelectedVariant():
    menu = _menu()
    viewer = _viewer(menu)
    _pickStew(menu, viewer, variant=1)
    values = menu.viewerValues(_Instance(), viewer)
    assert values["bookTitle"] == STEW["text"]
    assert values["bookVariant"] == "2 / %d" % len(STEW["Recipe"])
    assert values["book"][0]["newItemName"] == STEW["Recipe"][1][0][0]
    assert values["book"][Book.VESSEL_SLOT]["newItemName"] == "minecraft:bowl"
    assert values["book"][Book.RESULT_SLOT]["newItemName"] == "minecraft:mushroom_stew"
    assert len(values["recipes"]) == len(Book.visibleRecipes("蘑菇"))


# ---------------------------------------------------------------- 动作

def testSearchResetsTheSelection():
    menu = _menu()
    viewer = _viewer(menu)
    state = State(menu)
    viewer.update(picked=3, variant=2)
    assert _call(menu, state, viewer, "search", "汤") is True
    assert viewer == {"picked": -1, "variant": 0, "search": "汤"}


def testPickChecksTheIndexAgainstTheFilteredList():
    menu = _menu()
    viewer = _viewer(menu)
    state = State(menu)
    assert _call(menu, state, viewer, "pick", 0) is True and viewer["picked"] == 0
    assert _call(menu, state, viewer, "pick", len(Recipes.CookingPotRecipeList)) == "no_recipe"
    assert viewer["picked"] == 0   # 被拒时不改
    _call(menu, state, viewer, "search", "绝对没有这道菜")
    assert _call(menu, state, viewer, "pick", 0) == "no_recipe"


def testNextVariantCyclesAndNeedsASelection():
    menu = _menu()
    viewer = _viewer(menu)
    state = State(menu)
    assert _call(menu, state, viewer, "nextVariant") == "no_recipe"
    _pickStew(menu, viewer)
    count = len(STEW["Recipe"])
    assert count > 1
    seen = []
    for _ in range(count):
        assert _call(menu, state, viewer, "nextVariant") is True
        seen.append(viewer["variant"])
    assert seen == [(index + 1) % count for index in range(count)]   # 一圈回到第一个


def testAddFoodMovesOneOfEachIngredientFromTheInventory():
    menu = _menu()
    viewer = _viewer(menu)
    _pickStew(menu, viewer, variant=0)   # 红蘑菇 ×2：同种食材要占两个格子
    state = State(menu)
    state.put((INVENTORY, 3), _item("minecraft:red_mushroom", 5))
    assert _call(menu, state, viewer, "addFood") is True
    assert state.get(("ingredients", 0)) == Items.normalize(_item("minecraft:red_mushroom"))
    assert state.get(("ingredients", 1)) == Items.normalize(_item("minecraft:red_mushroom"))
    assert state.get(("ingredients", 2)) is None
    assert state.get((INVENTORY, 3))["count"] == 3   # 一共拿走两个


def testAddFoodTakesDifferentIngredientsFromDifferentStacksInSlotOrder():
    menu = _menu()
    viewer = _viewer(menu)
    _pickStew(menu, viewer, variant=2)   # 红蘑菇 + 棕蘑菇
    state = State(menu)
    state.put((HOTBAR, 8), _item("minecraft:brown_mushroom", 1))
    state.put((INVENTORY, 0), _item("minecraft:red_mushroom", 1))
    assert _call(menu, state, viewer, "addFood") is True
    placed = sorted(state.get(("ingredients", index))["newItemName"] for index in (0, 1))
    assert placed == ["minecraft:brown_mushroom", "minecraft:red_mushroom"]
    assert state.get((HOTBAR, 8)) is None and state.get((INVENTORY, 0)) is None


def testAddFoodIsAllOrNothingWhenAnIngredientIsMissing():
    menu = _menu()
    viewer = _viewer(menu)
    _pickStew(menu, viewer, variant=2)
    state = State(menu)
    state.put((HOTBAR, 0), _item("minecraft:red_mushroom", 4))   # 没有棕蘑菇
    ctx = Ctx(state, viewer)
    try:
        menu.actions["addFood"].handler(menu, ctx)
        raise AssertionError("应该被拒")
    except Actions.Refused as refused:
        assert refused.code == "missing"
    # 被拒的动作整体不提交：会话丢掉这份工作副本，真实格子原样
    assert state.get((HOTBAR, 0))["count"] == 4 and state.get(("ingredients", 0)) is None


def testAddFoodTopsUpAnExistingIngredientSlotAndLeavesFullOnesAlone():
    menu = _menu()
    viewer = _viewer(menu)
    _pickStew(menu, viewer, variant=0)
    state = State(menu)
    state.put(("ingredients", 0), _item("minecraft:red_mushroom", 2))
    state.put((HOTBAR, 0), _item("minecraft:red_mushroom", 9))
    assert _call(menu, state, viewer, "addFood") is True
    assert state.get(("ingredients", 0))["count"] == 3   # 已有的格子再加一个
    assert state.get(("ingredients", 1))["count"] == 1   # 第二个红蘑菇另占一格
    assert state.get((HOTBAR, 0))["count"] == 7
    # 已经有一格是满的：不影响其余食材的放入
    state.put(("ingredients", 0), _item("minecraft:red_mushroom", 64))
    state.put((HOTBAR, 0), _item("minecraft:red_mushroom", 9))
    state.put(("ingredients", 1), None)
    assert _call(menu, state, viewer, "addFood") is True
    assert state.get(("ingredients", 0))["count"] == 64
    assert state.get(("ingredients", 1))["count"] == 1


def testAddFoodRefusesWhenThereAreNoFreeSlotsOrNothingIsSelected():
    menu = _menu()
    viewer = _viewer(menu)
    state = State(menu)
    assert _call(menu, state, viewer, "addFood") == "no_recipe"
    _pickStew(menu, viewer, variant=0)
    for index in range(6):
        state.put(("ingredients", index), _item("minecraft:potato"))
    state.put((HOTBAR, 0), _item("minecraft:red_mushroom", 4))
    assert _call(menu, state, viewer, "addFood") == "no_room"


def testAddFoodDoesNothingWhenEverythingIsAlreadyThereAndFull():
    menu = _menu()
    viewer = _viewer(menu)
    _pickStew(menu, viewer, variant=2)
    state = State(menu)
    state.put(("ingredients", 0), _item("minecraft:red_mushroom", 64))
    state.put(("ingredients", 1), _item("minecraft:brown_mushroom", 64))
    state.put((HOTBAR, 0), _item("minecraft:red_mushroom", 4))
    assert _call(menu, state, viewer, "addFood") == "full"


def testActionsOnlyTakeValuesFromTheirSchema():
    # 客户端只能发：搜索词（文字，限长）、列表序号（整数范围）；添加食材、换变体不带任何参数（选了哪个只认服务端会话里记的）
    menu = _menu()
    assert menu.actions["addFood"].fields == () and menu.actions["nextVariant"].fields == ()
    assert len(menu.actions["pick"].fields) == 1 and len(menu.actions["search"].fields) == 1


def testCompiledLayoutIsRegisteredForBothProfiles():
    table = fdtest.load("dolorLayouts").LAYOUTS
    layout = table[PotMenu.MENU]
    assert layout["menu"] == PotMenu.MENU
    assert set(layout["screens"]) == {"classic", "pocket"}


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
