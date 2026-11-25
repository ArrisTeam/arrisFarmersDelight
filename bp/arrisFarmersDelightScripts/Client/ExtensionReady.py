# -*- coding: utf-8 -*-
"""ExtensionReady - 全部 Addon 脚本加载完时发新联动接口的客户端 ready 事件（客户端）

和服务端的 Server/ExtensionReady.py 对称：每端一次、出错不连累的做法在 Api/ExtensionApi/Ready.py；
广播用的系统在 ExtensionSystem.py，到要广播时才导入（离线测试换掉 _system）。
"""
from ..QuModLibs.Client import Listen
from ..Api.ExtensionApi import Ready


def _system():
    from .ExtensionSystem import getSystem
    return getSystem()


@Listen("LoadClientAddonScriptsAfter")
def OnClientExtensionApiReady(args=None):
    Ready.publish("client", _system)
