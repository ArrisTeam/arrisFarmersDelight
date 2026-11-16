# -*- coding: utf-8 -*-
"""BoardLogic - 切菜板站点的服务端逻辑：槽位、放上去、一刀刀切、取回、插工具、摆盘做成（服务端）

对应 Hands-On Delight：station/BoardLogic.java + station/CuttingBoardStation.java。站点只是交互层：槽组 board（板上的东西）和 layers
（摆盘的层）直接绑在方块实体数据 cuttingDict / dishLayers 上（BoardSlots.py），存档不变，经典玩法（潜行右键、没装前置包）照常读写同一份。
刀口进度只在站点实例里：最后一个人离开就重新布刀口。内核的点击只管托盘（光标栈）；放到板上的一切走自定义动作（槽什么也不收）：
    place {"one", "from", "by_use"}   光标栈上那叠（from 给了就是背包那一格，Shift 点托盘 / 右键开站时主手拿着的）放上去：左键整叠、
                                      one（右键）一个；规则在 Shared/Rules/HandsOn/BoardPlace.py；by_use 板不收就一声不吭
    carve {}                          光标栈上的工具插进空板（Shift 点板）
    chop {"mark", "at", "at_x", "yaw"} 落第 mark 刀（只认下一刀，两刀间隔 >= 0.15 秒），BoardChop.py
    take {}                           取回：有层拿最上一层，否则板上的整个还给厨师
    assemble {}                       层凑成的菜做成（BoardAssemble.py）
    bookFill {"key", "sets"}          食谱书里点的菜：从背包放料（BoardAssemble.fill）
表现事件（给站点里的人）：chopped {at, at_x, spot, angle, tool, item, yaw, count, done}、placed {at}、refused {stack}、taken {stack, at, carved}、
carved、assembled {layers, finish, block}。站点数据 data：marks（已切几刀）、plan / style / spots / angles / stroke（板上的东西怎么切）、
dish（层现在能做成的那道菜的物品名，没有是空串）。
"""
from . import BoardAssemble, BoardChop, BoardGive, BoardSlots, BoardTools
from .BookFill import setsOf
from ...Server.Helpers.BlockItems import DropLegacyDisplays
from ...Server.Helpers.Engine import GetBlockEntityData
from ...Server.Helpers.Fx import ToAllPlayerPlaySound
from ...Server.Helpers.Player import GiveOrDropItem
from ...Server.Helpers import BoardDish as Store
from ...Shared.Data.Cutting import CuttingBoardDict
from ...Shared.Rules import BoardStation as Rules
from ...Shared.Rules import CuttingStation
from ...Shared.Rules import DishStation as Dishes
from ...Shared.Rules.BoardStation import GROUP_BOARD, GROUP_LAYERS, keyOf
from ...Shared.Rules.HandsOn import BoardPlace as Place
from ...Shared.Rules.HandsOn import Cutting

REACH = 6.0
RECHECK_SECONDS = 0.25
SOUNDS = {Place.PLACED: "dig.wood", Place.TAKEN: "armor.equip_leather", Place.CARVED: "dig.wood"}


class BoardLogicMixin(object):
    """和前置包的 StationLogic 拼成站点逻辑类（register 里用 type() 组装，基类只在运行时拿得到）。"""

    kit = None           # 前置包的服务端 Api（register 里放进去）

    def __init__(self, station):
        super(BoardLogicMixin, self).__init__(station)
        self.cut = Cutting.BoardCut()
        self.recipe = None
        self.itemKey = None
        self.picked = None            # 书里最后点的那道菜（成品名）：层凑成它就立刻做成，不等厨师点
        self._sinceCheck = 0.0
        station.state.bindSlots(GROUP_BOARD, BoardSlots.BoardSlot(station.dimensionId, station.pos))
        station.state.bindSlots(GROUP_LAYERS, BoardSlots.LayerSlots(station.dimensionId, station.pos))
        self.restart()

    # ---------------------------------------------------------------- 钩子

    def mayPlace(self, ref, item):
        return False                                       # 放的一律走 place（HoD：内核自己的挪法猜不准）

    def mayTake(self, ref):
        return ref[0] == GROUP_BOARD

    def onOpen(self, playerId):
        data = self._data()
        if data is None:
            return False
        DropLegacyDisplays(data)
        if self._migrate(data):
            self.restart()
        return True

    def tick(self, dt):
        """板上换了东西（经典玩法、别的途径）：重布刀口。数量变了不算（往一叠上接着放不重布）。"""
        self._sinceCheck += dt
        if self._sinceCheck < RECHECK_SECONDS:
            return
        self._sinceCheck = 0.0
        if keyOf(self.boardItem()) != self.itemKey:
            self.restart()

    def onCustomAction(self, playerId, name, data):
        if self._data() is None:
            return False
        if name == "place":
            accepted = self._place(playerId, data)
        elif name == "carve":
            accepted = self._apply(playerId, Place.carve(self.ctx.getHand(), self.boardItem(), self.layers(), self.env()), None)
        elif name == "chop":
            accepted = BoardChop.chop(self, playerId, data)
        elif name == "take":
            accepted = self._apply(playerId, Place.take(self.boardItem(), self.layers(), self.env()), None)
        elif name == "assemble":
            accepted = BoardAssemble.assemble(self, playerId)
        elif name == "bookFill":
            accepted = BoardAssemble.fill(self, playerId, data.get("key"), setsOf(data.get("sets")))
        else:
            return False
        self._publish()
        return accepted

    # ---------------------------------------------------------------- 动作

    def _place(self, playerId, data):
        slot = data.get("from")
        carried = BoardGive.sourceOf(self, slot)
        if carried is None:
            return True                                    # 光标栈空着、背包格号越界或那格是空的：什么也不放（HoD 一样直接返回）
        result = Place.place(carried, self.boardItem(), self.layers(), data.get("one") is True, data.get("by_use") is True, self.env())
        return True if result.ignored else self._apply(playerId, result, slot)

    def _apply(self, playerId, result, slot):
        """把 Place 的结果落到方块、光标栈 / 背包、事件和声音上。"""
        if result.board != self.boardItem():
            self.setBoard(result.board)
        if result.layers != self.layers():
            self.setLayers(result.layers)
        if result.moved:
            BoardGive.take(self, slot, result.moved)
        for item in result.give:
            BoardGive.give(self, item)
        for event, data in result.events:
            self.station.effect(event, data)
            if event in SOUNDS:
                ToAllPlayerPlaySound(self.station.dimensionId, self.station.pos, SOUNDS[event])
        if result.restart:
            self.restart()
        if result.finish:
            BoardAssemble.finishIfWanted(self, playerId)
        return True

    # ---------------------------------------------------------------- 方块实体数据

    def _data(self):
        return GetBlockEntityData(self.station.dimensionId, self.station.pos)

    def env(self):
        return BoardTools.envFor(self)

    def boardItem(self):
        return BoardSlots.boardOf(self._data())

    def layers(self):
        return BoardSlots.layersOf(self._data())

    def setBoard(self, item):
        BoardSlots.writeBoard(self.station.dimensionId, self.station.pos, item)

    def setLayers(self, layers):
        BoardSlots.writeLayers(self.station.dimensionId, self.station.pos, layers)

    def _migrate(self, data):
        """旧版把做好的菜单独存在 dishDone：现在它躺在板的槽里。板空着就并过来，不然还给开站的人。返回板上的东西变没变。"""
        dish = Store.dishOf(data)
        if dish is None:
            return False
        data[Store.DONE_KEY] = None
        if self.boardItem() is None and not self.layers():
            self.setBoard(dish)
            return True
        if self.actor is not None:
            GiveOrDropItem(self.actor, dish, self.station.dimensionId)
        return False

    # ---------------------------------------------------------------- 刀口与同步

    def restart(self):
        """板上换了东西（或刚开站）：重新查配方、重布刀口，并同步给使用者（restart，652-702）。"""
        item = self.boardItem()
        self.itemKey = keyOf(item)
        self.recipe = CuttingBoardDict.get(self.itemKey) if item else None
        if self.recipe is not None and not self.layers():
            self.cut.restart(CuttingStation.planFor(item["newItemName"], self.recipe))
        else:
            self.cut = Cutting.BoardCut()
        self._publish()

    def _publish(self):
        """站点数据：已切几刀、怎么切（有刀口的东西）、层现在能做成哪道菜。"""
        data = {"marks": self.cut.marks, "dish": ""}
        if self.recipe is not None and not self.layers():
            data.update({"plan": self.cut.plan.marks, "style": self.cut.plan.style, "spots": [float(v) for v in self.cut.spots],
                         "angles": [float(v) for v in self.cut.angles], "stroke": CuttingStation.strokeOf(self.recipe)})
        keys = [keyOf(layer) for layer in self.layers()]
        done = Dishes.completed(keys) if keys else None
        if done is not None:
            data["dish"] = str(done["result"][0])
        self.station.state.setData(data)


def register(api):
    """前置包在场时调用：把 mixin 和前置包的 StationLogic 拼成逻辑类并登记站点（站点声明两端同一份，见 BoardStation.buildSchema）。
    太旧的前置包（API < BoardStation.MIN_API_VERSION）上砧板照旧走经典玩法，返回 None。"""
    if getattr(api, "API_VERSION", 0) < Rules.MIN_API_VERSION:
        return None
    logicClass = type("CuttingBoardLogic", (BoardLogicMixin, api.StationLogic), {"kit": api})
    api.registerStation(api.StationType(Rules.STATION_ID, Rules.BOARD_BLOCKS, logicClass, schema=Rules.buildSchema(api), reach=REACH))
    return logicClass
