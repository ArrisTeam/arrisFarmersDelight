# -*- coding: utf-8 -*-
"""ExtensionSystem - 新联动接口发客户端 ready 事件用的系统（客户端）

和服务端的 Server/ExtensionSystem.py 对称：按 Api/ExtensionApi/Events 公布的命名空间、系统名单建一个只用来广播的系统，要广播时才注册。
"""
from .Engine import clientApi
from ..Api.ExtensionApi import Events

_ClientSystem = clientApi.GetClientSystemCls()


class ExtensionApiClientSystem(_ClientSystem):
    """只用来广播 ClientExtensionApiReady。"""


def getSystem():
    """广播用的系统：已经有了就用它，没有就注册一个；引擎注册不了时是 None。"""
    system = clientApi.GetSystem(Events.EXTENSION_API_NAMESPACE, Events.EXTENSION_API_SYSTEM_NAME)
    if system:
        return system
    return clientApi.RegisterSystem(Events.EXTENSION_API_NAMESPACE, Events.EXTENSION_API_SYSTEM_NAME,
                                    ExtensionApiClientSystem.__module__ + "." + ExtensionApiClientSystem.__name__)
