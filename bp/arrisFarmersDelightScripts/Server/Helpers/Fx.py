# -*- coding: utf-8 -*-
"""Fx - 声音、粒子、方块实体 molang 的广播（服务端 → 全体客户端）

都是单次 Call("*") 广播，由客户端按维度过滤（见 Client/Endpoints.py）：
比在服务端给每个玩家建一次维度组件查询要便宜。
"""
from .Engine import Call


def ToAllPlayerPlaySound(dimensionId, pos, soundName):
    Call("*", "OnPlaySound", {"soundName": soundName, "pos": pos, "dimensionId": dimensionId})


def ToAllPlayerGrowthParticle(pos):
    """骨粉 / 作物生长的绿色粒子。"""
    Call("*", "PlayParticle", pos)


def ToAllPlayerBlockMolang(blockPos, name, value):
    """设置所有客户端上该方块实体的 molang 变量（name 形如 "variable.mod_heat"）。"""
    Call("*", "SetEntityBlockMolang", {"molang": value, "blockPos": blockPos, "name": name})
