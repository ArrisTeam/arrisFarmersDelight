# -*- coding: utf-8 -*-
"""ExtensionReady - 全部 Addon 脚本加载完时发新联动接口的服务端 ready 事件（服务端）

ModServer 把 LoadServerAddonScriptsAfter 转给这里（EventRegistry）。每端一次、出错不连累的做法在 Api/ExtensionApi/Ready.py；
广播用的系统在 ExtensionSystem.py：它要引擎的系统基类，到要广播时才导入（离线测试换掉 _system，不用假引擎）。
别的模组在 ready 里往农夫乐事的表里登记的东西，玩家进服时由表同步发给他的客户端（Server/TableSync.py 的基线是模块导入时的表，早于 ready）。
"""
from .EventRegistry import registerHandler
from ..Api.ExtensionApi import Ready, Recipes


def _system():
    from .ExtensionSystem import getSystem
    return getSystem()


def _syncNow():
    """ext.recipes.syncToClients：现在就把表的改动发给在线的玩家（表同步本来每 5 秒看一次，见 TableSync.py）。"""
    from . import TableSync
    TableSync.step()


@registerHandler("LoadServerAddonScriptsAfter")
def OnServerExtensionApiReady(args=None):
    Recipes.provide(syncNow=_syncNow)
    Ready.publish("server", _system)
