# -*- coding: utf-8 -*-
"""Deeds - 玩家做成了某件事的登记点：玩法模块在那件事做成的地方报一声，想知道的模块订阅（服务端，不碰引擎）

报：done(玩家, 事, 细节)。没有人订阅时就是一次字典查找；订阅者出错只打日志，不连累报的那一方。订阅：subscribe(事, 函数)，
函数收 (玩家, 细节)，同一个函数订阅两次只算一次。现在报的事和细节：
    CUT_ON_BOARD    在砧板上切开了一件（切的那件东西的物品名）：经典右键 Server/CuttingBoard、砧板站点 Compat/Diegesis/BoardChop
    SKILLET_COOKED  手持煎锅煎好了一件（原料的物品名）：Server/SkilletHand
    PLACED_BLOCK    脚本替玩家放下了一个方块（方块名）：Server/ItemToBlock（派、煎锅）、Server/Crops（稻米、蘑菇菌落）、
                    Server/RichSoil（沃土耕地上的原版作物）；引擎自己放的方块不在这里报（那是 EntityPlaceBlockAfterServerEvent）
    HARVESTED       右键采摘了一株作物（采摘前那一格的方块名）：Server/Crops（番茄）
"""
import traceback

CUT_ON_BOARD = "cut_on_board"
SKILLET_COOKED = "skillet_cooked"
PLACED_BLOCK = "placed_block"
HARVESTED = "harvested"

_subscribers = {}       # 事 -> [函数]


def subscribe(deed, func):
    """func(玩家, 细节) 在这件事做成时被调；同一个函数订阅两次只算一次。"""
    funcs = _subscribers.setdefault(deed, [])
    if func not in funcs:
        funcs.append(func)


def unsubscribe(deed, func):
    funcs = _subscribers.get(deed)
    if funcs and func in funcs:
        funcs.remove(func)


def done(playerId, deed, detail=None):
    """playerId 做成了 deed（细节见模块说明）；没有人订阅时什么都不做。"""
    funcs = _subscribers.get(deed)
    if not funcs:
        return
    for func in tuple(funcs):
        try:
            func(playerId, detail)
        except Exception:  # noqa: BLE001 - 订阅者的错不连累报事的玩法模块
            print("[arrisFarmersDelight] %s 的订阅者 %s 出错" % (deed, getattr(func, "__name__", func)))
            traceback.print_exc()
