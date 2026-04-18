# -*- coding: utf-8 -*-
from Util import (
    Unknown,
    InitOperation,
    errorPrint,
    _eventsRedirect,
    ObjectConversion as __ObjectConversion,
)
from IN import ModDirName
import mod.server.extraServerApi as __extraServerApi
serverApi = __extraServerApi                        
TickEvent = "OnScriptTickServer"
levelId = serverApi.GetLevelId()
System = serverApi.GetSystem("Minecraft","game")    
Events = _eventsRedirect                            

def getOwnerPlayerId():
    # type: () -> str | None
    """ 获取房主玩家ID 如果存在(联机大厅/网络游戏中不存在房主玩家) """
    from IN import RuntimeService
    return RuntimeService._envPlayerId

def regModLoadFinishHandler(func):
    """ 注册Mod加载完毕后触发的Handler """
    from IN import RuntimeService
    RuntimeService._serverLoadFinish.append(func)
    return func

def DestroyEntity(entityId):
    """ 注销特定实体 """
    return System.DestroyEntity(entityId)

def _getLoaderSystem():
    """ 获取加载器系统 """
    from Systems.Loader.Server import LoaderSystem
    return LoaderSystem.getSystem()

_loaderSystem = _getLoaderSystem()

def ListenForEvent(eventName, parentObject=None, func=lambda: None):
    # type: (str | object, object, object) -> object
    """ 动态事件监听 """
    eventName = eventName if isinstance(eventName, str) else eventName.__name__
    return _loaderSystem.nativeListen(eventName, parentObject, func)

def UnListenForEvent(eventName, parentObject=None, func=lambda: None):
    # type: (str | object, object, object) -> bool
    """ 动态事件监听销毁 """
    eventName = eventName if isinstance(eventName, str) else eventName.__name__
    return _loaderSystem.unNativeListen(eventName, parentObject, func)

def Listen(eventName=""):
    """  [装饰器] 游戏事件监听 """
    eventName = eventName if isinstance(eventName, str) else eventName.__name__
    from Systems.Loader.Server import LoaderSystem
    def _Listen(funObj):
        LoaderSystem.REG_STATIC_LISTEN_FUNC(eventName, funObj)
        return funObj
    return _Listen

def DestroyFunc(func):
    """ [装饰器] 注册销毁回调函数 """
    from Systems.Loader.Server import LoaderSystem
    LoaderSystem.REG_DESTROY_CALL_FUNC(func)
    return func

def Call(playerId, apiKey="", *args, **kwargs):
    # type: (str, str, object, object) -> None
    """ Call请求对立端API调用 当playerId为*时代表全体玩家 """
    return _loaderSystem.sendCall(playerId, apiKey, args, kwargs)

def MultiClientsCall(playerIdList=[], key="", *args, **kwargs):
    # type: (list[str], str, object, object) -> None
    """ 多玩家客户端合批Call请求 """
    return _loaderSystem.sendMultiClientsCall(playerIdList, key, args, kwargs)

def CallBackKey(key=""):
    """ (向下兼容 未来可能移除)[装饰器] 用于给指定函数标记任意key值 以便被Call匹配 """
    def _CallBackKey(fun):
        _loaderSystem.regCustomApi(key, fun)
        return fun
    return _CallBackKey

def AllowCall(func):
    """ 允许调用 同等于CallBackKey 自动以当前函数名字设置参数 """
    key = func.__name__
    key2 = "{}.{}".format(func.__module__, key)
    key3 = key2.split(ModDirName+".", 1)[1]
    _loaderSystem.regCustomApi(key, func)
    _loaderSystem.regCustomApi(key2, func)
    _loaderSystem.regCustomApi(key3, func)
    return func

def InjectHttpPlayerId(func):
    """ [装饰器] 注入玩家ID接收，可搭配@AllowCall使用（注意先后顺序） """
    def _wrapper(*args, **kwargs):
        return func(_loaderSystem.httpPlayerId, *args, **kwargs)
    _wrapper.__name__ = func.__name__
    return _wrapper

def LocalCall(funcName="", *args, **kwargs):
    """ 本地调用 执行当前端@AllowCall|@CallBackKey("...")的方法 """
    return _loaderSystem.localCall(funcName, *args, **kwargs)

class TaskProcessObj(object):
    def __init__(self, obj, workingHours, waitingTime):
        # type: (object, float, float) -> None
        self.obj = obj
        self.workingHours = workingHours
        self.waitingTime = waitingTime
        self._lock = False
        self.__isWorking = False
        self.__gen = None
    
    def stopTask(self):
        if not self.__isWorking:
            return
        self.__isWorking = False
    
    def clone(self):
        return TaskProcessObj(self.obj, self.workingHours, self.waitingTime)
    
    def run(self, *args, **kwargs):
        if self.__isWorking or self._lock:
            return
        self.__gen = self.obj(*args, **kwargs)
        self.__isWorking = True
        self._onStart()
    
    def _onStart(self):
        from time import time
        startTime = time()
        try:
            while self.__isWorking:
                slpTime = next(self.__gen)
                nowTime = time()
                if nowTime - self.workingHours >= startTime:
                    serverApi.GetEngineCompFactory().CreateGame(levelId).AddTimer(self.waitingTime, self._onStart)
                    break
                elif slpTime:
                    serverApi.GetEngineCompFactory().CreateGame(levelId).AddTimer(slpTime, self._onStart)
                    break
        except StopIteration:
            self.stopTask()
        except Exception as e:
            print("[Error] {} 任务异常: {}".format(self.obj.__name__, e))
            self.stopTask()

def TaskProcess(workingHours = 0.02, waitingTime = 0.04):
    """ 任务进程装饰器 """
    def _zsq(obj):
        taskProcessObj = TaskProcessObj(obj, workingHours, waitingTime)
        taskProcessObj._lock = True
        return taskProcessObj
    return _zsq

def TaskProcessCreate(obj):
    # type: (TaskProcessObj) -> TaskProcessObj
    """ 创建任务进程 """
    return obj.clone()

# ================== 客户端请求实现 ==================
@CallBackKey("__Client.Request__")
def __ClientRequest(PlayerId, Key, Args, Kwargs, BackKey):
    try:
        BackData = LocalCall(Key, *Args, **Kwargs)
    except Exception as e:
        Call(PlayerId, "__DelCallBackKey__", Key)
        raise e
    Call(PlayerId, BackKey, BackData)

@CallBackKey("__CALL.CLIENT__")
def __CallCLIENT(playerIdData, Key, Args, Kwargs):
    if isinstance(playerIdData, list):
        return MultiClientsCall(playerIdData, Key, *Args, **Kwargs)
    return Call(playerIdData, Key, *Args, **Kwargs)
# ================== 客户端请求实现 ==================

class QuObjectConversion(__ObjectConversion):
    @staticmethod
    def getClsWithPath(path):
        # type: (str) -> object
        lastPos = path.rfind(".")
        impObj = serverApi.ImportModule((path[:lastPos]))
        return getattr(impObj, path[lastPos+1:])

class QuDataStorage:
    """ Qu数据储存管理 """
    _versionKey = "__version__"
    _dataKey = "__data__"
    _autoMap = {}   # type: dict[type, dict]
    _init = False

    @staticmethod
    def formatStrType(typ):
        # type: (str) -> str
        """ 格式化字符串类型 """
        if typ in ("float", "int"):
            return "number"
        elif typ in ("str", "unicode"):
            return "baseString"
        return typ

    @staticmethod
    def loadData(clsObj, data):
        # type: (type, dict) -> None
        """ 加载数据 """
        for k, v in data.items():
            try:
                newObj = QuObjectConversion.loadDumpsObject(v)
                oldType = QuDataStorage.formatStrType(QuObjectConversion.getType(getattr(clsObj, k)))
                newType = QuDataStorage.formatStrType(QuObjectConversion.getType(newObj))
                if oldType != newType:
                    print("[QuDataStorage] 新旧数据类型不一已被放弃 ('{}' != '{}')".format(newType, oldType))
                    continue
                setattr(clsObj, k, newObj)
            except Exception as e:
                print(e)
    
    @staticmethod
    def dumpsData(clsObj):
        # type: (type) -> dict
        """ 获取序列化数据 """
        return {
            k : QuObjectConversion.dumpsObject(getattr(clsObj, k)) for k in dir(clsObj) if not k.startswith("__")
        }

    @staticmethod
    def AutoSave(version = 1):
        """ 自动保存装饰器
            @version 版本控制 当版本号不同时将会抛弃当前存档数据该用新版数据 一般用于大型数据变动
        """
        if not QuDataStorage._init:
            QuDataStorage._init = True
            _loaderSystem._onDestroyCall_LAST.append(QuDataStorage.saveData)

        def _autoSave(cls):
            path = QuObjectConversion.getClsPathWithClass(cls)
            comp = serverApi.GetEngineCompFactory().CreateExtraData(levelId)
            levelExData = comp.GetExtraData(path)
            if levelExData == None:
                levelExData = {}
            if levelExData.get(QuDataStorage._versionKey, version) == version:
                QuDataStorage.loadData(cls, levelExData.get(QuDataStorage._dataKey, {}))
            levelExData[QuDataStorage._versionKey] = version
            if not path in QuDataStorage._autoMap:
                QuDataStorage._autoMap[path] = levelExData
            return cls
        return _autoSave
    
    @staticmethod
    def saveData():
        """ 保存存档数据 """
        saveCount = 0
        levelcomp = serverApi.GetEngineCompFactory().CreateExtraData(levelId)
        for k, v in QuDataStorage._autoMap.items():
            saveCount += 1
            try:
                cls = QuObjectConversion.getClsWithPath(k)
                v[QuDataStorage._dataKey] = QuDataStorage.dumpsData(cls)
                levelcomp.SetExtraData(k, v, False)
            except Exception as e:
                print(e)
        if saveCount > 0:
            levelcomp.SaveExtraData()

@CallBackKey("__calls__")
def QUMOD_SERVER_CALLS_(datLis):
    # type: (list[tuple]) -> None
    """ 内置的多callData处理请求 """
    for key, args, kwargs in datLis:
        try:
            LocalCall(key, *args, **kwargs)
        except Exception as e:
            errorPrint("CALL发生异常 KEY值 '{}' >> {}".format(key, e))
            import traceback
            traceback.print_exc()

def EventHandler(key):
    """ 注册EventHandler 可搭配QuPresteTool完成代码分析并建立关联 """
    def _EventHandler(fun):
        return fun
    return _EventHandler

def Emit(eventHandler, *args, **kwargs):
    """ 发送消息 执行特定eventHandler """
    pass
