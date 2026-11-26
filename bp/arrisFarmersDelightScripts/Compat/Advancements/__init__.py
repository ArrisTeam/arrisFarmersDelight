# -*- coding: utf-8 -*-
"""
arrisFarmersDelight × arrisAdvancements（成就系统，脚本名 dolorAdvancements）联动：JE 农夫乐事的 21 条进度

入口 AdvBoot（modMain 里 MOD.Server）听成就系统的 ready，AdvBridge 登记节点、挂监听，AdvTriggers 算推进哪一条；
节点和条件表在 Shared/Data/Advancements。成就系统没装时什么都不做。
"""
