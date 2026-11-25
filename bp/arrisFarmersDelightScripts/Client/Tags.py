# -*- coding: utf-8 -*-
"""Tags - 客户端的标签引擎口：导入时装给 Shared/Rules/ItemTags 和 Shared/Rules/Grilling（客户端）

客户端问标签一律经 ItemTags、问"煎烤成什么"经 Grilling；这里只把客户端的引擎组件交给 Shared/Rules/TagPort.EnginePort
（客户端没有 GetBlockTags，不给方块信息组件）。客户端的标签进世界之前是不全的（网易 3.10 实机：LoadClientAddonScriptsAfter 时原版物品的
GetItemTags 还是 None、反查漏成员，进世界的过程中才全）：EnginePort 每秒最多探一次，探到农夫乐事登记的原版成员到了才算准备好；
之前 ItemTags 的枚举按静态词表答、按单件问的不缓存，Grilling 只认表；准备好的那一刻 ItemTags.generation() 加一。
单机时服务端的口也在，两个模块都用服务端的。
"""
import time

from .Engine import compFactory, levelId
from ..Shared.Rules import Grilling, ItemTags, TagPort

LOADED_AT = time.time()            # 这个模块导入的时刻：游戏内自检（Client/Debug/McdkTagsTest）拿它和 PORT.readyAt 比，标签晚多久才全
PORT = TagPort.EnginePort(lambda: compFactory.CreateItem(levelId), lambda: compFactory.CreateBlock(levelId), None, time.time,
                          recipes=lambda: compFactory.CreateRecipe(levelId))
ItemTags.setPort("client", PORT)
Grilling.setPort("client", PORT)
