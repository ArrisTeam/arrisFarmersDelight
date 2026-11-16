# -*- coding: utf-8 -*-
"""BoardDraw - 砧板站点里本人看到的板上的东西：等着切的食物（一叠、方块类、插着的工具）、摆盘的层、做好的菜，和它们的动画（客户端）

对应 Hands-On Delight：client/BoardBehavior.java 的 refresh / drawItem / land / taken / pulledOut / bounced / assembled 的 pop（409-510、595-727、1620-1652）。
HoD 把图标切成体素、按刀口分开；这里是客户端掉落物，整张图：食物平躺（一叠不止一个时底下再垫一张、转一个角度），方块类立着，
摆盘的层一层层叠起来（每层带一点固定的偏转偏移），插着的工具刀尖朝下。每样东西一个 Thing（Mover 管位置 / 缩放，道具跟着）：
手放下的东西从光标上方弧着落下、再落定；拿走的抬起来缩没；板不收的落在板顶又弹回；最后一刀切开的食物往上飘着缩没；
层凑成菜时各层缩小沉进去、菜弹出来。开站期间本端不画 Client/BlockItems 那份（hide），关站还原。位置是离板面中心的偏移 (x, 离板面的高, z)，
中心由 BoardView 按方块朝向算好交进来。
"""
import math

from .BoardThing import FLAT, UPRIGHT, Thing
from ...Shared.Data.Cutting import CuttingBoardDict
from ...Shared.Rules.BoardStation import MOST_LAYERS, keyOf
from ...Shared.Rules.HandsOn import BoardMotion as Motion
from ...Shared.Rules.HandsOn import BoardScene as Scene

BLOCK_TYPE = "block"
TOOL_TYPES = frozenset(("sword", "axe", "hoe", "shovel", "pickaxe"))
GHOSTS = 3                  # 同时飘着几个"拿走 / 弹回"的替身（scene 的 lift_N）
CARVED_SCALE = Scene.scaleOf(Scene.CARVED_SCALE * 16.0)       # 插着的工具画 0.6 个图标大：9.6 像素


class Draw(object):
    """一个打开着的砧板的画面。view 是 StationView，center 是板面中心（站点像素 x, z），typeOf(物品) 问物品类型，geometry 是内核的 Geometry。"""

    def __init__(self, view, center, typeOf, geometry):
        self.view = view
        self.cx, self.cz = center
        self.typeOf = typeOf
        self.geometry = geometry
        self.item = Thing(self)
        self.pile = Thing(self)
        self.layers = [Thing(self) for _ in range(MOST_LAYERS)]
        self.ghosts = [Thing(self) for _ in range(GHOSTS)]
        self.ghost = 0
        self.shown = {"board": None, "layers": []}      # 现在画着的：板上的 (身份, 数量, 种类)、各层的身份
        self.clock = 0.0
        self.steps = []
        self.melting = 0.0                              # 层正在沉进做好的菜：这么久之内不理状态里的东西
        self.cursor = None                              # 光标射线（站点射线）：落下的东西从光标上方来
        self.quiet = True                               # 刚开站的第一眼：板上有的就是有的，不落下

    # ---------------------------------------------------------------- 类型

    def isBlock(self, item):
        return self.typeOf(item) == BLOCK_TYPE

    def kindOf(self, item):
        """这件东西躺在板上是什么样：flat 平躺、block 立着的方块、tool 插着的工具。"""
        if self.typeOf(item) in TOOL_TYPES and keyOf(item) not in CuttingBoardDict:
            return "tool"
        return "block" if self.isBlock(item) else "flat"

    def rolled(self, item, upright):
        """立着的东西里，哪些要顺时针转 135 度（工具刀尖朝下）；方块不转。"""
        return upright and not self.isBlock(item)

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

    # ---------------------------------------------------------------- 状态来了

    def refresh(self, board, layers):
        """服务端状态变了：板上的东西、各层。board 是物品或 None，layers 是物品列表（底座在前）。"""
        if self.melting <= 0.0:
            self._board(board)
            self._layers(layers)
        self.quiet = False
        self.frame(0.0)                                  # 道具马上建 / 删：镜头还在飞（frame 要到位之后才有人调）时板上也不能空着

    def _board(self, board):
        key = (keyOf(board), board["count"], self.kindOf(board)) if keyOf(board) is not None else None
        if key == self.shown["board"]:
            return
        old, self.shown["board"] = self.shown["board"], key
        if key is None:
            self.item.hide()
            self.pile.hide()
            return
        kind = key[2]
        if kind == "tool":
            self.pile.hide()
            self.item.set(board, UPRIGHT, CARVED_SCALE)
            self.item.put(0.0, Scene.CARVED_Y + 1.01 - Scene.TOP - CARVED_SCALE * Scene.SPRITE_SPAN / 2.0, 0.0)
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
        for index in range(MOST_LAYERS):
            thing = self.layers[index]
            if index >= len(layers):
                thing.hide()
                continue
            pose = Scene.layerPose(index)
            thing.set(layers[index], FLAT, Scene.scaleOf(Scene.layerSize(index)), pose["turn"])
            home = (pose["x"], pose["y"], pose["z"])
            if index >= len(old) and not self.quiet:
                thing.hide()                                             # 新放的一层：从光标上方落下（书里一次放好几层时依次来）
                self.after((index - len(old)) * Motion.LAYER_STAGGER, lambda t=thing, h=home: Motion.land(t.mover, h, self.fromCursor(h, Motion.DROP_HEIGHT)))
            elif index < len(old) and old[index] == keys[index]:
                continue
            else:
                thing.put(*home)

    # ---------------------------------------------------------------- 一次性的事

    def _ghost(self, item, kind, scale, turn=0.0):
        self.ghost = (self.ghost + 1) % GHOSTS
        thing = self.ghosts[self.ghost]
        thing.set(item, kind, scale, turn)
        thing.mover.scaleTo(1.0)
        thing.mover.visible = True
        return thing

    def taken(self, stack, layer, carved):
        """拿走了一样（taken 效果）：在原位抬起、缩没；插着的工具拔出来。layer -1 是板上的东西。"""
        if layer >= 0:
            pose = Scene.layerPose(layer)
            ghost = self._ghost(stack, FLAT, Scene.scaleOf(Scene.layerSize(layer)), pose["turn"])
            Motion.lift(ghost.mover, (pose["x"], pose["y"], pose["z"]))
        elif carved:
            ghost = self._ghost(stack, UPRIGHT, CARVED_SCALE)
            Motion.pullOut(ghost.mover, (0.0, Scene.CARVED_Y + 1.01 - Scene.TOP - CARVED_SCALE * Scene.SPRITE_SPAN / 2.0, 0.0))
        else:
            isBlock = self.isBlock(stack)
            ghost = self._ghost(stack, UPRIGHT if isBlock else FLAT, Scene.itemScale(isBlock))
            Motion.lift(ghost.mover, (0.0, 0.0 if isBlock else Scene.pileLift(stack.get("count") or 1), 0.0))

    def bounced(self, stack):
        """板不收的东西：从手上落到板顶、弹回手上。"""
        board, layers = self.shown["board"], self.shown["layers"]
        top = len(layers) * Motion.LAYER_STEP if layers else (self.surface() - Scene.TOP + 0.3 if board else 0.0)
        ghost = self._ghost(stack, FLAT, Scene.scaleOf(Scene.LAYER_SIZE))
        Motion.bounce(ghost.mover, top, self.fromCursor((0.0, top, 0.0), Motion.DROP_HEIGHT))

    def gone(self, item):
        """最后一刀切开的食物：往上飘着缩没（这时状态里的食物已经没了）。"""
        isBlock = self.isBlock(item)
        ghost = self._ghost(item, UPRIGHT if isBlock else FLAT, Scene.itemScale(isBlock))
        Motion.floatAway(ghost.mover, (0.0, 0.0, 0.0))

    def assembled(self, made):
        """层凑成了菜（assembled 效果，状态已经是层清空、菜躺在板上）：把各层重新摆出来，缩小沉进去，菜弹出来。made 是做成的各层（物品，底座在前）。"""
        self.melting = Motion.MELT_TIME + 0.05
        self.item.hide()
        for index, layer in enumerate(made[:MOST_LAYERS]):
            pose = Scene.layerPose(index)
            thing = self.layers[index]
            thing.set(layer, FLAT, Scene.scaleOf(Scene.layerSize(index)), pose["turn"])
            home = (pose["x"], pose["y"], pose["z"])
            thing.put(*home)
            Motion.melt(thing.mover, home)
        board = self.shown["board"]
        lift = 0.0 if not board or board[2] == "block" else Scene.pileLift(board[1])

        def pop():
            self.melting = 0.0
            for thing in self.layers:
                thing.hide()
            if self.shown["board"] is not None:
                self.item.mover.visible = True
                Motion.popUp(self.item.mover, (0.0, lift, 0.0))
        self.after(Motion.MELT_TIME, pop)

    # ---------------------------------------------------------------- 每帧与收场

    def frame(self, dt):
        self.clock += dt
        if self.melting > 0.0:
            self.melting -= dt
        due = [step for step in self.steps if step[0] <= self.clock]
        self.steps = [step for step in self.steps if step[0] > self.clock]
        for _at, run in due:
            run()
        for thing in [self.item, self.pile] + self.layers + self.ghosts:
            thing.frame(dt)

    def close(self):
        for thing in [self.item, self.pile] + self.layers + self.ghosts:
            thing.drop()
