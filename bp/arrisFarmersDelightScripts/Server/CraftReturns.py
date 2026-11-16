# -*- coding: utf-8 -*-
"""CraftReturns - 工作台合成后补还原料的剩余物（服务端）

JE 里原料自带合成剩余物（奶桶剩空桶、奶瓶剩玻璃瓶、米饭剩碗，面团配方的水桶原样留下……）：做完一份放回原来那格，
那格没空就进背包（ResultSlot.onTake）。基岩版有序配方把剩余物写进 result 数组由引擎给；无序配方的 result 数组只出第一项，
这里补：取结果时记下合成格，对上本包的无序配方（Shared/Data/CraftReturns.py，tools/gen_crafts.py 生成），下一刻再读一遍格子，
按每格真的少了几件算做了几份（被取消、请求被拒都是 0 份），照 Shared/Rules/Crafting.py 放回格子或给玩家。
实机核对过（3.10）：CraftItemOutputChangeServerEvent 一次请求只发一次，这时读到的还是合成前的格子；
潜行一次做多份时 itemDict 的 count 是总数（做 3 份、一份 1 个就是 3）。
下游包往 Food.shapedRecipeContainerDict 里登记的成品（生成的表里没有的）仍按成品名还容器（旧契约：分不出是哪条配方，一份还一个）。
"""
from .EventRegistry import registerHandler
from .Helpers.Engine import compFactory, levelId, serverApi
from .Helpers.Player import GiveOrDropItem
from ..Shared.Data.CraftReturns import CraftReturns
from ..Shared.Data.Food import shapedRecipeContainerDict
from ..Shared.Rules import Crafting


def readGrid(playerId):
    """玩家合成格里现在的东西：{槽位: (物品名, 个数)}（2×2 和 3×3 一起读，没开的那边是空的）。"""
    item = compFactory.CreateItem(playerId)
    grid = {}
    for slot in Crafting.GRID_SLOTS:
        stack = item.GetPlayerUIItem(playerId, slot, False, False)
        if stack and stack.get("count"):
            grid[slot] = (stack.get("newItemName") or stack.get("itemName"), stack["count"])
    return grid


def _stack(name, count):
    return {"itemName": name, "newItemName": name, "auxValue": 0, "newAuxValue": 0, "count": count}


def _settle(playerId, entry, before, most):
    """下一刻：按格子真的少了几件还剩余物，能放回原来那格就放回，放不下的进背包。"""
    if playerId not in serverApi.GetPlayerList():
        return
    after = readGrid(playerId)
    crafts = Crafting.craftsDone(before, after, most)
    item = compFactory.CreateItem(playerId)
    for slot, name, count in Crafting.returnsOf(entry, before, crafts):
        info = compFactory.CreateItem(levelId).GetItemBasicInfo(name, 0) or {}
        put, rest = Crafting.settle(after.get(slot), name, count, info.get("maxStackSize") or 1)
        if put is not None:
            if item.SetPlayerUIItem(playerId, slot, _stack(put[0], put[1]), False, False):
                after[slot] = put
            else:                                   # 界面已经关了：全进背包
                rest = count
        if rest > 0:
            GiveOrDropItem(playerId, _stack(name, rest))


@registerHandler("CraftItemOutputChangeServerEvent")
def OnCraftOutput(args):
    playerId = args["playerId"]
    taken = args.get("itemDict") or {}
    result = taken.get("newItemName") or taken.get("itemName")
    entries = CraftReturns.get(result)
    if entries:
        before = readGrid(playerId)
        entry = Crafting.entryFor(entries, before)
        if entry is not None:
            most = Crafting.mostCrafts(taken.get("count"), entry["count"])
            compFactory.CreateGame(levelId).AddTimer(0.0, _settle, playerId, entry, before, most)
        return
    container = shapedRecipeContainerDict.get(result)
    if container:
        count = Crafting.mostCrafts(taken.get("count"), container.get("perCraft", 1))
        GiveOrDropItem(playerId, {"itemName": container["itemName"], "newItemName": container["itemName"],
                                  "auxValue": container.get("auxValue", 0), "newAuxValue": container.get("auxValue", 0),
                                  "count": count})
