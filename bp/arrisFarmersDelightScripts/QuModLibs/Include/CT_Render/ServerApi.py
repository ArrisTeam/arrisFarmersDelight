# -*- coding: utf-8 -*-
from ...Server import *
from ...Modules.SharedAPI.Util import SharedBox
from Configure import QueryList
# >>>>>>>>>>>>>>>>
#  [WAR] CTRender即将在未来废弃 推荐使用GLRender替代相关业务
# <<<<<<<<<<<<<<<<

UpDateEntityQuery = "__CTRENDER.UpDateEntityQuery__"
UpDateEntityDyRender = "__CTRENDER.UpDateEntityDyRender__"

QUERYDICT = {}
""" 节点映射表 """

class GlobalQuery:
    """ 全局Query节点数据处理 """
    EntityQuery = {}
    EntityQueryCache = {} # type: dict[str,dict[str,float|int]]
    """ 实体节点信息缓存 """

@Listen("EntityRemoveEvent")
def __CTEntityRemoveEvent(Args): # 实体删除事件
    EntityId = Args['id']
    if EntityId in GlobalQuery.EntityQuery:
        del GlobalQuery.EntityQuery[EntityId]

def TranDmEntityQueryList(EntityQueryList):
    # type: (dict[str,dict[str,float|int]]) -> dict[str, dict[str,dict[str,float|int]]]
    """ 将实体资源数据转换为维度实体资源数据 """
    DemoDictQuery = {
        # 按实体所在维度划分 降低资源消耗
    }
    for entityId, Data in EntityQueryList.items():
        Dm = str(serverApi.GetEngineCompFactory().CreateDimension(entityId).GetEntityDimensionId())
        if not Dm in DemoDictQuery:
            DemoDictQuery[Dm] = {}  # 初始化
        Dic = DemoDictQuery[Dm]
        Dic[entityId] = Data
    return DemoDictQuery

def UpDate(): # 更新实体节点信息
    # type: () -> None
    """ 更新实体节点信息 """
    if len(GlobalQuery.EntityQueryCache) > 0:
        DemoDictQuery = TranDmEntityQueryList(GlobalQuery.EntityQueryCache)
        for playerId in serverApi.GetPlayerList():
            Dm = str(serverApi.GetEngineCompFactory().CreateDimension(playerId).GetEntityDimensionId())
            DataDict = DemoDictQuery.get(Dm, {})
            if len(DataDict) > 0:
                Call(playerId, UpDateEntityQuery, DataDict)
        GlobalQuery.EntityQueryCache.clear() # 清空字典

def SetQuery(EntityId, QueryName, Value, AutoUpDate=False):
    # type: (str, str, float, bool) -> bool
    """ 设置实体节点数据 (默认采用延迟更新算法,在下一帧统一更新) """
    if QueryName and isinstance(QueryName, str):
        QST = "query.mod."
        if QueryName.startswith(QST):
            QueryName = "q."+QueryName[len(QST):]
    else:
        QueryName = QUERYDICT[QueryName]    # 读取映射
    comp = serverApi.GetEngineCompFactory().CreateGame(levelId)
    alive = comp.IsEntityAlive(EntityId)
    if not alive: return False
    if not EntityId in GlobalQuery.EntityQuery:
        GlobalQuery.EntityQuery[EntityId] = {} # 初始化实体数据
    Datas = GlobalQuery.EntityQuery[EntityId] # type: dict[str,float]
    if Datas.get(QueryName, None) != Value: # 设置Query资源节点
        Datas[QueryName] = Value # 设置实体节点数据
        GlobalQuery.EntityQueryCache[EntityId] = Datas # 设置缓存节点数据
    if AutoUpDate: UpDate()
    return True

def GetQuery(entityId, queryName, defaultValue = 0.0):
    # type: (str, str, float) -> float
    """ 获取实体节点值 (仅限SetQuery设置的) """
    if queryName and isinstance(queryName, str):
        QST = "query.mod."
        if queryName.startswith(QST):
            queryName = "q."+queryName[len(QST):]
    else:
        queryName = QUERYDICT[queryName]    # 读取映射
    if not entityId in GlobalQuery.EntityQuery:
        return defaultValue
    datas = GlobalQuery.EntityQuery[entityId]   # type:  dict[str, float]
    return datas.get(queryName, defaultValue)

@CallBackKey("__CTRENDER.PlayerUpDateQuery__")
@Listen("ClientLoadAddonsFinishServerEvent")
def __CTClientLoadAddonsFinishServerEvent(Args): # 客户端加载完毕事件
    playerId = Args["playerId"]
    if len(GlobalQuery.EntityQuery) > 0:
        DemoDictQuery = TranDmEntityQueryList(GlobalQuery.EntityQuery)
        Dm = str(serverApi.GetEngineCompFactory().CreateDimension(playerId).GetEntityDimensionId())
        DataDict = DemoDictQuery.get(Dm, {})
        if len(DataDict) > 0:
            Call(playerId, UpDateEntityQuery, DataDict)

@CallBackKey("__CTRENDER.PlayerDyRenderInit__")
def PlayerDyRenderInit(playerId):
    if len(DyRenderSystem._entityDyRender) > 0:
        Call(playerId, UpDateEntityDyRender, DyRenderSystem.getEntityDyRender())


@Listen("OnScriptTickServer")
def __CTOnScriptTickServer(args={}):
    UpDate()                         # 节点更新
    DyRenderSystem._ON_Tick()        # 动态资源更新

for i, Query in enumerate(QueryList): # 自定义节点表处理
    QUERYDICT[Query] = str(i)   # 节点映射


class DyRenderSystem:
    """ 动态资源管理系统

        该系统基于静态管理实现 因此你需要考虑到键位冲突问题, 每个DyRenderObj对象都有一个ID分配
        默认自动分配
    """

    # ======== 一些常用的材料 ========
    ENTITY = "entity"
    ENTITY_ALPHATEST = "entity_alphatest"
    ENTITY_EMISSIVE_ALPHA = "entity_emissive_alpha"
    ENTITY_EMISSIVE ="entity_emissive"

    # ======== 实体资源数据 ========
    _entityDyRender = {}            # type: dict[str,set[int]]
    _entityDyRenderCache = {}       # type: dict[str,set[int]]

    # ======== 玩家资源引用计数 ========
    _playerResRef = {}              # type: dict[str, dict[str, SharedBox]]

    class DyRenderObj(object):
        """ 动态资源渲染 """
        dyRenderCache = {}          # type: dict[str, DyRenderSystem.DyRenderObj]
        """ 动态渲染资源缓存 """
        def __new__(cls, *args, **kwargs):
            key = str(args)+str(kwargs)
            if key in DyRenderSystem.DyRenderObj.dyRenderCache:
                return DyRenderSystem.DyRenderObj.dyRenderCache[key]
            SELF = object.__new__(cls, *args, **kwargs)
            DyRenderSystem.DyRenderObj.dyRenderCache[key] = SELF
            return SELF

        def __init__(self,  materials = {}, textures = {}, geometry = {}, animate = [], animations = {}, render_controllers = [], particle_effects = {}, sound_effects = {}, res_id = None, customQuery = None):
            self._materials = materials
            """ 材料 """
            self._textures = textures
            """ 纹理 """
            self._geometry = geometry
            """ 模型 """
            self._animate = animate
            """ 动画播放键位表 """
            self._animations = animations
            """ 动画 """
            self._render_controllers = render_controllers
            """ 渲染控制器 """
            self._particle_effects = particle_effects
            """ 粒子特效 """
            self._sound_effects = sound_effects
            """ 声音效果 """
            self._render_id = int(res_id) if res_id != None else int(id(self))
            """ 渲染资源ID """
            self._customQuery = customQuery
            """ 自定义节点 如果存在 """

        def getRenderParm(self):
            # type: () -> dict
            """ 获取渲染参数表 """
            cQ = self.getCustomQuery()
            valueBase = lambda x:"({}) && ({} == 1.0)".format(x, cQ)
            return {
                "materials": self._materials,
                "textures": self._textures,
                "geometry": self._geometry,
                "animate": DyRenderSystem.DyRenderObj.formatDataList(self._animate, valueNon=cQ, valueBase=valueBase),
                "animations": self._animations,
                "particle_effects": self._particle_effects,
                "sound_effects": self._sound_effects,
                "render_controllers": DyRenderSystem.DyRenderObj.formatDataList(self._render_controllers, valueNon=cQ, valueBase=valueBase),
                "_render_id": self._render_id,
            }
        
        def getReferenceMap(self):
            # type: () -> dict[str, set[str]]
            """ 获取引用MAP """
            cQ = self.getCustomQuery()
            valueBase = lambda x:"({}) && ({} == 1.0)".format(x, cQ)
            _renderControllers = DyRenderSystem.DyRenderObj.formatDataList(self._render_controllers, valueNon=cQ, valueBase=valueBase)
            renderControllers = set()
            for v in _renderControllers:
                for k in v:
                    renderControllers.add(k)
            mapData = {
                "materials": set(self._materials),
                "textures": set(self._textures),
                "geometry": set(self._geometry),
                "render_controllers": renderControllers
            }
            return mapData
        
        def getCustomQuery(self):
            # type: () -> str
            """ 获取随机分配的自定义节点 """
            if self._customQuery:
                return self._customQuery
            return "query.mod.ct_render_" + str(abs(self._render_id))

        @staticmethod
        def formatDataList(lis, valueNon = "(1.0)", valueBase = lambda x: x):
            # type: (list, str, object) -> list[dict]
            """ 格式化数据列表 """
            def keyFormat(d):
                # type: (dict[str,str]) -> dict
                for k, v in d.items():
                    d[k] = valueBase(v)
                return d
            return [
                (keyFormat(x) if isinstance(x, dict) else {x: valueNon}) for x in lis
            ]
        
        def setEntityDyRenderObj(self, entityId, state = True, mustAlive = True):
            # type: (str, bool, bool) -> bool
            """ 设置实体动态资源
                @state
                渲染状态 默认为True 设置为False可停止渲染

                @mustAlive
                要求实体必须存活(脱离渲染也视为死亡), 设置为False可禁用

                PS:该方法采用延迟更新模式, 所有资源信息会在下一帧统一更新
            """
            return DyRenderSystem.setEntityDyRenderObj(entityId, self, state, mustAlive)

        def setPlayerDyRenderObj(self, entityId, state = True):
            # type: (str, DyRenderSystem.DyRenderObj, bool) -> bool
            """ (实验性) 设置玩家动态资源信息 
            相较于setEntityDyRenderObj 该方法提供了 [垃圾回收器] 以便回收所无引用资源 适用于玩家大量但低频率的资源操作
            """
            return DyRenderSystem.setPlayerDyRenderObj(entityId, self, state)

    @staticmethod
    def _registerDyRender(engineTypeStr, resId):
        # type: (str, int) -> bool
        """ 注册动态资源 """
        for dic in (DyRenderSystem._entityDyRenderCache, DyRenderSystem._entityDyRender):
            if dic is DyRenderSystem._entityDyRenderCache:
                # 缓存数据对比实际数据
                if engineTypeStr in DyRenderSystem._entityDyRender:
                    if resId in DyRenderSystem._entityDyRender[engineTypeStr]:
                        continue
            if not engineTypeStr in dic:
                # 初始化集合
                dic[engineTypeStr] = set()
            st = dic[engineTypeStr]
            if not resId in st:
                st.add(resId)
        return True

    @staticmethod
    def setEntityDyRenderObj(entityId, renderObj, state = True, mustAlive = True):
        # type: (str, DyRenderSystem.DyRenderObj, bool, bool) -> bool
        """ 设置实体动态资源
            @state
            渲染状态 默认为True 设置为False可停止渲染

            @mustAlive
            要求实体必须存活(脱离渲染也视为死亡), 设置为False可禁用

            PS:该方法采用延迟更新模式, 所有资源信息会在下一帧统一更新
        """
        comp = serverApi.GetEngineCompFactory().CreateGame(levelId)
        alive = comp.IsEntityAlive(entityId)
        if alive == False and mustAlive:
            return False
        # 实体标识符
        engineTypeStr = serverApi.GetEngineCompFactory().CreateEngineType(entityId).GetEngineTypeStr()
        if engineTypeStr == None:
            return False
        DyRenderSystem._registerDyRender(engineTypeStr, renderObj._render_id)
        # ======== 设置对应的资源Query节点状态 ========
        customQuery = renderObj.getCustomQuery()
        SetQuery(entityId, customQuery, float(state))
        return True
    
    @staticmethod
    def setPlayerDyRenderObj(entityId, renderObj, state = True):
        # type: (str, DyRenderSystem.DyRenderObj, bool) -> bool
        """ (实验性) 设置玩家动态资源信息 
        相较于setEntityDyRenderObj 该方法提供了 [垃圾回收器] 以便回收所无引用资源 适用于玩家大量但低频率的资源操作
        """
        comp = serverApi.GetEngineCompFactory().CreateGame(levelId)
        alive = comp.IsEntityAlive(entityId)
        if alive == False or serverApi.GetEngineCompFactory().CreateEngineType(entityId).GetEngineTypeStr() != "minecraft:player":
            # 无效的实体ID (或非玩家)
            return False
        back = DyRenderSystem.setEntityDyRenderObj(entityId, renderObj, state)
        return back
    
    @staticmethod
    def _ON_Tick():
        if len(DyRenderSystem._entityDyRenderCache) > 0:
            Call("*", UpDateEntityDyRender, DyRenderSystem.getEntityDyRenderCache())
            DyRenderSystem._entityDyRenderCache = {}
    
    @staticmethod
    def getEntityDyRenderCache():
        # type: () -> dict[str, list[int]]
        return DyRenderSystem._formatSet(DyRenderSystem._entityDyRenderCache)

    @staticmethod
    def getEntityDyRender():
        # type: () -> dict[str, list[int]]
        return DyRenderSystem._formatSet(DyRenderSystem._entityDyRender)
    
    @staticmethod
    def _formatSet(obj):
        # type: (dict[str, set[int]]) -> dict[str, list[int]]
        newDic = {}
        for k, v in obj.items():
            newDic[k] = list(v)
        return newDic
    
    @staticmethod
    @CallBackKey("__CTRENDER.RenderParms__")
    def getRenderParm(idList):
        # type: (list[int]) -> list[dict]
        """ 获取渲染信息 """
        idMap = set(idList)
        dyDict = DyRenderSystem.DyRenderObj.dyRenderCache
        return [v.getRenderParm() for _, v in dyDict.items() if v._render_id in idMap]


lambda: "CT_RENDER By Zero123"
print("[Qu.CT-Render] 服务端已加载")
