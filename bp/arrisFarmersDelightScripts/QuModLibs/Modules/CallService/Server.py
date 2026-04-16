# -*- coding: utf-8 -*-
from ...Server import Call, Events
from ..EventsPool.Server import POOL_ListenForEvent, POOL_UnListenForEvent

class CallService:
    """ 通信服务封装 (服务端) """
    _delayCacheMap = {}  # type: dict[str, list[tuple]]

    @staticmethod
    def _init():
        POOL_ListenForEvent(Events.OnScriptTickServer, CallService.updateDataPacks)

    @staticmethod
    def updateDataPacks(_={}):
        if len(CallService._delayCacheMap) <= 0:
            POOL_UnListenForEvent(Events.OnScriptTickServer, CallService.updateDataPacks)
            return
        _cacheMap = CallService._delayCacheMap
        # 处理每个玩家的具体数据包
        for playerId, datas in _cacheMap:
            datas = _cacheMap[playerId]
            if datas:
                Call(playerId, "__calls__", datas)
        CallService._delayCacheMap = {}

    @staticmethod
    def delayCall(playerId, key, *args, **kwargs):
        # type: (str, str, object, object) -> None
        """ 服务端延迟合批Call
            警告: 这并不一定能改善性能 取决于具体应用场景
        """
        CallService._init()
        CallService._delayCacheMap[playerId] = CallService._delayCacheMap.get(playerId, [])
        CallService._delayCacheMap[playerId].append((key, args, kwargs))

    # @staticmethod
    # def delayMultiCall(playerId, key, *args, **kwargs):
    #     # type: (str, str, object, object) -> None
    #     """ 延迟合批的批量数据包(适用于特效/音效类) """
    #     pass

    @staticmethod
    def updateNow():
        CallService.updateDataPacks()