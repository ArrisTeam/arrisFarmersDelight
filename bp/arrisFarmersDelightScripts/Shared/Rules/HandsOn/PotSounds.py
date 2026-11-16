# -*- coding: utf-8 -*-
"""PotSounds - 厨锅的声音日程：持续声、周期声、排队的咕噜、一次性音效表（双端）

移植自 Hands-On Delight 的 client/PotSounds.java（声音名）、client/PotBehavior.java 的 sounds()（1245-1265 行）和常量（173-185 行）、
Diegesis 的 impl/client/fx/StationLoop.java（持续声朝目标音量 / 音高的滑动）、sounds.json（pot.body / stir / plop / burst / blub / scoop）。
时间一律是秒（Java 的刻 = 1/20 秒，注明处才换算）。声音名是逻辑名（"body" "stir" "plop" ……），SOUND_IDS 给出 Java 里对应的声音事件，
放进基岩版的哪个声音由调用方映射。

PotSounds.step(dt, state) 每帧调一次，返回决定列表，每项 (种类, 名字, 音量, 音高)：
    "play"     一次性：现在播一下（沸腾、煎滋、咕噜）
    "loop"     Java 的 loopSound：持续声此刻该有的音量 / 音高，已按 Java 每刻 12% 的滑动算好（能随时改音量的引擎直接用）
    "restart"  引擎改不了正在播的声音的音量：量化成 3 档（带滞回）的音量变档了，请用这个音量 / 音高重新开始这条循环（第一次起声也是）
    "stop"     量化的档位落到 0：停掉这条循环
不能改音量的引擎只看 play / restart / stop；"loop" 的值给能改音量的引擎，或者拿来对照。
一次性音效另有 ONE_SHOTS 表和 shotOf()，造出 {"type": "sound", ...} 事件，厨锅其他模块（PotFinish / PotBadge / PotServe）的事件用同一个形状。
"""
from .Mth import TICKS_PER_SECOND, clamp

BODY_RESTING = 0.3       # 锅烧着、里面有东西但没在煮：底噪音量
BODY_COOKING = 0.7       # 正在煮（烧着、被搅着、有菜谱、没出锅）
STIR_VOLUME = 0.7        # 搅动声音量 = swirl * STIR_VOLUME
BLUB_VOLUME = 0.32
SIZZLE_VOLUME = 0.22
ADD_FOOD_VOLUME = 0.16
BOIL_EVERY = 2.6         # 沸腾声的间隔（秒）
BOIL_EVERY_COOKING = 1.7  # 正在煮时的间隔
SIZZLE_EVERY = 3.0       # 煎滋声的间隔（只在煮的时候）
BLUB_GAP = 0.11          # 两声咕噜至少隔这么久
MOST_BLUBS = 9           # 排队的咕噜最多这么多
GLIDE = 0.12             # StationLoop：每刻朝目标走这么多（音量、音高）
SILENT = 0.004           # StationLoop：起声时的音量；目标为 0 且音量落到这以下才停
STEPS = 3                # 搅动声量化成几档（body 只有 Java 的两个目标值，档位见 BODY_LEVELS）
HYSTERESIS = 0.03        # 量化的滞回：越过两档的分界还要再多走这么多音量才换档

BODY_LEVELS = (BODY_RESTING, 0.5, BODY_COOKING)
STIR_LEVELS = (0.2, 0.45, STIR_VOLUME)

# 逻辑名 -> Java 的声音事件（命名空间前缀：handson_delight / farmersdelight / minecraft）
SOUND_IDS = {
    "body": "handson_delight:pot.body", "stir": "handson_delight:pot.stir", "plop": "handson_delight:pot.plop",
    "burst": "handson_delight:pot.burst", "blub": "handson_delight:pot.blub", "scoop": "handson_delight:pot.scoop",
    "boil": "farmersdelight:block.cooking_pot.boil_soup", "sizzle": "farmersdelight:block.skillet.sizzle",
    "add_food": "farmersdelight:block.skillet.add_food", "chime": "minecraft:block.note_block.chime",
    "bucket_empty": "minecraft:item.bucket.empty", "bottle_empty": "minecraft:item.bottle.empty",
    "brush_sand": "minecraft:item.brush.brushing.sand", "egg_crack": "minecraft:block.turtle_egg.crack",
}

# 一次性音效：用途 -> 声音、音量、音高（perIndex：每个序号加多少；pitches：按序号给的音高）、在哪个节点响（None = 工位中心，"item_%d" 填序号）
ONE_SHOTS = {
    "plop": {"sound": "plop", "volume": 0.5, "pitch": 0.92, "perIndex": 0.03, "at": "item_%d"},          # PB 794：料落进汤里
    "plopDissolved": {"sound": "plop", "volume": 0.25, "pitch": 1.35, "at": "broth"},                  # PB 845：溶掉的料沉下去
    "plopEgg": {"sound": "plop", "volume": 0.35, "pitch": 1.25, "at": "broth"},                        # PB 831：蛋黄落进汤里
    "addFood": {"sound": "add_food", "volume": ADD_FOOD_VOLUME, "pitch": 0.8, "at": "item_%d"},        # PB 796：热锅里下料的滋啦声
    "burst": {"sound": "burst", "volume": 0.55, "pitch": 0.95, "perIndex": 0.05, "at": "broth"},       # PB 1022：料炸开（序号 = 槽位）
    "scoop": {"sound": "scoop", "volume": 0.55, "pitch": 1.0, "at": "broth"},                          # PB 698：舀出一份
    "scoopBack": {"sound": "scoop", "volume": 0.45, "pitch": 1.1, "at": "broth"},                      # PB 504：把沉下去的东西取回来
    "chime": {"sound": "chime", "volume": 0.35, "pitches": (1.0, 1.26, 1.5), "at": "badge"},           # PB 942：评星亮起（序号 = 第几颗星）
    "bucket": {"sound": "bucket_empty", "volume": 0.45, "pitch": 1.0, "at": None},                     # KitchenMotions.Pour：倒桶
    "bottle": {"sound": "bottle_empty", "volume": 0.45, "pitch": 1.0, "at": None},                     # KitchenMotions.Pour：倒瓶
    "sand": {"sound": "brush_sand", "volume": 0.25, "pitch": 1.4, "at": None},                         # KitchenMotions.Shake：抖粉末
    "crack": {"sound": "egg_crack", "volume": 0.35, "pitch": 1.5, "at": None},                         # KitchenLooks.crack：敲蛋
}


def shot(name, volume, pitch, at=None):
    """一次性音效事件：{"type": "sound", "name", "volume", "pitch", "at"}；at 是节点名（None = 工位中心）。"""
    return {"type": "sound", "name": name, "volume": volume, "pitch": pitch, "at": at}


def shotOf(use, index=0):
    """ONE_SHOTS 里 use 这一行的音效事件；index 是槽位 / 第几颗星（影响音高，和节点名里的 %d）。"""
    row = ONE_SHOTS[use]
    pitches = row.get("pitches")
    pitch = pitches[index] if pitches else row["pitch"] + row.get("perIndex", 0.0) * index
    at = row["at"]
    return shot(row["sound"], row["volume"], pitch, (at % index) if at and "%d" in at else at)


def playOf(event):
    """一次性音效事件 -> ("play", 名字, 音量, 音高) 决定。"""
    return ("play", event["name"], event["volume"], event["pitch"])


def stirPitch(volume):
    """搅动声在这个音量下的音高：0.9 + 0.15 * swirl，swirl = 音量 / STIR_VOLUME（PB 1248）。"""
    return 0.9 + 0.15 * volume / STIR_VOLUME


def _fixedPitch(_volume):
    return 1.0


class Loop(object):
    """一条持续声：Java StationLoop 的滑动，加上给"改不了音量"的引擎用的 3 档量化（带滞回）。

    step(dt, volume, pitch) 的 volume / pitch 是此刻想要的（Java 的 loopSound 参数）；返回这一步的决定列表。
    levels 是各档的音量（升序，档位 0 = 关）；pitchAt(档位音量) 给这一档的音高。
    """

    def __init__(self, name, levels, pitchAt):
        self.name = name
        self.levels = tuple(levels)
        self.pitchAt = pitchAt
        self.volume = 0.0        # Java 此刻实际在放的音量（滑动后）
        self.pitch = 1.0
        self.running = False     # Java 的循环实例是否在
        self.notch = 0           # 量化的档位 0..len(levels)

    def _bound(self, below):
        """第 below 档和 below + 1 档之间的分界音量（档位 0 与 1 之间是第一档的一半）。"""
        low = self.levels[below - 1] if below > 0 else 0.0
        return (low + self.levels[below]) / 2.0

    def _quantise(self, wanted):
        """带滞回的档位：向上要越过分界 + HYSTERESIS，向下要落到分界 - HYSTERESIS 以下。"""
        now = self.notch
        while now < len(self.levels) and wanted >= self._bound(now) + HYSTERESIS:
            now += 1
        while now > 0 and wanted <= self._bound(now - 1) - HYSTERESIS:
            now -= 1
        return now

    def step(self, dt, volume, pitch):
        out = []
        if not self.running and volume > 0.0:
            self.running, self.volume, self.pitch = True, SILENT, pitch
        if self.running:
            k = 1.0 - (1.0 - GLIDE) ** (dt * TICKS_PER_SECOND)
            self.volume += (volume - self.volume) * k
            self.pitch += (pitch - self.pitch) * k
            if volume <= 0.0 and self.volume < SILENT:
                self.running, self.volume = False, 0.0
            else:
                out.append(("loop", self.name, self.volume, self.pitch))
        now = self._quantise(volume)
        if now != self.notch:
            self.notch = now
            level = self.levels[now - 1] if now else 0.0
            out.append(("restart" if now else "stop", self.name, level, self.pitchAt(level) if now else pitch))
        return out


class PotSounds(object):
    """一口锅的声音日程。rand 是 0..1 的随机数（沸腾声的音高抖动用）。"""

    def __init__(self, rand):
        self.rand = rand
        self.boilClock = 0.0
        self.sizzleClock = 0.0
        self.blubClock = 0.0
        self.blubs = 0                       # 排队等响的咕噜
        self.body = Loop("body", BODY_LEVELS, _fixedPitch)
        self.stir = Loop("stir", STIR_LEVELS, stirPitch)

    def blub(self, count=1):
        """又有 count 块新的碎料浮上来：咕噜排进队里，最多 MOST_BLUBS 个（PB 1038）。"""
        self.blubs = min(MOST_BLUBS, self.blubs + max(0, count))

    def step(self, dt, state):
        """推进 dt 秒，返回这一步的决定列表（见模块说明）。

        state 的键：heated 锅烧着；cooking 正在煮（烧着 && 被搅着 && 有菜谱 && 没出锅）；
        soup 锅里有东西（汤、菜、预览或任何一格料：PB 里的 soup || hasFood()）；swirl 汤转得多快 0..1。
        """
        heated, cooking = bool(state.get("heated")), bool(state.get("cooking"))
        soup, swirl = bool(state.get("soup")), clamp(float(state.get("swirl", 0.0)), 0.0, 1.0)
        out = self.body.step(dt, 0.0 if not heated or not soup else (BODY_COOKING if cooking else BODY_RESTING), 1.0)
        out += self.stir.step(dt, swirl * STIR_VOLUME, 0.9 + 0.15 * swirl)
        self.boilClock -= dt
        if heated and soup and self.boilClock <= 0.0:
            self.boilClock = BOIL_EVERY_COOKING if cooking else BOIL_EVERY
            out.append(("play", "boil", 1.0, 0.95 + 0.1 * self.rand()))
        self.sizzleClock -= dt
        if cooking and self.sizzleClock <= 0.0:
            self.sizzleClock = SIZZLE_EVERY
            out.append(("play", "sizzle", SIZZLE_VOLUME, 0.9))
        self.blubClock -= dt
        if self.blubs > 0 and self.blubClock <= 0.0:
            self.blubs -= 1
            self.blubClock = BLUB_GAP
            out.append(("play", "blub", BLUB_VOLUME, 0.9 + 0.04 * self.blubs))
        return out
