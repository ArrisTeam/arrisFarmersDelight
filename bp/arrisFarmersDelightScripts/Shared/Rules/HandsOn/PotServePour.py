# -*- coding: utf-8 -*-
"""PotServePour - 一只手把容器里的液体倒进汤里：端过来、仰一下、倾倒、放正、端走（双端）

移植自 Hands-On Delight 的 client/KitchenMotions.java 的 Pour（93-283 行）。时间一律是秒；位置是场景像素，角度是度。
手是一个物品节点（奶桶、奶瓶），这里只算它每一刻的姿态和那一刻该发生的事：

    ARRIVE 0.3 秒从起点（手从玩家屏幕底部来）划着弧端到倒的位置，先小后大（FROM_SCALE -> 1），同时往倾倒的反方向仰 COCK 度；
    TIP 0.2 秒倾倒到 105 度（桶）/ 125 度（瓶）；
    flow 桶 0.8 秒、瓶 0.55 秒：液体流出来（发 "stream" 事件，粗细先涨后落，桶 1.0、瓶 0.45），容器一边倒一边再多倾 EMPTYING 度，手还有一点抖；
    BACK 0.2 秒放正，同时往上提 1 像素，倒空了的容器（"empty"）；AWAY 0.3 秒提回起点上方 3 像素、一路缩没。
流出来那一刻放倒桶 / 倒瓶的声音，发 "flow" 事件（汤从这时起染上这液体的颜色，PB 834）。
"""
import math

from .Mth import lerp
from .PotServeMath import ITEM_DRAWN, LEAN, LIP_X, LIP_Y, add, mix, pose, rotateY, smooth, tipped
from .PotSounds import shotOf

HAND_SIZE = 2.9               # 手里的瓶 / 桶 / 糖有多大（像素，PB 300）
ARRIVE = 0.3
TIP = 0.2
BUCKET_FLOW = 0.8
BOTTLE_FLOW = 0.55
BACK = 0.2
AWAY = 0.3
ARC = 2.0                     # 端过来的弧顶高出这么多（像素）
COCK = -12.0                  # 先往倾倒的反方向仰这么多度，倾倒时再倒过来
EMPTYING = 14.0               # 倒的时候越倒越倾，一共再倾这么多度
OVER = 3.2                    # 倾倒时瓶口在落点上方这么高（像素）
THROW = 1.3                   # 液体满流时离开瓶口落到离瓶口这么远（像素）
FROM_SCALE = 0.5              # 从手里端来的时候小一半，一路长到原大，不会突然跳到镜头前
WOBBLE = 2.0                  # 手不会纹丝不动：倾倒时角度上叠 2 * sin(11 * 时间) 度
BUCKET_TILT = 105.0
BOTTLE_TILT = 125.0


class Pour(object):
    """一次倒液体。bucket：是桶（慢、粗）还是瓶（快、细）；start：手从哪来；onto：液体落点 (x, _, z)；landY：液面高度（落点的 y）；
    side：-1 向屏幕左边倾（PB 用 -1），yaw：镜头转的度数（0）；color：液体颜色（ARGB）；key：同一个工位上区分几股液体。"""

    def __init__(self, bucket, start, onto, landY, size=HAND_SIZE, side=-1.0, yaw=0.0, color=0xFFFFFFFF, key="pour", liquid="broth"):
        self.bucket = bucket
        self.start = tuple(start)
        self.landY = landY
        self.size = size
        self.side = side
        self.yaw = yaw
        self.color = color
        self.key = key
        self.liquid = liquid
        self.lipX = side * LIP_X
        self.tilt = side * (BUCKET_TILT if bucket else BOTTLE_TILT)
        self.flow = BUCKET_FLOW if bucket else BOTTLE_FLOW
        self.thick = 1.0 if bucket else 0.45
        lip = tipped(self.lipX, LIP_Y, size, self.tilt, yaw)
        away = self._outward(THROW)
        # 倾倒到位时：中间点 + 瓶口 + 满流的抛出距离 = 落点
        self.middle = (onto[0] - away[0] - lip[0], landY + OVER - lip[1], onto[2] - away[2] - lip[2])
        self.age = 0.0
        self.flowing = False              # 液体已经开始流（Java 的 hasFlowed）
        self.emptied = False              # 已经倒空，显示的是空容器
        self.done = False
        self.scale = size / ITEM_DRAWN * FROM_SCALE

    @staticmethod
    def pouredBy(bucket):
        """从开始到液体倒完的秒数：ARRIVE + TIP + 流的时间（桶 1.3，瓶 1.05）。"""
        return ARRIVE + TIP + (BUCKET_FLOW if bucket else BOTTLE_FLOW)

    @property
    def duration(self):
        """整套动作多长（秒）：倒完之后还要放正和端走。"""
        return self.pouredBy(self.bucket) + BACK + AWAY

    def _outward(self, amount):
        """瓶口指的方向走 amount 像素（水平）。"""
        return rotateY((-self.side * amount, 0.0, 0.0), self.yaw)

    def _place(self, at, angle, scale=None):
        if scale is not None:
            self.scale = scale
        return pose(at, (LEAN, self.yaw, angle), self.scale, True, item="empty" if self.emptied else "full")

    def step(self, dt, landY=None):
        """推进 dt 秒；landY 是此刻的液面（缺省沿用构造时的）。返回 (pose, events)；走完后 pose 的 visible 为 False。

        pose：{"pos", "rot": (LEAN, yaw, 倾斜度), "scale", "visible", "item": "full" | "empty"}。
        events：sound（倒桶 / 倒瓶，液体开始流的那一刻）/ flow（同一刻）/ stream（流出来的每一帧：key、from、to、color、strength、liquid）/ droplets（倒空那一刻）。
        """
        land = self.landY if landY is None else landY
        events = []
        if self.done:
            return pose(self.start, (LEAN, self.yaw, 0.0), self.scale, False, item="empty"), events
        self.age += dt
        t = self.age
        side, size = self.side, self.size
        if t < ARRIVE:
            k = smooth(t / ARRIVE)
            at = add(mix(self.start, self.middle, k), (0.0, ARC * math.sin(k * math.pi), 0.0))
            return self._place(at, side * COCK * k, size / ITEM_DRAWN * lerp(k, FROM_SCALE, 1.0)), events
        t -= ARRIVE
        if t < TIP:
            return self._place(self.middle, lerp(smooth(t / TIP), side * COCK, self.tilt)), events
        t -= TIP
        if t < self.flow:
            if not self.flowing:
                self.flowing = True
                events.append(shotOf("bucket" if self.bucket else "bottle"))
                events.append({"type": "flow"})
            k = t / self.flow
            angle = self.tilt + side * EMPTYING * k + WOBBLE * math.sin(self.age * 11.0)
            strength = self.thick * smooth(t / 0.08) * (1.0 - 0.75 * smooth((k - 0.55) / 0.45))
            lip = add(tipped(self.lipX, LIP_Y, size, angle, self.yaw), self.middle)
            away = self._outward(THROW * (0.4 + 0.6 * strength / self.thick))
            events.append({"type": "stream", "key": self.key, "from": lip, "to": (lip[0] + away[0], land, lip[2] + away[2]), "color": self.color,
                           "strength": strength, "liquid": self.liquid})
            return self._place(self.middle, angle), events
        t -= self.flow
        if not self.emptied:
            self.emptied = True
            lip = add(tipped(self.lipX, LIP_Y, size, self.tilt + side * EMPTYING, self.yaw), self.middle)
            events.append({"type": "droplets", "count": 2, "pos": lip, "rise": (0.0, -6.0, 0.0), "spread": 0.05, "color": self.color})
        if t < BACK:
            k = smooth(t / BACK)
            return self._place(add(self.middle, (0.0, k, 0.0)), lerp(k, self.tilt + side * EMPTYING, 0.0)), events
        t -= BACK
        if t < AWAY:
            k = smooth(t / AWAY)
            lifted, gone = add(self.middle, (0.0, 1.0, 0.0)), add(self.start, (0.0, 3.0, 0.0))
            return self._place(mix(lifted, gone, k), 0.0, size / ITEM_DRAWN * (1.0 - k)), events
        self.done = True
        return pose(self.start, (LEAN, self.yaw, 0.0), self.scale, False, item="empty"), events
