# -*- coding: utf-8 -*-
"""BoardDraw - 砧板站点里本人看到的板上的东西：等着切的食物（一叠、方块类、插着的工具）、摆盘的层、做好的菜，和它们的动画（客户端）

对应 Hands-On Delight：client/BoardBehavior.java 的 refresh / drawItem / land / taken / pulledOut / bounced / assembled 的 pop（409-510、595-727、1620-1652）。
HoD 把图标切成体素、按刀口分开；这里是客户端掉落物，整张图：食物平躺（一叠不止一个时底下再垫一张、转一个角度），方块类立着，
摆盘的层一层层叠起来（每层带一点固定的偏转偏移），插着的工具刀尖朝下。每样东西一个 Thing（Mover 管位置 / 缩放，道具跟着）：
手放下的东西从光标上方弧着落下、再落定；书里一次放好几层的，从屏幕下沿（玩家那边）一层隔一层飞来；拿走的抬起来缩没；板不收的落在板顶又弹回；
最后一刀切开的食物往上飘着缩没；层凑成菜时各层缩小沉进去、菜弹出来。液体层和蛋层不是落下来的：一只手端着容器 / 蛋来倒、磕（BoardHandDraw，照 JE 的 arrives），
倒完容器走了、这一层什么也不画，蛋落稳了这一层才露出来、画成打开的蛋（BoardHands.lookOf）。开站期间本端不画 Client/BlockItems 那份（hide），关站还原。
位置是离板面中心的偏移 (x, 离板面的高, z)，中心由 BoardView 按方块朝向算好交进来。
"""
import math

from . import BoardFx
from .BoardDrawEvents import CARVED_SCALE, GHOSTS, DrawEvents
from .BoardHandDraw import Hand
from .BoardThing import FLAT, UPRIGHT, Thing
from ...Client.Engine import compFactory, levelId
from ...Shared.Rules.BoardStation import MOST_LAYERS, keyOf
from ...Shared.Rules.HandsOn import BoardMotion as Motion
from ...Shared.Rules.HandsOn import BoardScene as Scene
from ...Shared.Rules.HandsOn import FromPlayer


class Draw(DrawEvents):
    """一个打开着的砧板的画面。view 是 StationView，center 是板面中心（站点像素 x, z），env 是站点的 BoardStation.Env（问物品类型、是不是插着的工具），
    geometry 是内核的 Geometry，span 是内核把道具的中心换成轴心时用的贴图边长（Api.Client.ITEM_SPAN）。"""

    def __init__(self, view, center, env, geometry, span=Scene.SPRITE_SPAN):
        self.view, self.span = view, span
        self.cx, self.cz = center
        self.env = env
        self.typeOf = env.typeOf
        self.front = BoardFx.frontOf(view)              # 插着的工具的贴图正面朝哪（站点方向）
        self.geometry = geometry
        self.item = Thing(self)
        self.pile = Thing(self)
        self.layers = [Thing(self) for _ in range(MOST_LAYERS)]
        self.ghosts = [Thing(self) for _ in range(GHOSTS)]
        self.hand = Hand(self)                          # 倒液体层、磕蛋层的那只手（同一时刻一只）
        self.ghost = 0
        self.shown = {"board": None, "layers": []}      # 现在画着的：板上的 (身份, 数量, 种类)、各层的身份
        self.clock = 0.0
        self.steps = []
        self.melting = 0.0                              # 层在演收尾、沉进做好的菜：这么久之内层是动画的，状态先记着（late）；只有 assembled 的 done 把它归零
        self.late = None                                # 这一会儿里收到的最新状态 (板上的东西, 各层)：菜弹出来、层沉完时照它画
        self.cursor = None                              # 光标射线（站点射线）：落下的东西从光标上方来
        self.bouncing = 0.0                             # 板不收的东西正弹回手上：这么久之内光标栈上的那份先收起来
        self.quiet = True                               # 刚开站的第一眼：板上有的就是有的，不落下
        self.whole = False                              # 层凑成了一道等点的菜（凑成的那一刻各层落定）
        self.worn = 1.0                                 # 铲了几铲以后方块缩到多少
        self.landUntil = 0.0                            # 一起从玩家飞来的几层，要这么久才落完
        self.cleared = None                             # (时刻, 刚被清空的层的身份)：assembled 效果要知道哪些层原来就摆着

    # ---------------------------------------------------------------- 类型

    def isBlock(self, item):
        """画成立着的方块还是平躺的图标（BoardStation.Env.isBlock：物品类型是 block、而且 JE 里的模型是立体的；花、野生作物、蘑菇丛是一张贴图，平躺）。"""
        return self.env.isBlock(item)

    def isRaised(self, item):
        """平躺着画的这件，引擎是不是照方块物品的规矩抬高着画的（BoardStation.Env.isRaised：花、野生作物）。"""
        return self.env.isRaised(item)

    def kindOf(self, item):
        """这件东西躺在板上是什么样：flat 平躺、block 立着的方块、tool 插着的工具（BoardStation.Env.isCarving：没开站时 Client/BlockItems 问的是同一个规矩）。"""
        if self.env.isCarving(item):
            return "tool"
        return "block" if self.isBlock(item) else "flat"

    # ---------------------------------------------------------------- 位置

    def surface(self):
        """板上等着切的东西的顶面离站点地面多高。"""
        board = self.shown["board"]
        return Scene.surfaceHeight(board[1] if board else 1, bool(board and board[2] == "block"))

    def fromCursor(self, home, height):
        """落下的东西从哪来：光标射线在 home 上方 height 高的平面上的点（离落点最多 FROM_CURSOR），没有射线就在正上方。偏移 (x, y, z)。"""
        found = self.geometry.planeAtHeight(self.cursor, Scene.TOP + home[1] + height) if self.cursor is not None else None
        if found is None:
            return (home[0], home[1] + height, home[2])
        dx, dz = found[0] - self.cx - home[0], found[2] - self.cz - home[2]
        length = math.hypot(dx, dz)
        if length > Motion.FROM_CURSOR:
            dx, dz = dx * Motion.FROM_CURSOR / length, dz * Motion.FROM_CURSOR / length
        return (home[0] + dx, home[1] + height, home[2] + dz)

    def after(self, seconds, run):
        self.steps.append((self.clock + seconds, run))

    def fromPlayer(self, height=Scene.TOP + Motion.DROP_HEIGHT):
        """书里放的层从哪飞来，相对它落点的水平偏移 (x, z)（FromPlayer.offset(view, height, 0, 1)）：屏幕下沿正中那点投到 height 高的水平面上，
        减去屏幕正中投到同一个面上的点；拿不到屏幕或相机时是 (0, 0)，从正上方落下。"""
        size = compFactory.CreateGame(levelId).GetScreenSize()
        if not size:
            return (0.0, 0.0)
        fx, fy = FromPlayer.startAt(0, 1)
        points = []
        for x, y in ((fx, fy), FromPlayer.MIDDLE):
            ray = self.view.rayAt((size[0] * x, size[1] * y))
            points.append(FromPlayer.planeAt(ray, height) if ray is not None else None)
        return FromPlayer.offsetOf(points[0], points[1])

    # ---------------------------------------------------------------- 状态来了

    def refresh(self, board, layers):
        """服务端状态变了：板上的东西、各层。board 是物品或 None，layers 是物品列表（底座在前）。"""
        self.landUntil = 0.0
        if self.melting > 0.0:
            self.late = (board, layers)                  # JE 每刻都 refresh：板上的东西照旧跟着状态，层那一半等沉完（Float.isNaN(melting)）
        else:
            self._board(board)
            self._layers(layers)
        self.quiet = False
        self.frame(0.0)                                  # 道具马上建 / 删：镜头还在飞（frame 要到位之后才有人调）时板上也不能空着

    def _board(self, board):
        key = (keyOf(board), board["count"], self.kindOf(board)) if keyOf(board) is not None else None
        if key == self.shown["board"]:
            return
        old, self.shown["board"] = self.shown["board"], key
        self.worn = 1.0                                  # 换了东西：缩放回到 1（put 里做的），铲的磨损从头算
        if key is None:
            self.item.hide()
            self.pile.hide()
            return
        kind = key[2]
        if kind == "tool":
            self.pile.hide()
            home, facing, roll = self.carved(board)
            self.item.set(board, UPRIGHT, CARVED_SCALE, facing=facing, roll=roll)
            self.item.put(*home)
            return
        isBlock = kind == "block"
        self.item.set(board, UPRIGHT if isBlock else FLAT, Scene.itemScale(isBlock))
        lift = 0.0 if isBlock else Scene.pileLift(key[1])
        self.item.put(0.0, lift, 0.0)
        if key[1] > 1 and not isBlock:
            self.pile.set(board, FLAT, Scene.itemScale(), 17.0)
            self.pile.put(0.0, 0.0, 0.0)
        else:
            self.pile.hide()
        if not self.quiet and not self.shown["layers"] and (old is None or (old[0] == key[0] and key[1] > old[1])):
            Motion.land(self.item.mover, (0.0, lift, 0.0), self.fromCursor((0.0, lift, 0.0), Motion.DROP_HEIGHT))

    def _layers(self, layers):
        keys = [keyOf(layer) for layer in layers]
        if keys == self.shown["layers"]:
            return
        old, self.shown["layers"] = self.shown["layers"], keys
        if old and not keys:
            self.cleared = (self.clock, old)
        arriving = [] if self.quiet else list(range(len(old), len(layers)))
        together = len(arriving) > 1                       # 书里点一道菜一次放好几层：从玩家那边一层隔一层飞来，不是全从光标上落下
        for index in range(MOST_LAYERS):
            thing = self.layers[index]
            if index >= len(layers):
                thing.hide()
                continue
            home = self._dress(thing, index, layers[index])
            if index in arriving:
                thing.hide()                                             # 新放的一层：先藏着，到时候再落下（液体层、蛋层由手放）
                self.after(arriving.index(index) * Motion.LAYER_STAGGER, lambda t=thing, h=home, i=index, k=keys[index]: self._arrive(t, h, i, k, together))
            elif index < len(old) and old[index] == keys[index]:
                continue
            else:
                thing.put(*home)
        if together:
            self.landUntil = (len(arriving) - 1) * Motion.LAYER_STAGGER + Motion.PLAYER_LAND_TIME     # 最后一层落完要这么久（凑成菜的落定等它）

    def _arrive(self, thing, home, index, key, fromPlayer):
        """一层落到位：书里一次放好几层的从玩家那边飞来（弧高 2.5 倍），手放的从光标上方落下。排队等的时候这一层已经换了就不演。"""
        if index >= len(self.shown["layers"]) or self.shown["layers"][index] != key:
            return
        self.land(thing, home, index, key[0], fromPlayer, lambda: self._present(index, key))

    def _present(self, index, key):
        """第 index 层现在还是 key 吗（手磕的蛋落下时问：取走了就不露出来）。层正沉进做成的菜时状态已经清空、层是动画的，算还在。"""
        return self.melting > 0.0 or (index < len(self.shown["layers"]) and self.shown["layers"][index] == key)

    # ---------------------------------------------------------------- 每帧与收场

    def frame(self, dt):
        self.clock += dt
        self.bouncing = max(0.0, self.bouncing - dt)
        if self.melting > 0.0:
            self.melting = max(1.0e-6, self.melting - dt)     # 倒数不会自己走完：落在帧上的步骤最多晚一两帧，层还在沉时状态就不能等了
        due = [step for step in self.steps if step[0] <= self.clock]
        self.steps = [step for step in self.steps if step[0] > self.clock]
        for _at, run in due:
            run()
        self.hand.frame(dt)
        for thing in [self.item, self.pile] + self.layers + self.ghosts:
            thing.frame(dt)

    def close(self):
        self.hand.drop()
        for thing in [self.item, self.pile] + self.layers + self.ghosts:
            thing.drop()
