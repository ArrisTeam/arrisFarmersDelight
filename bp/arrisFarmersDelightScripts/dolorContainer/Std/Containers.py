# -*- coding: utf-8 -*-
"""
标准库：常用的容器种类（docs/ARCHITECTURE.md 第 3.2 节），两端都登记（界面模型声明容器时按名字核对）。
服务端怎么存在 Std/Server/Containers.py。

- TEMPORARY 玩家临时格：属于这位查看者的会话，关界面时退回背包；界面开着时服务器崩溃，下次进游戏退回（工作台的合成格）。
- STORAGE   实例存储：跟容器实例存，所有查看者同一份；可以不设上限。
- VIRTUAL   不放东西：只放算出的格子（工作台的产物格）。
- WORN      看界面的玩家自己身上：盔甲 4 格（WORN_ARMOR：头、身、腿、脚，与 Std/Slots 的部位同序）与副手 1 格（WORN_OFFHAND），
            共 WORN_SIZE 格。经引擎读写，改了当场穿上、拿上；不跟着实例，哪个界面里都是看的人自己的（原版物品栏的盔甲栏与副手）。
"""
from ..Common.Collections import ContainerKind, registerKind

TEMPORARY = registerKind(ContainerKind("temporary"))
STORAGE = registerKind(ContainerKind("storage", unbounded=True, stored=True))
VIRTUAL = registerKind(ContainerKind("virtual", holdsItems=False))
WORN = registerKind(ContainerKind("worn"))
WORN_ARMOR = (0, 1, 2, 3)
WORN_OFFHAND = 4
WORN_SIZE = 5
