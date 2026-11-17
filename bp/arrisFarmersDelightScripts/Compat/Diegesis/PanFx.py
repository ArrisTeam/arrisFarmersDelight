# -*- coding: utf-8 -*-
"""PanFx - 煎锅场景用的粒子和声音：把 PanShow 攒下的事件放出来（客户端）

粒子的"在哪、多快、多大、什么色"照 HoD 的 SkilletBehavior / HandsOnDelightClient.registerParticles：
    oil_pop   油泡（Diegesis 的 bubble + bubble_pop 帧，染 E6F7C27A，0.25-0.5 秒）   -> arris_diegesis:bubble_pop
    fat       油星（原版 drip_fall，染 FFE7A8，小，重力 75）                        -> arris_diegesis:droplet
    pan_smoke 贴锅面熟了冒的烟（steam 帧，染 58C8C6C2，1.8-2.6 像素，活 1.6-2.4 秒）-> arris:pan_smoke（rp/particles/arris_pan_smoke.json）
    steam / glint / dust                                                           -> 前置包同名的
    heat      热锅上的热浪（HoD 的 heat 四帧，染 48FFFFFF）                         -> arris:pan_heat（rp/particles/arris_pan_heat.json）
位置的抖动、速度的抖动照 Diegesis 的 SceneParticles.spawn（位置每轴 gauss * spread，速度每轴 gauss * max(0.3, |v| * 0.25)，gauss 是 nextGaussian() * 0.5），
算式在 Shared/Rules/SceneScatter（炉灶、厨锅场景也用它）。
声音名 -> 基岩版的声音：煎锅自己的两条沿用 FD 的声音定义（自带 20 倍 / 2 倍的音量，这里除回去，和厨锅同一个做法），其余是原版的
（挂灯 block.lantern.*、捡东西 random.pop、岩浆噗 liquid.lavapop、营火噼啪 block.campfire.crackle、蛋壳 block.turtle_egg.crack）。
"""
import random

from . import PotFx
from ...Shared.Rules import PanModelMath, SceneScatter, SoundMix
from ...Shared.Rules.HandsOn.PotServeMath import rotateY

SOUNDS = {      # HoD 的声音 -> 基岩版的声音名；定义里采样自带的音量 / 音调经 Shared/Rules/SoundMix 除回去（挂灯放置声原来没除，比 JE 高 1.1 倍）
    "sizzle": "ambient.skillet.sizzle", "add_food": "ambient.skillet.addfood",
    "lantern_step": "block.lantern.step", "lantern_place": "block.lantern.place", "lantern_hit": "block.lantern.hit",
    "item_pickup": "random.pop", "lava_pop": "liquid.lavapop", "campfire_crackle": "block.campfire.crackle",
    "egg_crack": "block.turtle_egg.crack",
}
HEAT = "arris:pan_heat"
# JE 的 PAN_SMOKE（HandsOnDelightClient.java:93-94）：蒸汽的帧、染 0x58C8C6C2、大小 1.8~2.6 像素、活 1.6~2.4 秒、重力 -4、阻力 0.75、长大到 3 倍、摆动 1、渐显 0.3、
# 不 emissive（跟着环境光）。这些数都写在 FD 自己的粒子里（rp/particles/arris_pan_smoke.json），不再借前置包满亮度的蒸汽（0.6~1.0 像素、别的重力阻力、emissive）
# 乘倍数。煎锅（"pan_smoke"）和炉灶（GrillFx 的 "smoke"）在 JE 里是同一个样式，这里也只此一处
PAN_SMOKE = ("arris:pan_smoke", 0x58C8C6C2, 1.0, None)
STYLES = {      # 样式 -> (粒子, 缺省色 ARGB, 大小倍数, 活多久（秒）的范围，None 用粒子自己的)
    "oil_pop": (PotFx.BUBBLE_POP, 0xE6F7C27A, 1.0, (0.25, 0.5)),
    "fat": (PotFx.DROPLET, 0xFFFFE7A8, 0.33, (0.3, 0.6)),
    "pan_smoke": PAN_SMOKE,
    "steam": (PotFx.STEAM, 0x50FFFFFF, 1.0, None),
    "glint": (PotFx.GLINT, 0xFFFFFFFF, 1.0, None),
    "dust": ("arris_diegesis:dust", 0x99C0B090, 1.0, None),
    "heat": (HEAT, 0x48FFFFFF, 3.5, (0.8, 1.3)),
}


class PanFx(object):
    def __init__(self, pos, facing):
        self.pos = (int(pos[0]), int(pos[1]), int(pos[2]))
        self.facing = facing

    def world(self, point):
        return PanModelMath.worldPoint(self.facing, self.pos, point)

    def play(self, events, near=True):
        """放这一阵攒下的事件；离得远（near 为假）就一概不放。"""
        if not near:
            return
        for event in events:
            if event["type"] == "sound":
                self.sound(event["name"], event["volume"], event["pitch"])
            elif event["type"] == "particle":
                self.particle(event)

    def sound(self, name, volume, pitch):
        found = SOUNDS.get(name)
        if found is not None:
            PotFx.sound(found, self.world((8.0, 2.0, 8.0)), *SoundMix.engineArgs(found, volume, pitch))

    def particle(self, event):
        found = STYLES.get(event["style"])
        if found is None:
            return
        identifier, defaultColor, scale, life = found
        argb = event["color"] or defaultColor
        rgb, alpha = argb & 0xFFFFFF, ((argb >> 24) & 0xFF) / 255.0
        velocity = event["vel"]
        for _ in range(int(event["count"])):
            at = SceneScatter.spawnPoint(event["pos"], event["spread"])
            speed = SceneScatter.spawnVelocity(velocity)
            vx, vz = rotateY((speed[0], 0.0, speed[2]), PanModelMath.worldYaw(self.facing))[::2]
            PotFx.particle(identifier, self.world(at), color=rgb, alpha=alpha, scale=scale, count=1,
                           life=random.uniform(*life) if life else None, velocity=(vx, speed[1], vz))
