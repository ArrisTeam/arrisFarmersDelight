# -*- coding: utf-8 -*-
"""StoveSlots - 炉灶的六个烤位的读写：炉灶站点的 grill 槽组绑在它上面（服务端）

炉灶顶上的东西存在方块实体数据 "0".."5"，每项 {"itemDict": 物品或 None, "cookTimer": 倒数的秒数}（Server/Stove.py）。站点的槽组经
前置包的 bindSlots 直接读写它：站点里摆上去、取下来的就是方块上的，经典玩法、料斗、别的玩家看到的是同一份；
FD 原样烤好弹出、手工烤好换成成品，站点那边由前置包的 pollStorages 发现并同步。
get 空烤位返回 None；set 把烤位换成这一件（None = 清空），倒数的秒数重新从头算；方块实体不在就抛（前置包把这个动作作废、东西还给玩家，不能悄悄吞）。
世界里展示的广播（Helpers/BlockItems.PublishStove）不在这里发：一次动作可能改好几格，由逻辑改完统一发一次。
"""
from .Engine import GetBlockEntityData


class StoveSlots(object):
    def __init__(self, dimensionId, blockPos, places, cookTimer):
        self.dimensionId = dimensionId
        self.blockPos = tuple(blockPos)
        self.places = places
        self.cookTimer = cookTimer

    def size(self):
        return self.places

    def get(self, index):
        data = GetBlockEntityData(self.dimensionId, self.blockPos)
        slot = data[str(index)] if data is not None else None
        item = slot.get("itemDict") if slot else None
        return item if item and item.get("newItemName") and (item.get("count") or 0) > 0 else None

    def set(self, index, item):
        data = GetBlockEntityData(self.dimensionId, self.blockPos)
        if data is None:                          # 方块实体不在（换方块的那几刻、没加载）：悄悄返回的话站点里放下的东西就没存下、手上却扣了：抛，动作作废、东西还给玩家
            raise RuntimeError("stove block entity missing at %s: place %d not written" % (self.blockPos, index))
        data[str(index)] = {"itemDict": dict(item) if item else None, "cookTimer": self.cookTimer}
