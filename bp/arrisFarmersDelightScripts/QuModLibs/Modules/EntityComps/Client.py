# -*- coding: utf-8 -*-
from ...Client import clientApi, Entity, levelId
from ...Util import TRY_EXEC_FUN, UniversalObject
from ...IN import ModDirName
from ..Services.Client import BaseService
from Globals import (
    QUnBindIN,
    _QBaseEntityComp,
    QEntityCompFlags,
    QEntityRuntime,
)
from copy import copy
lambda: "By Zero123"
_USE_SAVE_KEY = "{}_QComps".format(ModDirName)
universalObject = UniversalObject()

_gameComp = clientApi.GetEngineCompFactory().CreateGame(levelId)

class QEntityCompService(BaseService):
    def __init__(self):
        BaseService.__init__(self)
        self.entityCompMap = {}     # type: dict[str, QEntityRuntime]
        self.entityDefaultCompMap = {}  # type: dict[str, dict[str, type[QBaseEntityComp]]]
        self._closeState = False

    @BaseService.Listen("AddEntityClientEvent")
    def AddEntityClientEvent(self, args={}):
        engineTypeStr = args["engineTypeStr"]
        if not engineTypeStr in self.entityDefaultCompMap:
            return
        entityId = args["id"]
        compsMap = self.entityDefaultCompMap[engineTypeStr]
        for v in compsMap.values():
            _comp = TRY_EXEC_FUN(v)
            if not _comp:
                continue
            TRY_EXEC_FUN(_comp.bind, entityId)

    def getMemoryLiveState(self, entityId):
        """ 获取实体是否处于内存状态中 """
        # comp = clientApi.GetEngineCompFactory().CreateGame(levelId)
        # alive = comp.HasEntity(entityId)
        return _gameComp.HasEntity(entityId)

    def getEntityRuntime(self, entityId=""):
        """ 获取实体运行时管理对象 """
        if self._closeState:
            # 游戏关闭后为确保资源安全将无法再次获取实体运行时数据
            return None
        if not self.getMemoryLiveState(entityId):
            return None
        if not entityId in self.entityCompMap:
            # ========== 初始化实体资源数据 ==========
            newObj = QEntityRuntime(entityId)
            self.entityCompMap[entityId] = newObj
            return newObj
        return self.entityCompMap[entityId]
    
    def getTempEntityRuntimeObject(self, entityId=""):
        if entityId in self.entityCompMap:
            return self.entityCompMap[entityId]
        return QEntityRuntime(None)
    
    def removeEntityRuntimeObjects(self, entityId=""):
        """ 删除实体所有运行时数据 """
        if not entityId in self.entityCompMap:
            return
        runObj = self.entityCompMap[entityId]
        del self.entityCompMap[entityId]
        runObj.onFree(QUnBindIN(QUnBindIN.MOB_AUTO_REMOVED))
    
    @BaseService.Listen("RemoveEntityClientEvent")
    def RemoveEntityClientEvent(self, args={}):
        entityId = args["id"]
        self.removeEntityRuntimeObjects(entityId)

    def onServiceUpdate(self):
        BaseService.onServiceUpdate(self)
        # Tick事件触发器
        if not self.entityCompMap:
            return
        for obj in copy(self.entityCompMap).values():
            entityId = obj.entityId
            if not self.getMemoryLiveState(entityId) or obj.empty():
                self.removeEntityRuntimeObjects(entityId)
                continue
            TRY_EXEC_FUN(obj.onTick)

    def onServiceStop(self):
        BaseService.onServiceStop(self)
        self._closeState = True
        # 游戏关闭后释放所有实体运行时数据
        for v in copy(self.entityCompMap).values():
            TRY_EXEC_FUN(v.onFree)
        self.entityCompMap = {}

class QBaseEntityComp(_QBaseEntityComp):
    def __init__(self):
        _QBaseEntityComp.__init__(self)
        self._useSaveKey = _USE_SAVE_KEY
        self.entityObj = None   # type: Entity | None

    @staticmethod
    def regEntity(*entityTypeName):
        """ 装饰器 注册实体初始组件 """
        def __regEntity(cls):
            compCls = cls   # type: QBaseEntityComp
            compTypeName = compCls.getTypeUID()
            _service = QEntityCompService.access()
            if _service:
                compMap = _service.entityDefaultCompMap
                for entityType in entityTypeName:
                    _map = compMap.get(entityType, {})
                    if compTypeName in _map:
                        continue
                    _map[compTypeName] = cls
                    compMap[entityType] = _map
            return cls
        return __regEntity

    @classmethod
    def getComp(cls, entityId=""):
        """ 获取特定实体的单个组件实例 如果存在 """
        if 1 > 2:
            return cls()
        return QEntityCompService.access().getTempEntityRuntimeObject(entityId).getComp(cls.getTypeUID())

    @classmethod
    def getComps(cls, entityId=""):
        """ 获取实体的所有指定组件(非单例组件模式下使用) 返回浅层拷贝的集合 """
        if 1 > 2:
            return set([cls()])
        return QEntityCompService.access().getTempEntityRuntimeObject(entityId).getComps(cls.getTypeUID())

    @classmethod
    def getCompsGen(cls, entityId=""):
        """ 获取实体的所有指定组件(非单例组件模式下使用) 返回生成器对象 """
        if 1 > 2:
            return set([cls()])
        return QEntityCompService.access().getTempEntityRuntimeObject(entityId).getCompsGen(cls.getTypeUID())

    @classmethod
    def getSubComps(cls, entityId=""):
        """ 获取所有相关的子集组件(包括自己) """
        if 1 > 2:
            return set([cls()])
        return set(QEntityCompService.access().getTempEntityRuntimeObject(entityId).subCompsGen(cls))

    @classmethod
    def getSubComp(cls, entityId=""):
        """ 获取一条相关的子集组件(包括自己)实例, 如若不存在则返回None """
        if 1 > 2:
            return cls()
        subComp = None
        try:
            subComp = next(QEntityCompService.access().getTempEntityRuntimeObject(entityId).subCompsGen(cls))
        except:
            pass
        return subComp

    @classmethod
    def getTempSubComp(cls, entityId=""):
        """ 获取向下的临时组件操作对象 (当getSubComp返回None时将会抛出一个万能对象确保无None值安全操作) """
        subComp = cls.getSubComp(entityId)
        if subComp:
            return subComp
        return universalObject

    @classmethod
    def hasComp(cls, entityId=""):
        """ 获取目标实体是否持有该组件 """
        if cls.getComp(entityId) == None:
            return False
        return True

    @classmethod
    def removeComp(cls, entityId=""):
        """ 从特定实体身上移除特定组件 如果存在 """
        comp = cls.getComp(entityId)
        if comp:
            comp.unbind()

    @classmethod
    def removeAllComps(cls, entityId=""):
        """ 从特定实体身上移除所有特定组件 适用于非单例的实体组件 """
        for comp in cls.getComps(entityId):
            TRY_EXEC_FUN(comp.unbind)

    def _preVerification(self, tempEntityId=""):
        """ 组件绑定的预验证 如限制生物至多持有1例同类型组件 """
        if (self.__class__.FLAGS & 0x01) == 0x01:
            return True
        runTime = QEntityCompService.access().getTempEntityRuntimeObject(tempEntityId)
        return not runTime.hasTypeComp(self.getTypeName())

    def bind(self, entityId=""):
        if self.entityId:
            return False
        # comp = clientApi.GetEngineCompFactory().CreateGame(levelId)
        alive = _gameComp.HasEntity(entityId)
        if not alive or not self._preVerification(entityId):
            return False
        self.entityId = entityId
        self.entityObj = Entity(entityId)
        TRY_EXEC_FUN(self._onBind)
        return True

    def _malloc(self):
        QEntityCompService.access().getEntityRuntime(self.entityId).addComp(self.getTypeName(), self)

    def _free(self):
        QEntityCompService.access().getTempEntityRuntimeObject(self.entityId).removeComp(self.getTypeName(), self)

class EntityCacheData(QBaseEntityComp):
    """ 实体缓存数据 """
    def __init__(self):
        QBaseEntityComp.__init__(self)
        self._cacheMap = dict()

    def onBind(self):
        QBaseEntityComp.onBind(self)
        self.addTimer(QBaseEntityComp.Timer(self.checkData, time=1.0, loop=True))

    def checkData(self):
        if not self._cacheMap:
            self.unbind()

    @staticmethod
    def getCacheMap(entityId):
        """ 获取实体缓存Map (为考虑性能优化 空缓存表会被自动清理 每次操作前都建议实时获取) """
        return EntityCacheData.getEntityCacheComp(entityId)._cacheMap

    @staticmethod
    def getEntityCacheComp(entityId):
        comp = EntityCacheData.getComp(entityId)
        if comp:
            return comp
        newComp = EntityCacheData()
        newComp.bind(entityId)
        return newComp