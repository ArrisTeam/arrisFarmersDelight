# -*- coding: utf-8 -*-
"""PotSceneFx - 厨锅场景里一阵一阵的东西：气泡蒸汽、落水的水花、锅的声音、一批煮好时料胀大缩没的收尾（客户端）

PotScene 每帧调 step；数都照 HoD 的纯计算（PotLiquid 的粒子速率、PotDrift 的落水事件、PotSounds 的声音日程、PotFinish 的收尾），
这里只把它们变成前置包的粒子、HoD 的锅声和道具的缩放。HoD 的声音名到本包声音定义的对应在 SOUNDS：
农夫乐事原有的沸腾、煎滋、下料三条声音定义自带 20 倍 / 2 倍的音量，这里除回去。
"""
import random

from . import PotFx
from ...Shared.Rules import PotLookState
from ...Shared.Rules.HandsOn import PotDrift, PotFinish, PotLiquid, PotSounds

INNER_LO, INNER_SPAN = 4.0, 8.0             # 内胆 x、z 从 4 到 12
FLOOR = PotLiquid.BROTH_FLOOR
BUBBLE_RISE = 3.6                           # 气泡上浮的速度（像素每秒）：初速 3.5、浮力 6、阻力 0.8 的平衡速度
STEAM_ALPHA = 0x6C / 255.0                  # PotBehavior 的蒸汽比库里的更白
EDGE_SCALE = 0.5
POP_RIPPLE = 0.09                           # 气泡破了在液面起的水波（SceneParticles.POP_RIPPLE）
SOUNDS = {                                  # HoD 的声音 -> (本包 / 原版的声音名, 音量要乘多少)
    "body": ("handson.pot.body", 1.0), "stir": ("handson.pot.stir", 1.0), "plop": ("handson.pot.plop", 1.0),
    "burst": ("handson.pot.burst", 1.0), "blub": ("handson.pot.blub", 1.0), "scoop": ("handson.pot.scoop", 1.0),
    "boil": ("ambient.cooking_pot.boil_soup", 0.05), "sizzle": ("ambient.skillet.sizzle", 0.05),
    "add_food": ("ambient.skillet.addfood", 0.5), "chime": ("note.chime", 1.0), "bucket_empty": ("bucket.empty_water", 1.0),
    "bottle_empty": ("bottle.empty", 1.0), "brush_sand": ("brush.suspicious_sand", 1.0),
    "egg_crack": ("block.turtle_egg.crack", 1.0),
}


def play(name, world, volume, pitch):
    """按 HoD 的声音名播一声。"""
    found = SOUNDS.get(name)
    if found is not None:
        PotFx.sound(found[0], world, min(1.0, volume * found[1]), pitch)


def _inner(lo, hi):
    return INNER_LO + INNER_SPAN * (lo + (hi - lo) * random.random())


class SceneFx(object):
    def __init__(self, scene):
        self.scene = scene
        self.sounds = PotSounds.PotSounds(random.random)
        self.loops = {}                       # HoD 的声音名 -> PotFx.Loop
        self.pops = []                        # [还有多久浮到液面, x, z]
        self.finish = None
        self.melting = {}                     # 格号 -> 掉落物 id：一批煮好时原来浮着的料，留着演胀大缩没

    @property
    def busy(self):
        return bool(self.pops) or self.finish is not None

    @property
    def finishing(self):
        """一批刚煮好，料还在胀大缩没：碎料等它们走完才浮上来（PotFinish 的 waiting）。"""
        return self.finish is not None and self.finish.waiting

    # ---------------------------------------------------------------- 每帧

    def step(self, dt, near):
        self._landings(near)
        self._finish(dt, near)
        if near:
            self._particles(dt)
            self._sounds(dt)
        else:
            self.silence()

    def _landings(self, near):
        """料落水：染成汤色的水花、噗的一声（烧着的锅再加一声下料的嗞），锅心一圈水波。"""
        scene, drift = self.scene, self.scene.drift
        for kind, slot in drift.events:
            if kind == PotDrift.EVENT_POUR:
                scene.hands.start(slot)       # 不浮着的料：一只手端来倒 / 磕 / 抖（PotHands）
            if kind != PotDrift.EVENT_LANDED:
                continue
            ripple, splashes, volume, pitch, sizzle, sizzlePitch = PotDrift.landingEffects(slot, scene.look.heated)
            scene.model.ripple(8.0, 8.0, ripple)
            if near:
                where = scene.world(drift.x[slot], scene.liquid.surfaceY(), drift.z[slot])
                PotFx.particle(PotFx.SPLASH, where, color=scene.liquid.brothColor, count=splashes)
                play("plop", where, volume, pitch)
                if sizzle > 0.0:
                    play("add_food", where, sizzle, sizzlePitch)
        del drift.events[:]

    def _particles(self, dt):
        scene, liquid = self.scene, self.scene.liquid
        surface = liquid.surfaceY()
        for _ in range(liquid.emitBubbles):
            self._bubble(_inner(0.15, 0.85), _inner(0.15, 0.85), FLOOR + 0.2 + (surface - FLOOR - 0.2) * random.random())
        for pop in list(self.pops):
            pop[0] -= dt
            if pop[0] <= 0.0:
                self.pops.remove(pop)
                PotFx.particle(PotFx.BUBBLE_POP, scene.world(pop[1], surface + 0.3, pop[2]), color=liquid.bubbleColor)
                scene.model.ripple(pop[1], pop[2], POP_RIPPLE)
        for _ in range(liquid.emitSteam):
            PotFx.particle(PotFx.STEAM, scene.world(_inner(0.1, 0.9), surface + 0.2, _inner(0.1, 0.9)), alpha=STEAM_ALPHA)
        for _ in range(liquid.emitEdge):
            inset, along, side = 0.3 + 0.8 * random.random(), INNER_SPAN * random.random(), int(random.random() * 4.0)
            x = (INNER_LO + along) if side < 2 else (INNER_LO + inset if side == 2 else INNER_LO + INNER_SPAN - inset)
            z = (INNER_LO + inset if side == 0 else INNER_LO + INNER_SPAN - inset) if side < 2 else (INNER_LO + along)
            PotFx.particle(PotFx.BUBBLE_POP, scene.world(x, surface + 0.15, z), color=liquid.bubbleColor, scale=EDGE_SCALE)

    def bubbles(self, count):
        """锅底随处冒 count 个泡。"""
        for _ in range(count):
            self._bubble(_inner(0.15, 0.85), _inner(0.15, 0.85), FLOOR + 0.2)

    def _bubble(self, x, z, y):
        """水里冒一个泡：浮到液面的时候破掉、起一圈水波。"""
        liquid = self.scene.liquid
        life = max(0.05, (liquid.surfaceY() - y) / BUBBLE_RISE)
        PotFx.particle(PotFx.BUBBLE, self.scene.world(x, y, z), color=liquid.bubbleColor, life=life)
        self.pops.append([life, x, z])

    def _sounds(self, dt):
        scene, look = self.scene, self.scene.look
        state = {"heated": look.heated, "cooking": look.cooking, "swirl": scene.spoon.swirl,
                 "soup": PotLookState.hasFood(look)}       # 模型自带的沸腾声也按这条让位（PotModel.food）
        where = scene.world(8.0, scene.liquid.surfaceY(), 8.0)
        for kind, name, volume, pitch in self.sounds.step(dt, state):
            if kind == "play":
                play(name, where, volume, pitch)
            elif kind in ("restart", "stop") and name in SOUNDS:
                loop = self.loops.get(name)
                if loop is None:
                    loop = self.loops[name] = PotFx.Loop(SOUNDS[name][0], where)
                loop.play(volume * SOUNDS[name][1] if kind == "restart" else 0.0, pitch)
        for loop in self.loops.values():
            loop.step(dt)

    def silence(self):
        """走远了、歇着了、锅没了：循环声停掉（声音日程重来，回来时再起）。"""
        if self.loops:
            for loop in self.loops.values():
                loop.stop()
            self.loops = {}
            self.sounds = PotSounds.PotSounds(random.random)

    # ---------------------------------------------------------------- 一批煮好

    def batchDone(self, slots):
        """一批煮好了：slots 是原来浮着、现在被煮掉的格子。它们的道具留下来演胀大缩没（PotFinish），演完才删。"""
        scene, drift = self.scene, self.scene.drift
        positions = {}
        for slot in slots:
            prop = scene.props[slot]
            if prop is None:
                continue
            scene.props[slot] = None
            self.melting[slot] = prop[0]
            positions[slot] = (drift.x[slot] - 8.0, drift.y[slot] - 8.0, drift.z[slot] - 8.0)
        if positions:
            self.finish = PotFinish.start(sorted(positions), positions, scene.clock, scene.liquid.bubbleColor)

    def _finish(self, dt, near):
        if self.finish is None:
            return
        scene = self.scene
        poses, events = self.finish.step(dt)
        for pose in poses:
            entityId = self.melting.get(pose["slot"])
            if entityId is None:
                continue
            if pose["visible"]:
                x, y, z = pose["pos"]
                scene.placeProp(entityId, 8.0 + x, 8.0 + y, 8.0 + z, 0.0, 0.0, 0.0, pose["scale"])
            else:
                scene.removeProp(self.melting.pop(pose["slot"]))
        for event in events:
            kind = event["type"]
            if kind == "ripple":
                scene.model.ripple(event["x"], event["z"], event["strength"])
            elif not near:
                continue
            elif kind == "bubbles":
                self.bubbles(event["count"])
            elif kind == "steam":
                PotFx.particle(PotFx.STEAM, scene.world(*event["pos"]), alpha=STEAM_ALPHA, count=event["count"],
                               velocity=event["rise"])
            elif kind == "glint":
                PotFx.particle(PotFx.GLINT, scene.world(*event["pos"]), color=event["color"] & 0xFFFFFF, count=event["count"],
                               velocity=event["rise"])
            elif kind == "sound":
                play(event["name"], scene.world(8.0, scene.liquid.surfaceY(), 8.0), event["volume"], event["pitch"])
        if self.finish.done:
            self.finish = None

    def clear(self):
        for entityId in self.melting.values():
            self.scene.removeProp(entityId)
        self.melting = {}
        self.finish = None
        del self.pops[:]
        self.silence()
