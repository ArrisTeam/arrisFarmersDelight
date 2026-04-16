# -*- coding: utf-8 -*-
from ...Server import *
from ...Util import TRY_EXEC_FUN
from ...Modules.Services.Server import BaseService, BaseEvent, serviceBroadcast
from SharedRes import (
    GL_OPT_INSTRUCT,
    GL_BASE_RES_OPT,
    GL_RES_OPT,
    JSONRenderData,
    GL_MOB_QUERY_KEY,
)
from copy import copy
from time import time
lambda: "GLR 全局资源处理系统 By Zero123 相比CTR它更侧重与玩家资源操作的本身"
lambda: "TIME: 2025/4/26"

class STATIC_IN:
    USE_PLAYER_LEVEL_GC = False

class LineAnim:
    def __init__(self, fromValue, toValue, useTime = 1.0):
        self._fromValue = fromValue
        self._toValue = toValue
        self._useTime = useTime
        self._moveValue = toValue - fromValue
        self._nowTime = 0.0
    
    def getRatio(self):
        # type: () -> float
        """ 获取当前进度比率 """
        if self._useTime <= 0.0:
            return 1.0
        return self._nowTime / self._useTime
    
    def getValue(self):
        # type: () -> float
        """ 获取当前线性插值结果 """
        return self._fromValue + self.getRatio() * self._moveValue

    def update(self):
        # type: () -> int
        """ 更新计算数据 """
        self._nowTime += 0.0333
        if self._nowTime > self._useTime:
            self._nowTime = self._useTime
            return -1
        return 0

class PLAYER_RES_LOAD_BEFORE(BaseEvent):
    def __init__(self, playerId="-1", opt=GL_BASE_RES_OPT()):
        BaseEvent.__init__(self)
        self.playerId = playerId
        self.resOpt = opt
        self.redirect = None
    
    def isModelRes(self):
        return self.resOpt._INSTRUCT_ID == 1

    def isAnimRes(self):
        return self.resOpt._INSTRUCT_ID == 3

class GL_PLAYER_RES:
    GL_RES_KEY = "Q_{}_GL.RES".format(ModDirName)
    GL_QUERY_KEY = "Q_{}_GL.QUERY".format(ModDirName)
    GL_REST_ANIM_KEY = "Q_{}_GL.REST_ANIM".format(ModDirName)
    DEFAULT_KEY = "default"
    DEFAULT_TEXTURE = "textures/entity/steve"
    DEFAULT_GEO = "geometry.humanoid.custom"
    DEFAULT_MAT = "entity_alphatest"

    def __init__(self, playerId, manager):
        # type: (str, GL_Service) -> None
        self.playerId = playerId
        self.entityId = playerId
        self.manager = manager
        self._optPass = []  # type: list[GL_BASE_RES_OPT]
        """ OPT_PASS 存储记录单帧内所有资源操作 """
        self._kvOpt = {}    # type: dict[str, GL_BASE_RES_OPT]
        """ 键值OPT操作 """
        self._queryMap = {}
        """ 存储记录自定义Query节点 """
        self.needUpdate = False
        """ 存储记录是否需要更新 """
        self.needUpdateQuery = False
        """ 存储记录是否需要更新节点 """
        self._lineQueryMap = {} # type: dict[str, LineAnim]
        """ 线性节点map """
        self._animUpdateSet = set()
        """ 动画更新集合 """
    
    def lineQueryUpdate(self):
        """ 线性节点更新 """
        for key, value in copy(self._lineQueryMap).items():
            if value.update() == -1:
                del self._lineQueryMap[key]
            v = value.getValue()
            self.setQuery(key, v, 3)
    
    def onTick(self):
        """ 每tick更新计算 """
        # ============ 资源与节点更新 ============
        if self.needUpdateQuery:
            TRY_EXEC_FUN(self.updateQuery)
        if self.needUpdate:
            TRY_EXEC_FUN(self.updateRender)
        # ============ 线性节点更新 ============
        self.lineQueryUpdate()
        if len(self._animUpdateSet) > 0:
            self._updateAnim()
            self._animUpdateSet.clear()

    def onCreate(self):
        """ 资源系统被初始化创建时触发 """
        pass

    def onEntityMemoryRelease(self):
        """ 实体在正常状态下被游戏释放触发 """
        pass

    def onServiceRelease(self):
        """ 服务因业务原因触发的释放 """
        pass

    def onRelease(self):
        """ 任意情况的释放触发 """
        pass

    def copyOptPass(self):
        """ 克隆资源通道数据 """
        return self._optPass[::]

    def setOptPass(self, _optPass, needUpdate = True):
        """ 设置资源通道数据 """
        self._optPass = _optPass[::]
        self.needUpdate = needUpdate

    def addOptPass(self, optObj, callEvent=True):
        # type: (GL_BASE_RES_OPT, bool) -> None
        """ 添加资源通道操作 """
        if callEvent:
            event = PLAYER_RES_LOAD_BEFORE(self.entityId, optObj)
            serviceBroadcast(event)
            if event.redirect:
                optObj = event.redirect
        self.needUpdate = True
        key = optObj.hashKey()
        # ============ KV键值对互斥关系的资源 ============
        if key and isinstance(key, str):
            # 基于键值的通道资源 一步到位
            self._kvOpt[key] = optObj
            return
        # ============ 复杂关系的资源处理 ============
        # 用于实现一些复杂互斥关系的资源处理 性能开销较大
        for obj in self._optPass[::-1]:
            state = optObj.processing(obj)
            if state == GL_OPT_INSTRUCT.WRITE:
                # 通道合并 移除旧的放置新的操作
                self._optPass.remove(obj)
                self._optPass.append(optObj)
                return
            elif state == GL_OPT_INSTRUCT.DELETE:
                # 通道抵消 删除冲突的两个操作
                self._optPass.remove(obj)
                return
        # 无任何状况发生 追加操作
        self._optPass.append(optObj)

    def setLineQuery(self, _customQueryName, toValue, useTime = 0.0, refreshNow = False):
        """ 设置线性节点 """
        oldValue = self.getQuery(_customQueryName)
        if oldValue == toValue:
            return
        self.setQuery(_customQueryName, oldValue)
        _lineQueryObj = LineAnim(oldValue, toValue, useTime)
        self._lineQueryMap[_customQueryName] = _lineQueryObj
        if refreshNow:
            self.lineQueryUpdate()
    
    def playCMDAnim(self, animName = ""):
        """ 基于命令系统播放动画 """
        if not animName:
            return
        Entity(self.playerId).exeCmd("/playanimation @s {}".format(animName))
    
    def _updateAnim(self):
        animList = list(self._animUpdateSet)
        comp = serverApi.GetEngineCompFactory().CreateModAttr(self.playerId)
        comp.SetAttr(GL_PLAYER_RES.GL_REST_ANIM_KEY, [animList, round(time(), 3)])

    def restAnim(self, animKey = "", refreshNow = False):
        """ 刷新并重置动画资源 """
        if not animKey in self._animUpdateSet:
            self._animUpdateSet.add(animKey)
        if refreshNow:
            self._updateAnim()
    
    @staticmethod
    def getAnimHashName(animName = ""):
        # type: (str) -> str
        return "{}_{}".format(animName.split(".")[-1], hash(animName)).replace("-", "_")

    def playAnim(self, animName = "", blendMut = 1.0, blendTime = 0.0, autoUpdate = False, restAnim = True, doNotInit = False):
        # type: (str, float, float, bool, bool, bool) -> None
        """ 播放特定动画 """
        if not animName:
            return
        animKey = GL_PLAYER_RES.getAnimHashName(animName)
        customQuery = "query.mod." + animKey
        if blendTime > 0.0:
            self.setLineQuery(customQuery, blendMut, blendTime)
        else:
            self.setQuery(customQuery, blendMut)
        if not doNotInit:
            self.addOptPass(GL_RES_OPT.GL_ANIM(animKey, animName))
            self.addOptPass(GL_RES_OPT.GL_SCRIPT_ANIMATE(animKey, customQuery))
        if restAnim:
            self.restAnim(animKey)
        if autoUpdate:
            self.updateAll()
    
    def _prePlayAnim(self, animName = "", blendMut = 1.0, blendTime = 0.0):
        return self.playAnim(animName, blendMut, blendTime, autoUpdate = False, doNotInit=True)
    
    def initPyAnims(self, animsList = []):
        """ 批量初始化Py层动画资源 """
        for animName in animsList:
            animKey = GL_PLAYER_RES.getAnimHashName(animName)
            customQuery = "query.mod." + animKey
            self.addOptPass(GL_RES_OPT.GL_ANIM(animKey, animName))
            self.addOptPass(GL_RES_OPT.GL_SCRIPT_ANIMATE(animKey, customQuery))

    def stopAnim(self, animName = "", blendTime = 0.0):
        # type: (str, float) -> None
        """ 停止特定动画播放 """
        self.playAnim(animName, 0.0, blendTime, restAnim=False)
    
    def getQuery(self, _queryName):
        # type: (str) -> float
        """ 获取节点值 """
        return self._queryMap.get(_queryName, 0.0)

    def updateRender(self):
        """ 更新渲染数据 """
        self.needUpdate = False
        comp = serverApi.GetEngineCompFactory().CreateModAttr(self.playerId)
        resList = [v.build() for v in self._kvOpt.values()]     # 键值对资源
        resList.extend(opt.build() for opt in self._optPass)    # 通道资源
        comp.SetAttr(GL_PLAYER_RES.GL_RES_KEY, resList)

    def copyQueryMap(self):
        """ 克隆节点MAP """
        return {k:v for k,v in self._queryMap.items()}

    def setQueryMap(self, queryMap, needUpdate = True):
        # type: (dict, bool) -> None
        """ 设置节点MAP """
        self._queryMap = queryMap
        self.needUpdateQuery = needUpdate

    def updateQuery(self):
        """ 更新节点数据 """
        self.needUpdateQuery = False
        comp = serverApi.GetEngineCompFactory().CreateModAttr(self.playerId)
        comp.SetAttr(GL_PLAYER_RES.GL_QUERY_KEY, self._queryMap)
    
    def updateAll(self):
        """ 更新所有渲染数据 """
        self.updateQuery()
        self.updateRender()

    def setQuery(self, queryName, value, ndigits = 2):
        # type: (str, float, int) -> None
        """ 设置资源节点 """
        if value - int(value) != 0.0:
            value = round(value, ndigits)     # 通过最大精度限制优化IO开销
        oldValue = self._queryMap.get(queryName, None)
        if oldValue == value:
            return
        self._queryMap[queryName] = value
        self.needUpdateQuery = True
    
    def setQueryNow(self, queryName, value):
        # type: (str, float) -> None
        """ 立即设置节点 """
        self.setQuery(queryName, value)
        self.updateQuery()

    def restDefaultSkin(self, restMat = False):
        """ 重置默认纹理模型 """
        self.addOptPass(
            GL_RES_OPT.GL_TEXTURE(GL_PLAYER_RES.DEFAULT_KEY, GL_PLAYER_RES.DEFAULT_TEXTURE)
        )
        self.addOptPass(
            GL_RES_OPT.GL_GEOMETRY(GL_PLAYER_RES.DEFAULT_KEY, GL_PLAYER_RES.DEFAULT_GEO)
        )
        # 由于网易MC魔改了玩家资源 此处的默认材质不一定符合实际默认材质 选择性启用
        if restMat:
            self.addOptPass(
                GL_RES_OPT.GL_MATERIAL(GL_PLAYER_RES.DEFAULT_KEY, GL_PLAYER_RES.DEFAULT_MAT)
            )
    
    def loadJSONRenderData(self, data, SCRIPT_ANIMATE_AUTO_REPLACE = False):
        # type: (JSONRenderData, bool) -> None
        """ 加载渲染参数 """
        # =============== 基本资源处理 ===============
        for key, geo in data._geometry.items():
            self.addOptPass(GL_RES_OPT.GL_GEOMETRY(key, geo))
        for key, texture in data._textures.items():
            self.addOptPass(GL_RES_OPT.GL_TEXTURE(key, texture))
        for key, mat in data._materials.items():
            self.addOptPass(GL_RES_OPT.GL_MATERIAL(key, mat))
        for key, particle in data._particle_effects.items():
            self.addOptPass(GL_RES_OPT.GL_PARTICLE_EFFECT(key, particle))
        for key, sound in data._sound_effects.items():
            self.addOptPass(GL_RES_OPT.GL_SOUND_EFFECT(key, sound))
        for key, anim in data._animations.items():
            self.addOptPass(GL_RES_OPT.GL_ANIM(key, anim))
        # =============== 条件表达参数处理 ===============
        for key, molang in data.formatRenderControllers():
            self.addOptPass(GL_RES_OPT.GL_RENDER_CONTROLLER(key, molang))
        for key, molang in data.formatAnimate():
            self.addOptPass(GL_RES_OPT.GL_SCRIPT_ANIMATE(key, molang, SCRIPT_ANIMATE_AUTO_REPLACE))
    
    def releaseJSONRenderData(self, data, fixDefaultRes = True, emptyAnim = None, emptyAnimCon = None):
        # type: (JSONRenderData, bool, str | None, str | None) -> None
        """ 释放渲染参数 (仅支持动画控制器, 渲染控制器, 模型资源 无关资源不会做出处理)
            - fixDefaultRes 启用时 若释放的资源涉及default键位将会自动修正为原生数据
            - emptyAnim与emptyAnimCon 同时设置预值时将会使用对应动画作为空动画置换实现伪释放
        """
        for key, _ in data.formatRenderControllers():
            self.addOptPass(GL_RES_OPT.GL_RENDER_CONTROLLER(key, None))
        for key, _ in data._geometry.items():
            if fixDefaultRes and key == GL_PLAYER_RES.DEFAULT_KEY:
                self.addOptPass(GL_RES_OPT.GL_GEOMETRY(key, GL_PLAYER_RES.DEFAULT_GEO))
                continue
            self.addOptPass(GL_RES_OPT.GL_GEOMETRY(key, None))

        for key, value in data._animations.items():
            if not str(value).startswith("controller.animation."):
                if emptyAnim:
                    self.addOptPass(GL_RES_OPT.GL_ANIM(key, emptyAnim))
                continue
            self.addOptPass(GL_RES_OPT.GL_ANIM(key, emptyAnimCon))

class GL_Service(BaseService):
    def __init__(self):
        BaseService.__init__(self)
        self._entityResMap = {}     # type: dict[str, GL_PLAYER_RES]
        self._PLGlobalRes = None    # type: JSONRenderData | None
    
    def onServiceUpdate(self):
        BaseService.onServiceUpdate(self)
        for _, resObj in self._entityResMap.items():
            TRY_EXEC_FUN(resObj.onTick)

    @BaseService.Listen(Events.DelServerPlayerEvent)
    def DelServerPlayerEvent(self, args):
        entityId = args["id"]
        if entityId in self._entityResMap:
            obj = self._entityResMap[entityId]
            TRY_EXEC_FUN(obj.onEntityMemoryRelease)
            TRY_EXEC_FUN(obj.onRelease)
            obj.manager = None
            del self._entityResMap[entityId]
            if STATIC_IN.USE_PLAYER_LEVEL_GC:
                Call("*", "GL_GCPlayer", entityId)
    
    @BaseService.Listen(Events.AddServerPlayerEvent)
    def AddServerPlayerEvent(self, args):
        playerId = args["id"]
        if self._PLGlobalRes:
            playerRes = GL_Service.getPlayerRes(playerId)
            playerRes.loadJSONRenderData(self._PLGlobalRes, True)

    def CREATE_ENTITY_RES(self, entityId):
        """ 创建实体资源 """
        def createObj():
            if Entity(entityId).Identifier == "minecraft:player":
                return GL_PLAYER_RES(entityId, self)
            return None
        obj = createObj()
        obj.onCreate()
        return obj
    
    @classmethod
    def setPlayerGlobalRes(cls, _JSONRenderData):
        # type: (JSONRenderData) -> None
        """ 设置玩家全局资源 """
        cls.access()._PLGlobalRes = _JSONRenderData
    
    @classmethod
    def getPlayerRes(cls, entityId = "", mustAlive = True):
        """ 获取玩家实体资源对象 如果不存在则自动创建 """
        _this = cls.access()
        if entityId in _this._entityResMap:
            return _this._entityResMap[entityId]
        comp = serverApi.GetEngineCompFactory().CreateGame(levelId)
        alive = comp.IsEntityAlive(entityId)
        if mustAlive and not alive:
            return None
        obj = _this.CREATE_ENTITY_RES(entityId)
        _this._entityResMap[entityId] = obj
        return obj
    
    @classmethod
    def setEntityQuery(cls, entityId="", queryName="query.mod.test", value=0, mustAlive=True):
        """ 设置实体节点(对于非玩家实体需要在客户端声明白名单,此外非玩家实体不会动态注册query需主动声明) """
        comp = serverApi.GetEngineCompFactory().CreateGame(levelId)
        alive = comp.IsEntityAlive(entityId)
        if mustAlive and not alive:
            return None
        if Entity(entityId).IsPlayer:
            cls.getPlayerRes(entityId, mustAlive).setQueryNow(queryName, value)
            return
        comp = serverApi.GetEngineCompFactory().CreateModAttr(entityId)
        lastValue = comp.GetAttr(GL_MOB_QUERY_KEY, {})
        if not isinstance(lastValue, dict):
            lastValue = dict()
        lastValue[queryName] = value
        comp.SetAttr(GL_MOB_QUERY_KEY, lastValue)

    def onServiceStop(self):
        BaseService.onServiceStop(self)
        # 服务停用 回收资源
        for _, resObj in self._entityResMap.items():
            TRY_EXEC_FUN(resObj.onServiceRelease)
            TRY_EXEC_FUN(resObj.onRelease)
        self._entityResMap = {}
    
    @staticmethod
    @CallBackKey("GL_Service/callEntityResFuns")
    def callEntityResFuns(entityId, apiData = []):
        obj = GL_Service.getPlayerRes(entityId)
        for apiArgs in apiData:
            funName = apiArgs[0]
            args = tuple(apiArgs[1:])
            funObj = getattr(obj, funName)
            TRY_EXEC_FUN(funObj, *args)

lambda: "GL_RENDER By Zero123"
print("[Qu.GLRender] 服务端已加载")