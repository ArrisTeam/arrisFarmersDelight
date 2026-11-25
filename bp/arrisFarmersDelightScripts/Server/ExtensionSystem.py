# -*- coding: utf-8 -*-
"""ExtensionSystem - 新联动接口发服务端 ready 事件用的系统（服务端）

网易的 BroadcastEvent 是系统的方法，监听的人按广播者的（命名空间, 系统名）听：QuModLibs 的加载器系统用的是框架内部的名字，借不了，
所以单建一个只用来广播的系统，名字是 Api/ExtensionApi/Events 里对外公布的那两个（机械动力的 _server_system.py 也是这么做的）。
要广播时才注册（有就用现成的），不挂监听、不存状态。
"""
from .Helpers.Engine import serverApi
from ..Api.ExtensionApi import Events

_ServerSystem = serverApi.GetServerSystemCls()


class ExtensionApiServerSystem(_ServerSystem):
    """只用来广播 ServerExtensionApiReady。"""


def getSystem():
    """广播用的系统：已经有了就用它，没有就注册一个；引擎注册不了时是 None。"""
    system = serverApi.GetSystem(Events.EXTENSION_API_NAMESPACE, Events.EXTENSION_API_SYSTEM_NAME)
    if system:
        return system
    return serverApi.RegisterSystem(Events.EXTENSION_API_NAMESPACE, Events.EXTENSION_API_SYSTEM_NAME,
                                    ExtensionApiServerSystem.__module__ + "." + ExtensionApiServerSystem.__name__)
