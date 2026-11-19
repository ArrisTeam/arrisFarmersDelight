# -*- coding: utf-8 -*-
"""BoardView - 切菜板站点里本人的那一层：托盘拿放、点板、落刀、取回、摆盘、食谱书（客户端）

对应 Hands-On Delight：client/BoardBehavior.java 的 onEvent / onItemClick / onInventoryShiftClick / usable / onEffect / frame。
板上的画面（食物、层、落下 / 拿走 / 弹回的动画）在 BoardDraw.py，刀和虚线在 BoardCutter.py，切过的缝在 BoardSeams.py，服务端表现事件的处理在 BoardEffects.py，声音和碎屑在 BoardFx.py。照 JE 的规矩：
- 机位照 scenes/cutting_board.json：相机 (7.5, 35.5, -21) 看 (7.5, 1, 8)，视野 30，0.4 秒，窗口窄时保住左右；没有提示行、没有关闭按钮（chrome = java）；
- 底部托盘（前置包按 usable 列出背包里能切的、能摆盘的、切东西用的工具）拿一叠到手上点板 = 放上去（左键整叠、右键一个），Shift 点托盘 = 整叠直接放上去，
  右键开站时手里的食物也直接放；手上拿着刀、或手空着背包里有刀（选中格 -> 副手 -> 背包），光标移到食物上刀吸附下一刀的虚线，点一下落刀；
  右键 / 没有刀的左键 = 取回；摆盘一层层往上放，凑成了点一下做成；Shift 点空板 = 手上的工具插进去；
- 板上的东西由本端自己画（开站期间 Client/BlockItems 不画这块板，关站还原）；食谱书照旧挂在左边（BookSources）；
- 刀（工具）悬在食物上由本端画，这时内核画在光标上的那一份收起来（carrySize 缩成一个点，JE 的 setCarriedHidden）。
点哪一下算什么在 Shared/Rules/BoardClick.py（离线测过）；触屏没有右键 / Shift，按住不动的菜单在 BoardHold.py（onHold）。坐标：站点像素随玩家所在一侧转，板面中心按方块朝向（FD 的板底座在 x 1..12，柄在旁边）换算。
"""
from . import Arrival, BookSources, FlatSprites, TouchFeel
from . import BoardEffects, BoardFx, BoardHold
from .BoardCutter import Cutter
from .BoardDraw import Draw
from .BoardFx import KNOCK, play
from .BoardGlow import BoardGlow, placeable
from .BoardInv import offhand, selectedSlot, typeOf
from .BoardSeams import Seams
from ...Client import BlockItems
from ...Client.Engine import clientApi
from ...Shared.Rules import BoardClick as Click
from ...Shared.Rules import BoardStation as Rules
from ...Shared.Rules import HandsOnOptions as Options
from ...Shared.Rules.HandsOn import BoardScene as Scene
from ...Shared.Rules.HandsOn import Cutting

SCHEMA_MODULE = "arrisDiegesisScripts.Shared.Schema"   # 前置包的声明模块（StationSchema / ControlSpec / SlotRules）
CARRY_SIZE, CARRY_HIDDEN = 4.5, 0.01                    # 光标栈上的东西画多大（Diegesis 的缺省：板上没有槽节点，不改）；收起来时缩成一个点


class BoardViewMixin(object):
    """和前置包的 StationBehavior 拼成表现类（register 里用 type() 组装）。self.api 是前置包的 Api.Client。"""

    camera = Scene.CAMERA
    flightSeconds = Scene.FLIGHT_SECONDS
    chrome = "java"
    workPlane, carryLift = Scene.WORK_PLANE, 2.5

    def __init__(self, view):
        super(BoardViewMixin, self).__init__(view)
        self.env = Rules.Env(BlockItems.isKnife, typeOf, view.ports.maxStack, lambda: (view.data or {}).get(Rules.CARVED))
        self.draw = None
        self.cutter = self.seams = None
        self.screen = None
        self.carriedHidden = False
        self.glow, self.over = BoardGlow(view.pos), None      # 板的描边、光标底下是哪块（mouth / surface / None）
        self._usable = {}

    @property
    def carrySize(self):
        """内核每帧按它画光标栈上的东西（边长，像素）。本端正把刀 / 工具画在食物上、或板不收的东西正弹回手上时缩到看不见：
        JE 的 view.setCarriedHidden（内核没给这个接口，借它每帧都读 carrySize 这一点）。"""
        return CARRY_HIDDEN if self.carriedHidden else CARRY_SIZE

    # ---------------------------------------------------------------- 状态

    def board(self):
        item = self.view.state.getItem((Rules.GROUP_BOARD, 0))
        return item if Rules.keyOf(item) is not None else None

    def layers(self):
        return [item for item in self.view.state.getItems(Rules.GROUP_LAYERS) if item]

    def ready(self):
        return bool(self.view.data.get("dish"))

    def toolOf(self):
        """现在能用的工具：(物品, 是不是从背包借的)。光标栈上拿着的、切得了板上东西的；手空着就是背包里第一把（选中格 -> 副手 -> 按序）。"""
        board = self.board()
        if board is None or self.layers():
            return None, False
        hand = self.view.hand
        if hand is not None:
            return (hand, False) if self.env.cutsWith(board, hand) else (None, False)
        items, side = self.view.ports.inventory(), offhand()
        where = self.env.toolSlot(board, items, selectedSlot(), side)
        if where is None:
            return None, False
        return (side if where[0] == "offhand" else items[where[1]]), True

    def center(self):
        """板面中心（站点像素 x, z）：FD 的板底座在方块自己坐标的 (6.5, 8)，按方块朝向和玩家这一侧换算。"""
        station = self.view.toStation(*BoardFx.centerOf(self.view.pos))
        return station[0], station[2]

    # ---------------------------------------------------------------- 钩子

    def usable(self, item):
        """托盘里这件亮不亮（按名字和 aux 缓存：每帧要问 36 次）。"""
        key = (item["newItemName"], int(item.get("newAuxValue") or 0))
        if key not in self._usable:
            self._usable[key] = bool(self.env.usable(item))
        return self._usable[key]

    def onInventoryShiftClick(self, slot, item):
        """空手 Shift 点托盘里的一叠（BoardBehavior.onInventoryShiftClick）：能切的 / 能摆盘的整叠直接放上板，返回真——
        内核就不再发 QUICK_MOVE；刀、工具、板不收的返回假。"""
        if slot < 0 or item is None or not self.env.shiftPlaces(item, self.board()):
            return False
        self.view.sendAction("place", {"from": slot})
        return True

    def onTrayClick(self, slot, button, quick):
        """老版本的前置包没有上面那个钩子：Shift 点先发了 QUICK_MOVE（服务端不收），再在这里补 place。新的前置包里
        上面的钩子接了就到不了这里，没接（返回假）的到这里也是同一个判断、什么都不发。"""
        if quick and slot >= 0:
            item = self.view.ports.inventory()[slot]
            if item is not None and self.env.shiftPlaces(item, self.board()):
                self.view.sendAction("place", {"from": slot})

    def pickables(self):
        box = Scene.MOUTH if self.view.hand is not None else Scene.SURFACE
        return [self.api.box("mouth" if self.view.hand is not None else "surface", box[0], box[1])]

    def onOpen(self):
        BlockItems.hide(self.view.dimensionId, self.view.pos, True)
        self.draw = Draw(self.view, self.center(), self.env, self.api.Geometry, getattr(self.api, "ITEM_SPAN", Scene.SPRITE_SPAN))
        self.cutter, self.seams = Cutter(self), Seams(self)
        self.redraw()
        BookSources.attach(self.view, "board")
        if Arrival.byUse(self.view):                  # 从相邻的站点走过来的：主手上的东西不是给这块板的（openedByUse）
            self._useHeld()

    def _useHeld(self):
        """右键开站那一下手里拿着的：不是工具就当点了一下板放上去，板不收就留在手里一声不吭（useHeld，376-385）。"""
        selected = selectedSlot()
        items = self.view.ports.inventory()
        held = items[selected] if 0 <= selected < len(items) else None
        if held is not None and self.view.hand is None and not self.env.isTool(held, self.board()):
            self.view.sendAction("place", {"from": selected, "by_use": True})

    def onClose(self):
        if self.cutter is not None:
            self.cutter.close()
            self.seams.close()
        if self.draw is not None:
            self.draw.close()
        self.cutter = self.seams = self.draw = None
        self.carriedHidden = False
        self.glow.frame(0.0, False)
        BlockItems.hide(self.view.dimensionId, self.view.pos, False)

    def onState(self, changes):
        if self.draw is None:
            return
        self.cutter.pending.state(int(self.view.data.get("marks") or 0), changes.hasSlot((Rules.GROUP_BOARD, 0)))
        self.redraw()
        BookSources.refresh(self.view)

    def frame(self, dt):
        if self.draw is None:
            return
        self.draw.frame(dt)
        self.cutter.frame(dt, self.toolOf()[0])
        self.seams.frame(dt)
        self.carriedHidden = self.cutter.drawn or self.draw.bouncing > 0.0
        over = self.over == "mouth" or self.view.input == self.api.TOUCH       # 触屏没有悬停：拿着放得上的东西就描
        self.glow.frame(dt, over and placeable(self.env, self.view.hand, self.board(), self.layers()))
        if self.cutter.pending.expire(self.cutter.clock):
            self.redraw()

    # ---------------------------------------------------------------- 点

    def onPointer(self, event):
        if self.draw is None:
            return False
        self.screen = event.screen
        if event.ray is not None:
            self.draw.cursor = event.ray
        key = self.over = event.hit.node.key if event.hit is not None else None
        if event.kind != "down":
            return False
        if self.view.hand is not None:
            return key == "mouth" and self._withStack(event)
        return key == "surface" and self._bareHand(event)

    onHold = BoardHold.onHold                 # 触屏长按（前置包的 onHold 钩子）：手上的东西放一个、工具插在板上、空手取回

    def _withStack(self, event):
        """手上拿着东西点板（onItemClick）。"""
        board, layers, hand = self.board(), self.layers(), self.view.hand
        cuts = board is not None and not layers and self.env.cutsWith(board, hand)
        action = Click.withStack(self.env, hand, event.button, event.quick, board, layers, self.ready(), cuts)
        if action[0] == Click.PUT_AWAY:
            return False                                   # 内核把手上的东西放回背包
        if action[0] == Click.CHOP:
            self.cutter.click()
        elif action[0] == Click.KNOCK:
            play(KNOCK, self.view.toWorld(self.draw.cx, self.draw.surface(), self.draw.cz))
            TouchFeel.buzz(self.view, TouchFeel.REFUSE)
        elif action[0] == Click.PLACE:
            self.view.sendAction("place", {"one": bool(action[1])})
            if placeable(self.env, hand, board, layers):
                TouchFeel.flyIn(self.view)                 # 触屏点选的：从托盘里它那一格飞过来（板不收的不飞）
        else:
            self.view.sendAction(action[0])                # carve / assemble
            if action[0] == Click.CARVE:
                TouchFeel.flyIn(self.view)                 # 工具插到板上：也是把手上的东西放上去
        return True

    def _bareHand(self, event):
        """空手点板面（onEvent）。"""
        board = self.board()
        borrowed = self.toolOf()[1]
        carved = board is not None and self.env.isCarving(board)
        action = Click.bareHand(event.button, board, self.layers(), self.ready(), borrowed, carved)
        if action[0] == Click.CHOP:
            self.cutter.click()
        elif action[0] in (Click.TAKE, Click.ASSEMBLE):
            self.view.sendAction(action[0])
        else:
            return False
        return True

    def sendChop(self, x, z, mark):
        """落刀：mark 是第几刀，(x, z) 是刀刃在板面上的位置（离食物中心），换成站点像素给服务端画碎屑用。"""
        self.view.sendAction("chop", {"mark": int(mark), "at": round(self.draw.cz + z, 3), "at_x": round(self.draw.cx + x, 3),
                                      "yaw": int(self.view.yaw)})
        self.redraw()

    def redraw(self):
        """板上的东西、层、铲磨损、凑成菜的落定：状态变了或自己落了刀以后都重画一遍。"""
        data = self.view.data
        self.draw.refresh(self.board(), self.layers())
        self.draw.wear(data.get("stroke") == Cutting.TOOL_DIG, min(int(data.get("plan") or 0), int(data.get("marks") or 0) + self.cutter.pending.count))
        self.draw.settle(self.ready())

    # ---------------------------------------------------------------- 服务端的表现事件

    def onEffect(self, name, data):
        if self.draw is not None:
            BoardEffects.onEffect(self, name, data)


def register(api):
    """前置包在场时调用：把 mixin 和前置包的 StationBehavior 拼成表现类并登记（schema 和服务端同一份）。
    太旧的前置包（API < BoardStation.MIN_API_VERSION）上砧板照旧走经典玩法，返回 None；配置里关了砧板站点（cutting_board）也一样，和服务端的 BoardLogic.register 同一个条件。"""
    if not Options.cuttingBoard() or getattr(api, "API_VERSION", 0) < Rules.MIN_API_VERSION:
        return None
    behaviorClass = type("CuttingBoardBehavior", (BoardViewMixin, api.StationBehavior), FlatSprites.attrs(api, {"api": api}))
    kit = getattr(api, "Schema", None) or clientApi.ImportModule(SCHEMA_MODULE)
    api.registerBehavior(Rules.STATION_ID, Rules.BOARD_BLOCKS, behaviorClass, schema=Rules.buildSchema(kit))
    return behaviorClass
