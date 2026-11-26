# -*- coding: utf-8 -*-
"""CookingPot - 厨锅的 dolorContainer 界面模型：食材格、容器格、成品格、食谱格与选中食谱的详情（双端）

格子仍存在 netease:block_container 的 8 个引擎容器格里（0-5 食材，6 容器，7 成品）；烹饪、热源、预览格由
Server/CookingPot.py 照旧在方块实体数据里推进，界面数据（热源、进度、预览）经 setStateReader 登记的读数函数在服务端读出。
食谱照旧界面（rp/ui/arrisCookingPot.json）：左边是搜索框与食谱格，右边是选中食谱的详情。食谱格是算出的格子（库的 Choice，
原版切石机的配方按钮，内容与手势见 PotRecipes）：在看界面的那一端按这位查看者的搜索词过滤（Shared/Rules/PotSearch，照 JEI、用这一端
自己的显示名），点一格选中——发 pick(配方在表里的行号)，可预测；服务端只查这一行活着、形状对，不按搜索词判断任何事（联机时两端问到的
显示名可以不一样）。详情是食材（几种写法时每 Book.VARIANT_SECONDS 秒换下一种，服务端按钟算）、容器、成品、标题和"添加食材"
（挑写法见 PotFill）。搜索词、选中的行都记在每位查看者各自的会话里；换搜索词不清选中（被过滤掉的那道只是没有格子亮）。
两端都导入本模块（界面模型两端各建一份，规则一样），所以顶层不碰引擎，只导入 dolorContainer 的纯逻辑部分。
"""
import time

from ...dolorContainer.Common import Actions, Data, Menus, Schema
from ...dolorContainer.Common.Collections import COMBINED, HOTBAR, INVENTORY, PROFILE_CLASSIC, PROFILE_POCKET
from ...dolorContainer.Common.Slots import SlotType
from ...dolorContainer.Std import Containers
from ...dolorContainer.Std.Block import Common as BlockCommon
from ...dolorContainer.Std.Decor import Decor
from ...dolorContainer.Std.Slots import Display, Output
from ..Rules import CookingPotBook as Book
from ..Rules import PotSearch
from ..Rules.TableWire import isInt
from . import PotFill, PotRecipes

MENU = "arris:cooking_pot"
INGREDIENTS = "ingredients"
VESSEL = "vessel"
OUTPUT = "output"
BOOK = "book"
RECIPES = "recipes"
SPOON = "textures/ui/spoon"
RECIPE_CELLS = PotRecipes.CELLS
# 食谱格就有这么多格：下游模组追加的食谱都排得下，界面的控件按行回收（scroll_grid），不随格数变
RECIPE_CAPACITY = 4096
# pick 的参数是配方在 CookingPotRecipeList 里的行号（行只打墓碑、不删，站点和 matchIndex 也拿它当身份）；这里只是线上的范围校验，
# 真正的校验是那一行活着、形状对（Book.recipeAt）
MAX_ROW = 1 << 16
# 开着的界面每这么多刻重读一次热源、进度、预览（它们由 Server/CookingPot.py 的 tick 在会话之外改；5 Hz，与烹饪的处理节拍一致），
# 同时重算每位查看者的详情（写法轮换跟着变）
DATA_EVERY = 4

_stateReader, _takenHandler, _clock = [None], [None], [time.time]


def setStateReader(reader):
    """服务端登记读数函数 reader(实例键) -> {"heated": 布尔, "progress": 0-1, "preview": 物品堆或 None}（缺的键不发）。"""
    _stateReader[0] = reader


def setTakenHandler(handler):
    """服务端登记：成品格里的东西被拿走时 handler(玩家 id, 实例键, 物品堆) 记一笔（Server/CookingPotHost.py）。"""
    _takenHandler[0] = handler


def setClock(clock=None):
    """写法轮换用的钟：clock() -> 秒（测试注入；None 回到 time.time）。"""
    _clock[0] = clock or time.time


def stateFrom(data, cookSeconds):
    """
    厨锅方块实体数据 -> 界面数据 {"heated", "progress", "preview"}。data 读缺了的键得到 None（引擎的方块实体数据对象就是这样），
    cookSeconds 是一份菜的缺省烹饪时长：计时从总时长倒数到 0，没在烹饪时是满值，进度为 0；没热源时进度也是 0。
    总时长优先读方块实体数据的 timerTotal（按配方的 CookTime，和 JE 一样番茄酱 5 秒、南瓜盅 20 秒），没有才用 cookSeconds。
    预览是煮好、还没装进容器的成品（预览槽里的一份物品，空槽为 None）。
    """
    heated = bool(data["heatEnable"])
    timer, total = data["timer"], data["timerTotal"]
    if not isinstance(total, (int, float)) or isinstance(total, bool) or total <= 0:
        total = cookSeconds
    progress = 0.0
    if heated and isinstance(timer, (int, float)) and not isinstance(timer, bool):
        progress = max(0.0, min(1.0, 1.0 - float(timer) / float(total)))
    stack = (data["previewItemSlot"] or [None])[0]
    preview = None
    if stack and stack.get("newItemName"):
        # 换成普通字典再交给界面（引擎对象里读出来的堆，只用 Server/CookingPot.py 读预览槽时用过的取法）
        preview = {"newItemName": stack.get("newItemName"), "newAuxValue": stack.get("newAuxValue", 0),
                   "count": stack.get("count", 0)}
    return {"heated": heated, "progress": progress, "preview": preview}


class VesselSlot(SlotType):
    """
    容器格：手动放什么都收（与旧界面一致）；Shift 点击只收已知的容器，不然食材会被塞进这一格。既是容器又是食材的
    （卷心菜叶）Shift 点击当食材，只有这一格里已经是它时才续上。
    """

    def quickInto(self, ws, name, src, amount):
        stack = ws.get(src)
        itemName = stack.get("newItemName") if stack is not None else None
        if Book.isPureVessel(itemName):
            return None
        if Book.isAmbiguous(itemName):
            held = ws.get((name, 0))
            return None if held is not None and held.get("newItemName") == itemName else amount
        return amount


class IngredientSlot(SlotType):
    """食材格：手动放什么都收；Shift 点击不收只当容器用的东西（容器格放不下时也不会落到这里，混进食材把配方搅乱）。"""

    def quickInto(self, ws, name, src, amount):
        stack = ws.get(src)
        if stack is not None and Book.isPureVessel(stack.get("newItemName")):
            return amount
        return None


def routes():
    """
    去向表与收集顺序：背包 Shift 点击先试容器格，再试食材格（两种格子各挑自己收的东西），最后换到背包的另一半；厨锅的格子转进合并背包。
    两种界面档用同一个布局（物品栏都是快捷栏 + 主背包两个格子区），去向也一样。
    """
    mine = (INGREDIENTS, VESSEL, OUTPUT)
    into = ((VESSEL, True), (INGREDIENTS, True))
    quick = dict([(name, ((COMBINED, False),)) for name in mine]
                 + [(HOTBAR, into + ((INVENTORY, False),)), (INVENTORY, into + ((HOTBAR, False),))])
    gather = dict([(name, (name, INVENTORY, HOTBAR)) for name in mine]
                  + [(HOTBAR, (HOTBAR,) + mine + (INVENTORY,)), (INVENTORY, (INVENTORY,) + mine + (HOTBAR,))])
    return {PROFILE_CLASSIC: quick, PROFILE_POCKET: quick}, {PROFILE_CLASSIC: gather, PROFILE_POCKET: gather}


def _pickedRecipe(viewer):
    """选中的配方：每位查看者状态 picked 记的是表里的行号（-1 没选）；删掉了（墓碑）、形状不对的是 None。"""
    picked = (viewer or {}).get("picked", -1)
    return Book.recipeAt(picked) if isInt(picked) else None


@Menus.register(MENU)
class CookingPotMenu(Menus.Menu):
    layout = MENU
    dataEvery = DATA_EVERY
    data = {
        "heated": Data.Bool(), "progress": Data.Float(digits=3), "preview": Data.Item(),
        # 选中食谱的详情（每位查看者一份）：食材格与容器格（0-5 食材，6 容器）、成品、标题（可本地化的文字，没选时客户端按玩家的语言查）
        "book": Data.SlotValues(Data.Item(), BOOK, scope=Data.VIEWER),
        "bookResult": Data.Item(scope=Data.VIEWER),
        "bookTitle": Data.Lang(scope=Data.VIEWER),
    }
    # picked 是选中的配方在表里的行号（-1 没选；不是格号）；search 是搜索词（服务端只记着：客户端的预测靠它，应答会盖掉预测）；
    # pickedAt 是选中的时刻（服务端的钟，写法从这时起轮换）
    viewerState = {"picked": Data.Int(), "search": Data.Text(), "pickedAt": Data.Float()}

    def define(self, s):
        pot = s.container("pot", BlockCommon.ENGINE_CONTAINER, Book.POT_SLOTS)
        s.collection(INGREDIENTS, pot, 0, Book.INPUT_SLOTS, IngredientSlot())
        s.collection(VESSEL, pot, Book.VESSEL_SLOT, 1, VesselSlot(decor=Decor(placeholder=SPOON)))
        s.collection(OUTPUT, pot, Book.RESULT_SLOT, 1, Output())
        s.collection(BOOK, s.container("book_view", Containers.VIRTUAL, Book.BOOK_CELLS), 0, Book.BOOK_CELLS,
                     Display(items=BOOK))
        s.collection(RECIPES, s.container("recipe_view", Containers.VIRTUAL, RECIPE_CAPACITY), 0, RECIPE_CAPACITY,
                     PotRecipes.RecipeChoice("pick", "picked"))
        s.derive(RECIPES, PotRecipes.RecipeGrid(s.side))
        s.player()
        s.routes(*routes())

    # ---------------------------------------------------------------- 服务端：界面数据

    def onTaken(self, session, ref, stack):
        """成品格被拿走（点、Shift 点、丢出都算，FD 的 CookingPotResultSlot.onTake 一样）：交给服务端登记的处理。"""
        if _takenHandler[0] is not None and ref[0] == OUTPUT:
            _takenHandler[0](session.playerId, session.instance.key, stack)

    def dataValues(self, instance):
        read = _stateReader[0]
        return dict(read(instance.key) or {}) if read is not None else {}

    def viewerInitial(self, instance, playerId):
        return {"picked": -1}

    def viewerValues(self, instance, viewer):
        values = {"book": {}, "bookResult": None, "bookTitle": Book.UNPICKED_TITLE}
        recipe = _pickedRecipe(viewer)
        if recipe is not None:
            variant = Book.shownVariant(Book.variantCount(recipe), viewer.get("pickedAt") or 0.0, _clock[0]())
            values["book"] = Book.bookCells(recipe, variant)
            values["bookResult"] = Book.resultOf(recipe)
            values["bookTitle"] = Book.titleOf(recipe)
        return values

    # ---------------------------------------------------------------- 动作（服务端校验后执行）

    @Actions.action("search", Schema.Text(PotSearch.SEARCH_LIMIT, words=False))
    def search(self, ctx, text):
        # 只记着（客户端的预测靠它：服务端的应答会盖掉预测，不记的话食谱格一应答就回到全部）；选中的是行号，换搜索词不清它
        ctx.viewer["search"] = text

    @search.predicting
    def search(self, view, text):
        # 客户端当场按新的字过滤食谱格（用这一端的显示名，PotSearch）
        view.viewer["search"] = text

    @Actions.action("pick", Schema.Int(0, MAX_ROW))
    def pick(self, ctx, row):
        # 客户端发的是它点的那一格在它那一端过滤结果里的行号（PotRecipes.TapToPick）：服务端只查这一行活着、形状对
        if Book.recipeAt(row) is None:
            raise Actions.Refused("no_recipe")
        ctx.viewer["picked"] = row
        ctx.viewer["pickedAt"] = _clock[0]()

    @pick.predicting
    def pick(self, view, row):
        view.viewer["picked"] = row

    @Actions.action("addFood")
    def addFood(self, ctx):
        """
        "添加食材"：把选中食谱的一种写法的食材从玩家背包各取一个放进厨锅的食材格（配方书在 Java 版里的"一键放入"）。
        只认服务端会话里记着的选中项，客户端不传任何位置、格号；挑哪种写法、缺食材或放不下时怎么拒绝见 PotFill。
        """
        recipe = _pickedRecipe(ctx.viewer)
        if recipe is None:
            raise Actions.Refused("no_recipe")
        PotFill.fill(ctx.ws, recipe, INGREDIENTS)
