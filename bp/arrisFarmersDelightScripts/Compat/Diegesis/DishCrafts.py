# -*- coding: utf-8 -*-
"""DishCrafts - 前置包在场时，改在砧板上摆的菜工作台不再出（服务端）

照 Hands-On Delight 在 JE 上的缺省（remove_crafting_recipes = true）：FD 的食物合成搬到砧板上（Compat/Diegesis/DishBoard.py），
玩家自己的合成格（工作台、背包里的 2x2）拿成品时取消，并提示去砧板。哪些菜见 Shared/Rules/DishStation.isDishResult。
创造模式从物品栏里拿东西也走这个事件、而且分不出来，所以创造模式在背包界面里不拦（创造本来就能直接拿）。
只在前置包登记成功时由 ServerBoot 登记；没装前置时工作台一切照旧。
"""
from ...Server.EventRegistry import registerHandler
from ...Server.Helpers.Engine import serverApi, ShowTip
from ...Server.Helpers.Player import IsCreative
from ...Shared.Rules import DishStation

PRIORITY = 50                    # 先于合成后返还空容器（Server/PlayerSession.py）：取消了就不还


def _resultName(args):
    item = args.get("itemDict") or {}
    return item.get("newItemName") or item.get("itemName")


def onCraft(args):
    playerId = args.get("playerId")
    inventory = serverApi.GetMinecraftEnum().ContainerType.INVENTORY
    if args.get("screenContainerType") == inventory and IsCreative(playerId):
        return None
    args["cancel"] = True
    ShowTip(playerId, "这道菜要在砧板上摆：右键砧板，先放底座再一层层往上放")
    return True


def register():
    registerHandler("CraftItemOutputChangeServerEvent", match=DishStation.isDishResult, priority=PRIORITY,
                    keyOf=_resultName)(onCraft)
