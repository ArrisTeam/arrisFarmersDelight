# -*- coding: utf-8 -*-
"""BoardHandDraw - 砧板站点里放液体层、蛋层的那只手：端着容器 / 蛋过来倒、磕，再把这一层露出来（客户端）

对应 Hands-On Delight：client/BoardBehavior.java 的 arrives（1986-2027）、startHand（2036-2042）、frame 里推手（799-801）。每一刻的姿态和该发生的事在
Shared/Rules/HandsOn/BoardHands.py（用厨锅同一份 Pour / Crack，逐条照 KitchenMotions），这里只管画：
- 手里的东西是一件立着的客户端掉落物（正面朝镜头、往后仰 16 度、在贴图平面里倾）；倒空了换成空容器（桶、玻璃瓶、碗）；蛋磕开之后蛋液是一件平躺的打开的蛋；
- 液体：JE 是一股连着的水柱，下面那一层上再长出一层取液体颜色的淋面。掉落物染不了色、也没有贴着轮廓的膜，所以这里只有从瓶口朝落点撒的一串染了液色的水滴
  （前置包的 droplet 粒子，和厨锅倒液体同一个），倒完容器走了，这一层什么也不画；
- 蛋：磕在板沿、碎壳（本包的 board_dust）、脆响；打开后蛋液落到食物上，落稳了这一层才露出来（BoardDraw 给的 Thing），响一声落定。
同一时刻只有一只手（JE 的 hand_0 / spill_0）：新来的把旧的收起来，被打断的蛋这一层马上露出来（不响）。手只在操作者的客户端里演（旁观的人看到的是
Client/BlockItems 摆的最后的样子，声音由 BoardWatch 补）。
"""
import math
import random

from . import BoardFx
from ...Shared.Rules import BoardSounds as Sounds
from ...Shared.Rules import ItemPose
from ...Shared.Rules.HandsOn import BoardHands as Hands
from ...Shared.Rules.HandsOn import BoardMotion as Motion
from ...Shared.Rules.HandsOn import BoardScene as Scene

IDENTITY = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
HIDDEN = 0.02               # 缩到这么小就不画（BoardThing 同一个界）
STREAM_TIME = 0.16          # 水滴从瓶口到落点大约走这么久（定初速）：和厨锅 PotHands.STREAM_TIME 一样


class Hand(object):
    """一只手。draw 是 BoardDraw.Draw（要它的 view、板面中心、几何、光标射线、钟和 fromPlayer）。"""

    def __init__(self, draw, rng=random.random):
        self.draw = draw
        self.rng = rng
        self.motion = None             # 正在做的：PotServePour.Pour / PotServeHands.Crack
        self.kind = None
        self.name = None               # 手里的东西（装满的容器 / 蛋）的物品名
        self.owner = None              # 蛋落下来要露出的那一层：(Thing, 落定的位置, 这一层还在不在的判断)；倒液体的是 None
        self.revealed = True
        self.props = {}                # "hand" / "inside" -> [道具, 物品名]
        self.shaking = None            # [幅度, 总时间, 剩下的时间]：蛋磕在板沿上抖一下
        self.until = 0.0               # Draw.clock 上：手把这一层放好（液体倒完、蛋落下）的时刻

    # ---------------------------------------------------------------- 开始

    def pour(self, index, name, home, fromPlayer):
        """第 index 层是液体：手端着装满的容器来倒（arrives:1993-2009）。home 是这一层躺的位置（离板面中心的偏移 (x, 离板面的高, z)）。"""
        draw = self.draw
        start = self._start(Hands.handHeight(index, Hands.POUR), fromPlayer, home)
        self._begin(Hands.pourFor(index, name, home[0], home[2], (draw.cx, draw.cz), start), Hands.POUR, name, None, Hands.lasts(index, name))

    def crack(self, index, name, thing, home, fromPlayer, still):
        """第 index 层是蛋：手端着蛋来磕、打开、蛋液落下（arrives:2011-2027）；落稳了 thing（这一层）才露出来。still() 说这一层还在不在。"""
        draw = self.draw
        start = self._start(Hands.handHeight(index, Hands.CRACK), fromPlayer, home)
        turn = Scene.layerPose(index)["turn"]
        self._begin(Hands.crackFor(index, home[0], home[2], (draw.cx, draw.cz), start, turn), Hands.CRACK, name, (thing, home, still), Hands.lasts(index, name))

    def _start(self, height, fromPlayer, home):
        """手从哪来（handFrom，2044-2055；站点像素）：书里点的菜从屏幕底边（玩家那边）、手放的从光标落在 height 高的那一层平面上的点，没有光标在落点正上方。"""
        draw = self.draw
        if fromPlayer:
            off = draw.fromPlayer(height)
            return (draw.cx + home[0] + off[0], height, draw.cz + home[2] + off[1])
        found = draw.geometry.planeAtHeight(draw.cursor, height) if draw.cursor is not None else None
        return found if found is not None else (draw.cx + home[0], height + 2.0, draw.cz + home[2])

    def _begin(self, motion, kind, name, owner, lasts):
        self.stop()
        self.motion, self.kind, self.name, self.owner = motion, kind, name, owner
        self.revealed = owner is None
        self.shaking = None
        self.until = self.draw.clock + lasts

    # ---------------------------------------------------------------- 状态

    def remaining(self):
        """手还要多久才把这一层放好（秒）：做成菜要等它（pourUntil，250 / 1526）。"""
        return max(0.0, self.until - self.draw.clock) if self.motion is not None else 0.0

    def pending(self, thing):
        """这一层（Thing）是蛋、手还没把它放好：先不露出来，等蛋落下。"""
        return self.motion is not None and self.owner is not None and not self.revealed and self.owner[0] is thing

    # ---------------------------------------------------------------- 每帧

    def frame(self, dt):
        motion = self.motion
        if motion is None:
            return
        if self.kind == Hands.POUR:
            pose, events = motion.step(dt)
            poses = {"hand": pose}
        else:
            poses, events = motion.step(dt)
        for event in events:
            self._event(event)
        egg = poses.get("hand") or poses["egg"]
        name = (Hands.containerOf(self.name) or self.name) if egg.get("item") == "empty" else self.name
        self._hand(egg, name, self._shake(dt))
        if "inside" in poses:
            self._inside(poses["inside"])
        if self.kind == Hands.CRACK and motion.landed and not self.revealed:
            self._reveal(True)
        if motion.done:
            self.motion = None
            self._drop()

    def _shake(self, dt):
        """蛋磕在板沿上抖一下：每帧在 ±幅度里随机偏一点，幅度线性变小（NodeInstance.shake）。"""
        if self.shaking is None:
            return (0.0, 0.0, 0.0)
        self.shaking[2] = max(0.0, self.shaking[2] - dt)
        offset = Motion.shakeOffset(self.shaking[0], self.shaking[1], self.shaking[2], self.rng)
        if self.shaking[2] <= 0.0:
            self.shaking = None
        return offset

    def _hand(self, pose, name, offset):
        """手里的东西：立着，正面朝镜头、往后仰、在贴图平面里倾；缩到看不见就收掉。"""
        if not pose["visible"] or pose["scale"] <= HIDDEN or not name:
            return self._remove("hand")
        center = tuple(a + b for a, b in zip(pose["pos"], offset))
        self._put("hand", name, center, pose["scale"], matrix=ItemPose.standingMatrix(IDENTITY, pose["rot"][0], pose["rot"][2]))

    def _inside(self, pose):
        """蛋液：平躺的打开的蛋，大小是这一层的大小，转这一层的角度（和这一层最后的样子一个摆法，落下去那一帧收掉、由这一层接手）。"""
        scale = pose["scale"]
        if not pose["visible"] or scale <= HIDDEN:
            return self._remove("inside")
        x, y, z = pose["pos"]
        angle = math.radians(pose["rot"][1])
        self._put("inside", Hands.EGG_LOOK, (x, y + Scene.FLAT_LIFT * scale, z), Scene.scaleOf(self.motion.insideSize) * scale,
                  flat=True, along=(math.cos(angle), math.sin(angle)))

    def _put(self, node, name, center, scale, matrix=None, flat=False, along=(1.0, 0.0)):
        held = self.props.get(node)
        if held is not None and held[1] != name:                      # 倒空了换成空容器：重建
            self._remove(node)
            held = None
        if held is None:
            prop = self.draw.view.props.item({"newItemName": name, "newAuxValue": 0, "count": 1}, center, flat=flat, along=along, scale=scale, matrix=matrix)
            self.props[node] = [prop, name]
        else:
            held[0].move(center=center, along=along, scale=scale, matrix=matrix)

    def _remove(self, node):
        held = self.props.pop(node, None)
        if held is not None:
            self.draw.view.props.remove(held[0])

    def _drop(self):
        for node in list(self.props):
            self._remove(node)

    # ---------------------------------------------------------------- 事件

    def _world(self):
        draw = self.draw
        return draw.view.toWorld(draw.cx, Scene.TOP, draw.cz)

    def _event(self, event):
        """手的动作发的事：声音（倒桶 / 倒瓶 / 磕蛋）、蛋壳碎屑、水柱和瓶口的水滴、蛋磕在板沿上抖一下。"""
        draw, kind = self.draw, event["type"]
        view = draw.view
        if kind == "sound":
            sound = Sounds.handSound(event)
            if sound is not None:
                BoardFx.play(sound, self._world())
        elif kind == "dust":
            BoardFx.puffAt(draw.geometry, int(view.yaw), view.pos, (event["pos"], event["rise"], event["spread"], event["count"]), event["color"] & 0xFFFFFF, view)
        elif kind == "stream":
            start, end = event["from"], event["to"]
            velocity = tuple((end[i] - start[i]) / STREAM_TIME for i in range(3))
            count = 1 + int(event["strength"] * 2.0 + self.rng())
            BoardFx.dropletsAt(draw.geometry, int(view.yaw), view.pos, start, velocity, event["color"] & 0xFFFFFF, count)
        elif kind == "droplets":
            BoardFx.dropletsAt(draw.geometry, int(view.yaw), view.pos, event["pos"], event["rise"], event["color"] & 0xFFFFFF, event["count"])
        elif kind == "shake" and event["node"] == "egg":
            self.shaking = [event["amount"], event["seconds"], event["seconds"]]

    # ---------------------------------------------------------------- 收场

    def _reveal(self, landed):
        """蛋落到了（或被打断）：这一层露出来。落到的响一声落定（arrives:2023-2024），被打断的不响；这一层要是已经不在了（取走了）就不露。"""
        self.revealed = True
        thing, home, still = self.owner
        if still():
            thing.put(*home)
            if landed:
                BoardFx.play(Sounds.EGG_LANDED, self._world())

    def stop(self):
        """手上原来在做的收起来（startHand 的 stop）；被打断的蛋这一层马上露出来。"""
        if self.motion is not None and not self.revealed:
            self._reveal(False)
        self.drop()

    def drop(self):
        """关站：什么都收了（不露出任何层：站点没了）。"""
        self.motion = None
        self._drop()
