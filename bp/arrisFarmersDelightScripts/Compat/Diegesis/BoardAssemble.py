# -*- coding: utf-8 -*-
"""BoardAssemble - 砧板站点的摆盘：层凑成菜、做成、书里点一道菜从背包放料（服务端）

对应 Hands-On Delight：station/BoardLogic.java 的 finishIfWanted（303-308）、pick / fill（314-424）、assemble（549-611）。
- finishIfWanted：做成了、而且没法再往上加料（或就是书里点的那道）-> 立刻做成；还能长成更大的菜时等厨师点一下板；
- assemble：层凑成一道菜，一份每层用一件，最多 16 份；每层剩下的、换成别的东西的容器（桶、瓶、碗）全给厨师，
  成品躺回板上（板空着或同种，最多一叠，放不下的给厨师），发 assembled {layers, finish, block}；凑不成就拒绝；
- fill（书里点的菜，动作 bookFill {"key", "sets"}）：板空着放 1 份（Shift 16 份），板上已有层就放到和底座一样多；板上等着切的食物是这道菜的底座
  就拿它当第 0 层，别的等着切的食物留着、什么也不放；做好的旧菜先还给厨师；料从背包按格号取，同一种的叠放在一层，
  一层最多一叠（桶只放一个，所以一份）；原样留下的配料（面团的水桶）放一件就够。放完就做成这道菜（书里点的）。
"""
from . import BoardGive
from .BoardEmit import emit
from .BoardSlots import stack
from ...Shared.Rules import DishStation as Dishes
from ...Shared.Rules import StationBooks as Books
from ...Shared.Rules.BoardStation import BATCH, BOARD_MAX, keyOf
from ...Shared.Rules.HandsOn import Assembly, ItemData


def _wire(item):
    return {"newItemName": item["newItemName"], "newAuxValue": item.get("newAuxValue") or 0, "count": item["count"]}


def _one(kind, count=1):
    return {"newItemName": kind[0], "newAuxValue": kind[1], "count": count}


def finishIfWanted(logic, playerId):
    """放下一层之后：做成了且不能再长，或就是书里点的那道，就做成（finishIfWanted，303-308）。"""
    keys = [keyOf(layer) for layer in logic.layers()]
    dish = Dishes.completed(keys) if keys else None
    if dish is not None and (dish["result"][0] == logic.picked or not Dishes.canGrow(keys)):
        assemble(logic, playerId)


def assemble(logic, playerId):
    """层做成菜（assemble，549-611）；凑不成或一份也做不了就拒绝。"""
    layers = logic.layers()
    stacks = [(keyOf(layer), layer["count"]) for layer in layers]
    dish = Dishes.completed([kind for kind, _count in stacks]) if layers else None
    if dish is None:
        logic.station.effect("refused", {})
        return False
    plan = Dishes.makeOf(dish, stacks)
    logic.setLayers([])
    for layer, (_kind, left) in zip(layers, plan["left"]):
        BoardGive.give(logic, ItemData.copyOf(layer, left))       # 没用上的原样还（带着自己的附魔、改名……）
    for name, aux, count in plan["extras"]:
        BoardGive.give(logic, {"newItemName": name, "newAuxValue": aux, "count": count})
    name, aux, count = plan["result"]
    result = {"newItemName": name, "newAuxValue": aux, "count": count}
    board = logic.boardItem()
    if board is None or keyOf(board) == keyOf(result):
        room = min(logic.ctx.maxStackOf(result), BOARD_MAX) - (board["count"] if board else 0)
        there = max(0, min(room, count))
        if there > 0:
            logic.setBoard(dict(result, count=(board["count"] if board else 0) + there))
            result["count"] -= there
    BoardGive.give(logic, result)
    logic.restart()
    emit(logic, "assembled", {"layers": [_wire(dict(layer, count=1)) for layer in layers], "block": Dishes.isBlockResult(name),
                              "finish": Dishes.finishOf(dish)})
    return True


# ---------------------------------------------------------------- 书里点一道菜

def _removeFrom(window, kind, amount):
    """从背包窗口按格号扣 amount 件 kind（只扣不带数据的：带附魔 / 改名的那件做成一层再还回来会丢数据，书里放料不动它）。"""
    for index in range(len(window)):
        item = window[index]
        if amount <= 0:
            return
        if item is None or keyOf(item) != kind or ItemData.dataOf(item):
            continue
        used = min(item["count"], amount)
        window[index] = dict(item, count=item["count"] - used) if item["count"] > used else None
        amount -= used


def _pool(window):
    pool = {}
    for item in window:
        if item is not None and item.get("count", 0) > 0 and not ItemData.dataOf(item):
            pool[keyOf(item)] = pool.get(keyOf(item), 0) + item["count"]
    return pool


def _variants(variants, held):
    """能接上板上这些层（held：[物品身份]）的几种写法，各配上还缺的配料（底座在前）：[(dish, [缺的配料身份])]。"""
    found = []
    for dish in variants:
        taken = Assembly.assign(dish, held, lambda ingredient, layer: ingredient == layer) if held else []
        if taken is None:
            continue
        missing = [index for index in range(len(dish["ingredients"])) if index not in taken]
        missing.sort(key=lambda index: index != dish["base"])
        found.append((dish, [dish["ingredients"][index] for index in missing]))
    return found


def fill(logic, playerId, key, sets):
    """书里点的一道菜（fill，324-424）。放了东西返回 True；什么也没放返回 False。"""
    variants = Books.dishOf(key)
    if not variants:
        return False
    logic.picked = variants[0]["result"][0]
    ctx, board, layers = logic.ctx, logic.boardItem(), logic.layers()
    held = [keyOf(layer) for layer in layers]
    startsOnBoard = False
    if not layers and board is not None:
        if any(dish["ingredients"][dish["base"]] == keyOf(board) for dish in variants):
            startsOnBoard, held = True, [keyOf(board)]
        elif not Dishes.isDishResult(board["newItemName"]) and logic.env().cuttable(board):
            return False                                   # 等着切的食物留着板
    if held and any(not missing for _dish, missing in _variants(variants, held)):
        finishIfWanted(logic, playerId)                    # 板上已经是这道菜的全部层：不用放料，直接做成
        return True
    pool = _pool(ctx.inventory)
    want = (BATCH if sets > 1 else 1) if not held else (layers[0]["count"] if layers else min(board["count"], BATCH))
    best = None
    for dish, missing in _variants(variants, held):
        keeps = [kind for kind in missing if kind[0] in dish["keeps"]]
        counted = [kind for kind in missing if kind not in keeps]
        most = min([want] + [ctx.maxStackOf(_one(kind)) for kind in counted])
        count = Books.setsOf(counted, pool, most) if counted else (1 if missing else 0)
        if missing and (count > 0 and all(pool.get(kind, 0) >= 1 for kind in keeps)) and (best is None or count > best[0]):
            best = (count, dish, missing, keeps)
    if best is None:
        return False
    count, dish, missing, keeps = best
    for kind in missing:
        _removeFrom(ctx.inventory, kind, 1 if kind in keeps else count)
    if startsOnBoard:
        extra = board["count"] - min(board["count"], BATCH)
        if extra > 0:
            BoardGive.give(logic, dict(board, count=extra))
        layers = [dict(board, count=min(board["count"], BATCH))]
        logic.setBoard(None)
    elif board is not None and not layers:
        BoardGive.give(logic, board)                       # 做好的旧菜：取下来还给厨师
        logic.setBoard(None)
    layers = layers + [stack(_one(kind, 1 if kind in keeps else count)) for kind in missing]
    logic.setLayers(layers)
    logic.restart()
    emit(logic, "placed", {"at": len(layers) - 1})
    finishIfWanted(logic, playerId)
    return True
