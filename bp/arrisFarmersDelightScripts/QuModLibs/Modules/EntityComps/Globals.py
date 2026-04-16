# -*- coding: utf-8 -*-
from ...Util import TRY_EXEC_FUN
from ..Services.Globals import TimerLoader
from copy import copy
lambda: "By Zero123"

class QUnBindIN:
    """ 组件解除绑定的信息参数 """
    GAMEOVER = -2
    OTHER = -1
    MOB_AUTO_REMOVED = 0
    REMOVED_BY_SCRIPT = 1

    def __init__(self, state=-1):
        self.stateCode = state
    
    def isGameOver(self):
        return self.stateCode == QUnBindIN.GAMEOVER

    def isMobRemoved(self):
        return self.stateCode == QUnBindIN.MOB_AUTO_REMOVED

    def removedByScript(self):
        return self.stateCode == QUnBindIN.REMOVED_BY_SCRIPT

class QEntityCompFlags:
    ALLOW_DUPLICATES = 0x01
    """ 允许重复持有特定类型的组件 """
    IGNORE_RENDERING_STATUS = 0x02
    """ 忽略渲染状态 将会持久化工作(前提是实体存在与内存中) """

class _QBaseEntityComp(TimerLoader):
    FLAGS = 0x00
    _CUSTOM_UID_MAP = {}    # type: dict[type, str]
    def __init__(self):
        TimerLoader.__init__(self)
        self.entityId = None
        self._unBindIN = QUnBindIN()
        self.entityObj = None

    @staticmethod
    def compTypeName(typeName="customComp"):
        def __customCompTypeName(compCls):
            _QBaseEntityComp._CUSTOM_UID_MAP[id(compCls)] = typeName
            return compCls
        return __customCompTypeName

    @staticmethod
    def setFlags(_newFlags = 0x00):
        def __setFlags(compCls):
            setattr(compCls, "FLAGS", _newFlags)
            return compCls
        return __setFlags

    @classmethod
    def create(cls, entityId, *args, **kwargs):
        """ 构造并绑定组件到特定实体 """
        comp = cls(*args, **kwargs)
        comp.bind(entityId)
        return comp

    def getUnBindINFO(self):
        # type: () -> QUnBindIN
        """ 获取解绑信息 """
        return self._unBindIN
    
    def getEntityId(self):
        # type: () -> str | None
        """ 获取实体Id(仅在bind后才能拿到) """
        return self.entityId
    
    def bind(self, entityId=""):
        # type: (str) -> bool
        self.entityId = entityId
        return True

    def rebind(self, entityId=""):
        # type: (str) -> bool
        """ 重新绑定(自动解除上一位实体的绑定) """
        if entityId == self.entityId:
            return False
        if self.entityId:
            self.unbind()
        return self.bind(entityId)
    
    def unbind(self, _info = QUnBindIN(QUnBindIN.REMOVED_BY_SCRIPT)):
        # type: (QUnBindIN) -> bool
        if self.entityId:
            self._unBindIN = _info
            self._onUnBind()
            return True
        return False
    
    def onBind(self):
        pass
    
    def onUnBind(self):
        pass

    # def onRepeatBindUpdate(self, other):
    #     # type: (_QBaseEntityComp) -> None
    #     pass

    def getNeedUpdate(self):
        # type: () -> bool
        return True

    def onGameTick(self):
        pass

    def update(self):
        pass
    
    def _onGameTick(self):
        if (self.__class__.FLAGS & 0x02) != 0x02 and not self.getCanRender():
            return False
        self.onGameTick()
        if self.getNeedUpdate():
            # update仅在需要更新时更新
            self.update()
        self._timerUpdate()

    def _onBind(self):
        self._malloc()
        self.onBind()

    def _onUnBind(self):
        self._clearAllTimer()
        self._free()

    def _onManagerFree(self):
        TRY_EXEC_FUN(self.onUnBind)
        self._onUnBindLast()

    def _onUnBindLast(self):
        self.entityId = None
        self.entityObj = None

    def getCanRender(self):
        return True

    def _malloc(self):
        pass

    def _free(self):
        pass

    @classmethod
    def getTypeUID(cls):
        _clsId = id(cls)
        if _clsId in _QBaseEntityComp._CUSTOM_UID_MAP:
            return _QBaseEntityComp._CUSTOM_UID_MAP[_clsId]
        return "{}.{}".format(cls.__module__, cls.__name__)
    
    def getTypeName(self):
        return self.__class__.getTypeUID()

class QEntityRuntime:
    def __init__(self, entityId=""):
        self.entityId = entityId
        self.compsMap = {}  # type: dict[str, set[_QBaseEntityComp]]

    def onTick(self):
        if not self.compsMap:
            return
        for v in copy(self.compsMap).values():
            for comp in copy(v):
                # 二次校验以便应对运行时的组件remove
                if not comp in v:
                    continue
                TRY_EXEC_FUN(comp._onGameTick)

    def empty(self):
        return len(self.compsMap) == 0

    def getCompsGen(self, compTypeName=""):
        """ 获取组件生成器(生成器为运行时态,使用生成器时请确保不会动态创建/销毁新的组件) """
        for comp in self.compsMap.get(compTypeName, []):
            yield comp

    def getComps(self, compTypeName=""):
        """ 获取所有组件的浅拷贝 """
        return copy(self.compsMap.get(compTypeName, set()))

    def getComp(self, compTypeName=""):
        """ 获取单个组件 """
        if self.hasTypeComp(compTypeName):
            return next(self.getCompsGen(compTypeName))
        return None

    def subCompsGen(self, targetCompCls=_QBaseEntityComp):
        """ 子组件生成器(无序) """
        for compSet in self.compsMap.values():
            if len(compSet) <= 0:
                continue
            for comp in compSet:
                if not isinstance(comp, targetCompCls):
                    break
                yield comp

    def hasTypeComp(self, compTypeName=""):
        """ 是否存在指定类别的组件 """
        return compTypeName in self.compsMap

    def addComp(self, compTypeName="", compObj=None):
        """ 添加组件 """
        if not compTypeName in self.compsMap:
            self.compsMap[compTypeName] = set()
        self.compsMap[compTypeName].add(compObj)
    
    def clearTypeName(self, compTypeName=""):
        if compTypeName in self.compsMap:
            if len(self.compsMap[compTypeName]) <= 0:
                del self.compsMap[compTypeName]
    
    def removeTypeComps(self, compTypeName=""):
        if not compTypeName in self.compsMap:
            return
        comps = self.compsMap[compTypeName]
        for comp in copy(comps):
            comps.remove(comp)
            TRY_EXEC_FUN(comp._onManagerFree)
        self.clearTypeName(compTypeName)

    def removeComp(self, compTypeName="", compObj=None):
        # type: (str, _QBaseEntityComp | None) -> None
        if not compTypeName in self.compsMap:
            return
        comps = self.compsMap[compTypeName]
        if not compObj in comps:
            return
        comps.remove(compObj)
        self.clearTypeName(compTypeName)
        TRY_EXEC_FUN(compObj._onManagerFree)

    def freeAllComps(self, _info=QUnBindIN(QUnBindIN.MOB_AUTO_REMOVED)):
        for _st in copy(self.compsMap).values():
            for v in copy(_st):
                v._unBindIN = _info
                TRY_EXEC_FUN(v._onManagerFree)
        self.compsMap = {}

    def onFree(self, _info=QUnBindIN(QUnBindIN.GAMEOVER)):
        self.freeAllComps(_info)