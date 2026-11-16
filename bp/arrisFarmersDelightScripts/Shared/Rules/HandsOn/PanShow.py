# -*- coding: utf-8 -*-
"""PanShow - 一口煎锅在客户端的样子：锅里的食物怎么摆、怎么落进来、怎么颠、怎么冒油星、什么时候提醒翻面（双端，纯逻辑）

移植自 Hands-On Delight 的 client/SkilletBehavior.java 里"每个客户端都跑"的那部分（场景是 idle_visible：32 格内的人都看得见）：
状态来自服务端（PanLookState 解出来交给 apply / progress），动作由 frame 一帧帧往前走，粒子和声音攒成事件（drain），
本人手上的操作（抓锅柄、点食物）经 strokeStart / strokeMove / strokeEnd / clickFood 进来，要告诉服务端的攒进 actions。
Java 里用节点（piece_N 上面的、under_N 垫在下面的、lift_N 走的替身、hand_N 蛋的手、spill_N 蛋液、pan 整只锅）和 NodeView 的命令摆东西，
这里一样（PanNodes），画的人每帧读 nodes 里每个节点的 pos / rot / scale / visible / item。锅里的节点（pan 的孩子）位置在锅的坐标里
（离锅心），hand / spill 在场景坐标里。

整件事分在几个模块：PanLayout（摆法）、PanLand（落、走、蛋）、PanToss（颠锅）、PanHeat（油星热气声音）、PanOil（油膜）、PanStroke（手势）。
这里是它们共用的状态和 refresh（refresh 228-305）、drawPiece（312-334）、frame（465-488）、onEffect（880-916）。
规则（能不能煎、熟了变什么、蛋只煎一面）由调用方给的 rules 回答：canFry / friedOf / isOneSided。
"""
from functools import partial

from .Items import keyOf, make
from .PanEffects import onEffect
from .PanHeat import Heat
from .PanLand import GLIDE, LAND_FROM, LAND_TIME, PIECE_STAGGER, PLAYER_LAND_TIME, Egg, Landings, single
from .PanLayout import PIECES, counts, height, look, place, size, yaw
from .PanNodes import Node, Steps
from .PanOil import Oil
from .PanStroke import CLICK_STRENGTH, LIFT, LIFT_TIME, SET_DOWN_TIME, TOSS_GAP, Stroke
from .PanToss import TOSSING, IN_AIR, settle, tossed

TICK = 0.05                 # 客户端每刻（SkilletBehavior.tick）


class PanShow(object):
    def __init__(self, rules, rand, fromPlayer=None, cursorOn=None):
        self.rules, self.rand = rules, rand
        self.fromPlayer = fromPlayer or (lambda height, index, count: (0.0, 0.0))
        self.cursorOn = cursorOn or (lambda height: None)
        self.steps = Steps()
        self.nodes = {"pan": Node("pan", (8.0, 0.0, 8.0))}
        for i in range(PIECES):
            for name in ("piece", "under", "lift"):
                self.nodes["%s_%d" % (name, i)] = Node("%s_%d" % (name, i), (0.0, 1.01, 0.0), False)
            for name in ("hand", "spill"):
                self.nodes["%s_%d" % (name, i)] = Node("%s_%d" % (name, i), (0.0, 0.0, 0.0), False)
        self.item, self.byHand, self.heated, self.down, self.up = None, False, False, 0.0, 0.0      # 服务端说的
        self.shown, self.shownPieces, self.shownUnders, self.shownUp = None, 0, 0, -1.0           # 画出来的
        self.tossedUp, self.lookHeldUntil, self.tossedAt = None, 0.0, -10.0
        self.quiet, self.focused, self.waitOutline = True, False, False
        self.waitingIn = [False] * (PIECES * 2)
        self.cracking = [None] * PIECES
        self.landings, self.oil, self.heat, self.stroke = Landings(self), Oil(), Heat(self), Stroke()
        self.events, self.actions = [], []
        self._ticks = 0.0

    @property
    def clock(self):
        return self.steps.clock

    # ---- 给调用方 ----

    def drain(self):
        """这一阵攒下的粒子和声音事件；用完清空。"""
        events, self.events = self.events, []
        return events

    def takeActions(self):
        """要告诉服务端的动作 [(名字, 数据)]；用完清空。"""
        actions, self.actions = self.actions, []
        return actions

    def particles(self, style, pos, velocity, spread, count, color):
        self.events.append({"type": "particle", "style": style, "pos": pos, "vel": velocity, "spread": spread, "count": count, "color": color})

    def sound(self, name, volume, pitch):
        self.events.append({"type": "sound", "name": name, "volume": volume, "pitch": pitch})

    def handleOutlined(self, hovered):
        """锅柄描不描边：光标在上面，或者本人在锅边、食物等着翻（outlineHandle 673-675）。"""
        return bool(hovered or (self.waitOutline and self.focused))

    # ---- 食物的样子 ----

    def isCracked(self, stack):
        return stack is not None and self.rules.isOneSided(stack["newItemName"])

    def cookedOf(self, raw):
        """营火把它做成什么：熟的样子（没有就是它自己，347-350）。"""
        fried = self.rules.friedOf(raw["newItemName"])
        return single(raw) if fried is None else make(fried)

    def openedLook(self, stack):
        """生的那面画什么（KitchenLooks.opened）：蛋不连壳躺着，画煎蛋；别的原样。"""
        return self.cookedOf(stack) if self.isCracked(stack) else single(stack)

    def isShownDone(self):
        return self.shown is not None and not self.rules.canFry(self.shown["newItemName"])

    def tossing(self):
        return self.clock - self.tossedAt < TOSSING

    def inAir(self):
        return self.clock - self.tossedAt < IN_AIR

    # ---- 服务端的话 ----

    def apply(self, item, byHand, heated, down, up):
        """服务端告诉了锅里的东西和两面熟到哪（onStateChanged）：以它为准，自己预测的那面作废。"""
        self.item, self.byHand, self.heated, self.down, self.up = item, bool(byHand), bool(heated), down, up
        self.tossedUp = None
        self.refresh()

    def progress(self, down, up):
        """两面的熟度往前走了（客户端按速度推的）：不当作服务端的新话。"""
        self.down, self.up = down, up

    def refresh(self):
        """锅里的东西变了就重摆：几块、什么样、新来的落进来（refresh 228-305）。"""
        batch, pieces, unders = counts(self.item["count"] if self.item else 0)
        up = self.shownUp if self.clock < self.lookHeldUntil else (self.up if self.tossedUp is None else self.tossedUp)
        same = keyOf(self.item) == keyOf(self.shown) or (self.shown is not None and self.item is not None
                                                           and keyOf(self.cookedOf(self.shown)) == keyOf(self.item))
        if same and pieces == self.shownPieces and unders == self.shownUnders and look(up) == look(self.shownUp):
            return
        before = self.shownPieces if same else 0
        self.shown, self.shownPieces, self.shownUnders, self.shownUp = self.item, pieces, unders, up
        if pieces > 0:
            self.oil.lay([place(i, pieces) for i in range(pieces)], size(pieces))
        for i in range(PIECES):
            self._drawPiece(self.nodes["piece_%d" % i], i, i < pieces, False)
            self._drawPiece(self.nodes["under_%d" % i], i, i < unders, True)
        if not self.quiet:
            self._arrive(before, pieces)
        self.quiet = False

    def _drawPiece(self, node, index, visible, under):
        node.setVisible(visible and not self.waitingIn[PIECES + index if under else index])
        if not visible:
            return
        node.item = self.cookedOf(self.shown) if self.shownUp >= 1.0 else self.openedLook(self.shown)
        node.size = size(self.shownPieces)
        if not self.landings.landing(index, under) and not (self.tossing() and node.moving):
            at = place(index, self.shownPieces)
            node.moveTo(at[0], height(under, self.shownUnders), at[1], 0.0 if self.quiet else GLIDE)
            node.rotateTo(0.0, yaw(index, under), 0.0, 0.0)

    def _arrive(self, before, pieces):
        """新来的落进来；几块一起来的从玩家那边一块接一块飞来；原来躺着的不动（259-303）。"""
        together = pieces - before > 1
        for i in range(before, pieces):
            offset = self.fromPlayer(LAND_FROM, i - before, pieces - before) if together else None
            delay = (i - before) * PIECE_STAGGER
            if delay > 0.0:
                self.waitingIn[i] = self.waitingIn[PIECES + i] = True
                self.nodes["piece_%d" % i].setVisible(False)
                self.nodes["under_%d" % i].setVisible(False)
                self.steps.after(delay, partial(self._lands, i, offset))
            else:
                self._lands(i, offset)

    def _lands(self, index, offset):
        self.waitingIn[index] = self.waitingIn[PIECES + index] = False
        if index >= self.shownPieces:
            return
        if self.isCracked(self.shown):
            self._crack(index, offset)
        else:
            piece = self.nodes["piece_%d" % index]
            piece.setVisible(True)
            self.landings.land(piece, index, False, offset)
        under = self.nodes["under_%d" % index]
        if index < self.shownUnders:
            under.setVisible(True)
            self.landings.land(under, index, True, offset)
        if self.heated and not self.isCracked(self.shown):
            self.steps.after(LAND_TIME if offset is None else PLAYER_LAND_TIME, self.heat.hitsTheFat)

    def _crack(self, index, offset):
        old = self.cracking[index]
        if old is not None:
            old.stop()
        self.cracking[index] = Egg(self, index, offset, self.heated)

    # ---- 每帧 ----

    def frame(self, dt):
        self.steps.clock += dt
        for i in range(PIECES):
            if self.cracking[i] is not None and not self.cracking[i].frame(dt):
                self.cracking[i] = None
        self.steps.run()
        self.landings.step(dt)
        self.heat.frying(dt)
        self.heat.readyGlow(dt)
        self._ticks += dt
        while self._ticks >= TICK:
            self._ticks -= TICK
            self.tick()
        for node in self.nodes.values():
            node.update(dt, self.rand)

    def tick(self):
        self.refresh()
        for i in range(PIECES):
            lift = self.nodes["lift_%d" % i]
            if lift.visible and not lift.moving:
                lift.setVisible(False)

    # ---- 本人的手 ----

    def toss(self, strength):
        """本人颠：马上演给自己看、告诉服务端（772-781）。锅里没东西、上一颠还在空中就不颠。"""
        if self.shown is None or self.clock - self.tossedAt < TOSS_GAP:
            return False
        self.actions.append(("toss", {"strength": round(strength, 3)}))
        tossed(self, strength)
        return True

    def strokeStart(self, y):
        self.stroke.start(y, self.clock)
        self.nodes["pan"].moveTo(LIFT[0], LIFT[1], LIFT[2], LIFT_TIME)

    def strokeMove(self, y):
        if self.stroke.held:
            self.stroke.move(y, self.clock, self.toss)

    def strokeEnd(self):
        if self.stroke.held and self.stroke.end(self.clock, self.toss):
            self.nodes["pan"].moveTo(0.0, 0.0, 0.0, SET_DOWN_TIME)

    def clickFood(self, button):
        """点锅里的食物（721-728）：右键、或已经熟了，全拿出来；否则颠一下。"""
        if self.shown is None:
            return
        if button == 1 or self.isShownDone():
            self.actions.append(("take", {}))
        else:
            self.toss(CLICK_STRENGTH)

    def close(self):
        """本人离开站点：手松开，锅放回原位。"""
        self.stroke.cancel()
        settle(self.nodes["pan"], SET_DOWN_TIME)

    def effect(self, name, data):
        """服务端的一次性表现（onEffect，PanEffects）。"""
        onEffect(self, name, data)
