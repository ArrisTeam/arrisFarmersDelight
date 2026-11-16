# -*- coding: utf-8 -*-
"""CookingPot - 厨锅的 dolorContainer 界面模型：食材格、容器格、成品格、食谱书（双端）

格子仍存在 netease:block_container 的 8 个引擎容器格里（0-5 食材，6 容器，7 成品）；烹饪、热源、预览格由
Server/CookingPot.py 照旧在方块实体数据里推进，界面数据（热源、进度、预览）经 setStateReader 登记的读数函数在服务端读出。
食谱书：列表（可搜索）、选中食谱的详情（食材、容器、成品，可换变体）、"添加食材"按钮，状态都在每位查看者各自的会话里。
两端都导入本模块（界面模型两端各建一份，规则一样），所以顶层不碰引擎，只导入 dolorContainer 的纯逻辑部分。
"""
from ...dolorContainer.Common import Actions, Data, Menus, Rules, Schema
from ...dolorContainer.Common.Collections import COMBINED, HOTBAR, INVENTORY, PLAYER_SIZE, PROFILE_CLASSIC, PROFILE_POCKET
from ...dolorContainer.Common.Slots import SlotType
from ...dolorContainer.Std import Containers
from ...dolorContainer.Std.Block import Common as BlockCommon
from ...dolorContainer.Std.Decor import Decor
from ...dolorContainer.Std.Slots import Display, Output
from ..Rules import CookingPotBook as Book

MENU = "arris:cooking_pot"
INGREDIENTS = "ingredients"
VESSEL = "vessel"
OUTPUT = "output"
BOOK = "book"
SPOON = "textures/ui/spoon"
# 点列表一行的序号上限（线上校验用；实际范围看现在的食谱数）
MAX_PICK = 4095
# 开着的界面每这么多刻重读一次热源、进度、预览（它们由 Server/CookingPot.py 的 tick 在会话之外改；5 Hz，与烹饪的处理节拍一致）
DATA_EVERY = 4

_stateReader = [None]


def setStateReader(reader):
    """服务端登记读数函数 reader(实例键) -> {"heated": 布尔, "progress": 0-1, "preview": 物品堆或 None}（缺的键不发）。"""
    _stateReader[0] = reader


def stateFrom(data, cookSeconds):
    """
    厨锅方块实体数据 -> 界面数据 {"heated", "progress", "preview"}。data 读缺了的键得到 None（引擎的方块实体数据对象就是这样），
    cookSeconds 是一份菜的烹饪时长：计时从它倒数到 0，没在烹饪时是满值，进度为 0；没热源时进度也是 0。
    预览是煮好、还没装进容器的成品（预览槽里的一份物品，空槽为 None）。
    """
    heated = bool(data["heatEnable"])
    timer = data["timer"]
    progress = 0.0
    if heated and isinstance(timer, (int, float)) and not isinstance(timer, bool):
        progress = max(0.0, min(1.0, 1.0 - float(timer) / cookSeconds))
    stack = (data["previewItemSlot"] or [None])[0]
    preview = None
    if stack and stack.get("newItemName"):
        # 换成普通字典再交给界面（引擎对象里读出来的堆，只用 Server/CookingPot.py 读预览槽时用过的取法）
        preview = {"newItemName": stack.get("newItemName"), "newAuxValue": stack.get("newAuxValue", 0),
                   "count": stack.get("count", 0)}
    return {"heated": heated, "progress": progress, "preview": preview}


class VesselSlot(SlotType):
    """容器格：手动放什么都收（与旧界面一致）；Shift 点击只往里放已知的容器，不然食材会被塞进这一格。"""

    def quickInto(self, ws, name, src, amount):
        stack = ws.get(src)
        if stack is not None and stack.get("newItemName") in Book.vesselNames():
            return None
        return amount


def routes():
    """去向表与收集顺序：背包 Shift 点击先试容器格（只收已知容器），再试食材格，经典版最后换到背包的另一半。"""
    mine = (INGREDIENTS, VESSEL, OUTPUT)
    into = ((VESSEL, True), (INGREDIENTS, True))
    quick = {
        PROFILE_CLASSIC: dict([(name, ((COMBINED, False),)) for name in mine]
                              + [(HOTBAR, into + ((INVENTORY, False),)), (INVENTORY, into + ((HOTBAR, False),))]),
        PROFILE_POCKET: dict([(name, ((COMBINED, False),)) for name in mine] + [(COMBINED, into)]),
    }
    gather = {
        PROFILE_CLASSIC: dict([(name, (name, INVENTORY, HOTBAR)) for name in mine]
                              + [(HOTBAR, (HOTBAR,) + mine + (INVENTORY,)), (INVENTORY, (INVENTORY,) + mine + (HOTBAR,))]),
        PROFILE_POCKET: dict([(name, (name, COMBINED)) for name in mine] + [(COMBINED, (COMBINED,) + mine)]),
    }
    return quick, gather


def _pickedRecipe(viewer):
    return Book.pickedRecipe(viewer.get("search") or "", viewer.get("picked", -1))


def _sourceOf(ws, key):
    """背包里第一格装着 key 这种东西的格子（从快捷栏起）；没有为 None。"""
    for index in range(PLAYER_SIZE):
        ref = (COMBINED, index)
        if Book.keyOf(ws.get(ref)) == key:
            return ref
    return None


@Menus.register(MENU)
class CookingPotMenu(Menus.Menu):
    layout = MENU
    dataEvery = DATA_EVERY
    data = {
        "heated": Data.Bool(), "progress": Data.Float(digits=3), "preview": Data.Item(),
        # 食谱书（每位查看者各一份）：列表每行的成品、选中食谱的详情格（0-5 食材，6 容器，7 成品）、标题与变体序号的字
        "recipes": Data.List(Data.Item(), scope=Data.VIEWER),
        "book": Data.SlotValues(Data.Item(), BOOK, scope=Data.VIEWER),
        "bookTitle": Data.Text(scope=Data.VIEWER),
        "bookVariant": Data.Text(scope=Data.VIEWER),
    }
    # picked 是过滤后列表里的序号（-1 没选）；variant 是选中食谱的第几个变体
    viewerState = {"picked": Data.Int(), "variant": Data.Int(), "search": Data.Text()}
    # 携带版右半屏的两页：烹饪、食谱；每次打开都从烹饪页开始
    clientState = {"page": Data.Enum(("pot", "book"))}
    freshClientState = ("page",)

    def define(self, s):
        pot = s.container("pot", BlockCommon.ENGINE_CONTAINER, Book.POT_SLOTS)
        s.collection(INGREDIENTS, pot, 0, Book.INPUT_SLOTS)
        s.collection(VESSEL, pot, Book.VESSEL_SLOT, 1, VesselSlot(decor=Decor(placeholder=SPOON)))
        s.collection(OUTPUT, pot, Book.RESULT_SLOT, 1, Output())
        s.collection(BOOK, s.container("book_view", Containers.VIRTUAL, Book.BOOK_CELLS), 0, Book.BOOK_CELLS,
                     Display(items=BOOK))
        s.player()
        s.routes(*routes())

    # ---------------------------------------------------------------- 服务端：界面数据

    def dataValues(self, instance):
        read = _stateReader[0]
        return dict(read(instance.key) or {}) if read is not None else {}

    def viewerInitial(self, instance, playerId):
        return {"picked": -1}

    def viewerValues(self, instance, viewer):
        shown = Book.visibleRecipes(viewer.get("search") or "")
        values = {"recipes": Book.listRows(shown), "book": {}, "bookTitle": "请选择食谱", "bookVariant": ""}
        recipe = _pickedRecipe(viewer)
        if recipe is not None:
            variant, count = viewer.get("variant", 0), Book.variantCount(recipe)
            values["book"] = Book.bookCells(recipe, variant)
            values["bookTitle"] = recipe.get("text") or ""
            values["bookVariant"] = "%d / %d" % (variant % count + 1, count) if count > 1 else ""
        return values

    # ---------------------------------------------------------------- 动作（服务端校验后执行）

    @Actions.action("search", Schema.Text(Book.SEARCH_LIMIT, words=False))
    def search(self, ctx, text):
        ctx.viewer["search"] = text
        ctx.viewer["picked"] = -1
        ctx.viewer["variant"] = 0

    @Actions.action("pick", Schema.Int(0, MAX_PICK))
    def pick(self, ctx, index):
        if index >= len(Book.visibleRecipes(ctx.viewer.get("search") or "")):
            raise Actions.Refused("no_recipe")
        ctx.viewer["picked"] = index
        ctx.viewer["variant"] = 0

    @pick.predicting
    def pick(self, view, index):
        view.viewer["picked"] = index
        view.viewer["variant"] = 0

    @Actions.action("nextVariant")
    def nextVariant(self, ctx):
        recipe = _pickedRecipe(ctx.viewer)
        if recipe is None:
            raise Actions.Refused("no_recipe")
        ctx.viewer["variant"] = (ctx.viewer.get("variant", 0) + 1) % Book.variantCount(recipe)

    @Actions.action("addFood")
    def addFood(self, ctx):
        """
        "添加食材"：把选中食谱的选中变体的食材从玩家背包各取一个放进厨锅的食材格（配方书在 Java 版里的"一键放入"）。
        只认服务端会话里记着的选中项，客户端不传任何位置、格号；缺食材、放不下时整个不做（不会放一半）。
        """
        recipe = _pickedRecipe(ctx.viewer)
        if recipe is None:
            raise Actions.Refused("no_recipe")
        ws = ctx.ws
        slotKeys = [Book.keyOf(ws.get((INGREDIENTS, index))) for index in range(Book.INPUT_SLOTS)]
        plan = Book.planFill(Book.variantOf(recipe, ctx.viewer.get("variant", 0)), slotKeys)
        if plan is None:
            raise Actions.Refused("no_room")
        placements, topUps = plan
        for slot, key in placements:
            source = _sourceOf(ws, key)
            if source is None or Rules.transfer(ws, source, (INGREDIENTS, slot), 1) < 1:
                raise Actions.Refused("missing")
        moved = len(placements)
        for slot, key in topUps:
            source = _sourceOf(ws, key)
            if source is not None:
                moved += Rules.transfer(ws, source, (INGREDIENTS, slot), 1)
        if not moved:
            raise Actions.Refused("full")
