# -*- coding: utf-8 -*-
"""Tags - 客户端的标签引擎口：导入时装给 Shared/Rules/ItemTags（客户端）

客户端问标签一律经 ItemTags；这里只把客户端的引擎组件交给 Shared/Rules/TagPort.EnginePort（客户端没有 GetBlockTags，不给方块信息组件）。
客户端的标签进世界之前是不全的（网易 3.10 实机：LoadClientAddonScriptsAfter 时原版物品的 GetItemTags 还是 None、反查漏成员，
进世界的过程中才全）：EnginePort 每秒最多探一次，探到农夫乐事登记的原版成员到了才算准备好；之前 ItemTags 按静态词表答、不缓存，
准备好的那一刻 ItemTags.generation() 加一。单机时服务端的口也在，ItemTags 用服务端的。
"""
import time

from .Engine import compFactory, levelId
from ..Shared.Rules import ItemTags, TagPort

PORT = TagPort.EnginePort(lambda: compFactory.CreateItem(levelId), lambda: compFactory.CreateBlock(levelId), None, time.time)
ItemTags.setPort("client", PORT)
