# -*- coding: utf-8 -*-
"""BoardDrawEvents - 砧板站点里板上东西的一次性动画：拿走、弹回、切开飘走、削皮升起、做成融掉弹出、凑成了落定、铲一铲缩一点、点到活上抖一下（客户端）

从 BoardDraw.py 拆出来（Draw 的一个基类，用它的 ghosts / shown / layers / item / hand / after / isBlock / surface / fromCursor / fromPlayer）。
对应 Hands-On Delight：client/BoardBehavior.java 的 taken / pulledOut / bounced / pop（654-727、1620-1652）、blockDone（1459-1475）、
refresh 末尾凑成一道菜时各层落定（490-506）、drawWear（516-544）、impact 的 shake（1045-1047）、dress / arrives（1963-2027：液体层、蛋层交给手）。
"""
from . import BoardFx
from .BoardThing import FLAT, TO_CAMERA, UPRIGHT
from ...Shared.Rules import BoardSounds as Sounds
from ...Shared.Rules.BoardStation import MOST_LAYERS, keyOf
from ...Shared.Rules.HandsOn import BoardHands as Hands
from ...Shared.Rules.HandsOn import BoardMotion as Motion
from ...Shared.Rules.HandsOn import BoardScene as Scene

GHOSTS = 3                  # 同时飘着几个"拿走 / 弹回"的替身（scene 的 lift_N）
CARVED_SCALE = Scene.scaleOf(Scene.CARVED_SCALE * 16.0)       # 插着的工具画 0.6 个图标大：9.6 像素
CLEARED_WINDOW = 1.0         # 层刚被清空这么久之内收到的 assembled 才认"原来摆着的层"（状态先到、效果随后，隔不了多久）


class DrawEvents(object):
    def _dress(self, thing, index, layer):
        """第 index 层画成什么（dress，1963-1984）：液体层不画、蛋画成打开的蛋、别的原样（BoardHands.lookOf）；返回它躺的位置 (x, y, z)。"""
        pose = Scene.layerPose(index)
        look = Hands.lookOf(index, layer)
        if look is None:
            thing.blank()
        else:
            thing.set(look, FLAT, Scene.scaleOf(Scene.layerSize(index)), pose["turn"])
        return (pose["x"], pose["y"], pose["z"])

    def land(self, thing, home, index, name, fromPlayer, still):
        """第 index 层（物品 name）放到位（arrives，1990-2034）：液体由手端着容器来倒、蛋由手来磕（still() 说这一层还在不在，蛋落下时才露出来），
        别的从玩家那边飞来（fromPlayer）或从光标上方落下。"""
        kind = Hands.kindOf(index, name)
        if kind == Hands.POUR:
            self.hand.pour(index, name, home, fromPlayer)
        elif kind == Hands.CRACK:
            self.hand.crack(index, name, thing, home, fromPlayer, still)
        elif fromPlayer:
            Motion.landFromPlayer(thing.mover, home, self.fromPlayer())
        else:
            Motion.land(thing.mover, home, self.fromCursor(home, Motion.DROP_HEIGHT))

    def carved(self, item):
        """插着的工具怎么摆（FD 的 renderItemCarved，HoD 拔出的虚影用同一套，pulledOut）：画在方块的正中心（不是板底座的中间）、贴图平行于板的正面（朝板的背面）、
        在贴图平面里按类型转角度（镐 / 锄 225、三叉戟 135、别的 180）。返回 (离板面中心的偏移 (x, y, z), 贴图的正面朝哪, roll)；没开站时世界里摆的
        （Shared/Rules/BlockDisplay.boardLayout）是同一个位置、朝向和角度。"""
        home = (Scene.CARVED_X - self.cx, Scene.CARVED_HEIGHT - Scene.TOP - Scene.uprightLift(CARVED_SCALE), Scene.CARVED_X - self.cz)
        return home, self.front, Scene.carvedRoll(self.typeOf(item))

    def _ghost(self, item, kind, scale, turn=0.0, facing=TO_CAMERA, roll=0.0):
        self.ghost = (self.ghost + 1) % GHOSTS
        thing = self.ghosts[self.ghost]
        thing.set(item, kind, scale, turn, facing, roll)
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
            home, facing, roll = self.carved(stack)
            ghost = self._ghost(stack, UPRIGHT, CARVED_SCALE, facing=facing, roll=roll)
            Motion.pullOut(ghost.mover, home)
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
        self.bouncing = Motion.BOUNCE_DOWN + Motion.BOUNCE_UP

    def gone(self, item):
        """最后一刀切开的食物：往上飘着缩没（这时状态里的食物已经没了）。方块类不走这里：它们炸开（碎屑）或升起削出来的东西（stripped）。"""
        ghost = self._ghost(item, FLAT, Scene.itemScale(False))
        Motion.floatAway(ghost.mover, (0.0, 0.0, 0.0))

    def stripped(self, item):
        """削皮切到底：削出来的去皮原木从方块的位置升起 3 像素、缩没（0.3 秒）。"""
        ghost = self._ghost(item, UPRIGHT, Scene.itemScale(True))
        Motion.stripAway(ghost.mover, (0.0, 0.0, 0.0), Scene.BLOCK_SIZE / 2.0)

    def _seen(self):
        """刚被清空的层原来摆着哪些（状态先到、assembled 效果随后，所以这时 shown 已经空了）；隔太久的不算。"""
        stamp, before = self.cleared if self.cleared is not None else (None, [])
        self.cleared = None
        return before if stamp is not None and self.clock - stamp <= CLEARED_WINDOW else []

    def assembled(self, made):
        """层凑成了菜（assembled 效果，状态已经是层清空、菜躺在板上）：made 是做成的各层（物品，底座在前）。板上原来就摆着的在原位，
        没摆过的（书里点的菜一气呵成：放好、做成）先从玩家那边一层隔一层飞来（JE 的 arrive）；都落了各层缩小沉进去，菜同一刻弹出来
        （JE 的 pop：两件事一起开始），层沉完（MELT_TIME）才收起来、菜底下垫的那一张才露出来。这一会儿里又来的状态（又放了一层、
        菜被取走了）先记着（Draw.refresh 的 late）：板上的东西在弹出来那一刻、层在沉完那一刻照最新的画。
        返回各层都落完要多久：落完那一刻放做成的声音和面粉。"""
        seen, arrive, order, homes = self._seen(), self.hand.remaining(), 0, []         # 手还在倒 / 磕的先等它放好（pourUntil，1526）
        self.item.hide()
        self.pile.hide()                                      # 垫的那一张不和正在沉的层抢位置（1638）
        for index, layer in enumerate(made[:MOST_LAYERS]):
            thing = self.layers[index]
            home = self._dress(thing, index, layer)
            homes.append((thing, home))
            if index < len(seen) and seen[index] == keyOf(layer):
                if not self.hand.pending(thing):
                    thing.put(*home)                          # 蛋还在手上的这一层等蛋落下才露出来
                continue
            name = layer["newItemName"]
            delay, order = order * Motion.LAYER_STAGGER, order + 1
            arrive = max(arrive, delay + Hands.takes(index, name))
            thing.hide()
            self.after(delay, lambda t=thing, h=home, i=index, n=name: self.land(t, h, i, n, True, lambda: True))
        self.melting = arrive + Motion.MELT_TIME + 0.05

        def pop():
            for thing, home in homes:
                Motion.melt(thing.mover, home)
            if self.late is not None:
                self._board(self.late[0])
                self.pile.hide()
            board = self.shown["board"]
            if board is not None:
                Motion.popUp(self.item.mover, (0.0, 0.0 if board[2] != "flat" else Scene.pileLift(board[1]), 0.0))

        def done():
            self.melting = 0.0
            for thing in self.layers:
                thing.hide()
            late, self.late = self.late, None
            if late is not None:
                self._board(late[0])
            board = self.shown["board"]
            if board is not None and board[1] > 1 and board[2] == "flat":
                self.pile.put(0.0, 0.0, 0.0)
            if late is not None:
                self._layers(late[1])
        if arrive > 0.0:
            self.after(arrive, pop)
        else:
            pop()
        self.after(arrive + Motion.MELT_TIME, done)
        self.frame(0.0)                                  # 不用等的（第一层飞来、都摆着的马上沉）这一刻就开始
        return arrive

    def settle(self, whole):
        """层凑成了一道等点的菜（站点数据 dish 从空变成有）：各层在原位弹一下、放一声落定；那几层要是一起从玩家飞来的，等它们都落了再弹。"""
        if whole and not self.whole:
            count = len(self.shown["layers"])

            def settleAll():
                for index in range(count):
                    pose = Scene.layerPose(index)
                    Motion.settle(self.layers[index].mover, (pose["x"], pose["y"], pose["z"]))
                BoardFx.play(Sounds.SETTLE, self.view.toWorld(self.cx, Scene.TOP, self.cz))
            if self.landUntil > 0.0:
                self.after(self.landUntil, settleAll)
            else:
                settleAll()
        self.whole = whole

    def wear(self, digging, done):
        """切了 done 刀以后方块现在的样子：铲每一铲缩 14%（贴着板面，缩的是它自己的高），别的工具不缩。"""
        board = self.shown["board"]
        scale = Motion.wornScale(digging and board is not None and board[2] == "block", done)
        if scale != self.worn:
            self.worn = scale
            self.item.mover.scaleTo(scale, Motion.WEAR_TIME)

    def shake(self):
        """工具点到活上：板上等着切的东西抖一下（削皮、剪刀不抖，由调用的人挑）。"""
        self.item.shake()
