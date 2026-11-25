# -*- coding: utf-8 -*-
"""TableServerLink - 联动步骤 table（服务端）：前置包的原版工作台站点上登记农夫乐事的无序配方还容器

前置包的原版工作台是脚本合成、不发引擎的合成事件，Server/CraftReturns 管不到它：在那张工作台上做本包的无序配方会把桶和碗吞掉。
这一步把同一份规则登到它的接口上（TableHooksLink.returns）。接口不在（前置包太旧、没装它的内容包）：skipped，什么都不登。
砧板菜不让在那张工作台上做（dishVeto）跟着砧板站点走，在 board 那一步登（BoardServerLink）。
"""
from . import TableHooksLink


def link(ctx):
    return TableHooksLink.addReturns()
