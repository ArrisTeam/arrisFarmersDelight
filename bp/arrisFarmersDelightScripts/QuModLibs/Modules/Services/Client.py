# -*- coding: utf-8 -*-
from ...Client import ListenForEvent, UnListenForEvent, _loaderSystem, Events, Call, CallBackKey, playerId
from Globals import _BaseService, _ServiceManager, _AutoStopService, BaseEvent, BaseBusiness, KeyBusiness, QRequests
lambda: "Service By Zero123"

__all__ = [
    "BaseService",
    "_serviceManager",
    "AutoStopService",
    "BaseEvent",
    "BaseBusiness",
    "KeyBusiness",
    "QRequests"
]

_serviceManager = _ServiceManager(
    ListenForEvent, UnListenForEvent, Call, lambda key, funObj: CallBackKey(key)(funObj)
)

class BaseService(_BaseService):
    """ 服务基类 """
    _BINDMANAGER = _serviceManager

    def syncRequest(self, apiPath = "", argsObject = QRequests.Args()):
        # type: (str, QRequests.Args) -> None
        """ 同步请求 """
        argsObject.postParam = playerId
        return self.getManager().syncRequest(apiPath, argsObject)

class AutoStopService(BaseService, _AutoStopService):
    """ 自动关闭服务类 """
    def __init__(self):
        BaseService.__init__(self)
        _AutoStopService.__init__(self)
    
    def onAccessed(self):
        BaseService.onAccessed(self)
        return _AutoStopService.onAccessed(self)
    
    def _onTick(self):
        BaseService._onTick(self)
        _AutoStopService._onTick(self)

def getServiceManager():
    """ 获取服务管理器 """
    return _serviceManager

def listenServiceEvent(eventCls, funcObj, priority=None):
    # type: (type[BaseEvent], function, int | None) -> None
    """ 监听服务事件 """
    _serviceManager.serviceListen(eventCls, funcObj, priority)

def unListenServiceEvent(eventCls, funcObj):
    # type: (type[BaseEvent], function) -> None
    """ 反监听服务事件 """
    _serviceManager.unServiceListen(eventCls, funcObj)

def serviceBroadcast(eventObj):
    # type: (BaseEvent) -> None
    """ 发起服务广播 """
    _serviceManager.broadcast(eventObj)

# ================= 系统级业务逻辑注册 =================
ListenForEvent(Events.OnScriptTickClient, _serviceManager, _serviceManager.onTick)
def _SERVICE_MANAGER_ON_GAME_OVER():
    BaseService._CLOSE_STATE = True
    _serviceManager._closeState = True
    _serviceManager.removeAllService()
_loaderSystem._onDestroyCall_LAST.append(_SERVICE_MANAGER_ON_GAME_OVER)