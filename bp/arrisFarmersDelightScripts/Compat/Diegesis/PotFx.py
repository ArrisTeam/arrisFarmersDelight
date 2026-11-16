# -*- coding: utf-8 -*-
"""PotFx - 厨锅场景用的粒子和声音：前置包的 Diegesis 粒子（气泡、破泡、蒸汽、水花、闪光、水滴）、HoD 的锅声（客户端）

粒子定义在 diegesisRp/particles（照 DiegesisParticles.builtIn 的各项参数），这里只管"在哪、什么颜色、几颗、多大、活多久"：
Create 之后逐项 SetVariable（tint_* / alpha / scale / count / life / vx,vy,vz，像素每秒）。
声音是 rp/sounds/handson/pot 里 HoD 的 14 个文件（sound_definitions 的 handson.pot.*）。引擎不能改正在播的音量和音调，
循环声按档位换：换档时先起新的、再停旧的（StopCustomMusicById 在起播 7 帧内调会失败、之后再也停不掉，
所以停之前至少隔 MIN_STOP 秒；等着停的记在模块里，由 step 统一处理）。
"""
from ...Client.Engine import compFactory, levelId

BUBBLE = "arris_diegesis:bubble"
BUBBLE_POP = "arris_diegesis:bubble_pop"
STEAM = "arris_diegesis:steam"
SPLASH = "arris_diegesis:splash"
GLINT = "arris_diegesis:glint"
DROPLET = "arris_diegesis:droplet"
DUST = "arris_diegesis:dust"
MIN_STOP = 0.5


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


def sound(name, world, volume=1.0, pitch=1.0):
    """一声。返回播放 id（出错时引擎给的是负数的串）。"""
    return compFactory.CreateCustomAudio(levelId).PlayCustomMusic(name, tuple(world), float(volume), float(pitch), False, None)


_dying = []              # [[播放 id, 还要等多久才能停]]：全局一份，场景没了也照样停得掉


def step(dt):
    """每帧一次：把到时候的旧循环声停掉。"""
    if not _dying:
        return
    audio = compFactory.CreateCustomAudio(levelId)
    for entry in list(_dying):
        entry[1] -= dt
        if entry[1] <= 0.0:
            audio.StopCustomMusicById(entry[0], 0.15)
            _dying.remove(entry)


class Loop(object):
    """一条循环声：play(volume, pitch) 给想要的音量和音调（音量 0 = 停），值变了才换。"""

    def __init__(self, name, world):
        self.name = name
        self.world = tuple(world)
        self.musicId = None
        self.volume = 0.0
        self.pitch = 1.0
        self.age = 0.0

    def step(self, dt):
        self.age += dt

    def play(self, volume, pitch=1.0):
        if abs(volume - self.volume) < 1.0e-3 and abs(pitch - self.pitch) < 1.0e-3:
            return
        if self.musicId is not None:
            _dying.append([self.musicId, max(0.0, MIN_STOP - self.age)])
            self.musicId = None
        self.volume, self.pitch = volume, pitch
        if volume > 0.0:
            audio = compFactory.CreateCustomAudio(levelId)
            self.musicId = audio.PlayCustomMusic(self.name, self.world, float(volume), float(pitch), True, None)
            self.age = 0.0

    def stop(self):
        self.play(0.0)
