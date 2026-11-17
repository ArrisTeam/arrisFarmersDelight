# -*- coding: utf-8 -*-
"""BoardDrawEvents - 砧板站点里板上东西的一次性动画：拿走、弹回、切开飘走、削皮升起、做成融掉弹出、凑成了落定、铲一铲缩一点、点到活上抖一下（客户端）

从 BoardDraw.py 拆出来（Draw 的一个基类，用它的 ghosts / shown / layers / item / after / isBlock / surface / fromCursor）。
对应 Hands-On Delight：client/BoardBehavior.java 的 taken / pulledOut / bounced / pop（654-727、1620-1652）、blockDone（1459-1475）、
refresh 末尾凑成一道菜时各层落定（490-506）、drawWear（516-544）、impact 的 shake（1045-1047）。
"""
from . import BoardFx
from .BoardThing import FLAT, UPRIGHT
from ...Shared.Rules import BoardSounds as Sounds
from ...Shared.Rules.BoardStation import MOST_LAYERS
from ...Shared.Rules.HandsOn import BoardMotion as Motion
from ...Shared.Rules.HandsOn import BoardScene as Scene

GHOSTS = 3                  # 同时飘着几个"拿走 / 弹回"的替身（scene 的 lift_N）
CARVED_SCALE = Scene.scaleOf(Scene.CARVED_SCALE * 16.0)       # 插着的工具画 0.6 个图标大：9.6 像素


class DrawEvents(object):
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
            Motion.pullOut(ghost.mover, (0.0, Scene.CARVED_Y + 1.01 - Scene.TOP - Scene.uprightLift(CARVED_SCALE), 0.0))
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
        Motion.stripAway(ghost.mover, (0.0, 0.0, 0.0), Scene.uprightLift(Scene.itemScale(True)))

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
