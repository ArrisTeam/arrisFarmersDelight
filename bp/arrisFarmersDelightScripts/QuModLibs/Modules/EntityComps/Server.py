# -*- coding: utf-8 -*-
from ...Server import serverApi, Entity, levelId
from ...Util import TRY_EXEC_FUN, UniversalObject
from ...IN import ModDirName
from ..Services.Server import BaseService
from Globals import (
    QUnBindIN,
    _QBaseEntityComp,
    QEntityCompFlags,
    QEntityRuntime,
)
from BehaviorTree import _QBaseTaskNode, QBaseNode, QSharedData
from copy import copy
import weakref
lambda: "By Zero123"
_USE_SAVE_KEY = "{}_QComps".format(ModDirName)
universalObject = UniversalObject()

_gameComp = serverApi.GetEngineCompFactory().CreateGame(levelId)

class QEntityCompService(BaseService):
    def __init__(self):
        BaseService.__init__(self)
        self.entityCompMap = {}         # type: dict[str, QEntityRuntime]
        self.entityDefaultCompMap = {}  # type: dict[str, dict[str, type[QBaseEntityComp]]]
        self._closeState = False

    def getMemoryLiveState(self, entityId):
        """ 获取实体是否处于内存状态中 """
        # comp = serverApi.GetEngineCompFactory().CreateModAttr(entityId)
        # return comp.GetAttr(_USE_SAVE_KEY, None) != None
        return _gameComp.IsEntityAlive(entityId)

    def getEntityRuntime(self, entityId=""):
        """ 获取实体运行时管理对象 """
        if self._closeState:
            # 游戏关闭后为确保资源安全将无法再次获取实体运行时数据
            return None
        alive = _gameComp.IsEntityAlive(entityId)
        if not alive:
            return None
        if not entityId in self.entityCompMap:
            # ========== 初始化实体资源数据 ==========
            # comp = serverApi.GetEngineCompFactory().CreateModAttr(entityId)
            # if comp.GetAttr(_USE_SAVE_KEY) == None:
            #     comp.SetAttr(_USE_SAVE_KEY, {})
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
    
    @BaseService.Listen("EntityRemoveEvent")
    def EntityRemoveEvent(self, args={}):
        entityId = args["id"]
        self.removeEntityRuntimeObjects(entityId)
    
    @BaseService.Listen("AddEntityServerEvent")
    def AddEntityServerEvent(self, args={}):
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

class QEntityAttrData:
    def __init__(self, bindKey="", needRestore=False, defaultValue=None):
        self.entityId = None
        self.bindKey = bindKey
        self.needRestore = needRestore
        self.defaultValue = defaultValue
        self.value = defaultValue

    def bindEntityId(self, entityId=""):
        """ 绑定实体Id """
        self.entityId = entityId
        self.getValue(False)
        return self

    def _getSaveData(self):
        comp = serverApi.GetEngineCompFactory().CreateModAttr(self.entityId)
        data = comp.GetAttr(_USE_SAVE_KEY, dict())
        if not isinstance(data, dict):
            data = dict()
        return data

    def _setSaveData(self, newData=None):
        comp = serverApi.GetEngineCompFactory().CreateModAttr(self.entityId)
        if not isinstance(newData, dict):
            newData = dict()
        comp.SetAttr(_USE_SAVE_KEY, newData, self.needRestore)

    def getValue(self, useCache=True):
        """ 读取属性 """
        if not useCache:
            self.value = self._getSaveData().get(self.bindKey, self.defaultValue)
        return self.value

    def setValue(self, newValue=None):
        """ 设置属性 """
        self.value = newValue
        self.update()

    def update(self):
        """ 更新属性 """
        if not self.entityId:
            return
        data = self._getSaveData()
        data[self.bindKey] = self.value
        self._setSaveData(data)

class QBaseEntityComp(_QBaseEntityComp):
    def __init__(self):
        _QBaseEntityComp.__init__(self)
        self._useSaveKey = _USE_SAVE_KEY
        self.entityObj = None   # type: Entity | None
        self._lastServerTickTime = 0.0
        self._compAttrSet = set()   # type: set[QEntityAttrData]

    def getNeedUpdate(self):
        # MC服务端引擎帧率为20Tick 网易MODSDK在此基础上插值魔改了30Tick 通过重复判断剔除掉无用tick 针对update方法将会是纯引擎帧
        newTime = serverApi.GetServerTickTime()
        lastTime = self._lastServerTickTime
        self._lastServerTickTime = newTime
        if newTime == lastTime:
            return False
        return True

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
        alive = _gameComp.IsEntityAlive(entityId)
        if not alive or not self._preVerification(entityId):
            return False
        self.entityId = entityId
        self.entityObj = Entity(entityId)
        TRY_EXEC_FUN(self._onBind)
        return True

    def getCanRender(self):
        _eObj = self.entityObj
        if not _eObj:
            return False
        return _eObj.getNearPlayer() != None

    def _malloc(self):
        QEntityCompService.access().getEntityRuntime(self.entityId).addComp(self.getTypeName(), self)

    def _free(self):
        QEntityCompService.access().getTempEntityRuntimeObject(self.entityId).removeComp(self.getTypeName(), self)

    def saveAttrNow(self):
        # type: () -> None
        """ 立即储存当前实体通过Attr设置的持久化数据 """
        if not self.entityId:
            return
        comp = serverApi.GetEngineCompFactory().CreateModAttr(self.entityId)
        comp.SaveAttr()

    def _onBind(self):
        entityId = self.entityId
        if len(self._compAttrSet) > 0:
            try:
                for obj in self._compAttrSet:
                    obj.bindEntityId(entityId)
            except Exception as e:
                print(e)
        return _QBaseEntityComp._onBind(self)
    
    def _onUnBindLast(self):
        for obj in self._compAttrSet:
            obj.entityId = None
            obj.value = None
        return _QBaseEntityComp._onUnBindLast(self)

    def createSharedAttr(self, attrName="default", defaultValue=None, needRestore=False):
        """ 创建一个共享属性 所有的组件能够共同读取访问 """
        _data = QEntityAttrData(attrName, needRestore, defaultValue)
        self._compAttrSet.add(_data)
        return _data

    def createPrivateAttr(self, attrName="default", defaultValue=None, needRestore=False, useShortName=True):
        """ 创建一个私有属性 仅同cls/显性注册类型名的组件能够访问 """
        _typeName = self.getTypeName()
        if useShortName:
            _typeName = "{}_{}".format(self.__class__.__name__, hash(_typeName))
        return self.createSharedAttr("{}_{}".format(_typeName, attrName), defaultValue, needRestore)

class QBaseEntiyTaskNode(_QBaseTaskNode):
    """ [行为树] 实体Task节点基类
        - Task节点受时间精度所需 对应的QBehaviorTreeEntityComp默认使用网易30Tick
        您也可以重写实现 以便切换到20Tick

        - 默认情况下Task节点提供的内置定时器会在onStop期间自动销毁 如有暂停需求需另行实现
    """
    def __init__(self):
        _QBaseTaskNode.__init__(self)
        self._bindComp = None   # type: QBehaviorTreeEntityComp | None

    def onParentCompUnBind(self):
        """ 
            父集组件解除实体绑定时触发的处理(不会触发onStop 除非显性需求调用)
            该方法仅限节点进入update过程期间触发 (即onStart-onStop状态区间内)
        """
        pass

    def getEntityId(self):
        # type: () -> str
        """ 获取实体Id """
        return self._bindComp.entityId

    def getBindComp(self):
        # type: () -> QBehaviorTreeEntityComp
        """ 获取绑定的组件 """
        return self._bindComp

    def getEntityObj(self):
        # type: () -> Entity
        """ 获取实体对象 """
        return self._bindComp.entityObj

    def _evaluate(self, sharedData):
        # type: (QSharedData) -> int
        self._bindComp = sharedData.getValue("_bindQComp")
        state = _QBaseTaskNode._evaluate(self, sharedData)
        self._bindComp = None
        return state

class QBehaviorTreeEntityComp(QBaseEntityComp):
    """ [行为树] 实体组件类 """
    _NULL_SET = set()
    class TaskNodeArgs:
        def __init__(self, node, sharedData):
            # type: (QBaseEntiyTaskNode, QSharedData) -> None
            self.node = node
            self.sharedData = sharedData

    def __init__(self):
        QBaseEntityComp.__init__(self)
        self._rootNodeList = []     # type: list[QBehaviorTreeEntityComp.TaskNodeArgs]

    def createNodeSharedData(self):
        """ 创建节点所需的共享对象 默认返回QSharedData
            - QSharedData为运行时对象在实体被内存回收后也会跟着回收 可通过重写实现自定义数据容器作持久化储存
        """
        return QSharedData()

    def addRootNode(self, node=QBaseNode()):
        """ 添加运行时根节点(推荐在__init__初始化期间添加)返回TaskNodeArgs可操作相关共享数据 """
        _args = QBehaviorTreeEntityComp.TaskNodeArgs(node, self.createNodeSharedData())
        self._rootNodeList.append(_args)
        if self.entityId:
            # onBind后添加 单独绑定组件
            _args.sharedData.setValue("_bindQComp", self)
        return _args

    def onGameTick(self):
        QBaseEntityComp.onGameTick(self)
        self._updateRootNodeList()

    def onBind(self):
        QBaseEntityComp.onBind(self)
        self._rootNodesAllSetData("_bindQComp", self)

    def onUnBind(self):
        QBaseEntityComp.onUnBind(self)
        self._rootNodeUnBindEvent()
        self._rootNodesAllSetData("_bindQComp", None)

    def _rootNodesAllSetData(self, key, value):
        """ 根节点全部写入对应的数据 """
        for args in self._rootNodeList:
            args.sharedData.setValue(key, value)

    def _updateRootNode(self, args, needUpdate=True):
        # type: (QBehaviorTreeEntityComp.TaskNodeArgs, bool) -> None
        """ 更新单个节点 """
        node = args.node
        sharedData = args.sharedData
        # 上一次更新的节点表
        lastFrameUpdateObjs = sharedData.getValue(QBaseEntiyTaskNode._TEMP_RUN_SET_KEY, QBehaviorTreeEntityComp._NULL_SET)   # type: set[QBaseEntiyTaskNode]
        # 清空更新日志
        sharedData.setValue(QBaseEntiyTaskNode._TEMP_RUN_SET_KEY, set())
        node.loadNodes(sharedData)
        # 新一次更新的节点表
        newFrameUpdateObjs = sharedData.getValue(QBaseEntiyTaskNode._TEMP_RUN_SET_KEY, QBehaviorTreeEntityComp._NULL_SET)    # type: set[QBaseEntiyTaskNode]

        # 对照新增onStop状态
        for oldObj in lastFrameUpdateObjs:
            if oldObj in newFrameUpdateObjs:
                continue
            oldObj._bindComp = self
            TRY_EXEC_FUN(oldObj._onStop)
            oldObj._bindComp = None

        # 对照新增onStart状态
        for newObj in newFrameUpdateObjs:
            if newObj in lastFrameUpdateObjs:
                continue
            newObj._bindComp = self
            TRY_EXEC_FUN(newObj._onStart)
            newObj._bindComp = None

        if needUpdate:
            # 触发update
            for obj in newFrameUpdateObjs:
                newObj._bindComp = self
                TRY_EXEC_FUN(obj._onUpdate)
                newObj._bindComp = None

    def _updateRootNodeList(self):
        """ 更新Root节点表 """
        for rootNode in self._rootNodeList:
            TRY_EXEC_FUN(self._updateRootNode, rootNode)

    def _rootNodeUnBindEvent(self):
        # 处理所有处于update状态下节点的onParentCompUnBind方法
        for rootNode in self._rootNodeList:
            TRY_EXEC_FUN(self._rootNodeUnBind, rootNode)

    def _rootNodeUnBind(self, nodeArgs):
        # type: (QBehaviorTreeEntityComp.TaskNodeArgs) -> None
        sharedData = nodeArgs.sharedData
        frameUpdateObjs = sharedData.getValue(QBaseEntiyTaskNode._TEMP_RUN_SET_KEY, QBehaviorTreeEntityComp._NULL_SET)   # type: set[QBaseEntiyTaskNode]
        for obj in frameUpdateObjs:
            obj._bindComp = self
            TRY_EXEC_FUN(obj.onParentCompUnBind)
            obj._bindComp = None

class QConstraintNodeComp(QBaseEntityComp):
    """ 约束节点组件
        约束节点允许建立父子集绑定关系以便关联回收/实现有限状态机等机制
    """
    def __init__(self):
        QBaseEntityComp.__init__(self)
        self._parentRef = None
        self._childNodeSet = set()  # type: set[QConstraintNodeComp]

    def onBind(self):
        QBaseEntityComp.onBind(self)
        # 状态节点在被构造时理应将自己添加到父集的子节点管理集合中以便回收
        parent = self.getParent()
        if parent:
            parent._childNodeSet.add(self)

    def onUnBind(self):
        QBaseEntityComp.onUnBind(self)
        # 回收自己的所有子节点
        for node in copy(self._childNodeSet):
            TRY_EXEC_FUN(node.unbind)
        # 从自己所在的父节点回收自己
        parent = self.getParent()
        if parent and self in parent._childNodeSet:
            parent._childNodeSet.remove(self)

    def setParent(self, parentObj):
        # type: (QConstraintNodeComp) -> None
        """ 设置父节点 """
        self._parentRef = weakref.ref(parentObj)

    def getParent(self):
        # type: () -> QConstraintNodeComp | None
        """ 获取父节点 """
        if self._parentRef:
            return self._parentRef()
        return None

    def getChildsRef(self):
        """ 获取子节点集合引用 """
        return self._childNodeSet

    def addConstraintNode(self, node):
        # type: (QConstraintNodeComp) -> bool
        """ 添加并绑定一个约束节点到子集 """
        node.setParent(self)
        return node.bind(self.entityId)

    def transferConstraint(self, node):
        # type: (QConstraintNodeComp) -> bool
        """ 转移约束到另外一个节点(将会解除自己) """
        if not node._preVerification(self.entityId):
            # 新组件受权限声明/其他原因未能通过绑定验证
            return False
        TRY_EXEC_FUN(self.unbind)
        return self.getParent().addConstraintNode(node)

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