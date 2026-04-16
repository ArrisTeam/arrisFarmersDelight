# -*- coding: utf-8 -*-
from ...Client import *
from ...Util import TRY_EXEC_FUN, getObjectPathName
from copy import deepcopy
from ...Modules.Services.Client import (
    BaseService,
    BaseEvent,
    serviceBroadcast,
    listenServiceEvent,
)
from SharedRes import (
    GL_CUSTOM_QUERY,
    JSONRenderData,
    GL_RES_OPT,
    GL_MOB_QUERY_KEY,
)
lambda: "By Zero123"
lambda: "TIME: 2025/4/26"

class STATIC_IN:
    USE_LOCAL_CACHE = False
    FULL_MOB_QUERY_FUNC = False
    MOB_QUERY_WHITE_LIST = set()

class MOB_QUERYS_UPDATE_EVENTS(BaseEvent):
    """ 实体Querys节点更新事件 处于该事件下依然可以重定向修改节点数据 """
    def __init__(self, entityId="-1", queryMapRef={}, isPlayer=False):
        # type: (str, dict[str, float | object], bool) -> None
        BaseEvent.__init__(self)
        self.entityId = entityId
        self.queryMapRef = queryMapRef
        self.isPlayer = isPlayer

class PLAYER_RES_REBUILD_BEFORE(BaseEvent):
    """ 玩家资源重建事件 处于该事件下可以设置cancel拦截重建行为并重新实现 """
    def __init__(self, entityId="-1", lazyUpdate=False):
        # type: (str, bool) -> None
        BaseEvent.__init__(self)
        self.entityId = entityId
        self.lazyUpdate = lazyUpdate
        self.cancel = False

def GL_SET_ENTITY_QUERYS_MAP(entityId, queryMap={}, isPlayer=False):
    # type: (str, dict[str, float | object], bool) -> None
    serviceBroadcast(MOB_QUERYS_UPDATE_EVENTS(entityId, queryMap, isPlayer))
    comp = clientApi.GetEngineCompFactory().CreateQueryVariable(entityId)
    # 理论上GLR支持任意数据类型的value 但只有数值类型会被设置到节点
    for k, v in queryMap.items():
        if isinstance(v, (float, int)):
            comp.Set(k, v)

class MOB_QUERY_COMP:
    def __init__(self, entityId=None):
        self.entityId = entityId

    def onLoad(self):
        comp = clientApi.GetEngineCompFactory().CreateModAttr(self.entityId)
        queryData = self._toDict(comp.GetAttr(GL_MOB_QUERY_KEY, {}))
        self.updateQueryMap(queryData)
        comp.RegisterUpdateFunc(GL_MOB_QUERY_KEY, self.listenUpdateQuery)

    def _toDict(self, args={}):
        if isinstance(args, dict):
            return args
        return dict()

    def listenUpdateQuery(self, args={}):
        newValue = args["newValue"]
        self.updateQueryMap(self._toDict(newValue))

    def updateQueryMap(self, queryMap={}):
        # type: (dict[str, float]) -> None
        GL_SET_ENTITY_QUERYS_MAP(self.entityId, queryMap)

    def onFree(self):
        comp = clientApi.GetEngineCompFactory().CreateModAttr(self.entityId)
        comp.UnRegisterUpdateFunc(GL_MOB_QUERY_KEY, self.listenUpdateQuery)

@BaseService.Init
class PLAYER_RES_SERVICE(BaseService):
    """ 玩家资源处理服务 """
    GL_RES_KEY = "Q_{}_GL.RES".format(ModDirName)
    GL_QUERY_KEY = "Q_{}_GL.QUERY".format(ModDirName)
    GL_REST_ANIM_KEY = "Q_{}_GL.REST_ANIM".format(ModDirName)
    _LOCAL_EFFECT_LISTEN_MAP = {}   # type: dict[str, set[function]]    # 本地效果监听映射
    _REG_LOCAL_EFFECT_FUNCNAME = set()  # 存放使用装饰器注册过的函数路径 避免热重载带来的重复定义问题
    _LOCAL_PLAYER_CACHE = {}        # type: dict[str, list]
    _LOCAL_PLAYER_CACHE_STATIC = {}        # type: dict[str, list]

    @staticmethod
    def checkAndUpdatePlayerCache(playerId, newData=[], isStatic=False):
        """ 检查并更新玩家历史缓存更新统计，若和缓存一致返回True 否则返回False """
        target = PLAYER_RES_SERVICE._LOCAL_PLAYER_CACHE
        if isStatic:
            target = PLAYER_RES_SERVICE._LOCAL_PLAYER_CACHE_STATIC
        oldData = target.get(playerId, {})
        if oldData != newData:
            target[playerId] = deepcopy(newData)
            return False
        return True

    @staticmethod
    def _REGISTER_QUERY():
        """ 注册自定义Query """
        for queryName in GL_CUSTOM_QUERY.GL_QUERYS:
            comp = clientApi.GetEngineCompFactory().CreateQueryVariable(levelId)
            comp.Register(queryName, 0.0)

    @staticmethod
    def localEffectListen(queryBindName, bindFunc):
        # type: (str, function) -> function
        """ 建立本地效果监听(适用于绑定query动作特效的高性能同步方案) 推荐搭配组件类组合效果开发
            回调参数: (entityId, queryValue, event)
        """
        _LOCAL_EFFECT_LISTEN_MAP = PLAYER_RES_SERVICE._LOCAL_EFFECT_LISTEN_MAP
        if not _LOCAL_EFFECT_LISTEN_MAP:
            # 初始化监听
            listenServiceEvent(MOB_QUERYS_UPDATE_EVENTS, PLAYER_RES_SERVICE._localEffectListener)
        if not queryBindName in _LOCAL_EFFECT_LISTEN_MAP:
            _LOCAL_EFFECT_LISTEN_MAP[queryBindName] = set([bindFunc])
        else:
            _LOCAL_EFFECT_LISTEN_MAP[queryBindName].add(bindFunc)
        return bindFunc

    @staticmethod
    def localPlayerEffectListen(queryBindName, bindFunc):
        # type: (str, function) -> None
        """
            基于localEffectListen封装的玩家独占版本
            回调参数: (entityId, queryValue)
        """
        def _localPlayerEffectListenHandler(entityId, queryValue, event):
            # type: (str, float | int, MOB_QUERYS_UPDATE_EVENTS) -> None
            if event.isPlayer:
                return bindFunc(entityId, queryValue)
        PLAYER_RES_SERVICE.localEffectListen(queryBindName, _localPlayerEffectListenHandler)

    @staticmethod
    def localMobEffectListen(queryBindName, bindFunc):
        # type: (str, function) -> None
        """
            基于localEffectListen封装的全生物支持版本(包括玩家)
            回调参数: (entityId, queryValue)
        """
        def _localMobEffectListenHandler(entityId, queryValue, _):
            # type: (str, float | int, MOB_QUERYS_UPDATE_EVENTS) -> None
            return bindFunc(entityId, queryValue)
        PLAYER_RES_SERVICE.localEffectListen(queryBindName, _localMobEffectListenHandler)

    @staticmethod
    def localPlayerEffectListener(queryBindName):
        """ localPlayerEffectListen的装饰器封装版本 """
        def _regLoader(func):
            funcName = getObjectPathName(func)
            if not funcName in PLAYER_RES_SERVICE._REG_LOCAL_EFFECT_FUNCNAME:
                PLAYER_RES_SERVICE._REG_LOCAL_EFFECT_FUNCNAME.add(funcName)
                PLAYER_RES_SERVICE.localPlayerEffectListen(queryBindName, func)
            return func
        return _regLoader

    @staticmethod
    def localMobEffectListener(queryBindName):
        """ localMobEffectListen的装饰器封装版本 """
        def _regLoader(func):
            funcName = getObjectPathName(func)
            if not funcName in PLAYER_RES_SERVICE._REG_LOCAL_EFFECT_FUNCNAME:
                PLAYER_RES_SERVICE._REG_LOCAL_EFFECT_FUNCNAME.add(funcName)
                PLAYER_RES_SERVICE.localMobEffectListen(queryBindName, func)
            return func
        return _regLoader

    @staticmethod
    def _localEffectListener(event=MOB_QUERYS_UPDATE_EVENTS()):
        _LOCAL_EFFECT_LISTEN_MAP = PLAYER_RES_SERVICE._LOCAL_EFFECT_LISTEN_MAP
        for k, v in event.queryMapRef.items():
            if not k in _LOCAL_EFFECT_LISTEN_MAP:
                continue
            for func in _LOCAL_EFFECT_LISTEN_MAP[k]:
                TRY_EXEC_FUN(func, event.entityId, v, event)

    def __init__(self):
        BaseService.__init__(self)
        self.__class__._REGISTER_QUERY()
        self._OPTMap = {
            "0": self.OPT_TEXTURE,
            "1": self.OPT_GEOMETRY,
            "2": self.OPT_MATERIAL,
            "3": self.OPT_ANIM,
            "4": self.OPT_PARTICLE_EFFECT,
            "5": self.OPT_RENDER_CONTROLLER,
            "6": self.OPT_SCRIPT_ANIMATE,
            "7": self.OPT_SOUND_EFFECT,
            "8": self.OPT_PLAYER_SKIN,
        }
        self.staticPlayerResCMD = []
        """ 静态玩家资源操作指令 """
        self._querySet = set(GL_CUSTOM_QUERY.GL_QUERYS)
        self.entityTempData = {}    # type: dict[str, dict]
        """ 实体临时持有数据 """
        self.mobQueryComps = {}     # type: dict[str, MOB_QUERY_COMP]
        """ 实体Query节点组件表 """

    @staticmethod
    def rebuildPlayerRes(entityId, lazyUpdate=False):
        event = PLAYER_RES_REBUILD_BEFORE(entityId, lazyUpdate)
        serviceBroadcast(event)
        if not event.cancel:
            comp = clientApi.GetEngineCompFactory().CreateActorRender(entityId)
            comp.RebuildPlayerRender()

    def getEntityTempData(self, entityId):
        # type: (str) -> dict
        """ 获取实体临时持有数据 """
        if not entityId in self.entityTempData:
            self.entityTempData[entityId] = {}
        return self.entityTempData[entityId]

    def delEntityTempData(self, entityId):
        # type: (str) -> None
        """ 删除实体临时持有数据 """
        if entityId in self.entityTempData:
            del self.entityTempData[entityId]

    def getArgs(self, data = {}):
        return tuple(data["d"])
    
    def OPT_TEXTURE(self, entityId, _type, data):
        """ 纹理资源操作 """
        comp = clientApi.GetEngineCompFactory().CreateActorRender(entityId)
        key, value = self.getArgs(data)
        if value == None:
            return
        comp.AddPlayerTexture(key, value)

    def OPT_GEOMETRY(self, entityId, _type, data):
        """ 模型资源操作 """
        comp = clientApi.GetEngineCompFactory().CreateActorRender(entityId)
        key, value = self.getArgs(data)
        if value == None:
            comp.RemovePlayerGeometry(key)
            return
        comp.AddPlayerGeometry(key, value)

    def OPT_MATERIAL(self, entityId, _type, data):
        """ 材质资源操作 """
        comp = clientApi.GetEngineCompFactory().CreateActorRender(entityId)
        key, value = self.getArgs(data)
        if value == None:
            return
        comp.AddPlayerRenderMaterial(key, value)

    def OPT_ANIM(self, entityId, _type, data):
        """ 动画/控制器资源操作 """
        comp = clientApi.GetEngineCompFactory().CreateActorRender(entityId)
        key, value = self.getArgs(data)
        if str(value).startswith("animation."):
            # 是动画资源
            comp.AddPlayerAnimation(key, value)
            playerData = self.getEntityTempData(entityId)
            playerData[key] = value
            return
        elif str(value).startswith("controller.animation."):
            # 是动画控制器资源
            comp.AddPlayerAnimationController(key, value)
            return
        if value == None:
            comp.RemovePlayerAnimationController(key)
            return
        print("无效的动画资源: " + str(value))

    def OPT_PARTICLE_EFFECT(self, entityId, _type, data):
        """ 粒子资源操作 """
        comp = clientApi.GetEngineCompFactory().CreateActorRender(entityId)
        key, value = self.getArgs(data)
        if value == None:
            return
        comp.AddPlayerParticleEffect(key, value)

    def OPT_RENDER_CONTROLLER(self, entityId, _type, data):
        """ 渲染控制器资源操作 """
        comp = clientApi.GetEngineCompFactory().CreateActorRender(entityId)
        key, value = self.getArgs(data)
        if value == None:
            comp.RemovePlayerRenderController(key)
            return
        comp.AddPlayerRenderController(key, value)

    def OPT_SCRIPT_ANIMATE(self, entityId, _type, data):
        """ animate节点资源操作 """
        comp = clientApi.GetEngineCompFactory().CreateActorRender(entityId)
        key, value, _autoReplace = self.getArgs(data)
        if value == None:
            return
        if not _autoReplace:
            comp.AddPlayerScriptAnimate(key, value)
            return
        comp.AddPlayerScriptAnimate(key, value, _autoReplace)

    def OPT_SOUND_EFFECT(self, entityId, _type, data):
        """ 音效资源操作 """
        comp = clientApi.GetEngineCompFactory().CreateActorRender(entityId)
        key, value = self.getArgs(data)
        if value == None:
            return
        comp.AddPlayerSoundEffect(key, value)

    def OPT_PLAYER_SKIN(self, entityId, _type, data):
        """ 玩家皮肤资源操作 """
        value = self.getArgs(data)[0]
        comp = clientApi.GetEngineCompFactory().CreateModel(playerId)
        if value == None:
            comp.ResetSkin()
            return
        comp.SetSkin(value)

    def GL_RES_UPDATE(self, args, notRebuild=False):
        # type: (dict, bool) -> int
        entityId = args["entityId"]
        newValue = args["newValue"]     # type: list
        staticMode = args.get("staticMode", False)
        if len(newValue) == 0 or newValue == args["oldValue"]:
            return 0
        rc = 0  # 记录操作次数
        if not STATIC_IN.USE_LOCAL_CACHE or not PLAYER_RES_SERVICE.checkAndUpdatePlayerCache(entityId, newValue, staticMode):
            for data in newValue:
                _INSTRUCT_ID, _TYPE, _SHARED_DATA = str(data[0]), data[1], data[2]
                if _INSTRUCT_ID in self._OPTMap:
                    rc += 1
                    TRY_EXEC_FUN(self._OPTMap[_INSTRUCT_ID], entityId, _TYPE, _SHARED_DATA)
                else:
                    print("[PLAYER_RES_SERVICE] 找不到相关资源操作方法: {}".format(newValue))
        if rc <= 0 or notRebuild:
            return rc
        PLAYER_RES_SERVICE.rebuildPlayerRes(entityId)
        return rc

    def INIT_QUERY(self, queryKey = ""):
        """ 初始化节点 """
        if not queryKey in self._querySet:
            try:
                self._querySet.add(queryKey)
                comp = clientApi.GetEngineCompFactory().CreateQueryVariable(levelId)
                comp.Register(queryKey, 0.0)
            except:
                pass

    def GL_QUERY_UPDATE(self, args):
        entityId = args["entityId"]
        newValue = args["newValue"]     # type: dict
        oldValue = args["oldValue"]     # type: dict | None
        upDateMap = {}
        for k, v in newValue.items():
            if oldValue and v == oldValue.get(k, None):
                # 重复节点数据剔除
                continue
            self.INIT_QUERY(k)
            upDateMap[k] = v
        if upDateMap:
            GL_SET_ENTITY_QUERYS_MAP(entityId, upDateMap, True)

    def AUTO_RES_UPDATE(self, args):
        """ 由属性变化触发的自动资源更新 """
        return self.GL_RES_UPDATE(args)

    def GL_REST_ANIM(self, args):
        """ 刷新玩家资源 """
        entityId = args["entityId"]
        newValue = args["newValue"]     # type: list
        keyList = newValue[0]           # type: list[str]
        playerData = self.getEntityTempData(entityId)
        comp = clientApi.GetEngineCompFactory().CreateActorRender(entityId)
        for key in keyList:
            if not key in playerData:
                return
            anim = playerData[key]
            comp.AddPlayerAnimation(key, anim)

    @BaseService.Listen("AddPlayerCreatedClientEvent")
    def AddPlayerCreatedClientEvent(self, args={}):
        """ 玩家异步渲染事件 """
        playerId = args["playerId"]
        comp = clientApi.GetEngineCompFactory().CreateModAttr(playerId)
        rc = 0  # 统计资源操作次数 决策是否重建玩家渲染
        rc += self.staticResRender(playerId)
        rc += self.GL_RES_UPDATE({"entityId": playerId, "oldValue":[], "newValue": comp.GetAttr(self.__class__.GL_RES_KEY, [])}, True)
        if rc > 0:
            PLAYER_RES_SERVICE.rebuildPlayerRes(playerId, True)
        self.GL_QUERY_UPDATE({"entityId": playerId, "oldValue":{}, "newValue": comp.GetAttr(self.__class__.GL_QUERY_KEY, {})})
        # ======== ====== 为区域渲染内的玩家建立数据变更监听 ======== ======
        comp = clientApi.GetEngineCompFactory().CreateModAttr(playerId)
        comp.RegisterUpdateFunc(self.__class__.GL_RES_KEY, self.AUTO_RES_UPDATE)
        comp.RegisterUpdateFunc(self.__class__.GL_REST_ANIM_KEY, self.GL_REST_ANIM)
        comp.RegisterUpdateFunc(self.__class__.GL_QUERY_KEY, self.GL_QUERY_UPDATE)

    @BaseService.Listen("RemovePlayerAOIClientEvent")
    def RemovePlayerAOIClientEvent(self, args={}):
        """ 玩家离开渲染区域事件 """
        playerId = args["playerId"]
        # ======== ====== 对离开区域渲染的玩家取消数据变更监听 ======== ======
        comp = clientApi.GetEngineCompFactory().CreateModAttr(playerId)
        comp.UnRegisterUpdateFunc(self.__class__.GL_RES_KEY, self.AUTO_RES_UPDATE)
        comp.UnRegisterUpdateFunc(self.__class__.GL_REST_ANIM_KEY, self.GL_REST_ANIM)
        comp.UnRegisterUpdateFunc(self.__class__.GL_QUERY_KEY, self.GL_QUERY_UPDATE)
        self.delEntityTempData(playerId)

    @BaseService.Listen("AddEntityClientEvent")
    def AddEntityClientEvent(self, args={}):
        """ AOI客户端生物渲染事件 """
        entityId = args["id"]
        if STATIC_IN.FULL_MOB_QUERY_FUNC:
            self.mallocMobQueryData(entityId)
            return
        if args["engineTypeStr"] in STATIC_IN.MOB_QUERY_WHITE_LIST:
            self.mallocMobQueryData(entityId)

    @BaseService.Listen("RemoveEntityClientEvent")
    def RemoveEntityClientEvent(self, args={}):
        """ AOI客户端生物取消渲染事件 """
        entityId = args["id"]
        self.freeMobQueryData(entityId)

    def mallocMobQueryData(self, entityId=""):
        """ 分配生物节点数据 """
        if entityId in self.mobQueryComps:
            return
        comp = MOB_QUERY_COMP(entityId)
        self.mobQueryComps[entityId] = comp
        comp.onLoad()
    
    def freeMobQueryData(self, entityId=""):
        """ 释放生物节点数据 """
        if not entityId in self.mobQueryComps:
            return
        comp = self.mobQueryComps[entityId]
        del self.mobQueryComps[entityId]
        comp.onFree()

    def staticResRender(self, playerId):
        """ 加载静态资源 返回资源操作次数 """
        if len(self.staticPlayerResCMD) <= 0:
            return 0
        return self.GL_RES_UPDATE({"entityId": playerId, "oldValue":[], "newValue": self.staticPlayerResCMD, "staticMode": True}, True)

    def setPlayerStaticGlobalRes(self, data=JSONRenderData(), SCRIPT_ANIMATE_AUTO_REPLACE=True):
        """ [客户端异步] 设置玩家静态全局资源 """
        cmdList = []
        for key, geo in data._geometry.items():
            cmdList.append(GL_RES_OPT.GL_GEOMETRY(key, geo).build())
        for key, texture in data._textures.items():
            cmdList.append(GL_RES_OPT.GL_TEXTURE(key, texture).build())
        for key, mat in data._materials.items():
            cmdList.append(GL_RES_OPT.GL_MATERIAL(key, mat).build())
        for key, particle in data._particle_effects.items():
            cmdList.append(GL_RES_OPT.GL_PARTICLE_EFFECT(key, particle).build())
        for key, sound in data._sound_effects.items():
            cmdList.append(GL_RES_OPT.GL_SOUND_EFFECT(key, sound).build())
        for key, anim in data._animations.items():
            cmdList.append(GL_RES_OPT.GL_ANIM(key, anim).build())
        # =============== 条件表达参数处理 ===============
        for key, molang in data.formatRenderControllers():
            cmdList.append(GL_RES_OPT.GL_RENDER_CONTROLLER(key, molang).build())
        for key, molang in data.formatAnimate():
            cmdList.append(GL_RES_OPT.GL_SCRIPT_ANIMATE(key, molang, SCRIPT_ANIMATE_AUTO_REPLACE).build())
        self.staticPlayerResCMD = cmdList

def ENABLE_FULL_MOB_QUERY_FUNC(state=True):
    # type: (bool) -> None
    """ 启用全生物Query节点同步支持 """
    STATIC_IN.FULL_MOB_QUERY_FUNC = state

def ADD_MOB_QUERY_WHITE_LIST(*entityTypeArgs):
    # type: (str) -> None
    """ 添加生物Query节点同步白名单 """
    for entityType in entityTypeArgs:
        STATIC_IN.MOB_QUERY_WHITE_LIST.add(entityType)

@AllowCall
def GL_GCPlayer(entityId):
    if entityId in PLAYER_RES_SERVICE._LOCAL_PLAYER_CACHE:
        del PLAYER_RES_SERVICE._LOCAL_PLAYER_CACHE[entityId]
    if entityId in PLAYER_RES_SERVICE._LOCAL_PLAYER_CACHE_STATIC:
        del PLAYER_RES_SERVICE._LOCAL_PLAYER_CACHE_STATIC[entityId]

lambda: "GL_RENDER By Zero123"
print("[Qu.GLRender] 客户端已加载")
