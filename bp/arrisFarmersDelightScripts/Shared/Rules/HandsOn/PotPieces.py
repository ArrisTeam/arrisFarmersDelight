# -*- coding: utf-8 -*-
"""PotPieces - 煮好的汤里浮着的碎料：一块一块从下面冒上来、跟着汤转、绕开勺子和整件的料、走的时候缩没（双端）

移植自 Diegesis 的 impl/client/fx/LiquidPieces.java（update / render 里算位置的部分 / separate / leaveWake）和
Hands-On Delight 的 client/PotBehavior.java 的 pieces（1026-1040 行）。时间一律是秒；位置是汤那个节点的像素（锅中心在 (8, 8)，
汤的内壁各离中心 4 像素）。碎料有哪些、什么颜色见 PotPiecesKinds；一块碎料的常量和曲线在 PotPiecesPiece。

一块碎料：从汤面下 RISE_DEPTH 像素处用 RISE_TIME 秒冒上来（过冲 OVERSHOOT，冒到面上时在水面敲一圈涟漪），按金角螺旋排位置
（向外的距离 reach <= 0.9），随汤转（角速度 = 汤的流速 * (0.45 + 0.75 * reach) + 一点自己的飘），彼此挤开、绕开勺子和整件的料、
不出内壁；实心的（有厚度的）在流得快时偶尔翻个身（TUMBLE_*）。多了就缩走（半衰期 APPEAR_HALF_LIFE），最多 MAX 块。

    pieces = PotPieces(random.random)
    pieces.setMeal(floaters, servings)            # 汤里的份数变了（floaters 来自 PotPiecesKinds.cookedPieces）
    pieces.setCurrent(current); pieces.setObstacles(obstaclesOf(spoon, items))
    drawn, events = pieces.step(dt, surface)      # 每帧；drawn 里每块 {"id", "kind", "color", "size", "grow", "pos", "yaw", "flip", ...}
"""
import math

from .PotPiecesKinds import piecesCount
from .PotPiecesPiece import (APPEAR_HALF_LIFE, CLEARANCE, GONE, ITEM_RADIUS, LIFT, MAX, POT_CENTER, PUSH_HALF_LIFE, REACH, RISE_DEPTH, RISE_RING,
                             RISE_TIME, SEPARATE_PASSES, SPOON_RADIUS, TUMBLE_FROM, TUMBLE_HOP, TUMBLE_RATE, TUMBLE_TIME, WAKE, WAKE_FROM,
                             WAKE_RANGE, WAKE_STEP, Piece, approach, obstaclesOf, overshot, shaded)


class PotPieces(object):
    """一口锅的汤里的碎料。rand 是 0..1 的随机数；half 是汤的内壁离中心的像素（半宽、半深）。"""

    def __init__(self, rand, half=(4.0, 4.0), center=(POT_CENTER, POT_CENTER)):
        self.rand, self.half, self.center = rand, half, center
        self.pieces, self.sources = [], []
        self.wanted = self.made = self.shown = 0
        self.current = 0.0
        self.obstacles = []
        self.wake = WAKE
        self.time = 0.0
        self._events = []

    def set(self, floaters, count):
        """LiquidPieces.set：从现在起浮这些（floaters 列表），要 count 块（至多 MAX）；换了一批东西，原来的都缩走，新的一块块冒上来。"""
        self.wanted = 0 if not floaters else min(count, MAX)
        if list(floaters) != self.sources:
            self.sources = list(floaters)
            for piece in self.pieces:
                piece.leaving = True

    def setMeal(self, floaters, servings):
        """PB 的 pieces()：汤里有 servings 份，浮 piecesCount(servings) 块；新要浮的每一块排一个 "blub" 事件（PB 1038）。

        一批刚煮好、PotFinish 的替身还没走完（PotFinish.waiting）时别调（PB 1027：那时 pieces() 什么都不做）；等它的 "pieces" 事件再调。
        """
        count = piecesCount(servings)
        self.set(floaters, count)
        self._events += [{"type": "blub"} for _ in range(max(0, count - self.shown))]
        self.shown = count

    def setObstacles(self, obstacles):
        """汤里立着的东西：x, z, 半径 逐个排开的平铺列表，汤节点的像素（见 obstaclesOf）。"""
        self.obstacles = list(obstacles)

    def setCurrent(self, radiansPerSecond):
        """汤转得多快（弧度 / 秒，正负是转向）。"""
        self.current = radiansPerSecond

    def setWake(self, strength):
        """块走过留下的尾迹有多清晰，0..1，0 不留。"""
        self.wake = strength

    def step(self, dt, surface=0.0, height=None):
        """推进 dt 秒，返回 (drawn, events)。

        surface 是液面的高度（像素，和 pos 的 y 同一个坐标）；height(u, v) 是汤面在 (u, v)（0..1 的归一化坐标）处的波高，没有就是 0。
        drawn：每块 {"id", "kind", "color"（乘过自己的深浅 shade）, "baseColor", "size"（图案的标称宽度）, "grow"（0..1，实际宽度 = size * grow）,
        "pos": (x, y, z), "yaw"（绕竖轴，弧度）, "flip"（绕水平轴：随波摇 + 翻身，弧度）, "solid", "mirrored", "shade", "leaving"}。
        events：{"type": ...}：blub / ripple（x, z, u, v, strength：块冒到面上）/ wake（u, v, radius, strength：尾迹）。
        """
        events, self._events = self._events, []
        self._update(dt)
        return self._layout(surface, height, events), events

    def _update(self, dt):
        """LiquidPieces.update：长大 / 缩小、冒上来的进度、翻身、被挤开的偏移飘回、转角；缩没了的拿掉；一次只长出一块新的。"""
        self.time += dt
        staying = 0
        for piece in self.pieces:
            if not piece.leaving:
                staying += 1
                piece.leaving = staying > self.wanted
        if staying < self.wanted and self.sources and (not self.pieces or self.pieces[-1].grown > 0.3):
            self.pieces.append(Piece(self.sources[self.made % len(self.sources)], self.made, self.rand))
            self.made += 1
        kept = []
        for piece in self.pieces:
            piece.grown = approach(piece.grown, 0.0 if piece.leaving else 1.0, APPEAR_HALF_LIFE, dt)
            piece.rise = min(1.0, piece.rise + dt / RISE_TIME)
            piece.wakeClock += dt
            if piece.tumble > 0.0:
                piece.tumble += dt / TUMBLE_TIME
                if piece.tumble >= 1.0:
                    piece.tumble = 0.0
                    piece.over = not piece.over
            elif piece.floater[3] and abs(self.current) > TUMBLE_FROM and self.rand() < dt * TUMBLE_RATE * abs(self.current):
                piece.tumble = 0.001
            if not piece.touching:
                settle = 0.5 ** (dt / PUSH_HALF_LIFE)
                piece.pushX *= settle
                piece.pushZ *= settle
            piece.touching = False
            if piece.leaving and piece.grown < GONE:
                continue
            piece.angle += dt * (self.current * (0.45 + 0.75 * piece.reach) + 0.02 * piece.wander)
            kept.append(piece)
        self.pieces = kept

    def _layout(self, surface, height, events):
        """LiquidPieces.render 里算位置的部分：螺旋上的位置、挤开、绕开障碍、留尾迹、冒上来的涟漪、高度。"""
        halfX, halfZ = self.half
        centerX, centerZ = self.center
        for piece in self.pieces:
            cos, sin = math.cos(piece.angle), math.sin(piece.angle)
            stretch = piece.reach * REACH / max(abs(cos), abs(sin))       # 圆被推到方壁的角上：按方形的汤填满
            piece.u, piece.v = cos * stretch, sin * stretch
            size = piece.floater[2] * piece.grown
            piece.radius = size * CLEARANCE
            piece.wayX = centerX + piece.u * (halfX - size * 0.3)
            piece.wayZ = centerZ + piece.v * (halfZ - size * 0.3)
            piece.x, piece.z = piece.wayX + piece.pushX, piece.wayZ + piece.pushZ
        for _ in range(SEPARATE_PASSES):
            self._separate()
        drawn = []
        for piece in self.pieces:
            piece.pushX, piece.pushZ = piece.x - piece.wayX, piece.z - piece.wayZ
            self._leaveWake(piece, events)
            kind, color, nominal, solid = piece.floater
            waveU, waveV = 0.5 + piece.u / 2.0, 0.5 - piece.v / 2.0
            risen = overshot(piece.rise)
            if not piece.rang and risen >= 0.9:
                piece.rang = True
                events.append({"type": "ripple", "x": piece.x, "z": piece.z, "u": waveU, "v": waveV, "strength": RISE_RING})
            below = RISE_DEPTH * (1.0 - risen)
            eased = piece.tumble * piece.tumble * (3.0 - 2.0 * piece.tumble)
            hop = math.sin(piece.tumble * math.pi) * TUMBLE_HOP
            rock = math.sin(self.time * 0.9 + piece.wander * 3.0) * 0.06
            y = surface + LIFT + nominal * 0.1 + hop - below - (height(waveU, waveV) if height else 0.0)
            drawn.append({"id": piece.id, "kind": kind, "color": shaded(color, piece.shade), "baseColor": color, "size": nominal,
                          "grow": piece.grown, "pos": (piece.x, y, piece.z), "yaw": piece.yaw,
                          "flip": rock + (math.pi if piece.over else 0.0) + eased * math.pi, "solid": solid,
                          "mirrored": piece.mirrored, "shade": piece.shade, "leaving": piece.leaving})
        return drawn

    def _leaveWake(self, piece, events):
        """LiquidPieces.leaveWake：走得够远、够快、已经冒上来且不在走的块，在汤面留一个尾迹点。"""
        travelled = math.hypot(piece.x - piece.wakeX, piece.z - piece.wakeZ)
        if travelled < WAKE_STEP:
            return
        speed = travelled / max(piece.wakeClock, 0.001)
        piece.wakeX, piece.wakeZ, piece.wakeClock = piece.x, piece.z, 0.0
        strength = self.wake * min(1.0, (speed - WAKE_FROM) / WAKE_RANGE)
        if strength > 0.0 and piece.rise >= 1.0 and not piece.leaving:
            halfX, halfZ = self.half
            events.append({"type": "wake", "u": 0.5 + (piece.x - self.center[0]) / (2.0 * halfX),
                           "v": 0.5 + (piece.z - self.center[1]) / (2.0 * halfZ), "radius": piece.radius / (2.0 * halfX),
                           "strength": strength})

    def _separate(self):
        """LiquidPieces.separate：块和块互相挤开，让给汤里立着的东西，不出壁。"""
        pieces, obstacles = self.pieces, self.obstacles
        for i, one in enumerate(pieces):
            for j in range(i + 1, len(pieces)):
                other = pieces[j]
                dx, dz = other.x - one.x, other.z - one.z
                clear = one.radius + other.radius
                apart = math.hypot(dx, dz)
                if apart < clear:
                    nx = dx / apart if apart > 0.001 else math.cos(i + j)      # 正好叠在一起的各走各的方向
                    nz = dz / apart if apart > 0.001 else math.sin(i + j)
                    move = (clear - apart) / 2.0
                    one.x, one.z = one.x - nx * move, one.z - nz * move
                    other.x, other.z = other.x + nx * move, other.z + nz * move
                    one.touching = other.touching = True
            for o in range(0, len(obstacles) - 2, 3):
                dx, dz = one.x - obstacles[o], one.z - obstacles[o + 1]
                clear = obstacles[o + 2] + one.radius
                apart = math.hypot(dx, dz)
                if apart < clear:
                    out = clear / max(apart, 0.01)
                    one.x, one.z = obstacles[o] + dx * out, obstacles[o + 1] + dz * out
                    one.touching = True
        for piece in pieces:
            roomX, roomZ = self.half[0] - piece.radius * 0.8, self.half[1] - piece.radius * 0.8
            piece.x = min(max(piece.x, self.center[0] - roomX), self.center[0] + roomX)
            piece.z = min(max(piece.z, self.center[1] - roomZ), self.center[1] + roomZ)
