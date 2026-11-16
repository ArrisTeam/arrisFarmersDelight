# -*- coding: utf-8 -*-
"""GrillFx - 炉灶站点的粒子和声音：把 HandsOn/StoveFx 的日程放出去（客户端）

StoveFx 只说"哪一件上、偏哪、什么速度、几颗、什么色"和"哪一声、多大、多高"，这里换成前置包的粒子（arris_diegesis:steam 蒸汽、
glint 闪光，diegesisRp/particles）和本包 / 原版的声音。JE 的粒子样式（StoveBehavior 用的 STEAM / PAN_SMOKE / HEAT / GLINT）
在基岩版里的对应：
- steam：蒸汽，白色按 ARGB 的透明度，大小 1；
- smoke（PAN_SMOKE）：同一张蒸汽的帧，灰白（0xC8C6C2）、透明度 0x58、大小放大到 JE 的 2.2 / 0.8 倍、活 2 秒；
- glint：闪光；
- heat（热浪，HEAT）：煎锅用的同一个粒子 arris:pan_heat（rp/particles/arris_pan_heat.json，HoD 的 heat 四帧，淡白 0x48、3.5 倍、活 0.8~1.3 秒，
  照 PanFx.STYLES 的 heat），点着的烤架每秒 1.6 个，空烤架也有（JE 的 heat() 不看有没有东西）。
声音是农夫乐事自己的煎锅声（rp/sounds/skillet，定义自带 20 倍 / 2 倍的音量，这里除回去）和原版的方块声，JE 用的灯笼的三种声音
（LANTERN_STEP / PLACE / HIT）在基岩版里是 block.lantern.*。粒子是一次性的：每颗按 spread 把速度各抖一点再放。
"""
import random

from ...Client.Engine import compFactory, levelId
from ...Shared.Rules.HandsOn import StoveFx

STEAM = "arris_diegesis:steam"
GLINT = "arris_diegesis:glint"
HEAT = "arris:pan_heat"
HEAT_ARGB, HEAT_SCALE, HEAT_LIFE = 0x48FFFFFF, 3.5, (0.8, 1.3)        # 同 PanFx.STYLES["heat"]
SMOKE_SCALE = 2.2 / 0.8          # JE 的烟（1.8 ~ 2.6 px）比蒸汽（0.6 ~ 1.0 px）大这么多倍
SMOKE_LIFE = 2.0
SMOKE_COLOR = 0xC8C6C2
SMOKE_ALPHA = 0x58 / 255.0
SOUNDS = {                       # StoveFx 里的名字 -> (基岩版的声音名, 音量要乘多少)
    "sizzle": ("ambient.skillet.sizzle", 0.05), "add_food": ("ambient.skillet.addfood", 0.5),
    "lantern_step": ("block.lantern.step", 1.0), "lantern_place": ("block.lantern.place", 1.0),
    "lantern_hit": ("block.lantern.hit", 1.0), "item_pickup": ("random.pop", 1.0),
}


def particle(identifier, world, color=None, alpha=None, scale=None, count=None, life=None, velocity=None):
    """在世界坐标 world 放一次粒子。color 是 0xRRGGBB；velocity 是 (vx, vy, vz) 像素每秒。"""
    system = compFactory.CreateParticleSystem(None)
    particleId = system.Create(identifier, (float(world[0]), float(world[1]), float(world[2])))
    if particleId is None:
        return None
    if color is not None:
        for name, shift in (("variable.tint_r", 16), ("variable.tint_g", 8), ("variable.tint_b", 0)):
            system.SetVariable(particleId, name, ((int(color) >> shift) & 0xFF) / 255.0)
        system.SetVariable(particleId, "variable.tint_set", 1.0)
    for name, value in (("variable.alpha", alpha), ("variable.scale", scale), ("variable.count", count), ("variable.life", life)):
        if value is not None:
            system.SetVariable(particleId, name, float(value))
    if velocity is not None:
        for name, value in zip(("variable.vx", "variable.vy", "variable.vz"), velocity):
            system.SetVariable(particleId, name, float(value))
        system.SetVariable(particleId, "variable.speed_set", 1.0)
    return particleId


def sound(name, world, volume, pitch):
    """按 StoveFx 的声音名放一声。"""
    found = SOUNDS.get(name)
    if found is not None:
        compFactory.CreateCustomAudio(levelId).PlayCustomMusic(found[0], tuple(world), min(1.0, volume * found[1]), float(pitch), False, None)


def _style(spawn):
    """(粒子名, 颜色 0xRRGGBB 或 None, 透明度 或 None, 大小, 寿命 或 None)；没有对应粒子的返回 None。"""
    alpha = ((spawn.color >> 24) & 0xFF) / 255.0 if spawn.color else None
    color = spawn.color & 0xFFFFFF if spawn.color else None
    if spawn.kind == "steam":
        return STEAM, color, alpha, 1.0, None
    if spawn.kind == "glint":
        return GLINT, color, None, 1.0, None
    if spawn.kind == "smoke":
        return STEAM, SMOKE_COLOR, SMOKE_ALPHA, SMOKE_SCALE, SMOKE_LIFE
    if spawn.kind == "heat":
        return HEAT, HEAT_ARGB & 0xFFFFFF, ((HEAT_ARGB >> 24) & 0xFF) / 255.0, HEAT_SCALE, random.uniform(*HEAT_LIFE)
    return None


def play(effects, where):
    """放一串 StoveFx 的粒子和声音。where(place, offset) 把"哪一件 + 偏移"换成世界坐标（place 为 None 是烤架中心）。"""
    for effect in effects:
        if isinstance(effect, StoveFx.Sound):
            sound(effect.name, where(None, (0.0, 0.0, 0.0)), effect.volume, effect.pitch)
            continue
        style = _style(effect)
        if style is None:
            continue
        identifier, color, alpha, scale, life = style
        base = where(effect.place, effect.offset)
        for _ in range(max(1, int(effect.count))):
            jitter = [random.uniform(-effect.spread, effect.spread) for _ in range(3)] if effect.spread else [0.0, 0.0, 0.0]
            velocity = tuple(effect.velocity[axis] + jitter[axis] for axis in range(3))
            particle(identifier, base, color=color, alpha=alpha, scale=scale, count=1, life=life, velocity=velocity)
