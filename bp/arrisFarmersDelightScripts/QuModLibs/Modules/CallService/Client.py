# -*- coding: utf-8 -*-
from ...Client import Call, Events
from ..EventsPool.Client import POOL_ListenForEvent, POOL_UnListenForEvent

class CallService:
    """ 通信服务封装 (客户端推荐使用) """
    _cache = []

    @staticmethod
    def _init():
        POOL_ListenForEvent(Events.OnScriptTickClient, CallService.updateDataPacks)

    @staticmethod
    def updateDataPacks(_={}):
        if len(CallService._cache) <= 0:
            POOL_UnListenForEvent(Events.OnScriptTickClient, CallService.updateDataPacks)
            return
        Call("__calls__", CallService._cache)
        CallService._cache = []

    @staticmethod
    def delayCall(key, *args, **kwargs):
        # type: (str, object, object) -> None
        """ 延迟合批Call 优化频繁发包性能开销(有序通信) """
        CallService._init()
        CallService._cache.append((key, args, kwargs))

    @staticmethod
    def updateNow():
        CallService.updateDataPacks()