# -*- coding: utf-8 -*-
"""PotServeHands - 一只手把粉末抖进汤里、把蛋在锅沿敲开打进汤里；按东西的种类选手的动作（双端）

移植自 Hands-On Delight 的 client/KitchenMotions.java 的 Shake（285-392 行）、Crack（394-571 行），和 client/PotBehavior.java 的
goesIn（812-838 行）、wentIn（840-847 行）、常量 296-306 行。倒液体的 Pour 在 PotServePour。时间一律是秒；位置是场景像素。

Shake（糖、可可、骨粉这类干粉）：ARRIVE 0.3 秒端过来、TURN 0.18 秒翻过来、SHAKE 0.6 秒抖（手腕一抖一抖，粉末每秒 70 粒往下掉、越抖越少，
每 0.1 秒在汤面落下一圈小涟漪）、GONE 0.15 秒缩没。
Crack（蛋）：ARRIVE 0.3 秒端到锅沿、0.06 秒磕下去、0.1 秒弹起来（磕的那一刻蛋壳碎屑和脆响）、0.14 秒移到汤上方、0.1 秒壳裂开消失、
蛋黄蛋白 0.2 秒越落越快地掉进汤里，落到面上溅一下；sinks 时再 0.5 秒沉下去。
"""
import math

from .Mth import lerp
from .PotServeMath import ITEM_DRAWN, LEAN, LIP_Y, add, mix, out, pose, smooth, sub, tipped
from .PotServePour import HAND_SIZE, Pour
from .PotSounds import shotOf

EGG_SIZE = 2.4                # 蛋有多大（像素）
EGG_INSIDE = 2.6              # 打开之后蛋液有多大
POUR_SPREAD = 1.4             # 同时倒进去的几样，落点沿 z 错开这么多（序号 % 3 - 1 倍）
POUR_X = 7.4                  # 倒的落点：锅右边（勺子不在的那边）
POUR_Z = 8.8
RIM_OUT = 5.0                 # 蛋磕在离锅中心这么远的右沿
SHELL = 0xFFEAD9B8            # 蛋壳碎屑的颜色
SPLASH_EGG = 0xFFF4F0E4       # 蛋液落到汤面溅起的颜色
SHAKE_ARRIVE = 0.3
SHAKE_TURN = 0.18
SHAKE_SHAKE = 0.6
SHAKE_GONE = 0.15
SHAKE_TILT = 140.0
SHAKE_OVER = 3.5
GRAINS = 70.0                 # 抖的开头每秒掉多少粒
RINGS = 0.1                   # 抖的时候每隔多久在汤面落一圈涟漪
RING_STRENGTH = 0.05
CRACK_ARRIVE = 0.3
KNOCK_DOWN = 0.06
KNOCK_UP = 0.1
OVER_TIME = 0.14
OPEN = 0.1
FALL = 0.2
SINK = 0.5
KNOCK_DEPTH = 0.7


class Shake(object):
    """粉末抖进汤里。start：手从哪来；onto：落点 (x, _, z)；color：粉末的颜色（ARGB，FoodColors.main）；rand：0..1 的随机数（涟漪的落点抖一抖）。"""

    def __init__(self, start, onto, landY, color, rand, size=HAND_SIZE * 0.8, side=-1.0, yaw=0.0):
        self.start = tuple(start)
        self.landY = landY
        self.color = color
        self.rand = rand
        self.size = size
        self.yaw = yaw
        self.tilt = side * SHAKE_TILT
        mouth = tipped(0.0, LIP_Y, size, self.tilt, yaw)
        self.middle = (onto[0] - mouth[0], landY + SHAKE_OVER - mouth[1], onto[2] - mouth[2])
        self.age = 0.0
        self.started = False
        self.grains = 0.0
        self.rings = 0.0
        self.done = False

    @staticmethod
    def doneBy():
        return SHAKE_ARRIVE + SHAKE_TURN + SHAKE_SHAKE + SHAKE_GONE

    def _place(self, at, angle, scale):
        return pose(at, (LEAN, self.yaw, angle), self.size / ITEM_DRAWN * scale, True)

    def step(self, dt, landY=None):
        """推进 dt 秒，返回 (pose, events)。pose：{"pos", "rot", "scale", "visible"}；events：sound（开始抖）/ grains / ripple。"""
        events = []
        if self.done:
            return pose(self.start, (LEAN, self.yaw, 0.0), 0.0, False), events
        self.age += dt
        t = self.age
        lean = -10.0 * (1 if self.tilt > 0 else (-1 if self.tilt < 0 else 0))
        if t < SHAKE_ARRIVE:
            k = smooth(t / SHAKE_ARRIVE)
            return self._place(add(mix(self.start, self.middle, k), (0.0, 2.0 * math.sin(k * math.pi), 0.0)), lean * k, lerp(k, 0.5, 1.0)), events
        t -= SHAKE_ARRIVE
        if t < SHAKE_TURN:
            return self._place(self.middle, lerp(smooth(t / SHAKE_TURN), lean, self.tilt), 1.0), events
        t -= SHAKE_TURN
        if t < SHAKE_SHAKE:
            if not self.started:
                self.started = True
                events.append(shotOf("sand"))
            k = t / SHAKE_SHAKE
            jerk = math.sin(t * 50.0)                                   # 手腕一抖一抖
            at = add(self.middle, (0.15 * jerk, 0.25 * abs(jerk), 0.0))
            mouth = add(tipped(0.0, LIP_Y, self.size * (1.0 - 0.45 * k), self.tilt, self.yaw), self.middle)
            self.grains += dt * GRAINS * (1.0 - 0.6 * k)
            if self.grains >= 1.0:
                whole = int(math.floor(self.grains))
                events.append({"type": "grains", "count": whole, "pos": mouth, "rise": (0.0, -3.0, 0.0), "spread": 0.35, "color": self.color})
                self.grains -= whole
            self.rings -= dt
            if self.rings <= 0.0:
                self.rings = RINGS
                events.append({"type": "ripple", "x": mouth[0] + (self.rand() - 0.5), "z": mouth[2] + (self.rand() - 0.5), "strength": RING_STRENGTH})
            return self._place(at, self.tilt + 9.0 * jerk, 1.0 - 0.45 * k), events
        t -= SHAKE_SHAKE
        if t < SHAKE_GONE:
            k = smooth(t / SHAKE_GONE)
            return self._place(add(self.middle, (0.0, k, 0.0)), lerp(k, self.tilt, self.tilt * 0.7), 0.55 * (1.0 - k)), events
        self.done = True
        return pose(self.start, (LEAN, self.yaw, 0.0), 0.0, False), events


class Crack(object):
    """蛋在锅沿敲开、蛋液落进汤里。start：手从哪来；rim：蛋最低点磕在哪（场景像素）；onto：蛋液落点 (x, _, z)；landY：液面；
    sinks：蛋液落到面上后沉下去（打进汤里的蛋）还是留在原地等调用方接手；turn：蛋液绕竖轴躺着的度数；
    liquid：落点是不是一个液面（JE 的 liquid 节点，砧板上打在食物上是 null）：不是就落下去不起涟漪、不溅水花、也没有锅里那一声噗。"""

    def __init__(self, start, rim, onto, landY, size=EGG_SIZE, insideSize=EGG_INSIDE, sinks=True, yaw=0.0, turn=0.0, liquid=True):
        self.start = tuple(start)
        self.size = size
        self.insideSize = insideSize
        self.rim = add(rim, (0.0, size * 0.42, 0.0))
        self.over = (onto[0], landY + 2.5, onto[2])
        self.landY = landY
        self.sinks = sinks
        self.yaw = yaw
        self.turn = turn
        self.liquid = liquid
        self.age = 0.0
        self.knocked = self.opened = self.landed = self.done = False

    @staticmethod
    def landsBy():
        """蛋液落到汤面的时刻（秒）：0.3 + 0.06 + 0.1 + 0.14 + 0.1 + 0.2 = 0.9。"""
        return CRACK_ARRIVE + KNOCK_DOWN + KNOCK_UP + OVER_TIME + OPEN + FALL

    def _egg(self, at, angle, scale):
        return pose(at, (LEAN, self.yaw, angle), scale, True)

    def _inside(self, at, scale, visible=True):
        return pose(at, (0.0, self.turn, 0.0), scale, visible)

    def step(self, dt, landY=None):
        """推进 dt 秒，返回 (poses, events)。poses：{"egg": pose, "inside": pose}（蛋和蛋液各一个节点）；
        events：dust（磕的碎屑 / 壳裂开）/ sound（脆响、蛋液落下的噗）/ shake（节点抖一下：node、amount、seconds）/ ripple / splash。"""
        land = self.landY if landY is None else landY
        events = []
        hidden = pose(self.start, (LEAN, self.yaw, 0.0), 0.0, False)
        if self.done:
            return {"egg": hidden, "inside": self._inside(self.over, 0.0, False)}, events
        self.age += dt
        t = self.age
        base = self.size / ITEM_DRAWN
        above = add(self.rim, (0.0, 0.6, 0.0))                          # 停在沿上方一点，再重重磕下去弹开
        nothing = self._inside(self.over, 0.0, False)
        if t < CRACK_ARRIVE:
            k = smooth(t / CRACK_ARRIVE)
            at = add(mix(self.start, above, k), (0.0, 1.5 * math.sin(k * math.pi), 0.0))
            return {"egg": self._egg(at, -20.0 * k, base * lerp(k, 0.5, 1.0)), "inside": nothing}, events
        t -= CRACK_ARRIVE
        if t < KNOCK_DOWN:
            k = t / KNOCK_DOWN
            return {"egg": self._egg(sub(above, (0.0, (0.6 + KNOCK_DEPTH * 0.3) * k * k, 0.0)), -20.0, base), "inside": nothing}, events
        t -= KNOCK_DOWN
        if not self.knocked:
            self.knocked = True
            where = sub(self.rim, (0.0, self.size * 0.42, 0.0))
            events.append({"type": "dust", "count": 5, "pos": where, "rise": (0.0, 3.0, 0.0), "spread": 1.0, "color": SHELL})
            events.append(shotOf("crack"))
            events.append({"type": "shake", "node": "egg", "amount": 0.15, "seconds": 0.12})
        if t < KNOCK_UP:
            at = add(self.rim, (0.0, out(t / KNOCK_UP) * 1.2 - KNOCK_DEPTH * 0.3, 0.0))
            return {"egg": self._egg(at, -20.0, base), "inside": nothing}, events
        t -= KNOCK_UP
        if t < OVER_TIME:
            start = add(self.rim, (0.0, 1.2 - KNOCK_DEPTH * 0.3, 0.0))
            k = smooth(t / OVER_TIME)
            return {"egg": self._egg(mix(start, self.over, k), lerp(k, -20.0, 0.0), base), "inside": nothing}, events
        t -= OVER_TIME
        if not self.opened:
            self.opened = True
            events.append({"type": "dust", "count": 4, "pos": self.over, "rise": (0.0, 1.0, 0.0), "spread": 0.8, "color": SHELL})
        if t < OPEN:
            k = t / OPEN
            inside = self._inside((self.over[0], self.over[1] - 0.3 * k, self.over[2]), 0.5 + 0.2 * k)
            return {"egg": self._egg(self.over, 0.0, base * (1.0 - k)), "inside": inside}, events
        t -= OPEN
        if t < FALL:
            k = t / FALL
            inside = self._inside((self.over[0], lerp(k * k, self.over[1] - 0.3, land), self.over[2]), 0.7 + 0.3 * k)
            return {"egg": hidden, "inside": inside}, events
        t -= FALL
        if not self.landed:
            self.landed = True
            events.append({"type": "shake", "node": "inside", "amount": 0.12, "seconds": 0.15})
            if self.liquid:
                events.append({"type": "ripple", "x": self.over[0], "z": self.over[2], "strength": 0.35})
                events.append({"type": "splash", "count": 3, "pos": (self.over[0], land, self.over[2]), "rise": (0.0, 6.0, 0.0), "spread": 0.5,
                               "color": SPLASH_EGG})
                events.append(shotOf("plopEgg"))
        if not self.sinks:
            self.done = True
            return {"egg": hidden, "inside": self._inside((self.over[0], land, self.over[2]), 1.0, False)}, events
        if t < SINK:
            k = smooth(t / SINK)
            return {"egg": hidden, "inside": self._inside((self.over[0], land - 1.2 * k, self.over[2]), 1.0 - k)}, events
        self.done = True
        return {"egg": hidden, "inside": self._inside(self.over, 0.0, False)}, events


def goesIn(kind, index, start, landY, rimTop, rand, bucket=False, color=0xFFFFFFFF, key=None):
    """PB 的 goesIn：手把一件不浮着的东西带到汤上方，按种类用哪个动作。

    kind："cracked" 蛋（在右沿磕开）/ "poured" 液体（bucket 为 True 是桶，否则瓶）/ 其余（糖、骨粉……）抖。index 是槽位（同时倒进去的几样沿 z 错开）；
    start：手从哪来；landY：液面高度；rimTop：锅沿的高度（蛋磕在那里）；color：液体 / 粉末的颜色（ARGB）。返回对应的动作（Crack / Pour / Shake）。
    """
    onto = (POUR_X, 0.0, POUR_Z + POUR_SPREAD * (index % 3 - 1))
    if kind == "cracked":
        return Crack(start, (8.0 - RIM_OUT, rimTop, onto[2]), (8.0 - 2.0, 0.0, onto[2]), landY, EGG_SIZE, EGG_INSIDE, True, 0.0)
    if kind == "poured":
        return Pour(bucket, start, onto, landY, HAND_SIZE, -1.0, 0.0, color, key or ("pour_%d" % index))
    return Shake(start, onto, landY, color, rand, HAND_SIZE * 0.8, -1.0, 0.0)


def wentIn(kind, bubbleColor):
    """PB 的 wentIn：带来的东西沉进汤里之后的事——溶掉的粉末冒最后几个气泡、噗一声；倒进去的液体、打进去的蛋什么都不再有。"""
    if kind in ("cracked", "poured"):
        return []
    return [{"type": "bubbles", "count": 6, "rise": (0.0, 3.5, 0.0), "color": bubbleColor}, shotOf("plopDissolved")]
