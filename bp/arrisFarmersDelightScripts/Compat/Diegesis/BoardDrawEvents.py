# -*- coding: utf-8 -*-
"""BoardDrawEvents - 砧板站点里板上东西的一次性动画：拿走、弹回、切开飘走、削皮升起、做成融掉弹出、凑成了落定、铲一铲缩一点、点到活上抖一下（客户端）

从 BoardDraw.py 拆出来（Draw 的一个基类，用它的 ghosts / shown / layers / item / hand / after / isBlock / surface / fromCursor / fromPlayer）。
对应 Hands-On Delight：client/BoardBehavior.java 的 taken / pulledOut / bounced / assembled + pop（654-727、1521-1652）、blockDone（1459-1475）、
refresh 末尾凑成一道菜时各层落定（490-506）、drawWear（516-544）、impact 的 shake（1045-1047）、dress / arrives（1963-2027：液体层、蛋层交给手）。
做成一道菜：各层落定（书里点的先飞来），再照菜的种类演一套收尾（BoardFinishPlay，十种），演完各层沉进去、菜弹出来（pop）。
"""
from . import BoardFinishPlay as Play
from . import BoardFx
from .BoardThing import FLAT, TO_CAMERA, UPRIGHT
from ...Shared.Rules import BoardSounds as Sounds
from ...Shared.Rules.BoardStation import MOST_LAYERS, keyOf
from ...Shared.Rules.HandsOn import BoardFinish as Finish
from ...Shared.Rules.HandsOn import BoardFinishKit as Kit
from ...Shared.Rules.HandsOn import BoardHands as Hands
from ...Shared.Rules.HandsOn import BoardMotion as Motion
from ...Shared.Rules.HandsOn import BoardScene as Scene

GHOSTS = 3                  # 同时飘着几个"拿走 / 弹回"的替身（scene 的 lift_N）
CARVED_SCALE = Scene.scaleOf(Scene.CARVED_SCALE * 16.0)       # 插着的工具画 0.6 个图标大：9.6 像素
CLEARED_WINDOW = 1.0         # 层刚被清空这么久之内收到的 assembled 才认"原来摆着的层"（状态先到、效果随后，隔不了多久）


class DrawEvents(object):
    assembling = 0             # 还在演（pop、done 没走完）的 assembled 有几个：两个重叠时先演完的不还原层，等最后一个演完才还原
    # 下面三个的初值由 Draw.__init__ 给；这里写同样的类属性，是让网易机审（pylint，只看这个类）知道它们有定义（各方法里先读后赋）
    cleared = None
    whole = False
    worn = 1.0

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

    def assembled(self, made, finish, popped):
        """层凑成了菜（assembled 效果，状态已经是层清空、菜躺在板上）：made 是做成的各层（物品，底座在前），finish 是怎么收尾（Assembly.FINISH_*）。
        板上原来就摆着的在原位，没摆过的（书里点的菜一气呵成：放好、做成）先从玩家那边一层隔一层飞来（JE 的 arrive）；都落了，先照 finish 演一套收尾
        （BoardFinishPlay：拌 / 卷 / 串 / 揉 / 摆 / 夹 / 成形 / 冻 / 一起切，压什么也不演），演完（finishing）各层缩小沉进去，菜同一刻弹出来
        （JE 的 pop：两件事一起开始，popped() 放做成的声音、面粉 / 霜、闪光），层沉完（MELT_TIME）才收起来、菜底下垫的那一张才露出来。
        melting 是从现在起到层沉完要多久（等层落完 + 收尾 + MELT_TIME + 一刻）。这一会儿里又来的状态（又放了一层、菜被取走了）先记着
        （Draw.refresh 的 late）：板上的东西在弹出来那一刻、层在沉完那一刻照最新的画。
        第二个 assembled 在第一个没演完时到（书里点菜一键做成，每 0.1 秒能来一次）：JE 不取消前一个（排下的步骤照走），每个各演各的收尾、各响各的做成的声音，
        melting 是后一个覆盖前一个，层只在最后一个演完时才还原（assembling 数着还在演的几个）。"""
        seen, arrive, order, count = self._seen(), self.hand.remaining(), 0, len(made[:MOST_LAYERS])         # 手还在倒 / 磕的先等它放好（pourUntil，1526）
        self.item.hide()
        self.pile.hide()                                      # 垫的那一张不和正在沉的层抢位置（1638）
        for index, layer in enumerate(made[:MOST_LAYERS]):
            thing = self.layers[index]
            home = self._dress(thing, index, layer)
            if index < len(seen) and seen[index] == keyOf(layer):
                if not self.hand.pending(thing):
                    thing.put(*home)                          # 蛋还在手上的这一层等蛋落下才露出来
                continue
            name = layer["newItemName"]
            delay, order = order * Motion.LAYER_STAGGER, order + 1
            arrive = max(arrive, delay + Hands.takes(index, name))
            thing.hide()
            self.after(delay, lambda t=thing, h=home, i=index, n=name: self.land(t, h, i, n, True, lambda: True))
        plan = Finish.plan(finish, [layer["newItemName"] for layer in made[:MOST_LAYERS]], BoardFx.colorOf)
        self.melting = arrive + Kit.sinking(finish, count)
        Play.run(self, plan, arrive, lambda: self._ghost(made[0], FLAT, Scene.scaleOf(Scene.layerSize(0)), Motion.layerTurn(0)))

        def pop():
            for index in range(count):
                Motion.melt(self.layers[index].mover, plan.rest[index])
            late = self.late or ()                        # 没有后来的状态是 None：写成 `or ()`，网易机审（pylint）才不把取下标判成对 None 取下标
            if late:
                self._board(late[0])
                self.pile.hide()
            board = self.shown["board"]
            if board is not None:
                Motion.popUp(self.item.mover, (0.0, 0.0 if board[2] != "flat" else Scene.pileLift(board[1]), 0.0))
            popped()
            self.after(Motion.MELT_TIME, done)

        def done():
            self.assembling -= 1
            if self.assembling > 0:
                return                                        # 后一个 assembled 还在演：层是它在用的，等它演完再还原（JE 的 melting 是后一个覆盖前一个，倒数走完才 scaleTo(1, 0) + setVisible(false)）
            self.melting = 0.0
            for thing in self.layers:
                thing.reset()                                 # 缩小了、转着的层下一回再摆东西不能还是那样（JE 的 tick：scaleTo(1, 0) + setVisible(false)）
            late, self.late = self.late or (), None       # `or ()` 同 pop
            if late:
                self._board(late[0])
            board = self.shown["board"]
            if board is not None and board[1] > 1 and board[2] == "flat":
                self.pile.put(0.0, 0.0, 0.0)
            if late:
                self._layers(late[1])
        self.assembling += 1                                  # pop 和 done 各自排下了：和 done 里的减一对着
        if arrive + plan.seconds > 0.0:
            self.after(arrive + plan.seconds, pop)
        else:
            pop()
        self.frame(0.0)                                  # 不用等的（第一层飞来、都摆着的马上沉）这一刻就开始

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
