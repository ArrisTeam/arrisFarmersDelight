# -*- coding: utf-8 -*-
# runner: both
"""厨锅的 dolorContainer 界面模型（Shared/Menus/CookingPot.py）：用库的纯逻辑部分在内存里跑，不碰引擎。

两端各建一份界面模型；格子类型、Shift 点击的去向、界面数据、动作（搜索、选食谱、换变体、添加食材）都照服务端的写法执行。
"""
from __future__ import print_function

import copy

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
    """
    执行动作并提交（成了返回 True）；被拒返回错误码。照服务端会话的写法（Session.handleCall）：被拒时工作副本整个丢掉，
    这位查看者的状态回到调用之前。
    """
    action = menu.actions[name]
    ctx = Ctx(state, viewer)
    saved = copy.deepcopy(viewer)
    try:
        action.handler(menu, ctx, *args)
    except Actions.Refused as refused:
        viewer.clear()
        viewer.update(saved)
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


def testShiftClickNeverPutsAVesselThatDoesNotFitIntoTheIngredientSlots():
    state = State(_menu())
    state.put(("vessel", 0), _item("minecraft:glass_bottle", 3))   # 容器格里是别的容器
    state.put((HOTBAR, 0), _item("minecraft:bowl", 64))
    assert _shiftClick(state, (HOTBAR, 0))   # 食材格不收只当容器的碗：照箱子的规矩换到背包的另一半
    assert state.get(("vessel", 0))["newItemName"] == "minecraft:glass_bottle"
    assert [state.get(("ingredients", index)) for index in range(6)] == [None] * 6
    assert state.get((INVENTORY, 0))["newItemName"] == "minecraft:bowl"
    # 容器格是同种但满了：同样不往食材格落
    state = State(_menu())
    state.put(("vessel", 0), _item("minecraft:bowl", 64))
    state.put((HOTBAR, 0), _item("minecraft:bowl", 10))
    assert _shiftClick(state, (HOTBAR, 0))
    assert [state.get(("ingredients", index)) for index in range(6)] == [None] * 6
    assert state.get((INVENTORY, 0))["count"] == 10 and state.get(("vessel", 0))["count"] == 64


def testShiftClickTreatsAnItemThatIsBothVesselAndIngredientAsFood():
    leaf = "arris:cabbage_leaf"   # 饺子、卷心菜卷的容器，也是别的食谱的食材
    assert Book.isAmbiguous(leaf) and not Book.isPureVessel(leaf) and Book.isPureVessel("minecraft:bowl")
    state = State(_menu())
    state.put((HOTBAR, 0), _item(leaf, 4))
    assert _shiftClick(state, (HOTBAR, 0))
    assert state.get(("vessel", 0)) is None and state.get(("ingredients", 0))["count"] == 4   # 当食材放
    # 容器格里已经放着它时才续上
    state = State(_menu())
    state.put(("vessel", 0), _item(leaf, 2))
    state.put((HOTBAR, 0), _item(leaf, 4))
    assert _shiftClick(state, (HOTBAR, 0))
    assert state.get(("vessel", 0))["count"] == 6 and state.get(("ingredients", 0)) is None


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


class _BlockEntityData(dict):
    """引擎的方块实体数据对象的替身：读缺了的键得到 None。"""

    def __missing__(self, key):
        return None


def testStateFromBlockEntityData():
    stew = {"newItemName": "minecraft:mushroom_stew", "newAuxValue": 0, "count": 2}
    state = PotMenu.stateFrom(_BlockEntityData(heatEnable=True, timer=4.0, previewItemSlot=[stew]), 10.0)
    assert state["heated"] is True and abs(state["progress"] - 0.6) < 1e-9
    assert state["preview"] == stew and state["preview"] is not stew   # 换成了普通字典
    menu = _menu()
    assert set(state) <= set(menu.data)
    for name, value in state.items():
        assert menu.data[name].encode(value) is not None or value is None


def testStateFromIsIdleWithoutHeatAWholeTimerOrMissingKeys():
    idle = PotMenu.stateFrom(_BlockEntityData(), 10.0)   # /setblock 出来的厨锅：什么键都没有
    assert idle == {"heated": False, "progress": 0.0, "preview": None}
    cold = PotMenu.stateFrom(_BlockEntityData(heatEnable=False, timer=3.0, previewItemSlot=[{}]), 10.0)
    assert cold["progress"] == 0.0 and cold["preview"] is None   # 没热源就没有进度；空的预览槽没有预览
    waiting = PotMenu.stateFrom(_BlockEntityData(heatEnable=True, timer=10.0), 10.0)
    assert waiting["progress"] == 0.0   # 计时是满值：还没开始
    assert PotMenu.stateFrom(_BlockEntityData(heatEnable=True, timer=-0.2), 10.0)["progress"] == 1.0   # 夹在 0-1 里
    assert PotMenu.stateFrom(_BlockEntityData(heatEnable=True, timer=99.0), 10.0)["progress"] == 0.0
    assert PotMenu.stateFrom(_BlockEntityData(heatEnable=True, timer=True), 10.0)["progress"] == 0.0   # 布尔不算计时


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
    assert ctx.ws.changes == {}   # 先查后做：被拒之前工作副本里一格都没动（不靠会话丢掉它）
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
    assert _call(menu, state, viewer, "addFood") == "nothing"   # 已有的格子都满了、没有要放进空格的：什么都没动


def testSearchWithTheSameTextKeepsTheSelection():
    # 边打边提交的文本框在输入结束时总会再发一次（字没变也发；点列表一行或按钮时它失去焦点）：不能把刚选中的食谱清掉
    menu = _menu()
    viewer = _viewer(menu)
    state = State(menu)
    assert _call(menu, state, viewer, "search", "蘑菇") is True
    assert _call(menu, state, viewer, "pick", 0) is True
    assert _call(menu, state, viewer, "search", "蘑菇") is True   # 同样的字：什么都不动
    assert viewer["picked"] == 0 and viewer["search"] == "蘑菇"
    assert _call(menu, state, viewer, "search", "蘑") is True   # 字变了才清掉选中
    assert viewer["picked"] == -1


def testAddFoodSkipsSourcesThatCannotLeaveTheirSlot():
    menu = _menu()
    viewer = _viewer(menu)
    _pickStew(menu, viewer, variant=0)   # 红蘑菇 ×2
    locked = _item("minecraft:red_mushroom", 5)
    locked["userData"] = {"minecraft:item_lock": {"__type__": 1, "__value__": 1}}   # 锁在格子里
    state = State(menu)
    state.put((HOTBAR, 0), locked)
    state.put((HOTBAR, 1), _item("minecraft:red_mushroom", 2))
    assert _call(menu, state, viewer, "addFood") is True
    assert state.get((HOTBAR, 0))["count"] == 5 and state.get((HOTBAR, 1)) is None   # 用的是第二堆
    state = State(menu)
    state.put((HOTBAR, 0), locked)   # 只有锁住的那一堆：拿不到
    assert _call(menu, state, viewer, "addFood") == "missing"


def testAddFoodBooksEveryTakeAgainstTheStackItComesFrom():
    menu = _menu()
    viewer = _viewer(menu)
    _pickStew(menu, viewer, variant=0)   # 红蘑菇 ×2：占两个格子，要拿两个
    state = State(menu)
    state.put((HOTBAR, 0), _item("minecraft:red_mushroom", 1))   # 一堆只有一个
    ctx = Ctx(state, viewer)
    try:
        menu.actions["addFood"].handler(menu, ctx)
        raise AssertionError("一个红蘑菇不够两格")
    except Actions.Refused as refused:
        assert refused.code == "missing"
    assert ctx.ws.changes == {}
    state.put((INVENTORY, 0), _item("minecraft:red_mushroom", 1))   # 再来一堆就够了（两堆各出一个）
    assert _call(menu, state, viewer, "addFood") is True
    assert state.get((HOTBAR, 0)) is None and state.get((INVENTORY, 0)) is None
    assert state.get(("ingredients", 0))["count"] == 1 and state.get(("ingredients", 1))["count"] == 1


def testAddFoodGivesTheRequiredIngredientsPriorityOverTopUps():
    menu = _menu()
    viewer = _viewer(menu)
    _pickStew(menu, viewer, variant=0)   # 红蘑菇 ×2
    state = State(menu)
    state.put(("ingredients", 0), _item("minecraft:red_mushroom", 2))   # 已有一格：这一格是"再加一个"
    state.put((HOTBAR, 0), _item("minecraft:red_mushroom", 1))   # 背包里只有一个：先给必须放的第二格
    assert _call(menu, state, viewer, "addFood") is True
    assert state.get(("ingredients", 0))["count"] == 2 and state.get(("ingredients", 1))["count"] == 1


def testRecipesWithTheWrongShapeAreIgnored():
    # 下游模组经联动接口追加的食谱没人校验形状；界面数据在会话的定时刷新里算，出错会让所有开着界面的人都收不到更新
    table = Recipes.CookingPotRecipeList
    broken = [{"text": "没有成品", "Recipe": [[("test:a", 0)]]},
              {"text": "变体不是列表", "Recipe": "oops", "CookResult": ("test:b", 0)},
              {"text": "食材缺 aux", "Recipe": [[("test:a",)]], "CookResult": ("test:b", 0)},
              {"text": "容器不对", "Recipe": [[("test:a", 0)]], "CookResult": ("test:b", 0), "Vessel": 7},
              {"text": "没有变体", "Recipe": [], "CookResult": ("test:b", 0)},
              None]
    count = len(table)
    table.extend(broken)
    try:
        shown = Book.visibleRecipes("")
        assert shown == list(range(count))   # 形状不对的一条都不列
        assert Book.visibleRecipes("没有") == [] and Book.recipeAt(count) is None
        assert "test:a" not in Book.ingredientNames() and 7 not in Book.vesselNames()
        menu = _menu()
        viewer = _viewer(menu)
        values = menu.viewerValues(_Instance(), viewer)
        assert len(values["recipes"]) == count
    finally:
        del table[count:]


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
