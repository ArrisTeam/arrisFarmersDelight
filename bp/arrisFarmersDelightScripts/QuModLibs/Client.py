# -*- coding: utf-8 -*-
# 客户端端基本功能模块 为减缓IO开销 常用的功能均放置在该文件 其他功能按需导入使用
from Util import (
    Unknown,
    InitOperation,
    errorPrint,
    _eventsRedirect,
    ObjectConversion as __ObjectConversion
)
import mod.client.extraClientApi as __extraClientApi
import IN as __IN
from IN import ModDirName
IsServerUser = __IN.IsServerUser
""" 客户端常量_是否为房主 """
clientApi = __extraClientApi                        
TickEvent = "OnScriptTickClient"
System = clientApi.GetSystem("Minecraft","game")    
levelId = clientApi.GetLevelId()
playerId = clientApi.GetLocalPlayerId() 
Events = _eventsRedirect                            

def regModLoadFinishHandler(func):
    """ 注册Mod加载完毕后触发的Handler """
    from IN import RuntimeService
    RuntimeService._clientLoadFinish.append(func)
    return func

def creatTemporaryContainer():
    return type("TemporaryContainer",(object,),{})()

def _getLoaderSystem():
    """ 获取加载器系统 """
    from Systems.Loader.Client import LoaderSystem
    return LoaderSystem.getSystem()

_loaderSystem = _getLoaderSystem()

def Request(Key, args=tuple(), kwargs={}, onResponse=lambda *_: None):
    # type: (str, tuple, dict, object) -> bool
    """ (未来可能移除 推荐使用服务类的安全请求机制)Request 向服务端发送请求, 与Call不同的是,这是双向的,可以取得返回值 """
    from Util import RandomUid
    backKey = RandomUid()
    def _backFun(*_args, **_kwargs):
        _loaderSystem.removeCustomApi(backKey)
        return onResponse(*_args, **_kwargs)
    _loaderSystem.regCustomApi(backKey, _backFun)
    Call("__Client.Request__", playerId, Key, args, kwargs, backKey)
    return True

def CallOTClient(playerId="", key="", *Args, **Kwargs):
    # type: (str, str, object, object) -> bool
    """ Call其他玩家的客户端 如: 发起组队申请 """
    Call("__CALL.CLIENT__", playerId, key, Args, Kwargs)
    return True

def ListenForEvent(eventName, parentObject=None, func=lambda: None):
    # type: (str, object, object) -> object
    eventName = eventName if isinstance(eventName, str) else eventName.__name__
    return _loaderSystem.nativeListen(eventName, parentObject, func)

def UnListenForEvent(eventName, parentObject=None, func=lambda: None):
    # type: (str, object, object) -> bool
    eventName = eventName if isinstance(eventName, str) else eventName.__name__
    return _loaderSystem.unNativeListen(eventName, parentObject, func)

def Listen(eventName):
    """  [装饰器] 游戏事件监听 """
    eventName = eventName if isinstance(eventName, str) else eventName.__name__
    from Systems.Loader.Client import LoaderSystem
    def _Listen(funObj):
        LoaderSystem.REG_STATIC_LISTEN_FUNC(eventName, funObj)
        return funObj
    return _Listen

def DestroyFunc(func):
    """ [装饰器] 注册销毁回调函数 """
    from Systems.Loader.Client import LoaderSystem
    LoaderSystem.REG_DESTROY_CALL_FUNC(func)
    return func

def Call(apiKey="", *args, **kwargs):
    # type: (str, object, object) -> None
    """ Call请求服务端API调用 """
    return _loaderSystem.sendCall(apiKey, args, kwargs)

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

def LocalCall(funcName="", *args, **kwargs):
    """ 本地调用 执行当前端@AllowCall|@CallBackKey("...")的方法 """
    return _loaderSystem.localCall(funcName, *args, **kwargs)

# ======= QuMod提供的一些基于原版API的组件 =======
@CallBackKey("__DelCallBackKey__")
def __DelCallBackKey(key=""):
    return _loaderSystem.removeCustomApi(key)

class QuObjectConversion(__ObjectConversion):
    @staticmethod
    def getClsWithPath(path):
        # type: (str) -> object
        lastPos = path.rfind(".")
        impObj = clientApi.ImportModule((path[:lastPos]))
        return getattr(impObj, path[lastPos+1:])

class QuDataStorage:
    """ Qu数据储存管理 """
    _versionKey = "__version__"
    _dataKey = "__data__"
    _isGlobal = "__isGlobal__"
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
    def AutoSave(version = 1, isGlobal = False):
        """ 自动保存装饰器
            @version 版本控制 当版本号不同时将会抛弃当前存档数据该用新版数据 一般用于大型数据变动
            @isGlobal 是否为全局配置 False视为仅当前存档
        """
        if not QuDataStorage._init:
            QuDataStorage._init = True
            _loaderSystem._onDestroyCall_LAST.append(QuDataStorage.saveData)
        def _autoSave(cls):
            path = QuObjectConversion.getClsPathWithClass(cls)
            comp = clientApi.GetEngineCompFactory().CreateConfigClient(clientApi.GetLevelId())
            configDict = comp.GetConfigData(path, isGlobal)
            if configDict == None:
                configDict = {}
            if configDict.get(QuDataStorage._versionKey, version) == version:
                QuDataStorage.loadData(cls, configDict.get(QuDataStorage._dataKey, {}))
            configDict[QuDataStorage._versionKey] = version
            configDict[QuDataStorage._isGlobal] = isGlobal
            if not path in QuDataStorage._autoMap:
                QuDataStorage._autoMap[path] = configDict
            return cls
        return _autoSave
    
    @staticmethod
    def saveData():
        """ 保存存档数据 """
        levelcomp = clientApi.GetEngineCompFactory().CreateConfigClient(levelId)
        for k, v in QuDataStorage._autoMap.items():
            try:
                cls = QuObjectConversion.getClsWithPath(k)
                v[QuDataStorage._dataKey] = QuDataStorage.dumpsData(cls)
                levelcomp.SetConfigData(k, v, v.get(QuDataStorage._isGlobal, False))
            except Exception as e:
                print(e)

@CallBackKey("__calls__")
def QUMOD_CLIENT_CALLS_(datLis):
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
