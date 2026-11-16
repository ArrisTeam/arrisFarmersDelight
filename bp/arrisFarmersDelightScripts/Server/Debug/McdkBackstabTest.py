# -*- coding: utf-8 -*-
"""McdkBackstabTest - 背刺魔咒的游戏内自检（服务端）：测试函数，仅供 MCDK-MCP 的 execute_code / 开发调试调用

不会自动运行，没有 RPC 端点。给第一个玩家主手换一把背刺 III 的铁刀，在玩家南边 3 格生成两头猪：一头背对玩家、一头面对玩家，
各以玩家的名义打 5 点伤害（CreateHurt.Hurt，会走 DamageEvent），看扣的血：背后那头应是 5 * 1.8 = 9，正面那头是 5。
做完杀掉两头猪、把主手物品换回去。
    from arrisFarmersDelightScripts.Server.Debug import McdkBackstabTest as T
    T.mcdk_test_backstab()
"""
import time

from ..Helpers.Engine import compFactory, levelId, serverApi, System, GetCarriedItem, SetCarriedItem, DestroyEntity
from ...Shared.Rules import Backstabbing as Rules

HIT = 5.0
LEVEL = 3


def _health(entityId):
    return compFactory.CreateAttr(entityId).GetAttrValue(serverApi.GetMinecraftEnum().AttrType.HEALTH)


def _pig(pos, yaw, dimensionId):
    entityId = System.CreateEngineEntityByTypeStr("minecraft:pig", pos, (0.0, yaw), dimensionId)
    if entityId:
        compFactory.CreateRot(entityId).SetRot((0.0, yaw))
    return entityId


def mcdk_test_backstab():
    """测试函数：背后一刀和正面一刀各扣多少血；返回结构化结果。"""
    started = time.time()
    players = serverApi.GetPlayerList()
    if not players:
        return {"case": "backstab", "ok": False, "error": "no player"}
    playerId = players[0]
    x, y, z = compFactory.CreatePos(playerId).GetFootPos()
    dimensionId = compFactory.CreateDimension(playerId).GetEntityDimensionId()
    before = GetCarriedItem(playerId, True)
    SetCarriedItem(playerId, {"newItemName": "arris:iron_knife", "newAuxValue": 0, "count": 1,
                              "modEnchantData": [(Rules.ENCHANT, LEVEL)]})
    held = GetCarriedItem(playerId, True) or {}
    away = _pig((x - 1.0, y, z + 3.0), 0.0, dimensionId)       # 朝南看，玩家在它北边 = 背后
    facing = _pig((x + 1.0, y, z + 3.0), 180.0, dimensionId)   # 朝北看，正对玩家
    result = {"case": "backstab", "level": Rules.levelOf(held), "enchants": held.get("modEnchantData")}
    lost = {}
    for name, entityId in (("behind", away), ("front", facing)):
        if not entityId:
            continue
        full = _health(entityId)
        hurt = compFactory.CreateHurt(entityId).Hurt(HIT, serverApi.GetMinecraftEnum().ActorDamageCause.EntityAttack,
                                                     playerId, None, False)
        lost[name] = round(full - _health(entityId), 3)
        result[name + "Hurt"] = hurt
        DestroyEntity(entityId)
    SetCarriedItem(playerId, before or {"newItemName": "minecraft:air", "count": 0})
    result.update(lost=lost, duration_ms=int((time.time() - started) * 1000))
    result["ok"] = bool(result["level"] == LEVEL and abs(lost.get("behind", 0) - Rules.damageOf(HIT, LEVEL)) < 0.01
                        and abs(lost.get("front", 0) - HIT) < 0.01)
    return result
