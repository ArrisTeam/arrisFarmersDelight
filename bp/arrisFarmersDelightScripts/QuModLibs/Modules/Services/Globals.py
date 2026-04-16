# -*- coding: utf-8 -*-
from ...Util import TRY_EXEC_FUN, errorPrint
from ..Utils.AutoExpiringObjects import QTimedExpiryMap
from copy import copy
from time import time
lambda: "By Zero123 CREATE_TIME: 2024_04_20 LAST_UPDATE_TIME: 2025_4_18"

class ContextNode:
    """ 上下文节点 记录了LifecycleBind加载时的上下文信息 """
    def __init__(self, contextNode, funObj):
        # type: (object, function) -> None
        self.contextNode = contextNode
        self.funObj = funObj

class SERContextNode(ContextNode):
    """ 服务上下文节点 记录了LifecycleBind加载时的上下文信息 """
    def __init__(self, contextNode, funObj):
        # type: (_BaseService | BaseBusiness | object, function) -> None
        ContextNode.__init__(self, contextNode, funObj)
        self._baseService = contextNode

class LifecycleBind:
    """ 生命周期绑定 通常与服务注解搭配 """
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self._onLoad = lambda _: None
        self._onUnLoad = lambda _: None
    
    def onLoad(self, nodeSelf):
        # type: (ContextNode) -> None
        return TRY_EXEC_FUN(lambda: self._onLoad(nodeSelf))

    def onUnLoad(self, nodeSelf):
        # type: (ContextNode) -> None
        return TRY_EXEC_FUN(lambda: self._onUnLoad(nodeSelf))
    
    @classmethod
    def ON_ALL_LOAD(cls, nodeSelf):
        # type: (ContextNode) -> None
        """ 当服务中的所有注解处理加载完毕 服务中此处的nodeSelf无法拿到funObj """
        pass

    @classmethod
    def ON_ALL_OFF_LOAD(cls, nodeSelf):
        # type: (ContextNode) -> None
        """ 当服务中的所有注解处理取消加载完毕 服务中此处的nodeSelf无法拿到funObj """
        pass

    @classmethod
    def creatAnnotation(cls):
        """ 基于当前cls创建一个注解 """
        def _zj(*args, **kwargs):
            def _zsq(funObj):
                setattr(funObj, _BaseService.LIFECYCLEBIND_DATA_KEY, cls(*args, **kwargs))
                return funObj
            return _zsq
        return _zj

    @classmethod
    def creatAnnotationObj(cls, *args, **kwargs):
        """ 基于当前cls创建一个注解执行对象 """
        def _zsq(funObj):
            setattr(funObj, _BaseService.LIFECYCLEBIND_DATA_KEY, cls(*args, **kwargs))
            return funObj
        return _zsq

class ListenData(LifecycleBind):
    def __init__(self, eventName = ""):
        LifecycleBind.__init__(self)
        self.eventName = eventName

    def onLoad(self, nodeSelf):
        # type: (SERContextNode) -> None
        return nodeSelf._baseService.listenForEvent(self.eventName, nodeSelf.funObj)

    def onUnLoad(self, nodeSelf):
        # type: (SERContextNode) -> None
        return nodeSelf._baseService.unListenForEvent(self.eventName, nodeSelf.funObj)

class LoopTimerData(LifecycleBind):
    def __init__(self, callTime = 0.1):
        LifecycleBind.__init__(self)
        self.callTime = callTime

    def onLoad(self, nodeSelf):
        # type: (ContextNode) -> None
        contextNode = nodeSelf.contextNode
        if isinstance(contextNode, TimerLoader):
            contextNode.addTimer(_BaseService.Timer(nodeSelf.funObj, loop=True, time=self.callTime))

class ServiceListenData(LifecycleBind):
    def __init__(self, eventCls, priority = None):
        # type: (type[BaseEvent], int | None) -> None
        LifecycleBind.__init__(self)
        self.eventCls = eventCls
        self.priority = priority

    def onLoad(self, nodeSelf):
        # type: (SERContextNode) -> None
        sharedArgs = nodeSelf._baseService._sharedArgs
        key = self.__class__.__name__
        if not key in sharedArgs:
            sharedArgs[key] = []
        data = sharedArgs[key]  # type: list
        data.append((self.eventCls, nodeSelf.funObj, self.priority))

    @classmethod
    def ON_ALL_LOAD(cls, nodeSelf):
        # type: (SERContextNode) -> None
        """ 当服务中的所有注解处理加载完毕 此处的nodeSelf无法拿到funObj """
        _this = nodeSelf._baseService
        sharedArgs = _this._sharedArgs
        key = cls.__name__
        if not key in sharedArgs:
            return
        data = sharedArgs[key]  # type: list[tuple[type[BaseEvent], object, int | None]]
        for eventCls, funObj, priority in data:
            _this._serviceListen(eventCls, funObj, priority)

    @classmethod
    def ON_ALL_OFF_LOAD(cls, nodeSelf):
        # type: (SERContextNode) -> None
        """ 当服务中的所有注解处理取消加载完毕 此处的nodeSelf无法拿到funObj """
        _this = nodeSelf._baseService
        sharedArgs = _this._sharedArgs
        key = cls.__name__
        if not key in sharedArgs:
            return
        data = sharedArgs[key]  # type: list[tuple[type[BaseEvent], object, int | None]]
        _this.SERVICELISTEN_OFF_ALL(data)

class QCustomAPI(LifecycleBind):
    """ 自定义API对象 """
    def __init__(self, apiPath = ""):
        LifecycleBind.__init__(self)
        self.apiPath = apiPath
        self._state = True

    def onLoad(self, nodeSelf):
        # type: (SERContextNode) -> None
        service = nodeSelf._baseService
        try:
            service.getManager().regAPI(self.apiPath, nodeSelf.funObj)
        except Exception:
            self._state = False
            import traceback
            traceback.print_exc()
        
    def onUnLoad(self, nodeSelf):
        # type: (SERContextNode) -> None
        if self._state:
            service = nodeSelf._baseService
            service.getManager().removeAPI(
                self.apiPath
            )

class IService:
    def getID(self):
        """ 获取服务ID """

    def _onCreate(self):
        """ 内部服务创建成功事件 """

    def onCreate(self):
        """ 服务创建成功事件 """

    def _onTick(self):
        """ 内部调度Tick事件 """

    def _onRemove(self):
        """ 内部调度 服务销毁触发 """
    
    def onAccessed(self):
        """ 当前服务通过access获取时触发 """

    def onServiceUpdate(self):
        """ 服务更新事件 """
    
    def onServiceStopBefore(self):
        """ 服务停用之前触发 此时并未触发回收业务 """
    
    def onServiceStop(self):
        """ 服务停用事件 """

    def stopSelf(self):
        """ 关闭自我服务 """
    
    @classmethod
    def getUID(cls):
        """ 获取服务类识别标识符 """

class BaseTimer:
    """ 定时器 """
    def __init__(self, callObject, argsTuple = tuple(), kwargsDict = dict(), time = 0.0, loop = False):
        # type: (object, tuple, dict, float, bool) -> None
        self.callObject = callObject
        self.argsTuple = argsTuple
        self.kwargsDict = kwargsDict
        self.loop = loop
        self.setTime = time
        self.valueTime = time
        self._cacheUpdateTime = 0.0

    def call(self):
        TRY_EXEC_FUN(lambda: self.callObject(*self.argsTuple, **self.kwargsDict))

    def copy(self):
        # type: () -> _BaseService.Timer
        """ 拷贝定时器 """
        return self.__class__(self.callObject, self.argsTuple, self.kwargsDict, self.setTime, self.loop)

    def rest(self):
        """ 重置定时 """
        self.valueTime = self.setTime

class BaseEvent:
    """ 基本事件类 """
    def __init__(self):
        self._T_FROM_SERVICE = None     # type: _BaseService | None
        """ 临时属性 记录事件广播来源服务实例 在广播完毕后会归为None防止互相引用产生的内存泄漏 """
        self._T_CONTEXT_INDEX = 0       # type: int
        """ 临时属性 上下文索引 通常表示目标服务是第几个收到事件的 """

    @classmethod
    def getEngineKey(cls):
        return str(cls)
    
    @classmethod
    def getData(cls, _data):
        if isinstance(_data, cls):
            return _data
        return None

class QRequests:
    SUCCESS = 200
    CAN_NOT_FIND = 404
    SERVER_ERROR = 500
    class RequestResults:
        """ 请求结果"""
        def __init__(self, state = 0, _returnData = None, sTime = None):
            # type: (int, object | None, float | None) -> None
            self.state = state
            self.data = _returnData
            self.success = self.state == QRequests.SUCCESS
            """ 是否成功 """
            self.serviceTime = sTime
            """ 来自服务完成的时间 """
            if sTime == None:
                self.serviceTime = time()
        
        def dumps(self):
            return {
                "s": self.state,
                "d": self.data,
                "t": self.serviceTime
            }

        @classmethod
        def loads(cls, _dic):
            # type: (dict) -> QRequests.RequestResults
            return cls(_dic["s"], _dic["d"], _dic["t"])
    
    class Args:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs
            self._callBack = None
            # ======== 前参与后参 ========
            self.preParam = ""      # 通常代表是服务端发送到指定客户端的id
            self.postParam = ""     # 通常代表是客户端请求回调服务端的携带id
        
        def setCallBack(self, funObj = lambda *_: None):
            """ 设置回调函数 """
            self._callBack = funObj
            return self
        
        def getCallBackId(self):
            return str(id(self._callBack))

class _ServiceManager:
    """ 服务管理器 """
    SERVICE_CALL_KEY = "QServiceManager.CALL"
    SERVICE_CALLBAK_KEY = "QServiceManager.CALL_BACK"
    class PRIORITY_FUN_DATA:
        def __init__(self, funObj, priority = None):
            self.funObj = funObj
            self.priority = priority if priority != None else 10000

    def __init__(self, 
            _listenForEvent = lambda *_:None,
            _unListenForEvent = lambda *_:None,
            _callFun = lambda *_: None,
            _regCallFun = lambda *_: None
        ):
        self._closeState = False
        self._listenForEvent = _listenForEvent
        self._unListenForEvent = _unListenForEvent
        self._callFun = _callFun
        self._regCallFun = _regCallFun
        self._serviceMap = {}       # type: dict[str, _BaseService]
        self._eventMap = {}         # type: dict[str, list[_ServiceManager.PRIORITY_FUN_DATA]]
        self._waitUpdateEventCls = set()
        self._apiMap = {}                           # type: dict[str, object]
        self.apiCallBackMap = QTimedExpiryMap()
        self._initManager()

    def _initManager(self):
        """ 初始化管理器业务 注册Call监听之类的操作 """
        self._regCallFun(_ServiceManager.SERVICE_CALL_KEY, self._recv)
        self._regCallFun(_ServiceManager.SERVICE_CALLBAK_KEY, self._recvCallBack)

    def _recvCallBack(self, _id, dataDict):
        """ 接收CallBack回调 """
        funObj = self.apiCallBackMap.get(_id, refresh=False)
        self.apiCallBackMap.remove(_id)
        if not funObj:
            errorPrint("超时/异常丢失回调记录: {}".format(_id))
            return
        results = QRequests.RequestResults.loads(dataDict)
        TRY_EXEC_FUN(funObj, results)
    
    def _recv(self, apiPath = "", _id = "", _postParam = "", *args, **kwargs):
        """ 接收Call请求处理 """
        results = self.localRequest(apiPath, *args, **kwargs)
        if not _id:
            return
        # 存在回调函数 需要将计算结果发送回去
        if _postParam:
            # 后置参数追加 通常是服务端重新打包发回客户端
            self._callFun(_postParam, _ServiceManager.SERVICE_CALLBAK_KEY, _id, results.dumps())
            return
        self._callFun(_ServiceManager.SERVICE_CALLBAK_KEY, _id, results.dumps())

    def _serviceCall(self, *args, **kwargs):
        """ 服务Call """
        self._callFun(*args, **kwargs)

    def regAPI(self, apiPath = "", callFun = lambda *_: None):
        """ 注册API """
        if apiPath in self._apiMap:
            raise Exception("API: {} 已存在 请勿重新注册".format(apiPath))
        self._apiMap[apiPath] = callFun

    def removeAPI(self, apiPath = ""):
        """ 删除已注册的API """
        del self._apiMap[apiPath]

    def safeGetAPI(self, apiPath = "", noneApi = lambda *_: None):
        """ 安全的获取API对象 """
        if not self.hasAPI(apiPath):
            return noneApi
        return self.getAPI(apiPath)

    def getAPI(self, apiPath = ""):
        """ 获取API对象 """
        return self._apiMap[apiPath]

    def hasAPI(self, apiPath = ""):
        """ 获取指定API是否存在 """
        return apiPath in self._apiMap
    
    def localRequest(self, apiPath = "", *args, **kwargs):
        """ 本地请求 """
        if not self.hasAPI(apiPath):
            errorPrint("请求的资源不存在: {}".format(apiPath))
            return QRequests.RequestResults(
                QRequests.CAN_NOT_FIND, None
            )
        try:
            return QRequests.RequestResults(
                QRequests.SUCCESS, self.getAPI(apiPath)(*args, **kwargs)
            )
        except Exception:
            import traceback
            traceback.print_exc()
            return QRequests.RequestResults(
                QRequests.SERVER_ERROR, None
            )
    
    def syncRequest(self, apiPath = "", argsObject = QRequests.Args()):
        # type: (str, QRequests.Args) -> None
        """ 同步请求 """
        _id = ""
        if argsObject._callBack:
            # 存在回调响应
            _id = argsObject.getCallBackId()
            self.apiCallBackMap.save(_id, argsObject._callBack)
        if argsObject.preParam:
            # 存在前置参数(这通常是服务端发包客户端的指定玩家id)
            self._serviceCall(argsObject.preParam, _ServiceManager.SERVICE_CALL_KEY, apiPath, _id, argsObject.postParam, *argsObject.args, **argsObject.kwargs)
            return
        self._serviceCall(_ServiceManager.SERVICE_CALL_KEY, apiPath, _id, argsObject.postParam, *argsObject.args, **argsObject.kwargs)

    def asyncRequest(self, apiPath = "", argsObject = QRequests.Args()):
        # type: (str, QRequests.Args) -> None
        """ [暂未实现] 异步请求 """
        pass
    
    def broadcast(self, eventObj):
        # type: (BaseEvent) -> None
        """ 事件广播 """
        key = eventObj.__class__.getEngineKey()
        if not key in self._eventMap:
            return
        for callObj in copy(self._eventMap[key]):
            TRY_EXEC_FUN(callObj.funObj, eventObj)
            eventObj._T_CONTEXT_INDEX += 1

    def serviceListen(self, eventCls, callObj, priority = None):
        # type: (type[BaseEvent], object, int | None) -> None
        """ 服务监听
            允许设置优先级 考虑性能优化问题优先级设置后并不会立即刷新而是在下一帧统一更新
            如需要立即刷新 请调用SERVICELISTEN_PRIORITYSORT方法
        """
        key = eventCls.getEngineKey()
        PRIORITY_FUN = _ServiceManager.PRIORITY_FUN_DATA(callObj, priority)
        if not key in self._eventMap:
            self._eventMap[key] = []
        self._eventMap[key].append(PRIORITY_FUN)
        if priority != None and not key in self._waitUpdateEventCls:
            self._waitUpdateEventCls.add(key)

    def unServiceListen(self, eventCls, callObj):
        # type: (type[BaseEvent], object) -> None
        """ 单次取消服务监听 如需批量处理请使用 SERVICELISTEN_OFF_ALL 方法 """
        return self.SERVICELISTEN_OFF_ALL([(eventCls, callObj)])

    def SERVICELISTEN_OFF_ALL(self, dataIt):
        # type: (list[tuple[type[BaseEvent], object]] | tuple[tuple[type[BaseEvent], object]]) -> None
        """ 批量取消服务监听 """
        if self._closeState or not dataIt:
            return
        removeMap = {}          # type: dict[str, set[object]]
        for tupData in dataIt:
            # 统计所有待移除的执行对象以及KEY
            eventCls = tupData[0]
            callObj = tupData[1]
            key = eventCls.getEngineKey()
            if not key in removeMap:
                removeMap[key] = set()
            removeMap[key].add(callObj)
        for removeKey, removeSet in removeMap.items():
            # 处理所有相关key表
            if not removeKey in self._eventMap:
                continue
            # 重新构造event监听列表
            self._eventMap[removeKey] = [
                x for x in self._eventMap[removeKey] if not x.funObj in removeSet
            ]

    def SERVICELISTEN_PRIORITYSORT(self, eventKey):
        # type: (str) -> None
        """ 重新排序服务监听 """
        if eventKey in self._waitUpdateEventCls:
            self._waitUpdateEventCls.remove(eventKey)
        if not eventKey in self._eventMap:
            return
        self._eventMap[eventKey].sort(key = lambda obj: obj.priority)

    def listenForEvent(self, eventName, parent, funObj):
        return self._listenForEvent(eventName, parent, funObj)

    def unListenForEvent(self, eventName, parent, funObj):
        return self._unListenForEvent(eventName, parent, funObj)

    def onTick(self):
        for obj in self._serviceMap.values():
            TRY_EXEC_FUN(obj._onTick)
        if len(self._waitUpdateEventCls) > 0:
            for key in self._waitUpdateEventCls.copy():
                self.SERVICELISTEN_PRIORITYSORT(key)
            self._waitUpdateEventCls.clear()

    def getService(self, _cls):
        # type: (type[_BaseService]) -> _BaseService | None
        return self._serviceMap.get(_cls.getUID(), None)

    def removeService(self, _cls):
        # type: (type[_BaseService]) -> bool
        _service = self.getService(_cls)
        if _service:
            del self._serviceMap[_cls.getUID()]
            TRY_EXEC_FUN(_service._onRemove)
            return True
        return False
    
    def removeAllService(self):
        for obj in self._serviceMap.values():
            TRY_EXEC_FUN(obj._onRemove)
        self._serviceMap = {}
        self._eventMap = {}
    
    def createService(self, _cls):
        # type: (type[_BaseService]) -> _BaseService
        _service = self.getService(_cls)
        if _service:
            return _service
        newObj = _cls()
        TRY_EXEC_FUN(newObj._onCreate)
        self._serviceMap[_cls.getUID()] = newObj
        return newObj

class AnnotationLoader:
    """ 注解加载器 """
    ANNOTATION_KEY = "__quAnnotation__"
    LIFECYCLEBIND_DATA_KEY = "__quLifecycleBind__"
    _GLOBAL_ANNOTATION_LOADER_CACHE = {}    # type: dict[type, list[str]]
    ANNOTATION_USE_CACHE = True
    """ 是否启用注解缓存 默认True 能够大幅度提升构造/销毁性能表现 弊端是热重载可能无法引入新增注解需重启游戏 """

    def _findAllAnnotationData(self):
        """ 匹配所有注解 """
        dirList = []    # type: list
        cacheList = []
        summonCache = False
        if self.__class__.ANNOTATION_USE_CACHE:
            if self.__class__ in AnnotationLoader._GLOBAL_ANNOTATION_LOADER_CACHE:
                # 引用缓存
                dirList = AnnotationLoader._GLOBAL_ANNOTATION_LOADER_CACHE[self.__class__]
            else:
                dirList = dir(self)
                summonCache = True
        else:
            dirList = dir(self)
        for k in dirList:
            v = getattr(self, k)    # type: object
            if hasattr(v, self.__class__.LIFECYCLEBIND_DATA_KEY):
                dataObj = getattr(v, self.__class__.LIFECYCLEBIND_DATA_KEY)   # type: LifecycleBind
                yield (v, dataObj)
                if summonCache:
                    cacheList.append(k)
        if summonCache:
            AnnotationLoader._GLOBAL_ANNOTATION_LOADER_CACHE[self.__class__] = cacheList

    def _loadAnnotation(self):
        """ 加载注解业务 """
        dataCls_Set = set()     # type: set[type[LifecycleBind]]
        for fun, data in self._findAllAnnotationData():
            data.onLoad(self._createContextNode(fun))
            if not data.__class__ in dataCls_Set:
                dataCls_Set.add(data.__class__)
        # 后置批处理
        _contextNode = self._createContextNode(None)
        for dataCls in dataCls_Set:
            dataCls.ON_ALL_LOAD(_contextNode)

    def _createContextNode(self, funObj):
        # type: (object) -> ContextNode
        """ 创建上下文节点 """
        return ContextNode(self, funObj)

    def _unLoadAnnotation(self):
        """ 停止注解业务 """
        dataCls_Set = set()     # type: set[type[LifecycleBind]]
        for fun, data in self._findAllAnnotationData():
            data.onUnLoad(self._createContextNode(fun))
            if not data.__class__ in dataCls_Set:
                dataCls_Set.add(data.__class__)
        # 后置批处理
        _contextNode = self._createContextNode(None)
        for dataCls in dataCls_Set:
            dataCls.ON_ALL_OFF_LOAD(_contextNode)

class SERAnnotationLoader(AnnotationLoader):
    """ 特化：服务/业务类注解加载器 """
    def _createContextNode(self, funObj):
        return SERContextNode(self, funObj)

class TimerLoader:
    """ 定时器加载器 """
    _TICK_TIME = 1.0 / 30.0
    def __init__(self):
        self.__timerSet = set()     # type: set[BaseTimer]

    class Timer(BaseTimer):
        """ 业务定时器 """
        pass

    def getTimerSetRef(self):
        return self.__timerSet
    
    def timerEmpty(self):
        return len(self.__timerSet) <= 0

    def _clearAllTimer(self):
        self.__timerSet.clear()

    def addTimer(self, timer):
        # type: (BaseTimer) -> bool
        """ 添加定时器 (同一份定时器不允许多次添加,如有需要可使用定时器的copy方法)
            由于服务的高性能需求 Timer采用集合储存 执行顺序无序
        """
        if timer in self.__timerSet:
            return False
        self.__timerSet.add(timer)
        return True
    
    def removeTimer(self, timer):
        # type: (BaseTimer) -> bool
        """ 删除定时器 """
        if not timer in self.__timerSet:
            return False
        self.__timerSet.remove(timer)
        return True
    
    def _timerUpdate(self, updateTime=0.033):
        """ 定时器更新 """
        if not self.__timerSet:
            return
        # timer定时任务处理
        delTimerList = []         # type: list[BaseTimer]
        callTimers = []           # type: list[BaseTimer]
        for timer in self.__timerSet:
            timer.valueTime -= updateTime
            if timer.valueTime > 0.0:
                continue
            timer._cacheUpdateTime = timer.valueTime
            callTimers.append(timer)
            if not timer.loop:
                # 标记删除定时器
                delTimerList.append(timer)
            else:
                # 重置定时器
                timer.valueTime = timer.setTime
        # 删除定时器
        for timer in delTimerList:
            self.removeTimer(timer)
        # 调用触发定时器 (重新排序实现先后执行关系)
        callTimers.sort(key=lambda v: v._cacheUpdateTime)
        for callTimerObj in callTimers:
            callTimerObj.call()

class BaseBusiness(SERAnnotationLoader, TimerLoader):
    """ 基本业务类 """
    @staticmethod
    def Listen(eventName):
        """ [注解] 系统监听 """
        return ListenData.creatAnnotationObj(eventName)

    def _onCreate(self):
        self._loadAnnotation()
        TRY_EXEC_FUN(self.onCreate)

    def _onCreateError(self):
        """ 业务构建异常触发 默认提供注解反加载处理如需重写请确保此处正确回收资源 """
        self._unLoadAnnotation()
    
    def _onRemove(self):
        TRY_EXEC_FUN(self.onStopBefore)
        self._unLoadAnnotation()
        self.onStop()
        self._parentObj = None

    def __init__(self):
        TimerLoader.__init__(self)
        self._sharedArgs = {}
        self._parentObj = None    # type: _BaseService | None
    
    def listenForEvent(self, eventName, eventFun):
        return self.getParentService()._defaultListenForEvent(eventName, self, eventFun)

    def unListenForEvent(self, eventName, eventFun):
        return self.getParentService()._defaultUnListenForEvent(eventName, self, eventFun)
    
    def _onTick(self):
        self._timerUpdate()
        self.onTick()
    
    def _onReceiveServiceEvents(self, eventObj):
        # type: (BaseEvent) -> None
        """ 接收到服务事件 """
        pass
    
    def onTick(self):
        """ 业务期间每tick触发 """
        pass

    def onCreate(self):
        """ 业务构建成功触发 """
        pass

    def onStopBefore(self):
        """ 业务终止之前触发 """
        pass

    def onStop(self):
        """ 业务终止触发 """
        pass

    def getParentService(self):
        # type: () -> _BaseService | None
        """ 获取父类服务对象 """
        return self._parentObj

    def stopBusiness(self):
        """ 终止自我业务 """
        self.getParentService().removeBusiness(self)

class KeyBusiness(BaseBusiness):
    """ 键位业务
        使用该业务实现的业务在构建时将会在服务的共享参数中写入相关字典以便查询
    """
    DIC_KEY = "KeyBusiness_MAP"
    def __init__(self, key = ""):
        BaseBusiness.__init__(self)
        self.useKey = key
    
    def onCreate(self):
        self.onCreate(self)
        self._writeKey()
    
    def _onCreateError(self):
        BaseBusiness._onCreateError(self)
        self._delKey()

    def onStop(self):
        BaseBusiness.onStop(self)
        self._delKey()
    
    def getServiceDataDic(self):
        # type: () -> dict[str, KeyBusiness]
        parentObj = self.getParentService()
        dicKey = self.__class__.DIC_KEY
        if not dicKey in parentObj._sharedArgs:
            parentObj._sharedArgs[dicKey] = {}
        return parentObj._sharedArgs[dicKey]

    def _writeKey(self):
        dicData = self.getServiceDataDic()
        dicData[self.useKey] = self

    def _delKey(self):
        dicData = self.getServiceDataDic()
        if self.useKey in dicData:
            del dicData[self.useKey]

class _BaseService(IService, SERAnnotationLoader, TimerLoader):
    _BINDMANAGER = None     # type: _ServiceManager | None
    _CLOSE_STATE = False
    @staticmethod
    def Listen(eventName):
        """ [注解] 系统监听 """
        return ListenData.creatAnnotationObj(eventName)

    @staticmethod
    def REG_API(apiPath=""):
        """ [注解] 注册服务API """
        return QCustomAPI.creatAnnotationObj(apiPath)

    @staticmethod
    def ServiceListen(eventCls, priority = None):
        """ [注解] 服务私有监听 """
        return ServiceListenData.creatAnnotationObj(eventCls, priority)
    
    @staticmethod
    def LoopTimer(time = 0.1):
        """ [注解] 循环定时任务 """
        return LoopTimerData.creatAnnotationObj(time)
    
    @staticmethod
    def Init(clsObj):
        TRY_EXEC_FUN(clsObj.start)
        return clsObj

    @classmethod
    def getService(cls):
        """ 如果服务存在 返回服务实例 否则None """
        if 1 > 2:
            # Python2类型系统局限性 这段代码用于欺骗vscode给出正确提示
            return cls()
        return cls._BINDMANAGER.getService(cls)
    
    @classmethod
    def start(cls):
        """ 尝试启用服务 如果未启用 """
        if cls._CLOSE_STATE:
            return None
        if 1 > 2:
            # Python2类型系统局限性 这段代码用于欺骗vscode给出正确提示
            return cls()
        return cls._BINDMANAGER.createService(cls)

    @classmethod
    def stop(cls):
        """ 尝试停用服务 如果已启用 """
        return cls._BINDMANAGER.removeService(cls)
    
    @classmethod
    def access(cls):
        """ 服务访问 相比start将会触发一次访问事件可用于定时服务的自动销毁 """
        obj = cls.start()
        return obj.onAccessed()
    
    @classmethod
    def reload(cls):
        cls.stop()
        cls.start()

    @classmethod
    def getUID(cls):
        """ 获取服务类识别标识符 """
        clsPath = "{}::{}".format(cls.__module__, cls.__name__)
        return clsPath

    def getID(self):
        """ 获取服务ID """
        return id(self)
    
    def getManager(self):
        """ 获取管理器对象 """
        return self.__class__._BINDMANAGER
    
    def localRequest(self, apiPath = "", *args, **kwargs):
        """ 本地API请求 """
        return self.getManager().localRequest(
            apiPath, *args, **kwargs
        )

    def broadcast(self, eventObj):
        # type: (BaseEvent) -> None
        """ 事件广播 """
        eventObj._T_FROM_SERVICE = self
        self.__class__._BINDMANAGER.broadcast(eventObj)
        eventObj._T_FROM_SERVICE = None

    def _serviceListen(self, eventCls, callObj, priority = None):
        # type: (type[BaseEvent], object, int | None) -> None
        """ 服务监听
            允许设置优先级 考虑性能优化问题优先级设置后并不会立即刷新而是在下一帧统一更新
            如需要立即刷新 请调用SERVICELISTEN_PRIORITYSORT方法
        """
        return self.__class__._BINDMANAGER.serviceListen(eventCls, callObj, priority)
    
    def _unServiceListen(self, eventCls, callObj):
        # type: (type[BaseEvent], object) -> None
        """ 单次取消服务监听 如需批量处理请使用 SERVICELISTEN_OFF_ALL 方法 """
        return self.SERVICELISTEN_OFF_ALL([(eventCls, callObj)])
    
    def SERVICELISTEN_OFF_ALL(self, dataIt):
        # type: (list[tuple[type[BaseEvent], object]] | tuple[tuple[type[BaseEvent], object]]) -> None
        """ 批量取消服务监听 """
        return self.__class__._BINDMANAGER.SERVICELISTEN_OFF_ALL(dataIt)

    def SERVICELISTEN_PRIORITYSORT(self, eventCls):
        # type: (type[BaseEvent]) -> None
        """ 重新排序服务监听 """
        return self.__class__._BINDMANAGER.SERVICELISTEN_PRIORITYSORT(eventCls.getEngineKey())

    def _onCreate(self):
        self._loadAnnotation()
        self.onCreate()
    
    def _onRemove(self):
        self.removeAllBusiness()
        TRY_EXEC_FUN(self.onServiceStopBefore)
        self._unLoadAnnotation()
        self.onServiceStop()
        self._sharedArgs = {}
    
    def onAccessed(self):
        """ 当前服务通过access获取时触发 """
        return self
    
    def listenForEvent(self, eventName, fun):
        """ 注册事件监听(除非编写相关生命周期管理否则不会主动回收) """
        return self._defaultListenForEvent(eventName, self, fun)
    
    def _defaultListenForEvent(self, eventName, parent, fun):
        return self.__class__._BINDMANAGER.listenForEvent(eventName, parent, fun)

    def _defaultUnListenForEvent(self, eventName, parent, fun):
        return self.__class__._BINDMANAGER.unListenForEvent(eventName, parent, fun)

    def unListenForEvent(self, eventName, fun):
        """ 反注册事件监听 """
        return self._defaultUnListenForEvent(eventName, self, fun)

    def addBusiness(self, _businessObj):
        # type: (BaseBusiness) -> None
        """ 添加业务 """
        if _businessObj in self._businessSet:
            return
        try:
            _businessObj._parentObj = self
            self._businessSet.add(_businessObj)
            _businessObj._onCreate()
        except Exception:
            TRY_EXEC_FUN(_businessObj._onCreateError)
            _businessObj._parentObj = None
            if _businessObj in self._businessSet:
                self._businessSet.remove(_businessObj)
            import traceback
            traceback.print_exc()
            raise Exception("业务构建时发生异常")

    def getAllBusiness(self):
        """ 获取所有业务对象返回生成器 """
        for _businessObj in self._businessSet:
            yield _businessObj
        
    def getChildBusinessCount(self):
        # type: () -> int
        """ 获取运行中的子业务数量 """
        return len(self._businessSet)

    def removeBusiness(self, _businessObj):
        # type: (BaseBusiness) -> None
        """ 移除业务 """
        if not _businessObj in self._businessSet:
            return
        self._businessSet.remove(_businessObj)
        TRY_EXEC_FUN(_businessObj._onRemove)
        _businessObj._parentObj = None

    def removeAllBusiness(self):
        """ 移除所有业务 """
        for _businessObj in copy(self._businessSet):
            TRY_EXEC_FUN(_businessObj._onRemove)
            _businessObj._parentObj = None
        self._businessSet.clear()
    
    def updateAllBusiness(self):
        """ 更新所有业务 """
        for _businessObj in self._businessSet.copy():
            TRY_EXEC_FUN(_businessObj._onTick)

    def broadcastToBusiness(self, _eventObj):
        # type: (BaseEvent) -> None
        """ 对子业务进行广播 """
        _eventObj._T_FROM_SERVICE = self
        for _businessObj in self._businessSet.copy():
            TRY_EXEC_FUN(_businessObj._onReceiveServiceEvents, _eventObj)
            _eventObj._T_CONTEXT_INDEX += 1
        _eventObj._T_FROM_SERVICE = None
    
    def __init__(self):
        TimerLoader.__init__(self)
        self._sharedArgs = {}
        self._businessSet = set()   # type: set[BaseBusiness]
    
    def _onTick(self):
        self.updateAllBusiness()
        self._timerUpdate()
        self.onServiceUpdate()

    def stopSelf(self):
        """ 关闭自我服务 """
        return self.__class__.stop()

class _AutoStopService(IService):
    def __init__(self):
        self.STOP_SERVICE_MAX_TIME = 60.0
        """ 最大服务停止时间 """
        self._SERVICE_STOP_WAIT_TIME = 0.0

    def onAccessed(self):
        self._SERVICE_STOP_WAIT_TIME = 0.0
        return self

    def _onTick(self):
        self._SERVICE_STOP_WAIT_TIME += _BaseService._TICK_TIME
        if self._SERVICE_STOP_WAIT_TIME > self.STOP_SERVICE_MAX_TIME:
            TRY_EXEC_FUN(self.onServiceAutoStop)
            self.stopSelf()
            return

    def onServiceAutoStop(self):
        pass
