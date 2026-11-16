# -*- coding: utf-8 -*-
"""Backstabbing - 背刺魔咒：玩家从背后打中目标时伤害加成（服务端）

照 JE 的 BackstabbingEnchantment.BackstabbingEvent（LivingHurtEvent）：伤害来源是玩家、主手物品带背刺、伤害来的位置
（近战是玩家的位置，弹射物是弹射物的位置）在目标视线背后，就把伤害乘上去，并在玩家那里响一声暴击音。规则见
Shared/Rules/Backstabbing.py。DamageEvent 的 damage 是护甲结算前的值，和 JE 改的是同一步。
"""
from .EventRegistry import registerHandler
from .Helpers.Engine import compFactory, GetCarriedItem, GetEngineTypeStr
from .Helpers.Fx import ToAllPlayerPlaySound
from ..Shared.Rules import Backstabbing as Rules

PLAYER = "minecraft:player"
CRIT_SOUND = "game.player.attack.strong"     # 基岩版没有 JE 的 entity.player.attack.crit，用重击的那一声


@registerHandler("DamageEvent")
def OnBackstab(args):
    attackerId, targetId = args.get("srcId"), args.get("entityId")
    if not attackerId or attackerId == targetId or GetEngineTypeStr(attackerId) != PLAYER:
        return
    level = Rules.levelOf(GetCarriedItem(attackerId, True))
    if level <= 0:
        return
    sourceId = args.get("projectileId") or attackerId
    sourcePos = compFactory.CreatePos(sourceId).GetFootPos() or compFactory.CreatePos(attackerId).GetFootPos()
    targetPos = compFactory.CreatePos(targetId).GetFootPos()
    rot = compFactory.CreateRot(targetId).GetRot()
    if not sourcePos or not targetPos or not rot or not Rules.isBehind(Rules.lookOf(rot), targetPos, sourcePos):
        return
    args["damage"] = Rules.damageOf(float(args.get("damage") or 0), level)
    attackerPos = compFactory.CreatePos(attackerId).GetFootPos()
    if attackerPos:
        ToAllPlayerPlaySound(compFactory.CreateDimension(attackerId).GetEntityDimensionId(), attackerPos, CRIT_SOUND)
