# -*- coding: utf-8 -*-
"""Fx - 声音、粒子、方块实体 molang 的广播（服务端 → 全体客户端）

都是单次 Call("*") 广播，由客户端按维度过滤（见 Client/Endpoints.py）：
比在服务端给每个玩家建一次维度组件查询要便宜。
"""
from .Engine import Call
from ...Shared.Rules import SoundMix


def ToAllPlayerPlaySound(dimensionId, pos, soundName, volume=None, pitch=None):
    """在 pos 放一声。不给 volume / pitch 就按声音定义原样；给了的是 JE 里这一声的数，定义里自带音量 / 音调的声音（Shared/Rules/SoundMix）
    在这里除掉那一份，各客户端听到的就是 JE 的数。"""
    payload = {"soundName": soundName, "pos": pos, "dimensionId": dimensionId}
    if volume is not None or pitch is not None:
        payload["volume"], payload["pitch"] = SoundMix.engineArgs(soundName, 1.0 if volume is None else volume, 1.0 if pitch is None else pitch)
    Call("*", "OnPlaySound", payload)


def ToAllPlayerCrumbs(dimensionId, blockPos, itemName):
    """砧板切了一件 itemName：方块中心上方飞出几颗它颜色的碎屑（FD 的 spawnCuttingParticles，放什么样在 Client/Endpoints.py）。"""
    Call("*", "PlayCrumbs", {"dimensionId": dimensionId, "blockPos": blockPos, "itemName": itemName})


def ToAllPlayerGrowthParticle(pos):
    """骨粉 / 作物生长的绿色粒子。"""
    Call("*", "PlayParticle", pos)


def ToAllPlayerBlockMolang(blockPos, name, value):
    """设置所有客户端上该方块实体的 molang 变量（name 形如 "variable.mod_heat"）。"""
    Call("*", "SetEntityBlockMolang", {"molang": value, "blockPos": blockPos, "name": name})
