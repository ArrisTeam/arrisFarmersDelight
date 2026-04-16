# -*- coding: utf-8 -*-
from Math import Vec3, Vec2, QBox3D
from Util import (
    Unknown,
    InitOperation,
    errorPrint,
    _eventsRedirect,
    ObjectConversion as __ObjectConversion,
)
if 1 > 2:
    # 阻止补全库被真正import降低运行时开销
    import QuServerApi.extraServerApi as extraServerApi
    from QuServerApi.Events import Events as _EventsPrompt
from IN import ModDirName
import mod.server.extraServerApi as __extraServerApi
serverApi = __extraServerApi                        # type: extraServerApi
TickEvent = "OnScriptTickServer"
levelId = serverApi.GetLevelId()
compFactory = serverApi.GetEngineCompFactory()
System = serverApi.GetSystem("Minecraft","game")    # type: extraServerApi
Events = _eventsRedirect                            # type: type[_EventsPrompt]

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

class Entity(object):
    __slots__ = ("entityId","PropertySettingsDic",)
    ErrorSet = "[Error] 不支持的属性设置"

    class Type:
        PLAYER = "minecraft:player"

    class HealthComp(object):
        """ 生命值组件 """
        def __init__(self,entityId):
            # type: (str) -> None
            self.entityId = entityId
            self.PropertySettingsDic = {
                "Value":self.SetValue,
                "Max":self.SetMax
            }

        def __setattr__(self, Name, Value):
            """ 属性设置处理 """
            if Name in Entity.__slots__:
                return object.__setattr__(self, Name, Value)
            elif Name in self.PropertySettingsDic:
                Fun = self.PropertySettingsDic[Name]
                return Fun(Value)
            else:
                print(Entity.ErrorSet)
                return None

        def SetValue(self,Value):
            """ 设置Value值 """
            comp = compFactory.CreateAttr(self.entityId)
            return comp.SetAttrValue(0,Value)

        def SetMax(self,Value):
            """ 设置Max值 """
            comp = compFactory.CreateAttr(self.entityId)
            return comp.SetAttrMaxValue(0,Value)

        @property
        def Value(self):
            # type: () -> int
            comp = compFactory.CreateAttr(self.entityId)
            return comp.GetAttrValue(0)

        @property
        def Max(self):
            # type: () -> int
            comp = compFactory.CreateAttr(self.entityId)
            return comp.GetAttrMaxValue(0)
    
    @staticmethod
    def CreateEngineEntityByTypeStr(engineTypeStr, pos, rot, dimensionId = 0, isNpc = False):
        # type: (str, tuple[float], tuple[float], int, bool) -> str
        """ 服务端系统接口 创建微软生物 """
        return System.CreateEngineEntityByTypeStr(engineTypeStr, pos, rot, dimensionId, isNpc)
    
    def __init__(self, __entityId):
        # type: (str) -> None
        self.entityId = __entityId
        self.PropertySettingsDic = {
            "Pos":self.__SetPos,
            "FootPos":self.__SetPos,
            "Rot":self.__SetRot,
        }

    def __setattr__(self, Name, Value):
        """ 属性设置处理 """
        if Name in Entity.__slots__:
            return object.__setattr__(self, Name, Value)
        elif Name in self.PropertySettingsDic:
            Fun = self.PropertySettingsDic[Name]
            return Fun(Value)
        else:
            print(Entity.ErrorSet)
            return None

    def EntityPointDistance(self, otherEntity="", errorValue=0.0):
        # type: (str, float) -> float
        """ 获取与另外一个实体对应的脚部中心点距离(若实体异常将返回errorValue) """
        myPos = compFactory.CreatePos(self.entityId).GetPos()
        otherPos = compFactory.CreatePos(otherEntity).GetPos()
        if myPos == None or otherPos == None:
            return errorValue
        return Vec3.tupleToVec(myPos).vectorSubtraction(Vec3.tupleToVec(otherPos)).getLength()

    def EntityCenterPointDistance(self, otherEntity="", errorValue=0.0):
        # type: (str, float) -> float
        """ 获取与另外一个实体的中心点距离(若实体异常将返回errorValue) """
        myPos = compFactory.CreatePos(self.entityId).GetPos()
        otherPos = compFactory.CreatePos(otherEntity).GetPos()
        if myPos == None or otherPos == None:
            return errorValue
        myVec = Vec3.tupleToVec(myPos)
        otherVec = Vec3.tupleToVec(otherPos)
        comp = compFactory.CreateCollisionBox(self.entityId)
        mySize = comp.GetSize()
        comp = compFactory.CreateCollisionBox(otherEntity)
        otherSize = comp.GetSize()
        myVec.y -= mySize[1] * 0.5
        otherVec.y -= otherSize[1] * 0.5
        return myVec.vectorSubtraction(otherVec).getLength()

    def LookAt(self, otherPos=(0, 0, 0), minTime=2.0, maxTime=3.0, reject=True):
        comp = compFactory.CreateRot(self.entityId)
        comp.SetEntityLookAtPos(otherPos, minTime, maxTime, reject)

    def getBox3D(self, useBodyRot=False):
        # type: (bool) -> QBox3D
        """ 获取该实体的三维空间盒对象 """
        footPos = self.FootPos
        if not footPos:
            return QBox3D.createNullBox3D()
        comp = compFactory.CreateCollisionBox(self.entityId)
        sx, sy = comp.GetSize()
        x, y, z = footPos
        return QBox3D(Vec3(sx, sy, sx), Vec3(x, y + sy * 0.5, z), None, rotationAngle = 0 if not useBodyRot else self.Rot[1])

    def callEvent(self, eventName):
        # type: (str) -> bool
        """ 触发JSON中特定的事件定义 """
        comp = compFactory.CreateEntityEvent(self.entityId)
        return comp.TriggerCustomEvent(self.entityId, eventName)

    def getComponents(self):
        # type: () -> dict[str, object]
        """ 获取实体持有的运行时JSON组件 """
        comp = compFactory.CreateEntityEvent(self.entityId)
        return comp.GetComponents()

    def removeComponent(self, compName):
        # type: (str) -> bool
        """ 移除特定的JSON组件 """
        comp = compFactory.CreateEntityEvent(self.entityId)
        return comp.RemoveActorComponent(compName)

    def addComponent(self, compName, data):
        # type: (str, str | dict) -> bool
        """ 添加特定的JSON组件及参数 """
        if isinstance(data, dict):
            from json import dumps
            data = dumps(data)
        comp = compFactory.CreateEntityEvent(self.entityId)
        return comp.AddActorComponent(compName, data)

    def getBlockControlAi(self):
        # type: () -> bool
        """ 获取生物AI是否被屏蔽 """
        comp = compFactory.CreateControlAi(self.entityId)
        return comp.GetBlockControlAi()

    def setBlockControlAi(self, isBlock, freezeAnim=False):
        # type: (bool, bool) -> bool
        """ 设置生物AI是否被屏蔽 """
        comp = compFactory.CreateControlAi(self.entityId)
        return comp.SetBlockControlAi(isBlock, freezeAnim)

    def SetMarkVariant(self, value=1):
        # type: (int | float) -> bool
        """ 设置对应JSON组件的MarkVariant值 对应query.mark_variant(底层同步) """
        comp = compFactory.CreateEntityDefinitions(self.entityId)
        return comp.SetMarkVariant(value)

    def SetVariant(self, value=1):
        # type: (int | float) -> bool
        """ 设置对应JSON组件的Variant值 对应query.variant(底层同步) """
        comp = compFactory.CreateEntityDefinitions(self.entityId)
        return comp.SetVariant(value)

    def GetAttackTarget(self):
        # type: () -> str
        """ 获取攻击目标 """
        comp = compFactory.CreateAction(self.entityId)
        return comp.GetAttackTarget()

    def SetAttackTarget(self, targetId=None, autoResetAttackTarget=True):
        # type: (str | None, bool) -> bool
        """ 设置攻击目标 """
        comp = compFactory.CreateAction(self.entityId)
        if autoResetAttackTarget and self.GetAttackTarget() != targetId:
            self.ResetAttackTarget()
        if targetId:
            return comp.SetAttackTarget(targetId)

    def ResetAttackTarget(self):
        # type: () -> bool
        """ 重置攻击目标 """
        comp = compFactory.CreateAction(self.entityId)
        return comp.ResetAttackTarget()

    def GetMotionComp(self):
        """ 获取移动向量管理组件 """
        return compFactory.CreateActorMotion(self.entityId)

    def SetRuntimeAttr(self, attrName, value):
        """ 设置运行时属性数据(根据MOD隔离并同步客户端) """
        comp = compFactory.CreateModAttr(self.entityId)
        return comp.SetAttr("{}_{}".format(ModDirName, attrName), value)

    def GetRuntimeAttr(self, attrName, nullValue=None):
        """ 获取运行时属性数据(根据MOD隔离) """
        comp = compFactory.CreateModAttr(self.entityId)
        return comp.GetAttr("{}_{}".format(ModDirName, attrName), nullValue)

    def checkSubstantive(self):
        # type: () -> bool
        """ 检查实体是否具有实质性(非物品/抛掷物) """
        entityTypeEnum = serverApi.GetMinecraftEnum().EntityType
        comp = compFactory.CreateEngineType(self.entityId)
        entityType = comp.GetEngineType()
        if entityType & entityTypeEnum.Projectile == entityTypeEnum.Projectile or entityType & entityTypeEnum.ItemEntity == entityTypeEnum.ItemEntity:
            return False
        return True

    def getBodyDirVec3(self):
        # type: () -> Vec3
        """ 获取基于Body方向的单位向量 """
        vc = self.Vec3DirFromRot
        vc.y = 0.0
        if vc.getLength() > 0.0:
            vc.convertToUnitVector()
        return vc

    def convertToWorldVec3(self, absVec):
        # type: (Vec3) -> Vec3
        """ 基于当前实体转换一个相对向量到世界向量 """
        axis = Vec3(0, 1, 0)
        f = self.getBodyDirVec3()
        l = f.copy().rotateVector(axis, -90)
        worldVec3 = f.multiplyOf(absVec.z).addVec(l.multiplyOf(absVec.x))
        if worldVec3.getLength() > 0.0:
            worldVec3.convertToUnitVector()
            worldVec3.multiplyOf(Vec3(absVec.x, 0.0, absVec.z).getLength())
        worldVec3.y = absVec.y
        return worldVec3

    @property
    def Health(self):
        # type: () -> Entity.HealthComp
        """ 实体生命值属性 """
        return self.__class__.HealthComp(self.entityId)
    
    @property
    def Pos(self):
        # type: () -> tuple[float,float,float]  | None
        return compFactory.CreatePos(self.entityId).GetPos()

    @property
    def Vec3Pos(self):
        # type: () -> Vec3 | None
        """ 获取Vec3坐标 失败则返回None """
        pos = self.Pos
        if pos == None:
            return None
        return Vec3.tupleToVec(pos)

    @property
    def IsPlayer(self):
        # type: () -> bool
        """ 判断目标是不是玩家单位 """
        return self.Identifier == "minecraft:player"

    @property
    def Vec3FootPos(self):
        # type: () -> Vec3 | None
        """ 获取Vec3脚下坐标 失败则返回None """
        pos = self.FootPos
        if pos == None:
            return None
        return Vec3.tupleToVec(pos)

    @property
    def FootPos(self):
        # type: () -> tuple[float,float,float]  | None
        return compFactory.CreatePos(self.entityId).GetFootPos()

    @property
    def Rot(self):
        # type: () -> tuple[float,float]  | None
        return compFactory.CreateRot(self.entityId).GetRot()

    @property
    def Vec2Rot(self):
        # type: () -> Vec2 | None
        """ 获取Vec2旋转角度 失败则返回None """
        rot = self.Rot
        if rot == None:
            return None
        return Vec2.tupleToVec(rot)

    @property
    def Identifier(self):
        # type: () -> str
        return compFactory.CreateEngineType(self.entityId).GetEngineTypeStr()

    @property
    def Dm(self):
        # type: () -> int
        return compFactory.CreateDimension(self.entityId).GetEntityDimensionId()
    
    @property
    def DirFromRot(self):
        # type: () -> tuple[float,float,float]  | None
        return serverApi.GetDirFromRot(self.Rot)

    @property
    def Vec3DirFromRot(self):
        # type: () -> Vec3 | None
        rot = self.DirFromRot
        if rot == None:
            return None
        return Vec3.tupleToVec(rot)
    
    @property
    def DimensionId(self):
        # type: () -> int
        return self.Dm
    
    def __SetPos(self,Value):
        # type: (tuple[float, float, float] | Vec3) -> bool
        if Value and isinstance(Value, Vec3):
            Value = Value.getTuple()
        return compFactory.CreatePos(self.entityId).SetPos(Value)

    def __SetRot(self,Value):
        # type: (tuple[float, float] | Vec2) -> bool
        if Value and isinstance(Value, Vec2):
            Value = Value.getTuple()
        return compFactory.CreateRot(self.entityId).SetRot(Value)
    
    def Destroy(self):
        """ 注销 销毁实体 """
        return DestroyEntity(self.entityId)
    
    def Kill(self):
        """ 杀死实体 """
        return compFactory.CreateGame(levelId).KillEntity(self.entityId)
    
    def exeCmd(self, cmd):
        # type: (str) -> bool
        """ 使实体执行命令 """
        return compFactory.CreateCommand(levelId).SetCommand(cmd, self.entityId)

    def getNearPlayer(self):
        # type: () -> str | None
        """ 获取任意一个最近的玩家单位(渲染范围内) 可能为None """
        playerList = compFactory.CreatePlayer(self.entityId).GetRelevantPlayer([])
        if playerList:
            return playerList[0]
        return None

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
                    compFactory.CreateGame(levelId).AddTimer(self.waitingTime, self._onStart)
                    break
                elif slpTime:
                    compFactory.CreateGame(levelId).AddTimer(slpTime, self._onStart)
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
        from ..Api.InternalModules import importModule
        lastPos = path.rfind(".")
        impObj = importModule(path[:lastPos])
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
            comp = compFactory.CreateExtraData(levelId)
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
        levelcomp = compFactory.CreateExtraData(levelId)
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