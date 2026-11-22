# -*- coding: utf-8 -*-
"""GrillFx - 炉灶场景的粒子和声音：把 HandsOn/StoveFx 的日程放出去（客户端）

StoveFx 只说"哪一件上、偏哪、什么速度、几颗、什么色"和"哪一声、多大、多高"，这里换成前置包的粒子（arris_diegesis:steam 蒸汽、
glint 闪光，diegesisRp/particles）和本包 / 原版的声音。JE 的粒子样式（StoveBehavior 用的 STEAM / PAN_SMOKE / HEAT / GLINT）
在基岩版里的对应（热浪、蒸汽、烟和各种声音谁都看得见听得见，不用开着站点：StoveScene.py 里每座加载着的炉灶一份）：
- steam：蒸汽，白色按 ARGB 的透明度，大小 1；
- smoke（PAN_SMOKE）：和煎锅是同一个样式，只在 PanFx.PAN_SMOKE 定义一处：本包自己的粒子 arris:pan_smoke（rp/particles/arris_pan_smoke.json，蒸汽的帧、灰白 0xC8C6C2、
  透明度 0x58、大小 1.8~2.6 像素、活 1.6~2.4 秒、跟着环境光，数都写在粒子里）；
- glint：闪光；
- heat（热浪，HEAT）：煎锅用的同一个粒子 arris:pan_heat（rp/particles/arris_pan_heat.json，HoD 的 heat 四帧，淡白 0x48、3.5 倍、活 0.8~1.3 秒，
  照 PanFx.STYLES 的 heat），点着的烤架每秒 1.6 个，空烤架也有（JE 的 heat() 不看有没有东西）。
声音是农夫乐事自己的煎锅声（rp/sounds/skillet）和原版的方块声，JE 用的灯笼的三种声音（LANTERN_STEP / PLACE / HIT）在基岩版里是 block.lantern.*、
拾取声（ITEM_PICKUP）是 random.pop；定义里采样自带的音量（煎锅声 20 倍 / 2 倍）、音调（挂灯放置声 1.1 倍）经 Shared/Rules/SoundMix 除回去。
放上去、取走、烤好、被拒的声音都在这里放（谁都听得见，不再靠服务端的世界广播）。粒子是一次性的：每颗的起点按 spread、初速按 max(0.3, |v| * 0.25) 各散一点再放
（Diegesis 的 SceneParticles.spawn，算式在 Shared/Rules/SceneScatter）。
"""
import random

from ...Client.Engine import compFactory, levelId
from ...Shared.Rules import SceneScatter, SoundMix
from ...Shared.Rules.HandsOn import StoveFx
from .PanFx import PAN_SMOKE

STEAM = "arris_diegesis:steam"
GLINT = "arris_diegesis:glint"
HEAT = "arris:pan_heat"
HEAT_ARGB, HEAT_SCALE, HEAT_LIFE = 0x48FFFFFF, 3.5, (0.8, 1.3)        # 同 PanFx.STYLES["heat"]
SOUNDS = {                       # StoveFx 里的名字 -> 基岩版的声音名
    "sizzle": "ambient.skillet.sizzle", "add_food": "ambient.skillet.addfood", "lantern_step": "block.lantern.step",
    "lantern_place": "block.lantern.place", "lantern_hit": "block.lantern.hit", "item_pickup": "random.pop",
}


def particle(identifier, world, color=None, alpha=None, scale=None, count=None, life=None, velocity=None):
    """在世界坐标 world 放一次粒子。color 是 0xRRGGBB；velocity 是 (vx, vy, vz) 像素每秒。"""
    system = compFactory.CreateParticleSystem(None)
    particleId = system.Create(identifier, (float(world[0]), float(world[1]), float(world[2])))
    if not particleId:                    # 没有这个粒子、进世界头几秒粒子系统还没好：引擎回 0（不是 None），不能当编号去设变量
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
        volume, pitch = SoundMix.engineArgs(found, volume, pitch)
        compFactory.CreateCustomAudio(levelId).PlayCustomMusic(found, tuple(world), volume, pitch, False, None)


def _lifeIn(span):
    """寿命：span 是 (最短, 最长) 就在里面随便取一个；None（粒子 JSON 自己定寿命，PAN_SMOKE 现在就是）还是 None。
    单拎出来是因为直接写 random.uniform(*PAN_SMOKE[3])，网易机审（pylint）按常量里的 None 推断，判成"迭代 None"。"""
    return random.uniform(span[0], span[1]) if span else None


def _style(spawn):
    """(粒子名, 颜色 0xRRGGBB 或 None, 透明度 或 None, 大小, 寿命 或 None)；没有对应粒子的返回 None。"""
    alpha = ((spawn.color >> 24) & 0xFF) / 255.0 if spawn.color else None
    color = spawn.color & 0xFFFFFF if spawn.color else None
    if spawn.kind == "steam":
        return STEAM, color, alpha, 1.0, None
    if spawn.kind == "glint":
        return GLINT, color, None, 1.0, None
    if spawn.kind == "smoke":
        identifier, argb, scale, life = PAN_SMOKE
        return identifier, argb & 0xFFFFFF, ((argb >> 24) & 0xFF) / 255.0, scale, _lifeIn(life)
    if spawn.kind == "heat":
        return HEAT, HEAT_ARGB & 0xFFFFFF, ((HEAT_ARGB >> 24) & 0xFF) / 255.0, HEAT_SCALE, random.uniform(*HEAT_LIFE)
    return None


def play(effects, where):
    """放一串 StoveFx 的粒子和声音。where(place, offset) 把"哪一件 + 偏移"换成世界坐标（place 为 None 是烤架中心）：位置跟着炉灶的朝向转
    （WorldSpace.world，炉灶坐标 -> 世界）。速度（像素每秒）只有竖直的和对 90 度转动对称的随机抖动，不用跟着转。"""
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
            scatter = SceneScatter.spawnPoint((0.0, 0.0, 0.0), effect.spread)          # 像素；各轴同样的散布，炉灶朝哪都一样，不用跟着转
            velocity = SceneScatter.spawnVelocity(effect.velocity)
            at = tuple(base[axis] + scatter[axis] / 16.0 for axis in range(3))
            particle(identifier, at, color=color, alpha=alpha, scale=scale, count=1, life=life, velocity=velocity)
