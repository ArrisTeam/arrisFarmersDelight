# -*- coding: utf-8 -*-
from ...Client import *
from Configure import PlayerRes, QueryList
# >>>>>>>>>>>>>>>>
#  [WAR] CTRender即将在未来废弃 推荐使用GLRender替代相关业务
# <<<<<<<<<<<<<<<<

__InitState = False
__PlayerRes = {
    "materials":{},
    "textures":{},
    "geometry":{},
    "animate":[],
    "animations":{},
    "render_controllers":{},
    "particle_effects":{},
    "sound_effects": {}
}   # type: dict[str, dict | list]
""" 玩家资源数据 全局性 """

globalPlayerRes = __PlayerRes

QUERYDICT = {} 
""" 节点映射表 """
CUSTOMQUERYMAP = set()
""" 自定义节点的映射储存表 """

# ====== 新增玩家事件 ======
@Listen("OnLocalPlayerStopLoading")
def __CTOnLocalPlayerStopLoading(args):
    global __InitState; __InitState = True
    playerId = args["playerId"]; RenderPlayer(playerId)
    
@Listen("AddPlayerCreatedClientEvent")
def __CTAddPlayerCreatedClientEvent(args):
    return __CTOnLocalPlayerStopLoading(args)
# ====== 新增玩家事件 ======

@CallBackKey("__CTRENDER.UpDateEntityQuery__")
def UpDateEntityQuery(Dic):
    # type: (dict[str,dict[str,float]]) -> None
    for entityId, QueryDict in Dic.items():
        comp = clientApi.GetEngineCompFactory().CreateQueryVariable(entityId)
        for Query, Value in QueryDict.items():
            if isinstance(Query, str):
                queryName = Query
                if Query.startswith("q."):
                    queryName = "query.mod."+Query[2:]
                RegisterQuery(queryName)
                comp.Set(queryName, Value)
                continue
            Query = QUERYDICT[Query]    # 读取映射
            comp.Set(Query, Value)

@Listen("DimensionChangeFinishClientEvent")
def CTDimensionChangeFinishClientEvent(_Args):
    Call("__CTRENDER.PlayerUpDateQuery__", {"playerId":playerId})
            
# 渲染玩家数据
def RenderPlayer(playerId):
    if all(len(v) == 0 for v in __PlayerRes.values()):
        # 若不存在需要渲染的数据 则直接返回False
        return False
    comp = clientApi.GetEngineCompFactory().CreateActorRender(playerId)
    for data in __PlayerRes["materials"].items():
        comp.AddPlayerRenderMaterial(*data)
    for data in __PlayerRes["textures"].items():
        comp.AddPlayerTexture(*data)
    for data in __PlayerRes["geometry"].items():
        comp.AddPlayerGeometry(*data)
    for data in __PlayerRes["animations"].items():
        if str(data[1]).startswith("controller.animation."):
            comp.AddPlayerAnimationController(*data)
        else:
            comp.AddPlayerAnimation(*data)
    for data in __PlayerRes["render_controllers"].items():
        comp.AddPlayerRenderController(*data)
    for k,v in __PlayerRes["particle_effects"].items():
        comp.AddActorParticleEffect(Entity.Type.PLAYER, k, v)
    for data in __PlayerRes["animate"]:
        if isinstance(data, str):
            comp.AddActorScriptAnimate(Entity.Type.PLAYER, data, "(1.0)")
        elif isinstance(data, dict):
            for k,v in dict(data).items():
                comp.AddActorScriptAnimate(Entity.Type.PLAYER, k, v)
    for k, v in __PlayerRes["sound_effects"].items():
        comp.AddPlayerSoundEffect(k, v)
    Back = comp.RebuildPlayerRender()
    return Back

def LoadResDict(dic):
    # type: (dict) -> bool
    """ 解析Json(字典)资源数据 """
    materials = dic.get("materials", {})                            # type: dict
    textures = dic.get("textures", {})                              # type: dict
    geometry = dic.get("geometry", {})                              # type: dict
    animate = dic.get("animate", [])                                # type: list
    animations = dic.get("animations", {})                          # type: dict
    render_controllers = dic.get("render_controllers", [])          # type: list
    particle_effects = dic.get("particle_effects", {})              # type: dict
    sound_effects = dic.get("sound_effects", {})                    # type: dict
    # 设置材料
    for Key, Value in materials.items():
        SetMaterial(Key,Value)
    # 设置粒子
    for Key, Value in particle_effects.items():
        SetParticle(Key,Value)
    # 设置纹理
    for Key, Value in textures.items():
        SetTexture(Key,Value)
    # 设置模型
    for Key, Value in geometry.items():
        SetGeo(Key,Value)
    # 设置动画
    for Key, Value in animations.items():
        SetAnimation(Key,Value)
    # 设置ANIMATE
    for ani in animate:
        if isinstance(ani, str):
            SetAnimate(ani)
        elif isinstance(ani, dict):
            for k,v in dict(ani).items():
                SetAnimate(k, Molang=str(v))
    # 设置 渲染控制器
    for con in render_controllers:
        if isinstance(con, str):
            SetRenderCon(con, "(1.0)")
        elif isinstance(con, dict):
            for k,v in con.items():
                SetRenderCon(k, v)
    # 设置音效
    for Key, Value in sound_effects.items():
        SetSound(Key, Value)
    return True

# 增加粒子效果
def SetParticle(Key, Value):
    Key, Value = str(Key), str(Value)
    comp = __PlayerRes["particle_effects"]
    comp[Key] = Value
    return True

# 增加纹理
def SetTexture(Key, value):
    Key, value = str(Key), str(value)
    comp = __PlayerRes["textures"]
    comp[Key] = value
    return True

# 增加纹理
def SetSound(Key, value):
    Key, value = str(Key), str(value)
    comp = __PlayerRes["sound_effects"]
    comp[Key] = value
    return True

# 增加模型
def SetGeo(Key, value):
    Key, value = str(Key), str(value)
    comp = __PlayerRes["geometry"]
    comp[Key] = value
    return True

# 增加渲染控制器
def SetRenderCon(RenderC, molang):
    RenderCKey, molang = str(RenderC), str(molang)
    comp = __PlayerRes["render_controllers"]
    comp[RenderCKey] = molang
    return True

# 增加材料
def SetMaterial(Key,value):
    Key,value = str(Key), str(value)
    comp = __PlayerRes["materials"]
    comp[Key] = value
    return True

# 增加 Animate
def SetAnimate(Key, Molang = "(1.0)"):
    Key = str(Key)
    comp = __PlayerRes["animate"]
    comp.append({Key:Molang})
    return True

# 增加动画
def SetAnimation(Key,value):
    Key,value = str(Key), str(value)
    comp = __PlayerRes["animations"]
    comp[Key] = value
    return True

def RegisterQuery(queryName):
    """ 注册自定义Query """
    if queryName in CUSTOMQUERYMAP:
        return
    comp = clientApi.GetEngineCompFactory().CreateQueryVariable(levelId)
    comp.Register(queryName, 0.0)
    CUSTOMQUERYMAP.add(queryName)


LoadResDict(PlayerRes) # 加载全局配置的资源数据
for i, Query in enumerate(QueryList): # 加载自定义节点表
    QUERYDICT[str(i)] = Query   # 处理节点映射
    RegisterQuery(Query)


class PlayerManager:
    """ 玩家管理器 """
    playerVarDict = {}  # type: dict[str,float]
    """ Var字典映射存储 """
    isRuning = False
    """ 是否在工作 """
    player = Entity(playerId)
    """ 玩家实体对象 """
    varChangeFunDic = {} # type: dict[str,object]
    """ 变量变换回调方法字典 """

    def __init__(self):
        raise Exception("PlayerManager 不可实例化")
    
    @staticmethod
    def onLoop():
        """ Tick驱动循环 """
        player = PlayerManager.player
        for var, func in PlayerManager.varChangeFunDic.items():
            newQuery = player.GetQuery(var)         # 新的节点值
            if newQuery == None:
                newQuery = 0.0
            oldQuery = PlayerManager.getVar(var)    # 旧版节点值
            if newQuery != oldQuery:
                PlayerManager.playerVarDict[var] = newQuery
                try:
                    func(newQuery)
                except Exception as e:
                    print(e)

    @staticmethod
    def getVar(varName):
        # type: (str) -> float
        """ 获取var节点变量值(调用缓存实现 未注册的无法获取或返回0) """
        return PlayerManager.playerVarDict.get(varName, 0.0)

    @staticmethod
    def run():
        """ 运行服务 """
        if PlayerManager.isRuning:
            return
        ListenForEvent(TickEvent, PlayerManager, PlayerManager.onLoop)
        PlayerManager.isRuning = True

    @staticmethod
    def onVariableChange(varName):
        # type: (str) -> object
        """ [装饰器] 注册var变换监听 (返回变化后数值) """
        PlayerManager.run()
        keyWorld = "v."
        if varName.startswith(keyWorld):
            varName = "variable."+varName[len(keyWorld):]
        def zsq(func):
            PlayerManager.varChangeFunDic[varName] = func
            return func
        return zsq


class DyRenderRes:
    """ 动态渲染资源 """
    resDict = {}    # type: dict[str, dict]
    entityRes = {}  # type: dict[str, list[str]]
    renderCount = 0

    @staticmethod
    def reRenderAllPlayer():
        """ 重新渲染所有玩家 """
        for playerId in clientApi.GetPlayerList():
            RenderPlayer(playerId)

    @staticmethod
    def reRenderEntity(entityType):
        """ 重新渲染指定类型的实体 """
        _materials = {}
        """ 材料 """
        _textures = {}
        """ 纹理 """
        _geometry = {}
        """ 模型 """
        _animate = []
        """ 动画播放键位表 """
        _animations = {}    # type: dict[str, str]
        """ 动画 """
        _render_controllers = []
        """ 渲染控制器 """
        _particle_effects = {}
        """ 粒子效果 """
        _sound_effects = {}
        """ 音效 """

        def objMerge(a, b):
            # type: (dict | list, dict | list) -> None
            """ 将a合并到b """
            if isinstance(a, dict) and isinstance(b, dict):
                b.update(a)
            elif isinstance(a, list) and isinstance(b, list):
                b.extend(a)

        for resId in DyRenderRes.entityRes.get(entityType, []):
            res = DyRenderRes.getRenderDataById(resId)
            if res == None:
                continue
            # 实体资源处理
            objMerge(res.get("materials", {}), _materials)
            objMerge(res.get("textures", {}), _textures)
            objMerge(res.get("geometry", {}), _geometry)
            objMerge(res.get("animate", []), _animate)
            objMerge(res.get("animations", {}), _animations)
            objMerge(res.get("render_controllers", []), _render_controllers)
            objMerge(res.get("particle_effects", {}), _particle_effects)
            objMerge(res.get("sound_effects", {}), _sound_effects)

        if entityType == Entity.Type.PLAYER:
            # 玩家资源处理
            objMerge(_materials, globalPlayerRes["materials"])
            objMerge(_textures, globalPlayerRes["textures"])
            objMerge(_geometry, globalPlayerRes["geometry"])
            objMerge(_animate, globalPlayerRes["animate"])
            objMerge(_animations, globalPlayerRes["animations"])

            # 渲染控制器处理
            glRenderControllers = globalPlayerRes["render_controllers"]
            for data in _render_controllers:
                if isinstance(data, str):
                    glRenderControllers[data] = "(1.0)"
                elif isinstance(data, dict):
                    for k, v in data.items():
                        glRenderControllers[k] = v

            objMerge(_particle_effects, globalPlayerRes["particle_effects"])
            objMerge(_sound_effects, globalPlayerRes["sound_effects"])
            DyRenderRes.reRenderAllPlayer()
            return

        def keySet(obj, func = lambda k, v: None):
            # type: (dict | list, object) -> None
            if isinstance(obj, dict):
                for k, v in obj.items():
                    func(k, v)
                return
            elif isinstance(obj, list):
                for v in obj:
                    keySet(v, func)

        comp = clientApi.GetEngineCompFactory().CreateActorRender(levelId)
        keySet(_materials, lambda k, v: comp.AddActorRenderMaterial(entityType, k, v))
        keySet(_textures, lambda k, v: comp.AddActorTexture(entityType, k, v))
        keySet(_geometry, lambda k, v: comp.AddActorGeometry(entityType, k, v))
        keySet(_animate, lambda k, v: comp.AddActorScriptAnimate(entityType, k, v))
        keySet(_render_controllers, lambda k, v: comp.AddActorRenderController(entityType, k, v))
        keySet(_particle_effects, lambda k, v: comp.AddActorParticleEffect(entityType, k, v))
        keySet(_sound_effects, lambda k, v: comp.AddActorSoundEffect(entityType, k, v))
        for k, v in _animations.items():
            if v.startswith("controller.animation."):
                comp.AddActorAnimationController(entityType, k, v)
                continue
            comp.AddActorAnimation(entityType, k, v)
        comp.RebuildActorRender(entityType)

    @staticmethod
    def getRenderDataById(resId):
        # type: (str) -> dict[str,object] | None
        """ 获取渲染数据 """
        return DyRenderRes.resDict.get(resId, None)


@CallBackKey("__CTRENDER.UpDateEntityDyRender__")
def UpDateEntityDyRender(data):
    # type: (dict[str, list[int]]) -> None
    """ 更新实体资源数据 """
    USE_RES_LIST = []
    ND_QUERY_RES = []
    CAN_UP_DATE = True
    for _, resIdList in data.items():
        strResData = [str(x) for x in resIdList]
        USE_RES_LIST.extend(strResData)

    for key in set(USE_RES_LIST):
        if not key in DyRenderRes.resDict:
            # 无相关资源
            ND_QUERY_RES.append(int(key))
            CAN_UP_DATE = False
    
    def ReRender(data):
        # type: (dict[str, list[int]]) -> None
        for entityType, resIdList in data.items():
            needReRender = False
            if not entityType in DyRenderRes.entityRes:
                DyRenderRes.entityRes[entityType] = []
            data2 = DyRenderRes.entityRes[entityType]
            for resId in resIdList:
                stResId = str(resId)
                if not stResId in data2:
                    data2.append(stResId)
                    needReRender = True
            if needReRender:
                DyRenderRes.reRenderEntity(entityType)

    def OnResponse(rData):
        """ 请求获取的数据信息 """
        # type: (list[dict]) -> None
        for dic in rData:
            resId = str(dic["_render_id"])
            if not resId in DyRenderRes.resDict:
                DyRenderRes.resDict[resId] = dic
        ReRender(data)
    
    if not CAN_UP_DATE:
        Request("__CTRENDER.RenderParms__", args=(ND_QUERY_RES,), onResponse=OnResponse)
    else:
        ReRender(data)


@Listen("UiInitFinished")
def QCTRENDER_UiInitFinished(_={}):
    DyRenderRes.renderCount += 1
    if DyRenderRes.renderCount == 1:
        Call("__CTRENDER.PlayerDyRenderInit__", playerId)


lambda: "CT_RENDER By Zero123"
print("[Qu.CT-Render] 客户端已加载")
