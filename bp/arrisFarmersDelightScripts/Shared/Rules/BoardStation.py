# -*- coding: utf-8 -*-
"""BoardStation - 砧板站点的纯规则：站点声明（schema）、能切什么 / 什么是工具 / 什么进摆盘菜、托盘里哪些亮、插着的工具（双端）

对应 Hands-On Delight：station/CuttingBoardStation.java（SCHEMA、常量）、station/Cutting.java 的 recipesFor / isTool / canStick（128-234）、
client/BoardBehavior.usable（1502-1505）。放上板的判定树在 HandsOn/BoardPlace.py，刀口计划在 CuttingStation.py。
板的槽组两个：board 1 格（板上等着切的东西 / 做好的菜 / 插着的工具，存在方块实体数据 cuttingDict）、layers 9 格（摆盘的层，
每层最多一整批 16，存在 dishLayers）；都是 kept（关站不退还，东西留在方块里）、什么也不收（accepts 一律 False）：所有东西走
自定义动作 place，免得内核按自己的猜法把整叠挪进去（和 JE 一样，HoD 还有个接住放下的叠的 hand 槽，我们的内核没有 drop_zone，用不上）。
物品是 (物品名, aux)；这里的物品字典是引擎的 {"newItemName", "newAuxValue", "count", ...}。
"""
from ..Data.Cutting import CuttingBoardDict, CuttingTagDict, axeList, knifeList
from ..Data.FlatBlockItems import FlatBlockItems, ShownAs
from . import DishStation
from . import CuttingStation
from .CuttingStation import BOARD_BLOCKS, STATION_ID, fitsTool  # noqa: F401 - 站点和测试从这里取
from .HandsOn.Assembly import BATCH, MOST_LAYERS  # noqa: F401 - 一批 16、最多 9 层
from .HandsOn import ItemData
from .HandsOn.BoardPlace import BOARD_MAX  # noqa: F401 - 板上一种东西放多少
from .HandsOn.Items import keyOf  # noqa: F401 - 站点和测试从这里取

MIN_API_VERSION = 3          # 前置包 API：砧板站点用到光标栈 / 托盘 / 站点逻辑的 ctx（2）和输入方式、半透明悬着的东西（3）；更老的前置包上砧板走经典玩法
GROUP_BOARD = "board"
GROUP_LAYERS = "layers"
# FD 潜行使用会把这些插进空板（Cutting.canStick，216-218：TieredItem 是刀 / 剑 / 斧 / 镐 / 锹 / 锄，再加 TridentItem、ShearsItem）；键是引擎的物品类型
STICKABLE_TYPES = frozenset(("sword", "axe", "hoe", "shovel", "pickaxe", "trident", "shears"))
# 板上这件是不是插着的（FD 的 CuttingBoardBlockEntity.isItemCarvingBoard，存档里叫 IsItemCarved）：方块实体数据里的键，1 插着 / 0 躺着；
# 没有这个键 = 不知道（板空着，或是加这个标记之前的老存档）：读的人照老办法推断（Env.isCarving）
CARVED_DATA = "isItemCarved"
CARVED = "carved"           # 同一个标记在站点数据（view.data）和世界展示的物品表（Client/BlockItems 的 items）里的键：True / False，没有 = 不知道

_cache = {"stamp": None, "tools": frozenset(), "types": frozenset()}


def invalidate():
    """工具表下次用时重算（客户端把服务端发来的表并进去之后调，Shared/Rules/SyncTables.recompute）。"""
    _cache["stamp"] = None


def _tools():
    """所有配方的工具名和要求的物品类型；下游往配方表里加了配方、往刀 / 斧列表里追加了名字（配方的 tool 引用的就是这两个列表）时重算。"""
    stamp = (len(CuttingBoardDict), len(CuttingTagDict), len(knifeList), len(axeList))
    if _cache["stamp"] != stamp:
        _cache["stamp"] = stamp
        recipes = list(CuttingBoardDict.values()) + list(CuttingTagDict.values())
        _cache["tools"] = frozenset(name for recipe in recipes for name in recipe.get("tool") or ())
        _cache["types"] = frozenset(recipe["item_type"] for recipe in recipes if recipe.get("item_type"))
    return _cache["tools"], _cache["types"]


def shownItem(item):
    """这件东西画出来用哪件物品：蘑菇丛换成只用来显示的平面物品（Data/FlatBlockItems.ShownAs，数量照旧），别的就是它自己。
    站点里画板上的东西（Compat/Diegesis/BoardThing）、没开站时的世界展示（Client/BlockItems）、手上拿着的（前置包的 shownAs 钩子）都问它。"""
    key = keyOf(item)
    if key is None or key[0] not in ShownAs:
        return item
    return {"newItemName": ShownAs[key[0]], "newAuxValue": 0, "count": item.get("count", 1) or 1}


def acceptsNothing(item):
    """schema 里两个槽组的 accepts：站点的槽什么也不收（放的走自定义动作）。"""
    return False


def buildSchema(kit):
    """站点的声明，两端各建一份一模一样的。kit 是带 StationSchema / SlotRules 的东西：前置包的服务端 Api 模块，或它的 Shared/Schema 模块
    （客户端经 ImportModule 拿）；这里不导入前置包，Shared 保持纯。"""
    kept = kit.SlotRules.DEFAULT.kept().withAccepts(acceptsNothing)
    return (kit.StationSchema.builder()
            .slots(GROUP_BOARD, 1, kept)
            .slots(GROUP_LAYERS, MOST_LAYERS, kept.withMaxStack(BATCH))
            .build())


class Env(object):
    """放上板、托盘、点板要问的几件事。isKnife(物品名) 和 typeOf(物品字典) 要问引擎（刀的标签、物品类型），由两端各自注入；
    其余按 Shared 的数据表答（切的配方、摆盘的菜）。"""

    def __init__(self, isKnife, typeOf, maxStack=None, carved=None):
        self.isKnife = isKnife
        self.typeOf = typeOf
        self.maxStack = maxStack if maxStack is not None else (lambda item: 64)     # 物品最多叠几个
        self.carved = carved                  # () -> 这块板的 IsItemCarved 标记（True / False / None 不知道）；不给 = 一律不知道

    # ---------------------------------------------------------------- 切

    def recipeOf(self, item):
        """切这件东西的配方（精确的先，再看按标签的，CuttingStation.recipeOf）；切不了是 None。"""
        return CuttingStation.recipeOf(keyOf(item))

    def cuttable(self, item):
        return self.recipeOf(item) is not None

    def cutsWith(self, onBoard, tool):
        """tool 切得了 onBoard 吗（Cutting.findWith 非空）。"""
        recipe = self.recipeOf(onBoard)
        return recipe is not None and fitsTool(tool.get("newItemName"), self.typeOf(tool), recipe, self.isKnife)

    def isToolItem(self, item):
        """是不是某个配方的工具（Cutting.isTool(level, item)：刀、斧、镐、锹、锄、剪刀、别的包的刀）。"""
        key, (tools, types) = keyOf(item), _tools()
        return key is not None and (key[0] in tools or self.typeOf(item) in types or bool(self.isKnife(key[0])))

    def goesIntoADish(self, item):
        """是不是某道摆盘菜的一层（BoardBook.goesIntoADish）。"""
        key = keyOf(item)
        return key is not None and any(key in dish["ingredients"] for dish in DishStation.dishes())

    def toolSlot(self, onBoard, items, selected, offhand):
        """手空着时用背包里哪把工具（Cutting.toolSlot，195-210）：选中的快捷栏格、副手、再 0..35 按序，第一个切得了 onBoard 的。
        items 是 36 格背包（空格 None），selected 是选中的快捷栏格（0-8，不知道给 -1），offhand 是副手的物品或 None。
        返回 ("inv", 格号) / ("offhand",) / None。"""
        order = ([("inv", selected)] if 0 <= selected < min(9, len(items)) else []) + [("offhand",)] + [("inv", i) for i in range(len(items))]
        for where in order:
            tool = offhand if where[0] == "offhand" else items[where[1]]
            if keyOf(tool) is not None and self.cutsWith(onBoard, tool):
                return where
        return None

    def isTool(self, item, onBoard):
        """手上这件是不是板上的"工具"、永远不当一层也不当要切的东西（Cutting.isTool(level, 物品, 板上的, 全部摆盘菜)，221-234）：
        它是某个配方的工具，而且（能切板上这样东西，或没有任何摆盘菜把它当一层）。"""
        return self.isToolItem(item) and (bool(onBoard) and self.cutsWith(onBoard, item) or not self.goesIntoADish(item))

    # ---------------------------------------------------------------- 摆盘

    def isBase(self, item):
        key = keyOf(item)
        return key is not None and DishStation.isBase(key)

    def fits(self, layers, item):
        """板上这些层（底座在前）再放一层 item，还是不是某道菜的一部分（AssemblyRecipes.fits）。"""
        key = keyOf(item)
        return key is not None and DishStation.fitsNext([keyOf(layer) for layer in layers], key)

    # ---------------------------------------------------------------- 插着的工具

    def canHold(self, item):
        """这件东西的数据（附魔、染色、改名、耐久、extraId、userData……）存得进方块实体数据吗：存不进的板不收，不悄悄丢（ItemData.storable）。"""
        return ItemData.storable(item)

    def canStick(self, item):
        """FD 的潜行使用能把它插进空板（Cutting.canStick：有材质等级的工具、三叉戟、剪刀），而且身上的数据存得住（附魔的刀照样插，取回原样还）。"""
        key = keyOf(item)
        if key is None or not self.canHold(item):
            return False
        return self.typeOf(item) in STICKABLE_TYPES or bool(self.isKnife(key[0]))

    def isCarving(self, item, flag=None):
        """板上这件是不是插着的工具（FD 的 isItemCarvingBoard：潜行使用 / 站点里 Shift 点空板插进去的才是，平常放上去的工具躺着）。
        flag 是这块板的 IsItemCarved 标记（不给就问 self.carved()）：True / False 照它；None = 不知道（加这个标记之前的老存档）——照老办法推断：
        板上有、切不了、却是能插的工具就是。板上怎么画（站点里 Compat/Diegesis/BoardDraw、没开站时 Shared/Rules/BlockDisplay）、
        取回要不要拔出来的动作都问它，说同一个答案。"""
        if keyOf(item) is None:
            return False
        if flag is None and self.carved is not None:
            flag = self.carved()
        if flag is None:
            return not self.cuttable(item) and self.canStick(item)
        return bool(flag)

    def isBlock(self, item):
        """板上这件东西画成立着的方块、还是平躺的图标（JE：物品模型立体才是方块，HoD 的 ItemVoxels.icon / FD 的 CuttingBoardRenderer 的 isGui3d）。
        基岩版的物品类型是 block 的才可能是方块，其中花、野生作物、蘑菇丛的模型在 JE 里是一张贴图（Data/FlatBlockItems），要平躺。
        站点里画板上的东西（Compat/Diegesis/BoardDraw）、没开站时的世界展示（Shared/Rules/BlockDisplay）、切一刀的效果里的 block（BoardChop）都问它，说同一个答案。"""
        key = keyOf(item)
        return key is not None and self.typeOf(item) == "block" and key[0] not in FlatBlockItems and key[0] not in ShownAs

    def isRaised(self, item):
        """平躺着画的这件东西，引擎是不是照方块物品的规矩抬高着画的（物品类型是 block、掉落物却是一张贴图：花、野生作物）：
        摆的时候要把这段扣掉（Shared/Rules/ItemPose.raisedShift），不然浮在板上。站点里和没开站时的世界展示都问它。"""
        key = keyOf(item)
        return key is not None and self.typeOf(item) == "block" and key[0] in FlatBlockItems

    def isDone(self, onBoard):
        """板上的东西是不是"没活干"，该给新的食物让位（BoardLogic.isDone，245-248）：插着的工具，或没有刀切得了的东西（做好的菜）。"""
        return keyOf(onBoard) is not None and (self.isCarving(onBoard) or not self.cuttable(onBoard))

    # ---------------------------------------------------------------- 托盘

    def usable(self, item):
        """托盘里这件亮不亮（BoardBehavior.usable）：有切它的配方、进某道摆盘菜、或是某个配方的工具。"""
        return self.cuttable(item) or self.goesIntoADish(item) or self.isToolItem(item)

    def shiftPlaces(self, item, onBoard=None):
        """Shift 点托盘里这一格是不是直接整叠放上板（onInventoryShiftClick，1337-1348）：不是板上的工具，而且能切或进摆盘菜。"""
        return keyOf(item) is not None and self.canHold(item) and not self.isTool(item, onBoard) and (self.cuttable(item) or self.goesIntoADish(item))
