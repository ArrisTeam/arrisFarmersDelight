# -*- coding: utf-8 -*-
"""PotServe - 用容器从煮好的汤里盛一份：悬在汤面上的半透明容器，点一下浸下去、提上来、端走（双端）

移植自 Hands-On Delight 的 client/PotBehavior.java：offerBowl（575-618 行）、offerTakeBack（620-666 行）、dipOffered（541-551 行）、
onItemClick / onEffect 里盛一份的涟漪水花声音（527-537、684-700 行）、常量 209-217 / 309-319 行，和 client/KitchenMotions.java 的 Dip（573-685 行）。
时间一律是秒；位置是场景像素（锅中心在 (8, 8)，y 向上）。
倒进去的液体、打进去的蛋、溶掉的粉末这类"手把东西倒进汤里"的动作在 PotServeHands / PotServePour。

空手悬在煮好的汤上、背包里有能盛汤的容器时，容器半透明地悬在光标下面（offerOf）：点一下就盛，Shift 盛到没有。盛的时候容器按 Dip 的时间线
动：DOWN 秒内平方加速浸到面下 0.4 像素并歪 25 度，浸到的那一刻换成盛满的样子（"filled"）、敲一圈 0.45 的涟漪、溅起 4 簇水花；UP 秒内慢慢提到面上 3 像素，
再 HOLD 秒，每秒滴 14 滴；最后 AWAY 秒按 smoothstep 飞向调用方给的点（玩家屏幕底部）、一路缩没。

    offer = offerOf(cursor, surface, now, scoopedAt, spoon=..., carrying=..., hasContainer=...)    # 每帧；None = 不悬
    dip = Dip(offer["pos"], away, offer["scale"], offer["size"], brothColor)                       # 点下去的那一刻
    pose, events = dip.step(dt, surface)                                                           # 之后每帧，直到 dip.done
"""
import math

from .Mth import lerp
from .PotServeMath import ITEM_DRAWN, mix, out, pose, smooth
from .PotSounds import shotOf

OFFERED = 0x8CFFFFFF          # 悬着的容器半透明的白（ARGB 着色）
OFFER_LIFT = 1.5              # 悬在汤面上方这么高（像素）
OFFER_AWAY = 0.35             # 盛过之后这么久不再悬新的（秒）
POT_HALF = 5.0                # 光标离锅中心的 x、z 都要小于它才悬
POT_CENTER = 8.0
FILLED_SCALE = 0.45           # 方块容器（南瓜）悬着缩成这么小：等着被灌满，不浸下去
FILLED_LIFT = 5.0             # 方块容器悬得高一点（像素）
TAKE_BACK_SCALE = 0.6         # 取回沉下去的东西悬着的大小
SCOOP_BASE = 0.3              # 场景里 scoop 节点自带的缩放：缩放 1 的物品画 ITEM_DRAWN * SCOOP_BASE 像素高
DOWN = 0.14                   # Dip：浸下去
UP = 0.26                     # 提上来
HOLD = 0.08                   # 提到顶停一下
AWAY = 0.3                    # 端走
DRIPS = 14.0                  # 提着的时候每秒滴几滴
UNDER = 0.4                   # 浸到面下这么深（像素）
TOP = 3.0                     # 提到面上这么高
TILT = 25.0                   # 浸的时候歪这么多度
RIPPLE = 0.45
SPLASHES = 4
SPLASH_RISE = (0.0, 6.0, 0.0)
SPLASH_SPREAD = 0.6
DRIP_RISE = (0.0, -2.0, 0.0)
DRIP_SPREAD = 0.6
DRIP_FADE = 0.4               # 端走的前 40% 还在滴
SPLASH_UP = (0.0, 7.0, 0.0)   # 旁人看到的水花（贴着汤面随机处）的升速（PB 119）
BYSTANDER_RIPPLE = 0.5        # 旁人看到的涟漪（锅中心）
BYSTANDER_WINDOW = 1.0        # 厨师自己在这么久（秒）以内敲过涟漪就不再补
LADLED_DROPS = 8              # 舀进方块容器时溅向它的水滴数


def offerOf(cursor, surface, now, scoopedAt, focused=True, spoon=False, carrying=False, hasContainer=True, block=False, busy=False):
    """offerBowl：该不该悬一个容器、悬在哪。不悬返回 None，悬返回 {"pos", "scale", "size", "tint", "block"}。

    cursor：光标射线落在 surface + OFFER_LIFT 那个水平面上的点 (x, z)（场景像素），没落在面上是 None；surface：液面高度；
    now / scoopedAt：现在和上次盛的时间（秒），要隔 OFFER_AWAY 以上；focused：玩家在这口锅边；spoon：勺子在手里 / 光标在勺子上；
    carrying：光标上已经拿着东西；hasContainer：背包里有能盛汤的容器；block：那个容器是方块（南瓜）；busy：上一份还在端走。
    光标要在锅中心 +-POT_HALF 以内。pos 是容器此刻的位置，scale 是相对 scoop 节点自带缩放的倍数，size 是它画多高（像素）。
    """
    if busy or not focused or spoon or carrying or not hasContainer or cursor is None or now - scoopedAt < OFFER_AWAY:
        return None
    if not (abs(cursor[0] - POT_CENTER) < POT_HALF and abs(cursor[1] - POT_CENTER) < POT_HALF):
        return None
    scale = FILLED_SCALE if block else 1.0
    return {"pos": (cursor[0], surface + (FILLED_LIFT if block else OFFER_LIFT), cursor[1]), "scale": scale,
            "size": ITEM_DRAWN * SCOOP_BASE * scale, "tint": OFFERED, "block": bool(block)}


def takeBackOf(cursor, surface, now, scoopedAt, focused=True, spoon=False, carrying=False, offered=False, hasSunk=True, busy=False, hovered=False):
    """offerTakeBack：沉进汤里的东西（倒进去的奶、打进去的蛋、溶掉的糖）能不能点一下取回来。返回 (enabled, offer)。

    enabled：整个汤面该不该接点击（Java 里 sunk 节点开着）——要在锅边、手空着、没有悬着的碗、没有正在端走的、有东西沉着、且隔了 OFFER_AWAY；
    offer：enabled 且光标在汤面上（hovered）时悬着的取回的东西，{"pos", "scale": TAKE_BACK_SCALE, "size", "tint", "block"}，否则 None。
    """
    enabled = bool(focused and not spoon and not offered and hasSunk and not carrying and not busy and now - scoopedAt >= OFFER_AWAY)
    if not enabled or not hovered or cursor is None:
        return enabled, None
    return enabled, {"pos": (cursor[0], surface + OFFER_LIFT, cursor[1]), "scale": TAKE_BACK_SCALE,
                     "size": ITEM_DRAWN * SCOOP_BASE * TAKE_BACK_SCALE, "tint": OFFERED, "block": False}


def awayFallback(at, surface):
    """玩家屏幕底部那个点算不出来时的缺省：就在悬着的位置上方 8 像素（PB 548）。"""
    return (at[0], surface + 8.0, at[2])


def carriedBowlOn(point, surface, color):
    """手里拿着碗直接点在汤上（PB 527-537 的 onItemClick）：碗落进去的地方敲一圈 0.45 的涟漪、溅起 4 簇水花。point 是光标落在液面上的 (x, z)。
    声音由服务端的 "scooped" 效果放（scooped()）。返回事件列表。"""
    return [{"type": "ripple", "x": point[0], "z": point[1], "strength": RIPPLE},
            {"type": "splash", "count": SPLASHES, "pos": (point[0], surface, point[1]), "rise": SPLASH_RISE, "spread": SPLASH_SPREAD, "color": color}]


def scooped(surface, color, now=None, scoopedHere=None, dipping=False, block=False, into=None):
    """服务端说有人盛了一份（"scooped" 效果，PB 684-700）：这一份的涟漪、水花、声音。返回事件列表。

    厨师自己盛的时候碗落进汤的那一下已经由 Dip / carriedBowlOn 敲过涟漪了（正在 Dip、或 scoopedHere 在 BYSTANDER_WINDOW 秒以内），
    就不再敲；旁边的人看到的是碗落在汤的某处：锅中心一圈 BYSTANDER_RIPPLE 的涟漪 + 汤面上随机处 4 簇水花（"pos": None）。
    block：舀进方块容器（南瓜）——汤从汤面中心往 into（容器的位置，场景像素）溅出 8 滴；最后是舀的声音。color 是 ARGB 的汤色。
    """
    events = []
    if not dipping and (scoopedHere is None or now - scoopedHere > BYSTANDER_WINDOW):
        events.append({"type": "ripple", "x": POT_CENTER, "z": POT_CENTER, "strength": BYSTANDER_RIPPLE})
        events.append({"type": "splash", "count": SPLASHES, "pos": None, "rise": SPLASH_UP, "spread": 0.0, "color": color})
    if block and into is not None:
        centre = (POT_CENTER, surface, POT_CENTER)
        events.append({"type": "droplets", "count": LADLED_DROPS, "pos": centre, "rise": (into[0] - centre[0], into[1] - centre[1], into[2] - centre[2]),
                       "spread": 0.3, "color": color})
    events.append(shotOf("scoop"))
    return events


class Dip(object):
    """悬着的容器浸进汤里、盛满、提上来、端走。

    at：悬着的位置（offer["pos"]）；away：端到哪去（场景像素，玩家屏幕底部在汤面上方 6 像素那个面上的点，PB 548）；scale / size：offer 的缩放和高度
    （方块容器 FILLED_SCALE）；color：滴落和水花的颜色（ARGB，汤色）；sound：浸到的那一刻放的音效事件（取回沉下去的东西用 PotSounds.shotOf("scoopBack")，
    普通的盛一份由服务端的 "scooped" 效果放声音，传 None）。
    """

    def __init__(self, at, away, scale, size, color, sound=None):
        self.at = tuple(at)
        self.away = tuple(away)
        self.scale = scale
        self.half = size * 0.3            # 滴落点在容器下方这么远
        self.color = color
        self.sound = sound
        self.age = 0.0
        self.dipped = False
        self.filled = False               # 已经换成盛满的样子
        self.done = False
        self._drip = 0.0

    def step(self, dt, surface):
        """推进 dt 秒；surface 是此刻的液面高度（汤会被舀低）。返回 (pose, events)。

        pose：{"pos": (x, y, z), "rot": (tilt, 0, 0), "scale", "visible", "filled"}，tilt 是歪的度数；走完后 visible 为 False、归位（tilt 0、scale 还原）。
        events：ripple（x, z, strength）/ splash / filled（换成盛满的样子，着色还原成白）/ sound / drip。
        """
        events = []
        if self.done:
            return self._pose(self.at, 0.0, self.scale, False), events
        self.age += dt
        t = self.age
        ax, ay, az = self.at
        under = surface - UNDER
        if t < DOWN:
            k = t / DOWN
            return self._pose((ax, lerp(k * k, ay, under), az), TILT * k, self.scale), events
        t -= DOWN
        if not self.dipped:
            self.dipped = self.filled = True
            events.append({"type": "ripple", "x": ax, "z": az, "strength": RIPPLE})
            events.append({"type": "splash", "count": SPLASHES, "pos": (ax, surface, az), "rise": SPLASH_RISE, "spread": SPLASH_SPREAD,
                           "color": self.color})
            events.append({"type": "filled"})
            if self.sound:
                events.append(self.sound)
        top = surface + TOP
        if t < UP + HOLD:
            k = out(min(1.0, t / UP))
            y = lerp(k, under, top)
            self._dripping(dt, (ax, y - self.half, az), events)
            return self._pose((ax, y, az), TILT * (1.0 - k), self.scale), events
        t -= UP + HOLD
        if t < AWAY:
            k = smooth(t / AWAY)
            where = mix((ax, top, az), self.away, k)
            if k < DRIP_FADE:
                self._dripping(dt, (where[0], where[1] - self.half, where[2]), events)
            return self._pose(where, 0.0, self.scale * (1.0 - k)), events
        self.done = True
        return self._pose(self.at, 0.0, self.scale, False), events

    def _pose(self, pos, tilt, scale, visible=True):
        return pose(pos, (tilt, 0.0, 0.0), scale, visible, filled=self.filled)

    def _dripping(self, dt, where, events):
        """每秒 DRIPS 滴：攒够一滴就放。"""
        self._drip += dt * DRIPS
        if self._drip >= 1.0:
            whole = int(math.floor(self._drip))
            events.append({"type": "drip", "count": whole, "pos": where, "rise": DRIP_RISE, "spread": DRIP_SPREAD, "color": self.color})
            self._drip -= whole
