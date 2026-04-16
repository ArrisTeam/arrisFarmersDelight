# -*- coding: utf-8 -*-
from ...Server import *
from ..Services.Server import BaseService, BaseEvent, serviceBroadcast
from ..EntityComps.Server import QBaseEntityComp
from ...Util import TRY_EXEC_FUN, QTemplate
from copy import copy, deepcopy
lambda: "联机大厅模块 By Zero123"

# 该项目处于实验阶段 请警惕使用
# 推荐使用 QuickLobbyManager 作为联机大厅的管理器

def LOG_TO_ALL_PLAYER(text=""):
    for playerId in serverApi.GetPlayerList():
        comp = serverApi.GetEngineCompFactory().CreateGame(playerId)
        comp.SetNotifyMsg(str(text), serverApi.GenerateColor("BLUE"))

def AUTO_DEBUG_MODE():
    if serverApi.GetPlatform() != -1:
        BaseLobbyManager.LOCAL_DEBUG_MODE = True

class DebugStorePurchaseEvent(BaseEvent):
    """ DEBUG模式 商品购买事件 """
    def __init__(self, playerId=None):
        BaseEvent.__init__(self)
        self.playerId = playerId

class OrderINFO:
    """ 订单信息类"""
    def __init__(self, dic={}):
        # type: (dict) -> None
        self.orderId = dic.get("order_id", -1)          # type: int
        self.timestamp = dic.get("timestamp", -1)       # type: int
        self.cmd = dic.get("cmd", "")                   # type: str
        self.productCount = dic.get("product_count", 0) # type: int
        self.uid = -1

    def automaticShipping(self, callback=lambda *_: None):
        """ 自动设置订单发货 """
        BaseLobbyManager.LOBBY_SET_STORAGE_AND_USER_ITEM(self.uid, callback, self.orderId, None)

class LobbyPlayerComp(QBaseEntityComp):
    """ 联机大厅玩家数据管理组件
        - 高性能管理逻辑:
            在 onFirstDataUpdate 事件下读取数据并写入内存 后续直接在内存上操作并使用惰性写入(lazyWriteData)同步后台
            确高性能和及时性 (玩家中途退出游戏会立即触发惰性更新) [绝大多数场景使用该策略即可]

        - 及时同步:
            通过 asyncUpdateStorage 方法获取最新数据并在回调下安全处理 适用于严格场景数据计算
    """
    # _BIND_TARGET_KEYS = []
    # _TEMPLATE_ARGS = [ "_BIND_TARGET_KEYS" ]

    # @classmethod
    # def __createTemplateCls__(cls, argDatas):
    #     # 重新实现模板生成方法 支持增量参数
    #     return QTemplate.__createTemplateCls__(cls, [argDatas])

    def __init__(self):
        QBaseEntityComp.__init__(self)
        self.lobbyCacheData = dict()
        """ 联机大厅的用户缓存数据 """
        self._firstCacheData = dict()
        """ 初次缓存数据 """
        self.playerUidCache = None
        self.userTargetKeyDatas = []
        """ 用户数据KEY表(需预声明)或使用模板声明 """
        self.httpUpdateCount = 0
        """ 记录网络数据更新次数 """
        self.lazyUpdateStorageTime = 2.5
        """ 惰性更新频率 """
        self._lazyWaitWriteDataTime = 3.0
        """ 惰性写入频率 """
        self._waitLazyUpdateKeys = set()
        """ 等待惰性更新的Keys值表 """
        self._waitWriteData = dict()
        """ 待写入数据表 """
        self._waitWriteCallBackData = dict()
        """ 待写入数据回调表 """
        # if self.__class__._BIND_TARGET_KEYS:
        #     self.userTargetKeyDatas += self.__class__._BIND_TARGET_KEYS
        self._userDataInitFinish = False
        self._automatedOrderProcHook = lambda *_: None

    def onBind(self):
        QBaseEntityComp.onBind(self)
        self.addTimer(QBaseEntityComp.Timer(self._callLazyWriteData, time=self._lazyWaitWriteDataTime, loop=True))
        self.addTimer(QBaseEntityComp.Timer(self._callLazyUpdateStorage, time=self.lazyUpdateStorageTime, loop=True))

    def asyncUpdateStorage(self, targetKeyDatas=None, callback=None):
        # type: (list[str] | None, function | None) -> None
        targetKeyDatas = targetKeyDatas or self.userTargetKeyDatas
        if not targetKeyDatas:
            return
        uid = self.getUid()
        def _callback(datas):
            if datas:
                for k, v in ((v["key"], v["value"]) for v in datas["entity"]["data"]):
                    self.lobbyCacheData[k] = v
                if callback:
                    TRY_EXEC_FUN(callback, datas)
                if self.httpUpdateCount == 0:
                    for k, v in self.lobbyCacheData.items():
                        self._firstCacheData[k] = v
                    TRY_EXEC_FUN(self._onFirstDataUpdate)
                self.httpUpdateCount += 1
                self.onUserDataUpdate()
            else:
                raise RuntimeError("玩家数据获取失败, UID: {}({})".format(uid, self.entityId))
        BaseLobbyManager.LOBBY_GET_STORAGE(uid, targetKeyDatas, _callback)

    def lazyUpdateStorage(self, targetKeyDatas=None):
        # type: (list[str] | None) -> None
        """ 惰性更新数据 """
        targetKeyDatas = targetKeyDatas or self.userTargetKeyDatas
        for k in targetKeyDatas:
            self._waitLazyUpdateKeys.add(k)

    def lazyWriteData(self, key, value, callback=None):
        # type: (str, object, function) -> None
        """ 惰性写入基本数据类型(仅支持官方接口允许的数据) """
        self._waitWriteData[key] = value
        if callback:
            self._waitWriteCallBackData[key] = callback

    def _callLazyWriteData(self):
        # 处理惰性写入数据
        if not self._waitWriteData:
            return
        uid = self.getUid()
        waitWriteDic = copy(self._waitWriteData)
        callBackDic = copy(self._waitWriteCallBackData)
        def _callback(datas):
            if datas:
                # 更新本地数据
                for k, v in ((v["key"], v["value"]) for v in datas["entity"]["data"]):
                    self.lobbyCacheData[k] = v
                for callback in callBackDic.values():
                    TRY_EXEC_FUN(callback, datas)
                self.httpUpdateCount += 1
                self.onUserDataUpdate()
            else:
                raise RuntimeError("玩家数据设置失败, UID: {}({})".format(uid, self.entityId))
        BaseLobbyManager.LOBBY_SET_STORAGE_AND_USER_ITEM(uid, _callback, None, lambda: [{"key": k, "value": v} for k, v in waitWriteDic.items()])
        self._waitWriteData.clear()
        self._waitWriteCallBackData.clear()

    def _callLazyUpdateStorage(self):
        # 处理惰性更新数据
        if not self._waitLazyUpdateKeys:
            return
        targetList = list(self._waitLazyUpdateKeys)
        self._waitLazyUpdateKeys.clear()
        self.asyncUpdateStorage(targetList)

    def setOrderShipment(self, orderId, callback=None):
        """ 设置订单发货 """
        uid = self.getUid()
        def _callback(datas):
            if datas:
                for k, v in ((v["key"], v["value"]) for v in datas["entity"]["data"]):
                    self.userTargetKeyDatas[k] = v
                if callback:
                    TRY_EXEC_FUN(callback, datas)
                self.httpUpdateCount += 1
                self.onUserDataUpdate()
            else:
                raise RuntimeError("订单发货失败, UID: {}({}), 订单ID: {}".format(uid, self.entityId, orderId))
        BaseLobbyManager.LOBBY_SET_STORAGE_AND_USER_ITEM(uid, _callback, orderId, None)

    def searchForUnshippedOrders(self, callback=None):
        """ 查询未发货的订单 """
        uid = self.getUid()
        def _callback(datas):
            if datas:
                if callback:
                    TRY_EXEC_FUN(callback, datas)
            else:
                raise RuntimeError("订单查询失败, UID: {}({})".format(uid, self.entityId))
        BaseLobbyManager.LOBBY_QUERY_USER_ITEM(uid, _callback)

    def getCacheData(self, key, nullValue=None):
        """ 获取缓存数据(只读) 该数据参数同步不及时 请勿用于重要数据计算 """
        return self.lobbyCacheData.get(key, nullValue)

    def getFirstCacheData(self, key, nullValue=None):
        """ 读取初始化的缓存数据(只读) 相较于getCacheData它不会在运行时更新 适用于不重要的货币计算(纯业务端计算, 后台写入) """
        return self._firstCacheData.get(key, nullValue)

    def initMemoryCache(self, key, nullValue=None):
        """ 初始化内存缓存 """
        value = self.getFirstCacheData(key, nullValue)
        if not key in self.lobbyCacheData:
            self.lobbyCacheData[key] = value
        return value

    def getUid(self):
        """ 获取玩家UID """
        if self.playerUidCache is None:
            self.playerUidCache = BaseLobbyManager.GET_PLAYER_UID(self.entityId)
        return self.playerUidCache

    def _onLobbyStorePurchase(self):
        # 局内购买物品
        if self.onLobbyStorePurchase():
            # 若用户业务返回True则阻止后续的自动处理
            return
        self._callAutomatedOrder()

    def _callAutomatedOrder(self, automaticShipping=True):
        """ 自动处理订单请求 """
        def _callBack(datas):
            for dic in datas["entity"]["orders"]:
                info = OrderINFO(dic)
                info.uid = self.getUid()
                def automatedOrderProc():
                    # 必须确保订单数据安全处理后才会发货(若返回False 强制终止行为)
                    if self.onAutomatedOrderProc(info) == False:
                        return
                    # hook处理逻辑(若返回False 强制终止行为)
                    if self._automatedOrderProcHook(self.entityId, info) == False:
                        return
                    if automaticShipping:
                        info.automaticShipping()
                TRY_EXEC_FUN(automatedOrderProc)
        self.searchForUnshippedOrders(_callBack)

    def onAutomatedOrderProc(self, orderIn=OrderINFO()):
        """ 自动订单处理时触发 """
        pass

    def onLobbyStorePurchase(self):
        """ 玩家在局内购买物品触发 """
        pass

    def onUserDataUpdate(self):
        """ 用户数据更新时触发(网络数据响应) """
        pass

    def _onFirstDataUpdate(self):
        self._userDataInitFinish = True
        self.onFirstDataUpdate()
    
    def update(self):
        QBaseEntityComp.update(self)
        if self._userDataInitFinish:
            self.userUpdate()

    def userUpdate(self):
        # 更为安全的更新逻辑 确保在初始化数据之后才会进行
        pass

    def onFirstDataUpdate(self):
        pass

    def onUnBind(self):
        QBaseEntityComp.onUnBind(self)
        self._callLazyWriteData()

class BaseLobbyManager(BaseService, QTemplate):
    """  联机大厅管理器基类
        #### 模板语句创建特化绑定类
        ```
        @BaseLobbyManager.Init
        class MyManager(BaseLobbyManager[YourComp]):
            pass
        ```
    """
    _BIND_LOBBY_PLAYER_COMP = LobbyPlayerComp
    _TEMPLATE_ARGS = [ "_BIND_LOBBY_PLAYER_COMP" ]
    LOCAL_DEBUG_MODE = False
    """ 本地调试模式 启用后将使用本地临时数据处理策略 """
    LOCAL_DEBUG_SAVE_LEVEL = False
    """ 调试模式下是否保存数据到存档 """
    LOCAL_DEBUG_FORCE_SIMULATION_UID = 0
    """ 若非0 调试模式下将强制模拟该UID """
    LOCAL_DEBUG_GLOBAL_DATAS = {}
    """ 调试模式下全局数据"""
    _LOCAL_DEBUG_DATAS = {}
    _LOCAL_DEBUG_ORDERS = {}

    def __init__(self):
        BaseService.__init__(self)
        self._lobbyEnvInitState = False
        """ 环境初始化状态 表示是否触发过网络游戏加入事件 """

    def onCreate(self):
        BaseService.onCreate(self)
        if not BaseLobbyManager.LOCAL_DEBUG_MODE or not BaseLobbyManager.LOCAL_DEBUG_SAVE_LEVEL:
            return
        # 调试模式 存档数据读取
        datasKey = "{}_LOCAL_DEBUG_DATAS".format(ModDirName)
        ordersKey = "{}_LOCAL_DEBUG_ORDERS".format(ModDirName)
        comp = serverApi.GetEngineCompFactory().CreateExtraData(levelId)
        saveDatas = comp.GetExtraData(datasKey)
        if saveDatas:
            BaseLobbyManager._LOCAL_DEBUG_DATAS = saveDatas
        saveOrders = comp.GetExtraData(ordersKey)
        if saveOrders:
            BaseLobbyManager._LOCAL_DEBUG_ORDERS = saveOrders
    
    def onServiceStop(self):
        BaseService.onServiceStop(self)
        if not BaseLobbyManager.LOCAL_DEBUG_MODE or not BaseLobbyManager.LOCAL_DEBUG_SAVE_LEVEL:
            return
        # 调试模式 存档数据保存
        datasKey = "{}_LOCAL_DEBUG_DATAS".format(ModDirName)
        ordersKey = "{}_LOCAL_DEBUG_ORDERS".format(ModDirName)
        comp = serverApi.GetEngineCompFactory().CreateExtraData(levelId)
        comp.SetExtraData(datasKey, BaseLobbyManager._LOCAL_DEBUG_DATAS, False)
        comp.SetExtraData(ordersKey, BaseLobbyManager._LOCAL_DEBUG_ORDERS, True)

    def getLobbyEnvState(self):
        """ 获取联机大厅环境状态 """
        return self._lobbyEnvInitState

    @staticmethod
    def GET_PLAYER_UID(playerId):
        # type: (str) -> int
        """ 获取玩家的uid """
        if BaseLobbyManager.LOCAL_DEBUG_MODE:
            if BaseLobbyManager.LOCAL_DEBUG_FORCE_SIMULATION_UID:
                return BaseLobbyManager.LOCAL_DEBUG_FORCE_SIMULATION_UID
            return int(playerId)
        comp = serverApi.GetEngineCompFactory().CreateHttp(levelId)
        return comp.GetPlayerUid(playerId)

    @staticmethod
    def GET_DEBUG_ENTITY_DATAS(uid):
        # type: (int) -> dict
        if not uid in BaseLobbyManager._LOCAL_DEBUG_DATAS:
            BaseLobbyManager._LOCAL_DEBUG_DATAS[uid] = dict()
        return BaseLobbyManager._LOCAL_DEBUG_DATAS[uid]

    @staticmethod
    def LOBBY_GET_STORAGE(uid, keys, callback):
        # type: (int, list[str], function) -> None
        """ 获取存储的数据 """
        if BaseLobbyManager.LOCAL_DEBUG_MODE:
            dataMap = BaseLobbyManager.GET_DEBUG_ENTITY_DATAS(uid)
            TRY_EXEC_FUN(callback, {"entity": {
                "data": deepcopy([{"key": k, "value": dataMap[k]} for k in keys if k in dataMap])
            }})
            return
        comp = serverApi.GetEngineCompFactory().CreateHttp(levelId)
        comp.LobbyGetStorage(callback, uid, keys)

    @staticmethod
    def LOBBY_GET_STORAGE_BY_SORT(key, length, callback, ascend=False, offset=0):
        # type: (str, int, function, bool, int) -> None
        """ 排序获取存储的数据 仅联机大厅可用(length单次请求至多50个数量) """
        comp = serverApi.GetEngineCompFactory().CreateHttp(levelId)
        comp.LobbyGetStorageBySort(callback, key, ascend, offset, length)

    @staticmethod
    def LOBBY_SET_STORAGE_AND_USER_ITEM(uid, callback, orderId=None, entitiesGetter=None):
        # type: (int, function, int | None, function | None) -> None
        """ 设置订单已发货或者存数据 """
        if BaseLobbyManager.LOCAL_DEBUG_MODE:
            if not orderId is None:
                orderMap = BaseLobbyManager._DEBUG_GET_PLAYER_ORDERS_MAP(uid)
                if orderId in orderMap:
                    del orderMap[orderId]
                    print("[DEBUG] 模拟订单发货成功 {}".format(orderId))
                else:
                    print("[ERROR][DEBUG] 模拟订单发货失败 {}".format(orderId))
            dataMap = BaseLobbyManager.GET_DEBUG_ENTITY_DATAS(uid)
            if entitiesGetter:
                dataList = entitiesGetter()
                for data in dataList:
                    key = data["key"]
                    value = data["value"]
                    dataMap[key] = value
            TRY_EXEC_FUN(callback, {
                "code": 0,
                "message": "ok",
                "entity": {
                    "data": deepcopy([{"key": k, "value": v} for k, v in dataMap.items()])
                }
            })
            return
        comp = serverApi.GetEngineCompFactory().CreateHttp(levelId)
        comp.LobbySetStorageAndUserItem(callback, uid, orderId, entitiesGetter)

    @staticmethod
    def LOBBY_QUERY_USER_ITEM(uid, callback):
        # type: (int, function) -> None
        """ 查询还没发货的订单 """
        if BaseLobbyManager.LOCAL_DEBUG_MODE:
            data = {
                "entity": {
                    "orders": list(BaseLobbyManager._DEBUG_GET_PLAYER_ORDERS_MAP(uid).values())
                }
            }
            TRY_EXEC_FUN(callback, data)
            return
        comp = serverApi.GetEngineCompFactory().CreateHttp(levelId)
        comp.QueryLobbyUserItem(callback, uid)

    @staticmethod
    def _DEBUG_GET_PLAYER_ORDERS_MAP(uid):
        # type: (int) -> dict
        """ DEBUG模拟获取玩家的订单数据 """
        if not BaseLobbyManager.LOCAL_DEBUG_MODE:
            return dict()
        if not uid in BaseLobbyManager._LOCAL_DEBUG_ORDERS:
            BaseLobbyManager._LOCAL_DEBUG_ORDERS[uid] = dict()
        return BaseLobbyManager._LOCAL_DEBUG_ORDERS[uid]

    @staticmethod
    def _DEBUG_CREATE_UID_ORDER(uid, orderId=-1, cmd="", productCount=1):
        # type: (int, int, str, int) -> None
        """ [内部实现] 模拟创建UID订单 仅在DEBUG模式下生效 否则什么也不会发生 """
        from time import time
        orderMap = BaseLobbyManager._DEBUG_GET_PLAYER_ORDERS_MAP(uid)
        orderMap[orderId] = {
            "order_id": orderId,
            "timestamp": time(),
            "cmd": cmd,
            "product_count": productCount
        }

    @staticmethod
    def DEBUG_CREATE_PLAYER_ORDER(playerId, cmd="", productCount=1, orderId=None):
        # type: (str, str, int, int | None) -> bool
        """ 模拟创建玩家订单 仅在DEBUG模式下生效 否则什么也不会发生 """
        if not BaseLobbyManager.LOCAL_DEBUG_MODE:
            return False
        if orderId is None:
            from random import randint
            orderId = randint(1000, 100000000)
        BaseLobbyManager._DEBUG_CREATE_UID_ORDER(BaseLobbyManager.GET_PLAYER_UID(playerId), orderId, cmd, productCount)
        serviceBroadcast(DebugStorePurchaseEvent(playerId))
        return True

    @BaseService.Listen("lobbyGoodBuySucServerEvent")
    def lobbyGoodBuySucServerEvent(self, args={}):
        """ 玩家登录联机大厅服务器, 或者联机大厅游戏内购买商品时触发 如果是玩家登录, 触发时玩家客户端已经触发了UiInitFinished事件 """
        eid = args["eid"]
        if args["buyItem"] == False:
            if not self._lobbyEnvInitState:
                self._lobbyEnvInitState = True
                TRY_EXEC_FUN(self.onLobbyEnvInit)
            self._onPlayerEnterGameSession(eid)
            return
        self._onLobbyStorePurchase(eid)

    @BaseService.ServiceListen(DebugStorePurchaseEvent)
    def _onDebugStorePurchase(self, data=DebugStorePurchaseEvent()):
        # 模拟订单发货事件
        self.lobbyGoodBuySucServerEvent({"eid": data.playerId, "buyItem": True})

    @BaseService.Listen("AddServerPlayerEvent")
    def AddServerPlayerEvent(self, args={}):
        if not BaseLobbyManager.LOCAL_DEBUG_MODE:
            return
        playerId = args["id"]
        # 本地调试模式下模拟事件触发
        self.lobbyGoodBuySucServerEvent({"eid": playerId, "buyItem": False})

    def _onPlayerEnterGameSession(self, playerId):
        # 玩家加入网络游戏
        comp = self.__class__._BIND_LOBBY_PLAYER_COMP()
        self._playerCompInitHook(comp)
        comp.bind(playerId)
        self.getPlayerComp(playerId).asyncUpdateStorage()
        self.onPlayerEnterGameSession(playerId)

    def _playerCompInitHook(self, comp):
        # type: (LobbyPlayerComp) -> None
        comp._automatedOrderProcHook = self.onPlayerAutomatedOrderProc

    def _onLobbyStorePurchase(self, playerId):
        # 玩家购买商品
        comp = self.getPlayerComp(playerId)
        if comp:
            TRY_EXEC_FUN(comp._onLobbyStorePurchase)
        self.onLobbyStorePurchase(playerId)
    
    def getPlayerComp(self, playerId):
        """ 获取玩家逻辑组件 """
        return self._BIND_LOBBY_PLAYER_COMP.getComp(playerId)

    def getPlayerUid(self, playerId):
        """ 获取玩家的UID数据 """
        return self.getPlayerComp(playerId).getUid()

    def onPlayerEnterGameSession(self, playerId):
        """ 玩家加入大厅游戏完毕时触发 """
        pass

    def onLobbyStorePurchase(self, playerId):
        """ 玩家在局内购买物品触发 """
        pass

    def onLobbyEnvInit(self):
        """ 联机大厅环境初始化时触发(至少一个玩家加入时) """
        pass

    def callPlayerAutomatedOrder(self, playerId, automaticShipping=True):
        """ 主动调用订单处理请求 """
        self.getPlayerComp(playerId)._callAutomatedOrder(automaticShipping)

    def onPlayerAutomatedOrderProc(self, playerId, info=OrderINFO()):
        """ 玩家订单逻辑处理时触发可在此处处理订单响应亦或者在组件类中重写实现 """
        pass

class QuickLobbyPlayerComp(LobbyPlayerComp):
    """ 快速联机大厅玩家数据管理组件 """
    MMP_ERROR_MSG = "内存映射数据未完全初始化"
    def __init__(self):
        LobbyPlayerComp.__init__(self)
        self._memoryMap = dict()
        self._dataInitState = False
        self.mmpNeedUpdate = False
        self.mmUpdateHandler = lambda _: None

    def _initMemoryMap(self, dic={}):
        # type: (dict) -> None
        self._memoryMap = dic
        self.userTargetKeyDatas = list(dic.keys())

    def onFirstDataUpdate(self):
        LobbyPlayerComp.onFirstDataUpdate(self)
        for k, v in self._firstCacheData.items():
            self._memoryMap[k] = v
        self._dataInitState = True
        if self._memoryMap:
            self.mmpNeedUpdate = True

    def getMemoryValue(self, key, nullValue=None):
        """ 获取内存数据 """
        if not self._dataInitState:
            raise RuntimeError(QuickLobbyPlayerComp.MMP_ERROR_MSG)
        return self._memoryMap.get(key, nullValue)

    def setMemoryValue(self, key, value):
        """ 设置内存数据 (由于内部缓存机制影响 若直接修改MAP引用对象数据如容器 则不会触发更新 需要使用asyncMemoryKey更新) """
        if not self._dataInitState:
            raise RuntimeError(QuickLobbyPlayerComp.MMP_ERROR_MSG)
        if key in self._memoryMap:
            if value == self._memoryMap[key]:
                return
        self._memoryMap[key] = value
        self.lazyWriteData(key, value)
        self.mmpNeedUpdate = True

    def changeMemoryValue(self, key, changeFunc=lambda _: None):
        """ 改变内存数据 (基于lambda表达式) """
        if not self._dataInitState:
            raise RuntimeError(QuickLobbyPlayerComp.MMP_ERROR_MSG)
        if not key in self._memoryMap:
            raise RuntimeError("内存映射数据不存在, key: {}".format(key))
        value = self._memoryMap[key]
        self._memoryMap[key] = changeFunc(value)
        self.asyncMemoryKey(key)

    def asyncMemoryKey(self, key):
        """ 声明需要异步同步的Key (当直接操作原始缓存对象时需要显性调用该方法) """
        if not self._dataInitState:
            raise RuntimeError(QuickLobbyPlayerComp.MMP_ERROR_MSG)
        if not key in self._memoryMap:
            return
        self.lazyWriteData(key, self._memoryMap[key])
        self.mmpNeedUpdate = True

    def asyncAllMemoryDatas(self):
        """ 声明需要异步更新所有缓存数据 """
        if not self._dataInitState:
            raise RuntimeError(QuickLobbyPlayerComp.MMP_ERROR_MSG)
        for key, value in self._memoryMap.items():
            self.lazyWriteData(key, value)
        self.mmpNeedUpdate = True

    def update(self):
        LobbyPlayerComp.update(self)
        if self.mmpNeedUpdate:
            self.mmpNeedUpdate = False
            self.onMmpUpdate()

    def getAllMmpData(self):
        return self._memoryMap

    def onMmpUpdate(self):
        self.mmUpdateHandler(self.entityId)

    def onUnBind(self):
        LobbyPlayerComp.onUnBind(self)
        self.mmUpdateHandler = lambda _: None

class QuickLobbyManager(BaseLobbyManager[QuickLobbyPlayerComp]):
    """ 快速联机大厅管理器 (大量使用内存交换操作 更加高效易用)
        #### 直接使用(简单业务)
        ```
        class MyManager(QuickLobbyManager):
            pass
        ```
        #### 模板特化(复杂业务)
        ```
        @QuickLobbyManager.Init
        class MyManager(QuickLobbyManager[YourComp]):
            pass
        ```
        使用该管理器需要重写initMemoryMap方法返回默认数据表
    """
    def __init__(self):
        BaseLobbyManager.__init__(self)
        self._globalMemoryMap = {}
        self._globalDataRPCInit = False

    def onCreate(self):
        BaseLobbyManager.onCreate(self)
        debugMode = BaseLobbyManager.LOCAL_DEBUG_MODE
        if debugMode and BaseLobbyManager.LOCAL_DEBUG_GLOBAL_DATAS:
            # 调试模式下使用本地模拟的全局数据
            self._globalMemoryMap = BaseLobbyManager.LOCAL_DEBUG_GLOBAL_DATAS
            return
        self._globalMemoryMap = self.initGlobalMemoryMap()
        if debugMode or not self._globalMemoryMap:
            return
        # 非DEBUG模式 远程请求后台全局数据
        def _callBack(datas):
            # type: (dict | None) -> None
            self._globalDataRPCInit = True
            if datas:
                for k, v in ((v["key"], v["value"]) for v in datas["entity"]["data"]):
                    if k == "op_config" and isinstance(v, dict):
                        for opKey, opValue in v.items():
                            self._globalMemoryMap[opKey] = opValue
            else:
                raise RuntimeError("全局数据获取失败, 请检查参数配置")
        BaseLobbyManager.LOBBY_GET_STORAGE(0, ["op_config"], _callBack)

    def initMemoryMap(self):
        # type: () -> dict
        """ 初始化内存映射表(适用于分配用户数据) """
        return {}

    def initGlobalMemoryMap(self):
        # type: () -> dict
        """ 初始化全局内存映射表(适用于分配全局数据)
        备注：
            - 用于初始化全局共享的数据结构。
            - 返回值应为 dict 类型。
        """
        return {}

    def getGlobalDataMap(self):
        # type: () -> dict
        """ 获取全局数据表(只读) """
        return self._globalMemoryMap

    def _playerCompInitHook(self, comp):
        # type: (QuickLobbyPlayerComp) -> None
        BaseLobbyManager._playerCompInitHook(self, comp)
        comp._initMemoryMap(copy(self.initMemoryMap()))
        comp.mmUpdateHandler = self.onPlayerMmpUpdate

    def getPlayerComp(self, playerId):
        # type: (str) -> QuickLobbyPlayerComp
        """ 获取玩家逻辑组件 """
        return BaseLobbyManager.getPlayerComp(self, playerId)

    def getPlayerMMPData(self, playerId, key, nullValue=None):
        """ 获取指定玩家的MMP数据 """
        return self.getPlayerComp(playerId).getMemoryValue(key, nullValue)

    def setPlayerMMPData(self, playerId, key, value):
        """ 设置指定玩家的MMP数据 """
        return self.getPlayerComp(playerId).setMemoryValue(key, value)

    def changePlayerMMPData(self, playerId, key, changeFunc=lambda v: v):
        """ 基于lambda表达式修改指定玩家的MMP数据 """
        return self.getPlayerComp(playerId).changeMemoryValue(key, changeFunc)

    def getPlayerAllMMPData(self, playerId):
        """ 获取玩家所有的MMP数据 """
        return self.getPlayerComp(playerId).getAllMmpData()

    def updatePlayerMMPKey(self, playerId, key):
        """ 更新玩家特定的MMP Key(当直接修改map的引用对象时需要手动调用该方法而不是setPlayerMMPData) """
        return self.getPlayerComp(playerId).asyncMemoryKey(key)

    def onPlayerMmpUpdate(self, playerId):
        """ 玩家MMP数据更新时触发 """
        pass