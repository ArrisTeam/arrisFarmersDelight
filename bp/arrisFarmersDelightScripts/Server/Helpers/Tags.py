# -*- coding: utf-8 -*-
"""Tags - 服务端的标签引擎口：导入时装给 Shared/Rules/ItemTags（服务端）

服务端问标签一律经 ItemTags（它在口答不了、没准备好时按农夫乐事的静态词表 Shared/Data/Tags 答）；这里只把服务端的三个引擎组件交给
Shared/Rules/TagPort.EnginePort。服务端从系统建好起标签就是全的（网易 3.10 实机），第一次探就算准备好；GetBlockTags 只有服务端有。
由 Server/ModServer.py 最先导入：别的模块导入时就按标签建东西也问得到引擎。
"""
import time

from .Engine import compFactory, levelId
from ...Shared.Rules import ItemTags, TagPort

PORT = TagPort.EnginePort(lambda: compFactory.CreateItem(levelId), lambda: compFactory.CreateBlock(levelId),
                          lambda: compFactory.CreateBlockInfo(levelId), time.time)
ItemTags.setPort("server", PORT)
