# -*- coding: utf-8 -*-
# runner: both
"""厨锅的 dolorContainer 界面模型（Shared/Menus/CookingPot.py、PotRecipes.py、PotFill.py）：用库的纯逻辑部分在内存里跑，不碰引擎。

两端各建一份界面模型；格子类型、两种界面档的 Shift 点击与双击收集、食谱格（算出的格子：客户端按这一端的搜索过滤，服务端给空）、
选中的底格（按行号画）、点一格发的是行号、界面数据（详情的写法按注入的钟轮换）、动作（搜索、选食谱、添加食材）都照服务端的写法执行；
两个客户端问到的显示名不一样时，各自搜到、点中的是同一道菜。
"""
from __future__ import print_function

import copy
import time

import fdtest

Book = fdtest.load("Shared.Rules.CookingPotBook")
Search = fdtest.load("Shared.Rules.PotSearch")
Names = fdtest.load("Shared.Rules.ItemNames")
PotRules = fdtest.load("Shared.Rules.CookingPot")
PotMenu = fdtest.load("Shared.Menus.CookingPot")
Recipes = fdtest.load("Shared.Data.CookingPotRecipes")
Actions = fdtest.load("dolorContainer.Common.Actions")
Collections = fdtest.load("dolorContainer.Common.Collections")
Items = fdtest.load("dolorContainer.Common.Items")
Libs = fdtest.load("dolorContainer.Common.Menus")
Rules = fdtest.load("dolorContainer.Common.Rules")
BlockCommon = fdtest.load("dolorContainer.Std.Block.Common")
Operations = fdtest.load("dolorContainer.Std.Operations")
StdSlots = fdtest.load("dolorContainer.Std.Slots")
fdtest.load("dolorContainer.Std.Defaults")   # 库的缺省实现（标准交互、操作）随之登记，与游戏里一样

RULES = Items.ItemRules(lambda name, aux: 64)
HOTBAR, INVENTORY, COMBINED = Collections.HOTBAR, Collections.INVENTORY, Collections.COMBINED
CLASSIC, POCKET = Collections.PROFILE_CLASSIC, Collections.PROFILE_POCKET
RECIPES = PotMenu.RECIPES
RED, BROWN = ("minecraft:red_mushroom", 0), ("minecraft:brown_mushroom", 0)
# 夹具配方（不依赖真配方表，插在表头 = 下标 0）：红蘑菇 ×2 / 棕蘑菇 ×2 / 红 + 棕，碗盛
STEW = {"Recipe": [[RED] * 2, [BROWN] * 2, [RED, BROWN]],
        "CookResult": ("minecraft:mushroom_stew", 0), "Vessel": ("minecraft:bowl", 0), "PushItem": [], "text": u"测试蘑菇煲"}
# 卷心菜叶在 FD 1.3.4 里只是食材；拿它当容器的夹具配方造出"既是容器又是食材"的东西
WRAP = {"Recipe": [[("test:filling", 0)]], "CookResult": ("test:wrap", 0), "Vessel": ("arris:cabbage_leaf", 0),
        "PushItem": [], "text": u"测试卷"}
# 一种写法要三格（放不下时 no_room），另一种只要一样背包里没有的东西（missing）
MIX = {"Recipe": [[("test:a", 0)] * 3, [("test:b", 0)]], "CookResult": ("test:mix", 0), "PushItem": [], "text": u"测试混合"}
Recipes.CookingPotRecipeList.insert(0, STEW)
Recipes.CookingPotRecipeList.extend([WRAP, MIX])


def _menu(side=Libs.SERVER):
    return Libs.create(PotMenu.MENU, {}, side, RULES)


def _item(name, count=1, aux=0):
    return {"newItemName": name, "newAuxValue": aux, "count": count}


class State(Rules.SlotState):
    """界面模型的全部容器放在一张字典里：{容器格: 物品堆}；viewer 是这位查看者的状态（算出的食谱格读它）。"""

    def __init__(self, menu, data=None, viewer=None):
        self.menu = menu
        self.structure = menu.structure
        self.slots = {}
        self._data = data or {}
        self.viewer = viewer

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


class View(object):
    """客户端预测拿到的那一份（只用到 viewer）。"""

    def __init__(self, viewer):
        self.viewer = viewer


class Clock(object):
    """注入给写法轮换的钟。"""

    def __init__(self, now):
        self.now = now

    def __call__(self):
        return self.now


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


def _refusal(menu, state, viewer):
    """addFood 被拒的错误码，并核对被拒之前工作副本里一格都没动（先查后做，不靠会话丢掉它）。"""
    ctx = Ctx(state, viewer)
    try:
        menu.actions["addFood"].handler(menu, ctx)
    except Actions.Refused as refused:
        assert ctx.ws.changes == {}, ctx.ws.changes
        return refused.code
    raise AssertionError("应该被拒")


def _pick(menu, viewer, word, index):
    """搜 word（这一端的食谱格里看得到表里第 index 条），再选中它：pick 的参数是行号。"""
    state = State(menu)
    assert _call(menu, state, viewer, "search", word) is True
    assert index in Search.rows(word), (word, index)
    assert _call(menu, state, viewer, "pick", index) is True


def _pickStew(menu, viewer):
    _pick(menu, viewer, "蘑菇", 0)


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
        sizes = [structure.get(name).size for name in ("ingredients", "vessel", "output", "book", RECIPES)]
        assert sizes == [6, 1, 1, Book.BOOK_CELLS, PotMenu.RECIPE_CAPACITY]
        assert set(menu.actions) == {"search", "pick", "addFood"}
        assert menu.dataEvery == PotMenu.DATA_EVERY and menu.layout == PotMenu.MENU
        assert not menu.clientState, "携带版的两页签没有了，客户端界面状态也就没有了"


def testTheRecipeGridHoldsFarMoreThanTheTableAndPickTakesARow():
    # 下游模组往食谱表里追加：食谱格不能悄悄只显示前几道（控件按行回收，格数多不费控件）；pick 的参数是表里的行号（行只打墓碑不删）
    assert PotMenu.RECIPE_CAPACITY >= 512
    assert _menu().actions["pick"].fields[0].high == PotMenu.MAX_ROW >= PotMenu.RECIPE_CAPACITY


def testOutputTakesNothingAndOtherSlotsTakeAnything():
    state = State(_menu())
    ws = Rules.Workspace(state, RULES)
    carrot = Items.normalize(_item("minecraft:carrot"))
    assert not ws.canPlace(("output", 0), carrot)
    assert ws.canPlace(("ingredients", 0), carrot)
    assert ws.canPlace(("vessel", 0), carrot)   # 手动放什么都收（与旧界面一致），Shift 点击才挑
    assert not ws.canPlace(("book", 0), carrot)   # 食谱的详情格只看，不能放
    assert not ws.canPlace((RECIPES, 0), carrot)   # 食谱格只能选，不能放
    assert not ws.canLeave((RECIPES, 0), ws.get((RECIPES, 0))), "食谱格里的成品拿不走"


# ---------------------------------------------------------------- Shift 点击与双击收集（两种界面档同一个布局、同一份去向表）

def _shiftClick(state, ref, profile=CLASSIC):
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
    leaf = "arris:cabbage_leaf"   # 夹具 WRAP 的容器，也是卷心菜卷等真配方的食材
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


def testBothProfilesShareOneRouteTable():
    # 携带版用的也是经典版的物品栏（快捷栏 + 主背包两个格子区，不是合并背包）：去向表要按这两个集合写，两种界面档一样
    structure = _menu().structure
    for name in (HOTBAR, INVENTORY, "ingredients", "vessel", "output"):
        assert structure.quickTargets(name, CLASSIC) == structure.quickTargets(name, POCKET) != []
        assert structure.gatherOrder(name, CLASSIC) == structure.gatherOrder(name, POCKET) != []


def testShiftClickAndDoubleTapWorkInBothProfiles():
    for profile in (CLASSIC, POCKET):
        state = State(_menu())
        state.put((INVENTORY, 11), _item("minecraft:bowl", 2))
        state.put((HOTBAR, 4), _item("minecraft:carrot", 3))
        assert _shiftClick(state, (INVENTORY, 11), profile) and state.get(("vessel", 0))["count"] == 2, profile
        assert _shiftClick(state, (HOTBAR, 4), profile) and state.get(("ingredients", 0))["count"] == 3, profile
        assert _shiftClick(state, ("ingredients", 0), profile), profile   # 锅里的转回合并背包，快捷栏起
        assert state.get((HOTBAR, 0)) == Items.normalize(_item("minecraft:carrot", 3)), profile
        # 双击（触屏）收集同种：快捷栏、锅里、主背包里散着的都收进这一格
        state = State(_menu())
        state.put((HOTBAR, 0), _item("minecraft:carrot", 5))
        state.put((INVENTORY, 3), _item("minecraft:carrot", 7))
        state.put(("ingredients", 2), _item("minecraft:carrot", 2))
        ws = Rules.Workspace(state, RULES)
        assert Operations.gatherToSlot(ws, (HOTBAR, 0), profile), profile
        state.apply(ws)
        assert state.get((HOTBAR, 0))["count"] == 14, profile
        assert state.get((INVENTORY, 3)) is None and state.get(("ingredients", 2)) is None, profile


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
    quick = PotMenu.stateFrom(_BlockEntityData(heatEnable=True, timer=2.5, timerTotal=5.0), 10.0)
    assert abs(quick["progress"] - 0.5) < 1.0e-9, "番茄酱这类 5 秒的菜：按 timerTotal 算进度"
    assert PotMenu.stateFrom(_BlockEntityData(heatEnable=True, timer=99.0), 10.0)["progress"] == 0.0
    assert PotMenu.stateFrom(_BlockEntityData(heatEnable=True, timer=True), 10.0)["progress"] == 0.0   # 布尔不算计时


def testViewerStartsWithNothingSelected():
    menu = _menu()
    viewer = _viewer(menu)
    assert viewer == {"picked": -1, "search": "", "pickedAt": 0.0}
    values = menu.viewerValues(_Instance(), viewer)
    assert values == {"book": {}, "bookResult": None, "bookTitle": Book.UNPICKED_TITLE}, \
        "没选食谱时标题是语言文件的键（客户端按玩家的语言查，tests/test_pot_screen_texts.py），详情空着"
    for name, value in values.items():
        assert menu.data[name].scope == "viewer"
        assert menu.data[name].encode(value) is not None or value is None


def _details(menu, viewer):
    return menu.viewerValues(_Instance(), viewer)


def testTheDetailsRotateThroughTheVariantsOncePerSecondStartingWithTheFirst():
    clock = Clock(100.0)
    PotMenu.setClock(clock)
    try:
        menu = _menu()
        viewer = _viewer(menu)
        _pickStew(menu, viewer)
        assert viewer["pickedAt"] == 100.0, "选中的时刻记在服务端的钟上"
        for now, variant in ((100.0, 0), (100.5, 0), (100.99, 0), (101.0, 1), (101.7, 1), (102.0, 2), (103.0, 0),
                             (104.2, 1), (99.0, 0)):
            clock.now = now
            values = _details(menu, viewer)
            assert values["book"] == Book.bookCells(STEW, variant), (now, values["book"])
        values = _details(menu, viewer)
        assert values["bookTitle"] == STEW["text"] and values["bookResult"] == Book.resultOf(STEW)
        assert values["book"][Book.VESSEL_SLOT]["newItemName"] == "minecraft:bowl"
        clock.now = 104.2   # 第二种写法显示着时再点一次：从第一种重新开始
        _pickStew(menu, viewer)
        assert _details(menu, viewer)["book"] == Book.bookCells(STEW, 0)
    finally:
        PotMenu.setClock()
    assert PotMenu._clock[0] is time.time


def testASingleVariantRecipeSendsNothingNewAsTimeGoesBy():
    clock = Clock(50.0)
    PotMenu.setClock(clock)
    try:
        menu = _menu()
        viewer = _viewer(menu)
        _pick(menu, viewer, "测试卷", Recipes.CookingPotRecipeList.index(WRAP))
        first = _details(menu, viewer)
        for now in (50.4, 51.0, 57.3, 1000.0):
            clock.now = now
            later = _details(menu, viewer)
            assert later == first, now
            for name in first:   # 会话按编码后的值比，变了才发：一样就一条更新都不发
                assert menu.data[name].encode(later[name]) == menu.data[name].encode(first[name])
    finally:
        PotMenu.setClock()


# ---------------------------------------------------------------- 食谱格（算出的格子）

def _grid(menu, viewer):
    """这位查看者看到的食谱格：(显示几格, 前几格加一格里的东西)。"""
    ws = Rules.Workspace(State(menu, viewer=viewer), RULES)
    count = menu.structure.derivers[RECIPES].shown(RECIPES, ws.get, viewer)
    return count, [ws.get((RECIPES, index)) for index in range(count + 1)]


def testTheRecipeGridListsEveryResultInTableOrderOnTheClientAndNothingOnTheServer():
    menu = _menu(Libs.CLIENT)
    count, cells = _grid(menu, _viewer(menu))
    table = Recipes.CookingPotRecipeList
    assert count == len(table)
    assert [(cell["newItemName"], cell["newAuxValue"], cell["count"]) for cell in cells[:count]] == \
        [(recipe["CookResult"][0], recipe["CookResult"][1], 1) for recipe in table]
    assert cells[count] is None, "显示的格数之后是空的"
    server = _menu()
    assert _grid(server, _viewer(server)) == (0, [None]), "服务端不知道客户端过滤出了什么、也用不到：给空（客户端的格子客户端自己算）"


def testTheRecipeGridFollowsTheSearchOfEachViewer():
    menu = _menu(Libs.CLIENT)
    viewer = _viewer(menu)
    viewer["search"] = "蘑菇"
    shown = Search.rows("蘑菇")
    count, cells = _grid(menu, viewer)
    assert count == len(shown) and 0 < count < len(Recipes.CookingPotRecipeList)
    assert [cell["newItemName"] for cell in cells[:count]] == \
        [Recipes.CookingPotRecipeList[index]["CookResult"][0] for index in shown]
    assert _grid(menu, _viewer(menu))[0] == len(Recipes.CookingPotRecipeList), "另一位查看者没搜：照旧是全部"
    viewer["search"] = "绝对没有这道菜"
    assert _grid(menu, viewer) == (0, [None])


def _looks(menu, viewer, count):
    slot = menu.structure.get(RECIPES).slot
    ws = Rules.Workspace(State(menu, viewer=viewer), RULES)
    return [slot.decorate(ws, (RECIPES, index), ws.get((RECIPES, index))).cell for index in range(count)]


def testTheRecipeGridIsAChoiceThatMarksTheCellOfThePickedRow():
    menu = _menu(Libs.CLIENT)
    slot = menu.structure.get(RECIPES).slot
    assert isinstance(slot, StdSlots.Choice) and (slot.select, slot.selected) == ("pick", "picked")
    assert slot.cells == PotMenu.RECIPE_CELLS == ("textures/ui/recipe_book_item_bg", "textures/ui/recipe_book_touch_cell_selected")
    off, on = slot.cells
    viewer = _viewer(menu)
    viewer["picked"] = 2
    assert _looks(menu, viewer, 4) == [off, off, on, off], "没搜：第 2 格就是第 2 行，选中的那格一直是选中的底格"
    viewer["search"] = u"测试"                      # 夹具三道：测试蘑菇煲（第 0 行）、测试卷、测试混合
    shown = Search.rows(u"测试")
    assert [Recipes.CookingPotRecipeList[row] for row in shown] == [STEW, WRAP, MIX]
    viewer["picked"] = shown[2]
    assert _looks(menu, viewer, 3) == [off, off, on], "picked 记的是行号：亮的是这一行在本端过滤结果里的那一格"
    viewer["picked"] = 2
    assert _looks(menu, viewer, 3) == [off, off, off], "选中的那一行被过滤掉了：哪格都不亮"
    viewer["picked"] = -1
    assert on not in _looks(menu, viewer, 3)


class _Press(object):
    def __init__(self, ref, position):
        self.ref, self.position, self.data = ref, position, {}


class _Workspace(object):
    def __init__(self, viewer):
        self.viewer = viewer


class _Gestures(object):
    """客户端手势识别的最小替身：食谱格的手势用到的那几样（拖过 5 个单位算拖动，真的按屏幕像素算滚动的距离）；
    viewer 是这一端显示的查看者状态（workspace().viewer）。"""

    def __init__(self, menu, viewer=None):
        self.structure, self.calls, self.sounds, self.held, self.lastActionRef = menu.structure, [], [], None, None
        self.viewer = viewer if viewer is not None else {}

    def workspace(self):
        return _Workspace(self.viewer)

    def forgetDoubleClick(self):
        pass

    def hold(self, ref, button, now, position, owner):
        self.held = _Press(ref, position)
        return self.held

    def trackMove(self, press, pointer):
        if pointer is not None and abs(pointer[0] - press.position[0]) + abs(pointer[1] - press.position[1]) > 5:
            press.data["moved"] = True

    def slotType(self, ref):
        return self.structure.get(ref[0]).slot

    def call(self, name, args):
        self.calls.append((name, list(args)))
        return True

    def sound(self, name):
        self.sounds.append(name)


def testTouchPicksARecipeOnlyWhenTheFingerLiftsWithoutDragging():
    menu = _menu(Libs.CLIENT)
    tap = menu.structure.get(RECIPES).slot.interaction
    g = _Gestures(menu)
    tap.press(g, (RECIPES, 3), Rules.PRIMARY, 0.0, (0, 0))
    assert g.calls == [("pick", [3])] and g.sounds, "键鼠、手柄：按下就选中（照原版的按钮放一声）"
    g.calls = []
    assert tap.touchPress(g, (RECIPES, 5), 0.0, (10, 10)) is True and g.calls == [], "触屏按下先不选"
    tap.holdTick(g, g.held, 0.1, (11, 10))
    tap.holdRelease(g, g.held, (RECIPES, 5), 0.2)
    assert g.calls == [("pick", [5])], "松开在同一格、没拖动：选中"
    # 拖动过（在滚食谱格）、松开在别的格子上、这一下被打断：都不选
    for pointer, release in (((10, 40), (RECIPES, 5)), ((10, 10), (RECIPES, 6)), ((10, 10), None)):
        g.calls = []
        tap.touchPress(g, (RECIPES, 5), 0.0, (10, 10))
        tap.holdTick(g, g.held, 0.1, pointer)
        tap.holdRelease(g, g.held, release, 0.2)
        assert g.calls == [], (pointer, release)


def testAPickSendsTheRowOfTheCellInThisSidesFilteredList():
    """点一格发的是这一格在本端过滤结果里是表里的哪一行（不是格号）：服务端不过滤，只认行号。没有东西的格子什么都不发。"""
    menu = _menu(Libs.CLIENT)
    tap = menu.structure.get(RECIPES).slot.interaction
    g = _Gestures(menu, {"search": u"测试"})            # 测试蘑菇煲、测试卷、测试混合
    tap.press(g, (RECIPES, 1), Rules.PRIMARY, 0.0, (0, 0))
    assert g.calls == [("pick", [Recipes.CookingPotRecipeList.index(WRAP)])], g.calls
    g.calls = []
    tap.touchPress(g, (RECIPES, 2), 0.0, (10, 10))
    tap.holdRelease(g, g.held, (RECIPES, 2), 0.2)
    assert g.calls == [("pick", [Recipes.CookingPotRecipeList.index(MIX)])], "触屏抬起也一样"
    g.calls, g.sounds = [], []
    tap.press(g, (RECIPES, 3), Rules.PRIMARY, 0.0, (0, 0))
    assert g.calls == [] and g.sounds == [], "过滤结果只有三道：第 3 格没有东西，什么都不发"


# ---------------------------------------------------------------- 动作

def testSearchKeepsTheSelectionAndTheClientPredictsIt():
    """选中的是配方本身（行号）：换搜索词不清它（被过滤掉的那道只是没有格子亮），详情和"添加食材"不会因为打字消失。"""
    menu = _menu()
    viewer = _viewer(menu)
    state = State(menu)
    viewer.update(picked=3)
    assert _call(menu, state, viewer, "search", "汤") is True
    assert (viewer["picked"], viewer["search"]) == (3, "汤")
    assert _call(menu, state, viewer, "search", "汤") is True and viewer["picked"] == 3, "输入结束时同样的字再发一次：照旧"
    predicted = _viewer(_menu(Libs.CLIENT))
    predicted.update(picked=3)
    menu.actions["search"].predict(menu, View(predicted), "汤")
    assert (predicted["picked"], predicted["search"]) == (3, "汤"), "字一变客户端的食谱格当场跟着变，选中不动"


def testTheServerNeverFiltersByTheSearch():
    """服务端只记着搜索词（客户端的预测靠它：应答会盖掉预测），不按它判断任何事：选中、详情、添加食材只看行号。"""
    menu = _menu()
    viewer = _viewer(menu)
    state = State(menu)
    assert _call(menu, state, viewer, "search", u"绝对没有这道菜") is True
    assert _call(menu, state, viewer, "pick", 0) is True and _details(menu, viewer)["bookResult"] == Book.resultOf(STEW)
    state.put((HOTBAR, 0), _item("minecraft:red_mushroom", 2))
    assert _call(menu, state, viewer, "addFood") is True and state.get(("ingredients", 1))["newItemName"] == "minecraft:red_mushroom"


def testPickTakesALiveRowAndRemembersWhen():
    clock = Clock(7.5)
    PotMenu.setClock(clock)
    table = Recipes.CookingPotRecipeList
    dead = {"Recipe": [[("test:dead", 0)]], "CookResult": ("test:dead", 0), "PushItem": [], "text": "x", "Disabled": True}
    try:
        menu = _menu()
        viewer = _viewer(menu)
        state = State(menu)
        assert _call(menu, state, viewer, "pick", 0) is True and (viewer["picked"], viewer["pickedAt"]) == (0, 7.5)
        clock.now = 9.0
        assert _call(menu, state, viewer, "pick", len(table)) == "no_recipe"
        assert (viewer["picked"], viewer["pickedAt"]) == (0, 7.5), "被拒时不改"
        table.append(dead)
        PotRules.rebuildIndex()
        assert _call(menu, state, viewer, "pick", len(table) - 1) == "no_recipe", "删掉了（墓碑）：行还在，选不了"
        assert _call(menu, state, viewer, "pick", table.index(MIX)) is True and viewer["picked"] == table.index(MIX)
    finally:
        PotMenu.setClock()
        if dead in table:
            table.remove(dead)
            PotRules.rebuildIndex()
    predicted = _viewer(_menu(Libs.CLIENT))
    menu.actions["pick"].predict(menu, View(predicted), 4)
    assert predicted["picked"] == 4, "点食谱格当场显示成选中（以服务端为准）"


def testTwoClientsWithDifferentNamesPickTheSameDish():
    """主会话定的 A2：联机时两端问到的显示名可以不一样（语言不同）。两个客户端各按自己的语言搜、点中的格子不一样，发的是同一个行号，
    服务端照这一行给详情。夹具菜没写 text，只能按显示名（或物品 ID）搜到。"""
    table = Recipes.CookingPotRecipeList
    tofu = {"Recipe": [[("test:bean", 0)]], "CookResult": ("test:tofu", 0), "PushItem": [], "text": "test:tofu"}
    table.append(tofu)
    PotRules.rebuildIndex()
    row = table.index(tofu)
    sent = []
    try:
        for names, word in (({("test:tofu", 0): "Tofu", ("test:bean", 0): "Soybean"}, u"soybean"),
                            ({("test:tofu", 0): u"豆腐", ("test:bean", 0): u"黄豆"}, u"豆腐")):
            Names.setPort(None)
            Names.forget()
            Names.setPort(lambda name, aux, names=names: names.get((name, aux)))
            Search.forget()
            client = _menu(Libs.CLIENT)
            tap = client.structure.get(RECIPES).slot.interaction
            g = _Gestures(client, {"search": word})
            cell = Search.rows(word).index(row)
            tap.press(g, (RECIPES, cell), Rules.PRIMARY, 0.0, (0, 0))
            sent.append(g.calls[0])
    finally:
        table.remove(tofu)
        PotRules.rebuildIndex()
        Names.setPort(None)
        Names.forget()
        Search.forget()
    assert sent == [("pick", [row]), ("pick", [row])], sent
    table.append(tofu)
    try:
        server = _menu()
        viewer = _viewer(server)
        assert _call(server, State(server), viewer, "pick", row) is True
        assert _details(server, viewer)["bookResult"]["newItemName"] == "test:tofu"
    finally:
        table.remove(tofu)


def testAddFoodTakesTheFirstVariantWhenThePotIsEmpty():
    menu = _menu()
    viewer = _viewer(menu)
    _pickStew(menu, viewer)   # 第一种写法：红蘑菇 ×2，同种食材要占两个格子
    state = State(menu)
    state.put((INVENTORY, 3), _item("minecraft:red_mushroom", 5))
    state.put((INVENTORY, 4), _item("minecraft:brown_mushroom", 5))
    assert _call(menu, state, viewer, "addFood") is True
    assert state.get(("ingredients", 0)) == Items.normalize(_item("minecraft:red_mushroom"))
    assert state.get(("ingredients", 1)) == Items.normalize(_item("minecraft:red_mushroom"))
    assert state.get(("ingredients", 2)) is None
    assert state.get((INVENTORY, 3))["count"] == 3 and state.get((INVENTORY, 4))["count"] == 5   # 一共拿走两个红蘑菇


def testAddFoodPrefersTheVariantThePotAlreadyHoldsMostOf():
    menu = _menu()
    viewer = _viewer(menu)
    _pickStew(menu, viewer)
    state = State(menu)
    state.put(("ingredients", 0), _item("minecraft:brown_mushroom"))   # 锅里已经有一个棕蘑菇：棕 ×2、红 + 棕各有一件
    state.put((HOTBAR, 0), _item("minecraft:red_mushroom", 9))
    state.put((HOTBAR, 1), _item("minecraft:brown_mushroom", 9))
    assert [row for row in Book.fillOrder(STEW, [BROWN] + [None] * 5)] == [[BROWN] * 2, [RED, BROWN], [RED] * 2], \
        "一样多的照表里的先后，一件都没有的排最后"
    assert _call(menu, state, viewer, "addFood") is True
    assert [state.get(("ingredients", index)) for index in range(3)] == \
        [Items.normalize(_item("minecraft:brown_mushroom", 2)), Items.normalize(_item("minecraft:brown_mushroom")), None], \
        "接着补棕 ×2：已有的那格再加一个，第二个棕蘑菇另占一格；不混进红蘑菇"
    assert state.get((HOTBAR, 0))["count"] == 9 and state.get((HOTBAR, 1))["count"] == 7


def testAddFoodSkipsVariantsWithMissingIngredients():
    menu = _menu()
    viewer = _viewer(menu)
    _pickStew(menu, viewer)   # 红 ×2、棕 ×2 都凑不齐，红 + 棕凑得齐
    state = State(menu)
    state.put((HOTBAR, 8), _item("minecraft:brown_mushroom", 1))
    state.put((INVENTORY, 0), _item("minecraft:red_mushroom", 1))
    assert _call(menu, state, viewer, "addFood") is True
    placed = sorted(state.get(("ingredients", index))["newItemName"] for index in (0, 1))
    assert placed == ["minecraft:brown_mushroom", "minecraft:red_mushroom"]
    assert state.get((HOTBAR, 8)) is None and state.get((INVENTORY, 0)) is None


def testAddFoodIsAllOrNothingWhenEveryVariantMissesSomething():
    menu = _menu()
    viewer = _viewer(menu)
    _pickStew(menu, viewer)
    state = State(menu)
    state.put((HOTBAR, 0), _item("minecraft:red_mushroom", 1))   # 一个红蘑菇：哪种写法都凑不齐
    assert _refusal(menu, state, viewer) == "missing"
    assert state.get((HOTBAR, 0))["count"] == 1 and state.get(("ingredients", 0)) is None


def testAddFoodRefusesWhenThereAreNoFreeSlotsOrNothingIsSelected():
    menu = _menu()
    viewer = _viewer(menu)
    state = State(menu)
    assert _call(menu, state, viewer, "addFood") == "no_recipe"
    _pickStew(menu, viewer)
    for index in range(6):
        state.put(("ingredients", index), _item("minecraft:potato"))
    state.put((HOTBAR, 0), _item("minecraft:red_mushroom", 4))
    assert _refusal(menu, state, viewer) == "no_room"


def testAMissingIngredientOutranksNoRoom():
    menu = _menu()
    viewer = _viewer(menu)
    _pick(menu, viewer, "测试混合", Recipes.CookingPotRecipeList.index(MIX))
    state = State(menu)
    for index in range(4):   # 只剩两个空格：a ×3 放不下，b 放得下但背包里没有
        state.put(("ingredients", index), _item("minecraft:potato"))
    state.put((HOTBAR, 0), _item("test:a", 9))
    assert _refusal(menu, state, viewer) == "missing", "有因为缺食材跳过的写法时说缺食材，不说放不下"
    state.put((HOTBAR, 1), _item("test:b", 1))
    assert _call(menu, state, viewer, "addFood") is True and state.get(("ingredients", 4))["newItemName"] == "test:b"


def testAddFoodTopsUpAnExistingIngredientSlotAndLeavesFullOnesAlone():
    menu = _menu()
    viewer = _viewer(menu)
    _pickStew(menu, viewer)
    state = State(menu)
    state.put(("ingredients", 0), _item("minecraft:red_mushroom", 2))
    state.put((HOTBAR, 0), _item("minecraft:red_mushroom", 9))
    assert _call(menu, state, viewer, "addFood") is True   # 红 ×2：锅里已有一件（红 + 棕也是一件，照表里的先后）
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


def testAddFoodDoesNothingWhenThePotAlreadyHoldsAVariantAndNothingMoreFits():
    menu = _menu()
    viewer = _viewer(menu)
    _pickStew(menu, viewer)
    state = State(menu)
    state.put(("ingredients", 0), _item("minecraft:red_mushroom", 64))
    state.put(("ingredients", 1), _item("minecraft:brown_mushroom", 64))
    state.put((HOTBAR, 0), _item("minecraft:red_mushroom", 4))
    # 红 + 棕已经齐了、都满了：拒绝，不往后试红 ×2（那会在空格里再放一个红蘑菇，混成另一种写法）
    assert _refusal(menu, state, viewer) == "nothing"
    assert state.get((HOTBAR, 0))["count"] == 4 and state.get(("ingredients", 2)) is None


def testAddFoodSkipsSourcesThatCannotLeaveTheirSlot():
    menu = _menu()
    viewer = _viewer(menu)
    _pickStew(menu, viewer)   # 红蘑菇 ×2
    locked = _item("minecraft:red_mushroom", 5)
    locked["userData"] = {"minecraft:item_lock": {"__type__": 1, "__value__": 1}}   # 锁在格子里
    state = State(menu)
    state.put((HOTBAR, 0), locked)
    state.put((HOTBAR, 1), _item("minecraft:red_mushroom", 2))
    assert _call(menu, state, viewer, "addFood") is True
    assert state.get((HOTBAR, 0))["count"] == 5 and state.get((HOTBAR, 1)) is None   # 用的是第二堆
    state = State(menu)
    state.put((HOTBAR, 0), locked)   # 只有锁住的那一堆：拿不到
    assert _refusal(menu, state, viewer) == "missing"


def testAddFoodBooksEveryTakeAgainstTheStackItComesFrom():
    menu = _menu()
    viewer = _viewer(menu)
    _pickStew(menu, viewer)   # 红蘑菇 ×2：占两个格子，要拿两个
    state = State(menu)
    state.put((HOTBAR, 0), _item("minecraft:red_mushroom", 1))   # 一堆只有一个
    assert _refusal(menu, state, viewer) == "missing"
    state.put((INVENTORY, 0), _item("minecraft:red_mushroom", 1))   # 再来一堆就够了（两堆各出一个）
    assert _call(menu, state, viewer, "addFood") is True
    assert state.get((HOTBAR, 0)) is None and state.get((INVENTORY, 0)) is None
    assert state.get(("ingredients", 0))["count"] == 1 and state.get(("ingredients", 1))["count"] == 1


def testAddFoodGivesTheRequiredIngredientsPriorityOverTopUps():
    menu = _menu()
    viewer = _viewer(menu)
    _pickStew(menu, viewer)   # 红蘑菇 ×2
    state = State(menu)
    state.put(("ingredients", 0), _item("minecraft:red_mushroom", 2))   # 已有一格：这一格是"再加一个"
    state.put((HOTBAR, 0), _item("minecraft:red_mushroom", 1))   # 背包里只有一个：先给必须放的第二格
    assert _call(menu, state, viewer, "addFood") is True
    assert state.get(("ingredients", 0))["count"] == 2 and state.get(("ingredients", 1))["count"] == 1


def testRecipesWithTheWrongShapeAreIgnored():
    # 下游模组经联动接口追加的食谱没人校验形状；界面数据在会话的定时刷新里算，出错会让所有开着界面的人都收不到更新
    table = Recipes.CookingPotRecipeList
    broken = [{"text": "没有成品", "Recipe": [[("test:broken", 0)]]},
              {"text": "变体不是列表", "Recipe": "oops", "CookResult": ("test:b", 0)},
              {"text": "食材缺 aux", "Recipe": [[("test:broken",)]], "CookResult": ("test:b", 0)},
              {"text": "容器不对", "Recipe": [[("test:broken", 0)]], "CookResult": ("test:b", 0), "Vessel": 7},
              {"text": "没有变体", "Recipe": [], "CookResult": ("test:b", 0)},
              None]
    count = len(table)
    table.extend(broken)
    try:
        shown = Search.rows("")
        assert shown == list(range(count))   # 形状不对的一条都不列
        assert Search.rows("没有") == [] and Book.recipeAt(count) is None
        assert "test:broken" not in Book.ingredientNames() and 7 not in Book.vesselNames()
        menu = _menu(Libs.CLIENT)
        assert _grid(menu, _viewer(menu))[0] == count, "食谱格也只列形状对的"
        server = _menu()
        assert _call(server, State(server), _viewer(server), "pick", count) == "no_recipe", "形状不对的行选不了"
    finally:
        del table[count:]


def testActionsOnlyTakeValuesFromTheirSchema():
    # 客户端只能发：搜索词（文字，限长 32：带前缀的词放得下）、配方的行号（整数范围）；添加食材不带任何参数（选了哪个只认服务端会话里记的）
    menu = _menu()
    assert menu.actions["addFood"].fields == ()
    assert len(menu.actions["pick"].fields) == 1 and len(menu.actions["search"].fields) == 1
    assert menu.actions["search"].fields[0].limit == Search.SEARCH_LIMIT == 32
    assert menu.actions["addFood"].predict is None, "添加食材等服务端的应答"


def testWhatIsTakenFromTheResultSlotIsHandedToTheServersTakenHandler():
    class Instance(object):
        key = "0:10:64:10"

    class Session(object):
        playerId, instance = "a", Instance()

    heard = []
    PotMenu.setTakenHandler(lambda playerId, key, stack: heard.append((playerId, key, stack)))
    try:
        menu, stack = _menu(), _item("arris:dumplings", 3)
        menu.onTaken(Session(), (PotMenu.OUTPUT, 0), stack)
        assert heard == [("a", "0:10:64:10", stack)], "成品格拿走的：玩家、实例键、拿走的那一堆"
        menu.onTaken(Session(), (PotMenu.INGREDIENTS, 0), stack)
        assert len(heard) == 1, "别的格子不算"
    finally:
        PotMenu.setTakenHandler(None)
    _menu().onTaken(Session(), (PotMenu.OUTPUT, 0), stack)      # 没登记处理（离线）：什么都不做


def testBothProfilesUseTheSameCompiledContent():
    table = fdtest.load("dolorLayouts").LAYOUTS
    layout = table[PotMenu.MENU]
    assert layout["menu"] == PotMenu.MENU and set(layout["screens"]) == {"classic", "pocket"}
    classic, pocket = layout["screens"]["classic"], layout["screens"]["pocket"]
    assert classic["widgets"] == pocket["widgets"] and classic["names"] == pocket["names"], "携带版共用经典版的那一个界面"
    collections = set(widget.get("collection") for widget in classic["widgets"]) - {None}
    assert collections == {RECIPES, "ingredients", "vessel", "output", "book", HOTBAR, INVENTORY}, collections
    grid = [widget for widget in classic["widgets"] if widget.get("collection") == RECIPES]
    assert len(grid) == 1 and grid[0]["widget"] == "scroll_grid" and grid[0]["columns"] == 4 and grid[0]["fixedColumns"], \
        "食谱格按行回收：控件数是行控件数 × 4，不随食谱数变"
    assert "Std.Windowed.Client" in layout["imports"]


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
