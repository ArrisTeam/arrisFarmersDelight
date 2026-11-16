# -*- coding: utf-8 -*-
"""DishCrafts - 前置包在场时，改在砧板上摆的菜工作台不再出（服务端）

照 Hands-On Delight 在 JE 上的缺省（remove_crafting_recipes = true）：FD 的食物合成搬到砧板上（Compat/Diegesis/DishBoard.py），
玩家自己的合成格（工作台、背包里的 2x2）拿成品时取消，并提示去砧板。
拦的是"配方"不是"成品"：取结果时读合成格（Server/CraftReturns.readGrid），格子里的原料正好是这道菜在砧板上的某条配方才拦
（Shared/Rules/DishStation.isDishCraft）。同一成品的别的配方照常——切片拼回整个派只有一种原料，不是砧板菜；
创造模式从物品栏里拿东西也发这个事件，那时合成格对不上，也不拦。
只在前置包登记成功时由 ServerBoot 登记；没装前置时工作台一切照旧。
"""
from ...Server.CraftReturns import readGrid
from ...Server.EventRegistry import registerHandler
from ...Server.Helpers.Engine import ShowTip
from ...Shared.Rules import Crafting, DishStation

PRIORITY = 50                    # 先于合成后补还剩余物（Server/CraftReturns.py）：取消了就不还


def _resultName(args):
    item = args.get("itemDict") or {}
    return item.get("newItemName") or item.get("itemName")


def onCraft(args):
    playerId = args.get("playerId")
    if not DishStation.isDishCraft(_resultName(args), Crafting.namesOf(readGrid(playerId))):
        return None
    args["cancel"] = True
    ShowTip(playerId, "这道菜要在砧板上摆：右键砧板，先放底座再一层层往上放")
    return True


def register():
    registerHandler("CraftItemOutputChangeServerEvent", match=DishStation.isDishResult, priority=PRIORITY,
                    keyOf=_resultName)(onCraft)
