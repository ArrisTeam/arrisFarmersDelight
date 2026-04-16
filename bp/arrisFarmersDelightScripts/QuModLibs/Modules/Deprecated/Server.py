# -*- coding: utf-8 -*-
from ...Server import *
from time import time
lambda: "By Zero123"
# 以下功能计划与未来移除并提供对应的替代方案

class EasyThread:
    """ QuMod提供的简易多线程 """
    from ...Util import ThreadLock
    @classmethod
    def IsThread(cls, *Args, **Kwargs):
        """ 用于将函数装饰为多线程下执行的函数 @IsThread 无参数"""
        from ...Util import IsThread
        return IsThread(*Args, **Kwargs)
    
    @classmethod
    def NextTick(cls, Fun, Args=tuple(), Kwargs={}, WaitReturn=False):
        """ 
            添加函数到下一游戏Tick运行 用于解决线程下无法使用API的现象
            选填参数 WaitReturn=False(默认值) 设置为True后将会等待返回结果后再执行后续代码
            Args=tuple(),Kwargs={} 可传参
        """
        cls.ThreadLock.acquire() # 上锁
        Back = []
        Obj = EasyThread()
        def Tick(_={}):
            UnListenForEvent(TickEvent, Obj, Tick)
            RunBack = Fun(*Args,**Kwargs)
            Back.append(RunBack)
            
        ListenForEvent(TickEvent, Obj, Tick)
        cls.ThreadLock.release() # 释放锁
        # 返回值处理
        if WaitReturn:
            while not len(Back):
                pass
            return Back[0]

class EntityCompController:
    """ 实体组件控制器 用来处理全局Tick循环以及死亡判定 """
    TickRealTime = False
    """ Tick启用真实时间校验 """

    class QuEventASData(object):
        """ 关于自我的事件数据 """
        def __init__(self, eventName, parent, callBack):
            self.eventName = eventName
            """ 事件名称 """
            self.parent = parent    # type: EntityCompCls
            """ 父节点 即注册者self实例 """
            self.callBack = callBack
            """ 回调方法 """
    
    class QuEvent(object):
        """ 事件组 """
        def __init__(self, eventName, callBack):
            self.eventName = eventName
            """ 事件名字 """
            self.callBack = callBack
            """ 回调方法 """
            ListenForEvent(eventName, self, self.Run)
        
        def Run(self, args):
            return self.callBack(args)
        
        def Remove(self):
            UnListenForEvent(self.eventName, self, self.Run)

    RunState = False
    """ 运行状态 """
    LastTickTime = 0
    """ 上一次Tick时间 """
    EntityCompDic = {
    }   # type: dict[str,list[EntityCompCls]]
    """ 实体组件映射表 """
    EntityCompSleepDic = {
    }   # type: dict[str,list[SuperEntityCompCls]]
    """ 实体组件休眠表 """
    GlobalEventsDic = {
    }   # type: dict[EntityCompController.QuEvent, list[EntityCompController.QuEventASData]]
    """ 全局事件响应字典 """
    CachePlayerList = []    # type: list[str]
    """ 玩家缓存列表(如处于传送状态的玩家) """
    StopRender = False
    """ 停止渲染 """

    @staticmethod
    def GetPlayerDmDict():
        # type: () -> dict[str,list[str]]
        """ 获取玩家维度字典 """
        playerList = serverApi.GetPlayerList()
        dmDict = {} # type: dict[str,list[str]]
        for playerId in playerList:
            dm = str(Entity(playerId).Dm)
            lis = dmDict.get(dm, [])
            lis.append(playerId)
            dmDict[dm] = lis
        return dmDict
    
    @staticmethod
    def _OnCompStopTick(comp):
        # type: (EntityCompCls) -> None
        comp._compStopTick += 1
        try:
            comp._onStopRenderTick()
        except Exception:
            import traceback
            traceback.print_exc()
        if comp._engineAutoFree and comp._compStopTick > comp._compMaxStopTick:
            comp._onEngineStopRenderAndRecycle()
            comp.RemoveComp()
    
    @staticmethod
    def CanEntityRender(comp, playerDmDict):
        # type: (EntityCompCls, list[str]) -> bool
        """ 用于计算实体是否可以渲染 """
        entityId = comp.entityId
        if entityId == levelId or comp.persistentWork: # 持久化工作
            return True
        if EntityCompController.StopRender:
            return False
        dm = str(Entity(entityId).Dm)
        if dm != "0" and not dm in playerDmDict:
            EntityCompController._OnCompStopTick(comp)
            return False
        try:
            if serverApi.GetEngineCompFactory().CreatePlayer(entityId).GetRelevantPlayer(EntityCompController.CachePlayerList):
                comp._compStopTick = 0
                return True
        except:
            pass
        return False

    @staticmethod
    def PointDistance(point1, point2):
        # type: (tuple, tuple) -> float
        """ 两点测距 """
        x1, y1, z1 = point1
        x2, y2, z2 = point2
        result = ((x2 - x1)**2 + (y2 - y1)**2 + (z2 - z1)**2)**0.5
        return result

    @staticmethod
    def QuListenForEventAboutSelf(data):
        # type: (EntityCompController.QuEventASData) -> bool
        """ 注册事件监听 """
        eventName = data.eventName
        for Obj, Lis in EntityCompController.GlobalEventsDic.items():
            if Obj.eventName == eventName:
                # 已找到事件组 归入数据
                Lis.append(data)
                return True
        # 未找到事件组 初始化数据
        eventDataList = [ data ]    # type: list[EntityCompController.QuEventASData]
        def OnEvent(args):
            if not (args and isinstance(args, dict)):
                return
            KeyEntityIdList = args.values()
            for ASData in eventDataList:
                if ASData.parent.entityId in KeyEntityIdList:
                    EntityCompController.TryExec(ASData.callBack, args)
        EntityCompController.GlobalEventsDic[
            EntityCompController.QuEvent(eventName, OnEvent)
        ] = eventDataList
        return True
    
    @staticmethod
    def QuDelAllEventASData(SELF):
        # type: (EntityCompCls) -> bool
        """ 清空所有相关事件监听基于实例 """
        DelEventList = [] # type: list[EntityCompController.QuEvent]
        """ 待清理的事件组 """
        for QEvent, EventList in EntityCompController.GlobalEventsDic.items():
            for QEventData in EventList[::]:
                if QEventData.parent == SELF:
                    # 删除事件数据
                    EventList.remove(QEventData)
            if len(EventList) == 0:
                # 该事件组无数据 销毁事件组
                DelEventList.append(QEvent)
        for QEvent in DelEventList:
            QEvent.Remove()
            del EntityCompController.GlobalEventsDic[QEvent]
        return True

    @staticmethod
    def TryExec(Fun, *Args, **Kwargs):
        """ 尝试执行函数 """
        try:
            Fun(*Args, **Kwargs)
        except Exception:
            import traceback
            traceback.print_exc()

    @staticmethod
    def AddEntityComp(entityId, comp):
        # type: (str, EntityCompCls) -> bool
        """ 添加实体组件 """
        if entityId == None: return False
        if not entityId in EntityCompController.EntityCompDic:
            EntityCompController.EntityCompDic[entityId] = [] # 初始化数据
        List = EntityCompController.EntityCompDic[entityId]
        if comp in List: return False
        List.append(comp)
        return False

    @staticmethod
    def RemoveEntityComp(entityId, comp):
        # type: (str, EntityCompCls) -> bool
        """ 移除实体组件 如果存在 """
        if entityId == None: return False
        if entityId in EntityCompController.EntityCompDic:
            List = EntityCompController.EntityCompDic[entityId]
            if comp in List:
                if comp.QuAddToEventEngine:
                    EntityCompController.TryExec(
                        EntityCompController.QuDelAllEventASData, comp
                    )
                List.remove(comp)
                return True
        return False

    @staticmethod
    def RemoveEntityAllComps(entityId, _isRemoveEvent = False):
        # type: (str, bool) -> bool
        """ 移除实体所有组件 """
        if entityId == None: return False
        if entityId in EntityCompController.EntityCompDic:
            for Comp in EntityCompController.EntityCompDic[entityId][::]:
                if _isRemoveEvent:
                    EntityCompController.TryExec(Comp.onEntityRemoveEvent)
                EntityCompController.TryExec(Comp.RemoveComp)
            try:
                del EntityCompController.EntityCompDic[entityId]
            except Exception as e:
                errorPrint(e)
        return False
    
    @staticmethod
    def RemoveAllComps():
        """ 移除所有组件 """
        if not EntityCompController.RunState:
            return False
        for entityId in EntityCompController.EntityCompDic:
            for Comp in EntityCompController.EntityCompDic[entityId][::]:
                EntityCompController.TryExec(Comp.onGameDestroy)
                EntityCompController.TryExec(Comp.RemoveComp)
        EntityCompController.EntityCompDic = {}
        return True

    @staticmethod
    def OnScriptTickServer(_={}):
        """ 建立全局循环 """
        nowTime = 0
        TickRealTime = EntityCompController.TickRealTime
        if TickRealTime:
            nowTime = time()
        if not TickRealTime or nowTime >= EntityCompController.LastTickTime+1/30.0/2.0:
            # 执行组件tick
            playerDmDict = EntityCompController.GetPlayerDmDict()
            for _, compList in EntityCompController.EntityCompDic.items():
                for comp in compList[::]:
                    if not EntityCompController.CanEntityRender(comp, playerDmDict):
                        comp.compIsWorking = False
                        continue
                    comp.compIsWorking = True
                    EntityCompController.TryExec(comp.OnTick)
        EntityCompController.LastTickTime = nowTime
    
    @staticmethod
    def EntityRemoveEvent(args):
        """ 实体删除事件 """
        entityId = args["id"]
        if entityId in EntityCompController.EntityCompDic:
            EntityCompController.RemoveEntityAllComps(entityId, True)
        if entityId in EntityCompController.EntityCompSleepDic:
            EntityCompController.RemoveSleepComp(entityId)
    
    @staticmethod
    def RemoveSleepComp(entityId):
        # type: (str) -> bool
        """ 删除休眠组件 """
        try:
            compList = EntityCompController.EntityCompSleepDic[entityId]    # 休眠组件列表
            for comp in compList:
                del comp.__class__.UserList[entityId]                       # 从用户组件清单移除
                EntityCompController.TryExec(comp.OnRemove)
            del EntityCompController.EntityCompSleepDic[entityId]
        except:
            return False
        return True
    
    @staticmethod
    def DimensionChangeServerEvent(args):
        """ 玩家开始切换维度 """
        data = Events.DimensionChangeServerEvent(args)
        EntityCompController.CachePlayerList.append(data.playerId)
        if len(serverApi.GetPlayerList()) <= 1:
            EntityCompController.StopRender = True

    @staticmethod
    def DimensionChangeFinishServerEvent(args):
        """ 玩家切换维度完毕 """
        data = Events.DimensionChangeFinishServerEvent(args)
        cacheList = EntityCompController.CachePlayerList
        if data.playerId in cacheList:
            cacheList.remove(data.playerId)
        EntityCompController.StopRender = False

    @staticmethod
    def Run():
        """ 运行服务 """
        if not EntityCompController.RunState:
            EntityCompController.RunState = True
            ListenForEvent(Events.OnScriptTickServer, EntityCompController, EntityCompController.OnScriptTickServer)
            ListenForEvent(Events.EntityRemoveEvent, EntityCompController, EntityCompController.EntityRemoveEvent)
            ListenForEvent(Events.DimensionChangeServerEvent, EntityCompController, EntityCompController.DimensionChangeServerEvent)
            ListenForEvent(Events.DimensionChangeFinishServerEvent, EntityCompController, EntityCompController.DimensionChangeFinishServerEvent)

class EntityCompCls(object):
    """ QuMod提供的实体组件类 开发者可以继承并开发实体组件功能 """
    # UserList 用作记录使用者Id,防止同组件复用现象
    UserList = {}           # type: dict[str, EntityCompCls]

    @staticmethod
    def _newDict():
        return dict()

    @classmethod
    def GetUserList(cls):
        # type: () -> dict[str, EntityCompCls]
        bases = cls.__bases__   # type: tuple[type[EntityCompCls]]
        for parentCls in bases:
            # if cls.UserList is parentCls.UserList:
            if cls.UserList is getattr(parentCls, "UserList"):  # 弱智网易机审报找不到UserList
                cls.UserList = EntityCompCls._newDict()
                break
        return cls.UserList

    @classmethod
    def GetComp(cls, entityId):
        # type: (str) -> EntityCompCls | None
        """ [静态方法] 获取指定实体的组件实例 """
        return cls.GetUserList().get(entityId, None)
        
    def __init__(self, entityId):
        self.entityId = entityId
        self.InitState = True
        """ 初始化状态 """
        self.persistentWork = False # type: bool
        """ 持久化工作

        设置为True时组件将不会计算渲染范围并且不会因为当前维度丢失玩家客户端而主动销毁组件
        除非生物销毁/主动销毁组件, 此外levelId全局组件不受该属性影响
        """
        self.compIsWorking = False
        """ 组件是否在工作 由引擎直接设置 """
        # =================== 自动垃圾回收 ===================
        # 该业务逻辑用于处理错误的实体id传递可能导致的内存泄漏 如果您有确切把握可以禁用此功能
        self._compStopTick = 0
        """ 组件停止的Tick """
        self._compMaxStopTick = 5
        """ 组件最大停止Tick 当_engineAutoFree启用后达到最大停止Tick将会强制回收 """
        self._engineAutoFree = True
        """ 使用引擎自动释放 与持久化工作冲突 禁用后只在RemoveEntity时释放 """
        # =================== 自动垃圾回收 ===================
        cls = self.__class__
        UserList = cls.GetUserList()
        if entityId in UserList:
            self.InitState = False
            return None
        self.QuAddToEventEngine = False
        """ (不建议改动) 是否被添加到事件引擎 使用QuListenForEventAboutSelf方法后即被登记将在组件销毁时识别处理 """
        EntityCompController.Run()
        EntityCompController.AddEntityComp(self.entityId, self)
        UserList[entityId] = self

    def onEntityRemoveEvent(self):
        """ 当实体被系统删除时触发 随后将会触发OnRemove """
        pass
    
    def onGameDestroy(self):
        """ 当游戏关闭会话连接时触发 随后将会触发OnRemove """
        pass

    def _onStopRenderTick(self):
        """ 当停止渲染时触发的Tick """
        pass

    def _onEngineStopRenderAndRecycle(self):
        """ 当引擎停止渲染并回收 与_engineAutoFree关联 """
        pass

    def OnRemove(self):
        """ [可覆写] 组件移除后自动执行 不建议在此处再次移除实体 """
        pass
    
    def OnTick(self):
        """ [可覆写] Tick 一秒30次 如有需要可以覆写此方法 """
        pass

    def QuListenForEventAboutSelf(self, eventName, callback):
        # type: (str | object, object) -> bool
        """
            监听有关与自我的事件
            与直接注册监听不同, 该方法由QuMod实体组件全局事件引擎处理
            仅当指定事件的返回参数中涉及到当前实体时回调
            在实体死亡/组件销毁时自动结束监听
        """
        eventName = eventName if eventName and isinstance(eventName, str) else eventName.__name__
        self.QuAddToEventEngine = True
        return EntityCompController.QuListenForEventAboutSelf(
            EntityCompController.QuEventASData(
                eventName, self, callback
            )
        )
    
    def RemoveComp(self):
        """ 删除组件方法,可以手动调用 生物死亡后也会自动调用 """
        try:
            cls = self.__class__
            del cls.UserList[self.entityId]
            EntityCompController.RemoveEntityComp(self.entityId, self)
            self.OnRemove()
            return True
        except:
            pass
        return False

class SuperEntityCompCls(EntityCompCls):
    """ 超级实体组件类
    
        基于EntityCompCls实现的增强版组件类, 相较于EntityCompCls它具有定时器管理,休眠策略等功能
        使用SuperEntityCompCls时需确保重新实现时正确调用父类方法, 否则可能导致功能无效
    """
    class Timer(object):
        """ 定时器 允许传递参数亦或者设置循环 """
        def __init__(self, callObject, argsTuple = tuple(), kwargsDict = dict(), time = 0.0, loop = False):
            # type: (object, tuple, dict, float, bool) -> None
            self.callObject = callObject
            self.argsTuple = argsTuple
            self.kwargsDict = kwargsDict
            self.loop = loop
            self.setTime = time
            self.valueTime = time
        
        def call(self):
            try:
                self.callObject(*self.argsTuple, **self.kwargsDict)
            except Exception as e:
                errorPrint("Timer定时器抛出异常 {}".format(e))
                import traceback
                traceback.print_exc()
        
        def copy(self):
            # type: () -> SuperEntityCompCls.Timer
            """ 拷贝定时器 """
            return self.__class__(self.callObject, self.argsTuple, self.kwargsDict, self.setTime, self.loop)
        
        def rest(self):
            """ 重置定时 """
            self.valueTime = self.setTime

    _RegisterMap = {}           # type: dict[str, type[SuperEntityCompCls]]
    _EntityRegisterMap = {}     # type: dict[str, set[str]]

    @staticmethod
    def Register(*entityTypeTuple):
        # type: (str) -> object
        """ 常驻组件注册 在生物生成时自动创建并绑定 """
        def _register(cls):
            modulePath = "{}.{}".format(cls.__module__, cls.__name__)
            SuperEntityCompCls._RegisterMap[modulePath] = cls
            for entityType in entityTypeTuple:
                if not entityType in SuperEntityCompCls._EntityRegisterMap:
                    SuperEntityCompCls._EntityRegisterMap[entityType] = set()
                compSet = SuperEntityCompCls._EntityRegisterMap[entityType]
                if not modulePath in compSet:
                    compSet.add(modulePath)
            return cls
        if len(SuperEntityCompCls._RegisterMap) == 0:
            # 初始化自动组件注册管理
            ListenForEvent(Events.AddEntityServerEvent, SuperEntityCompCls, SuperEntityCompCls._AutoAddEntityServerEvent)
        return _register
    
    @staticmethod
    def _AutoAddEntityServerEvent(args):
        data = Events.AddEntityServerEvent(args)
        if not data.engineTypeStr in SuperEntityCompCls._EntityRegisterMap:
            return
        for compPath in SuperEntityCompCls._EntityRegisterMap[data.engineTypeStr]:
            compCls = SuperEntityCompCls._RegisterMap[compPath]
            try:
                compCls.creat(data.id)
            except:
                pass

    @classmethod
    def creat(cls, entityId, *args, **kwargs):
        # type: (str, tuple, dict) -> bool
        """ 创建组件 如果已存在则返回False """
        comp = cls.GetComp(entityId)    # type: SuperEntityCompCls | None
        if comp != None:
            return False
        comp = cls(entityId, *args, **kwargs)
        comp._create()
        return True
    
    @classmethod
    def create(cls, entityId, *args, **kwargs):
        """ 创建组件 如果已存在则返回False """
        return cls.creat(entityId, *args, **kwargs)
    
    @classmethod
    def getSubComps(cls, entityId):
        """ 获取指定实体当前组件以及所有的成员组件(继承组件) """
        def deepComps(compCls):
            # type: (type[SuperEntityCompCls]) -> list[SuperEntityCompCls]
            comp = compCls.GetComp(entityId)
            if comp != None:
                yield comp
            for childCompCls in compCls.__subclasses__():
                for x in deepComps(childCompCls):
                    yield x
        return deepComps(cls)
    
    @classmethod
    def getSubComp(cls, entityId):
        # type: (str) -> SuperEntityCompCls | None
        """ 获取包含成员组件(继承组件)在内的任意一个组件 不存在则返回None """
        gen = cls.getSubComps(entityId)
        try:
            return next(gen)
        except:
            return None

    def _create(self):
        pass

    def __init__(self, entityId):
        EntityCompCls.__init__(self, entityId)
        self.__timerList = []   # type: list[SuperEntityCompCls.Timer]
        self.__sleepState = False
        self.__isDelComp = False

    def addTimer(self, timer):
        # type: (Timer) -> bool
        """ 添加定时器 (同一份定时器不允许多次添加,如有需要可使用定时器的copy方法) """
        if timer in self.__timerList:
            return False
        self.__timerList.append(timer)
        return True
    
    def removeTimer(self, timer):
        # type: (Timer) -> bool
        """ 删除定时器 """
        if not timer in self.__timerList:
            return False
        self.__timerList.remove(timer)
        return True

    def OnTick(self):
        EntityCompCls.OnTick(self)
        # timer定时器处理
        delTimerList = []  # type: list[SuperEntityCompCls.Timer]
        tickTime = 1.0/30.0
        for timer in self.__timerList:
            timer.valueTime -= tickTime
            if timer.valueTime <= 0.0:
                timer.call()
                if timer.loop == False:
                    # 标记删除定时器
                    delTimerList.append(timer)
                else:
                    # 重置定时器
                    timer.valueTime = timer.setTime
        for timer in delTimerList:
            self.removeTimer(timer)

    def callEvent(self, eventName):
        """ 执行自身的json event """
        comp = serverApi.GetEngineCompFactory().CreateEntityEvent(self.entityId)
        return comp.TriggerCustomEvent(self.entityId, eventName)
    
    def setSleepState(self, state):
        # type: (bool) -> bool
        """ 设置休眠状态 (不推荐)

            处于休眠状态下的组件实例依旧存在 但不会被组件管理器驱动工作
            不会进入Tick更新, 生物死亡后不会智能回收
            可以被查询与获取
        """
        if self.__sleepState == state:
            return False
        self.__sleepState = state
        if state == True:
            try:
                # 从组件管理器中移除自己的存档 此时将不会被tick驱动/智能回收
                EntityCompController.RemoveEntityComp(self.entityId, self)
                sleepCompList = EntityCompController.EntityCompSleepDic.get(self.entityId, [])
                sleepCompList.append(self)
                EntityCompController.EntityCompSleepDic[self.entityId] = sleepCompList
            except:
                return False
            EntityCompController.TryExec(self.onSleep)
        else:
            try:
                # 在组件管理器中添加自己的存档
                EntityCompController.AddEntityComp(self.entityId, self)
                sleepCompList = EntityCompController.EntityCompSleepDic.get(self.entityId, [])
                if self in sleepCompList:
                    sleepCompList.remove(self)
            except:
                return False
            if self.__isDelComp: return True
            EntityCompController.TryExec(self.onUnSleep)
        return True
    
    def getSleepState(self):
        # type: () -> bool
        """ 获取休眠状态 """
        return self.__sleepState

    def tryRemoveComp(self, compCls):
        # type: (type[EntityCompCls]) -> bool
        """ 尝试删除当前实体的指定组件 """
        comp = compCls.GetComp(self.entityId)    # type: EntityCompCls
        if comp:
            comp.RemoveComp()
            return True
        return False

    def onSleep(self):
        """ 休眠回调方法 可覆写 """

    def onUnSleep(self):
        """ 结束休眠回调方法 可覆写 """

    def RemoveComp(self):
        self.__isDelComp = True
        if self.getSleepState():
            self.setSleepState(False)
        return EntityCompCls.RemoveComp(self)

class EntityStateCompCls(SuperEntityCompCls):
    """ [实验性] 状态组件类
        使用状态组件请务必调用create方法完成
        PS: 该组件类为实验性功能 可能在未来修改结构亦或者实现
    """
    __entryKey__ = "__quEntry__"
    entryCls = None                     # type: type[EntityStateCompCls] | None
    childCls = set()                    # type: set[type[EntityStateCompCls]]
    parentCls = None                    # type: type[EntityStateCompCls] | None

    @classmethod
    def _initRes(cls):
        """ 内部使用 初始化资源 """
        if not cls.childCls is EntityStateCompCls.childCls:
            return
        # 初始化子类集合
        cls.childCls = set()
        for key in dir(cls):
            value = getattr(cls, key)
            if value and hasattr(value, "__entryKey__"):
                # 是class
                if cls.parentCls == value:
                    continue
                try:
                    cls.childCls.add(value)
                    value.parentCls = cls
                    if hasattr(value, EntityStateCompCls.__entryKey__):
                        cls.entryCls = value
                except Exception as e:
                    print(e)

    @staticmethod
    def Entry(obj):
        """ 入口装饰器 修饰子状态默认入口 """
        setattr(obj, EntityStateCompCls.__entryKey__, True)
        return obj

    def __init__(self, entityId):
        SuperEntityCompCls.__init__(self, entityId)
        self.__class__._initRes()
        self.usingState = None      # type: EntityStateCompCls | None
        self.onEntry()
    
    def _create(self):
        """ 初始化进入状态 """
        SuperEntityCompCls._create(self)
        entryCls = self.__class__.entryCls
        if entryCls == None:
            return
        entryCls.creat(self.entityId)
        self.usingState = entryCls.GetComp(self.entityId)

    def onEntry(self):
        """ 进入状态触发回调 """

    def onExit(self):
        """ 退出状态触发回调 """
    
    def transformState(self, state):
        # type: (type[EntityStateCompCls]) -> bool
        """ 在当前状态层切换状态 """
        parent = self.parent
        if parent == None:
            print("{} 无有效同级状态可供切换".format(self))
            return False
        parentCls = parent.__class__
        if state == None in parentCls.childCls:
            print("{} 无效的状态切换 亦或者不在同一状态层 请检查".format(self))
            return False
        # 创建状态组件
        if parent.usingState != None:
            if parent.usingState.__class__ == state:
                # 已在当前状态无需切换
                return False
            parent.usingState.RemoveComp()
            parent.usingState = None
        state.creat(self.entityId)
        parent.usingState = state.GetComp(self.entityId)
        return True
        
    @property
    def parent(self):
        # type: () -> EntityStateCompCls | None
        """ 获取当前状态父节点 如果存在 """
        parentCls = self.__class__.parentCls
        if parentCls != None:
            return parentCls.GetComp(self.entityId)
        return None

    @property
    def childs(self):
        # type: () -> list[EntityStateCompCls]
        """ 获取所有子节点实例 """
        for compCls in self.__class__.childCls:
            comp = compCls.GetComp(self.entityId)
            if comp != None:
                yield comp
    
    def OnRemove(self):
        SuperEntityCompCls.OnRemove(self)
        try:
            self.onExit()
        except Exception as e:
            print("[Error] {} 在 onExit 方法下发生了异常 {}".format(self, e))
        for comp in self.childs:
            comp.RemoveComp()

class ProjectileHitComponent(SuperEntityCompCls):
    """ 抛射物碰撞代理组件 """

    _enable = False
    _entityQuoteMaps = {}       # type: dict[str, int]
    """ 实体引用表 记录实体抛射组件施加次数 以便剔除与优化 """

    @staticmethod
    def _getAllProjectileHitComponent(entityId):
        # type: (str) -> list[ProjectileHitComponent]
        for comp in ProjectileHitComponent.getSubComps(entityId):
            if isinstance(comp, ProjectileHitComponent):
                yield comp

    @staticmethod
    def _ProjectileDoHitEffectEvent(args):
        """ 抛射物碰撞引擎事件 """
        entityId = args["id"]
        if not entityId in ProjectileHitComponent._entityQuoteMaps:
            return
        entityPos = (args["x"], args["y"], args["z"])
        hitTargetType = args["hitTargetType"]
        if hitTargetType == "BLOCK":
            # 方块处理
            hitFace = args["hitFace"]
            blockPos = (args["blockPosX"], args["blockPosY"], args["blockPosZ"])
            for comp in ProjectileHitComponent._getAllProjectileHitComponent(entityId):
                comp.hitPos = entityPos
                try:
                    comp.onHitBlock(blockPos, hitFace)
                except Exception as e:
                    errorPrint("{} 在方块碰撞时发生异常 {}".format(comp, e))
        elif hitTargetType == "ENTITY":
            # 实体处理
            targetId = args["targetId"]
            for comp in ProjectileHitComponent._getAllProjectileHitComponent(entityId):
                comp.hitPos = entityPos
                try:
                    comp.onHitEntity(targetId)
                except Exception as e:
                    errorPrint("{} 在实体碰撞时发生异常 {}".format(comp, e))
    
    @staticmethod
    def _enableEvent():
        """ 启用全局事件管理 """
        if ProjectileHitComponent._enable == False:
            ProjectileHitComponent._enable = True
            ListenForEvent(Events.ProjectileDoHitEffectEvent, ProjectileHitComponent, ProjectileHitComponent._ProjectileDoHitEffectEvent)

    def __init__(self, entityId):
        SuperEntityCompCls.__init__(self, entityId)
        self.sourceId = serverApi.GetEngineCompFactory().CreateBulletAttributes(self.entityId).GetSourceEntityId()
        """ 抛射物源ID 通常指物主 """
        self.hitPos = (0, 0, 0)                  # type: tuple[float]
        """ 碰撞坐标 由引擎提供 """
        ProjectileHitComponent._enableEvent()
        
        # 引用计数
        if not entityId in ProjectileHitComponent._entityQuoteMaps:
            ProjectileHitComponent._entityQuoteMaps[entityId] = 0
        ProjectileHitComponent._entityQuoteMaps[entityId] += 1

    def onHitEntity(self, targetId):
        """ 抛射物碰撞实体触发 """
        pass

    def onHitBlock(self, blockPos, hitFace = -1):
        """ 抛射物碰撞方块触发 """
        pass
    
    def OnRemove(self):
        SuperEntityCompCls.OnRemove(self)

        # 引用计数减消 实现自动回收
        if not self.entityId in ProjectileHitComponent._entityQuoteMaps:
            return
        
        ProjectileHitComponent._entityQuoteMaps[self.entityId] -= 1
        if ProjectileHitComponent._entityQuoteMaps[self.entityId] <= 0:
            del ProjectileHitComponent._entityQuoteMaps[self.entityId]

class EntityComponent(SuperEntityCompCls):
    """ [Beta] 实体代理组件 """

    _enable = False
    _entityQuoteMaps = {}       # type: dict[str, int]
    """ 实体引用表 """

    @staticmethod
    def _getAllEntityComponent(entityId):
        # type: (str) -> list[EntityComponent]
        for comp in EntityComponent.getSubComps(entityId):
            if isinstance(comp, EntityComponent):
                yield comp
    
    @staticmethod
    def _ActuallyHurtServerEvent(args):
        hurtOtherId = args["srcId"]
        hurtEntityId = args["entityId"]
        if hurtOtherId in EntityComponent._entityQuoteMaps:
            # 实体伤害他人
            for comp in EntityComponent._getAllEntityComponent(hurtOtherId):
                try:
                    comp.hurtServerEvent = args
                    comp.onHurtOther(hurtEntityId)
                except Exception as e:
                    errorPrint("组件在onHurtOther事件发生异常 {}".format(e))

        if hurtEntityId in EntityComponent._entityQuoteMaps:
            # 实体受伤
            for comp in EntityComponent._getAllEntityComponent(hurtEntityId):
                try:
                    comp.hurtServerEvent = args
                    comp.onHurt(hurtOtherId)
                except Exception as e:
                    errorPrint("组件在onHurt事件发生异常 {}".format(e))

    @staticmethod
    def _enableEvent():
        """ 启用全局事件管理 """
        if EntityComponent._enable == False:
            EntityComponent._enable = True
            ListenForEvent(Events.ActuallyHurtServerEvent, EntityComponent, EntityComponent._ActuallyHurtServerEvent)

    def __init__(self, entityId):
        SuperEntityCompCls.__init__(self, entityId)
        self.entityObj = Entity(entityId)
        self.hurtServerEvent = {}                   # type: dict
        """ 由引擎传递的上一次受伤事件args """
        EntityComponent._enableEvent()
        
        # 引用计数
        if not entityId in EntityComponent._entityQuoteMaps:
            EntityComponent._entityQuoteMaps[entityId] = 0
        EntityComponent._entityQuoteMaps[entityId] += 1

    def onHurt(self, targetId = None):
        """ 受伤事件 """
        pass
    
    def onHurtOther(self, targetId = None):
        """ 实体对他人造成伤害事件 """
        pass

    def OnRemove(self):
        SuperEntityCompCls.OnRemove(self)

        # 引用计数减消 实现自动回收
        if not self.entityId in EntityComponent._entityQuoteMaps:
            return
        
        EntityComponent._entityQuoteMaps[self.entityId] -= 1
        if EntityComponent._entityQuoteMaps[self.entityId] <= 0:
            del EntityComponent._entityQuoteMaps[self.entityId]