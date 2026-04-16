# -*- coding: utf-8 -*-
lambda: "By Zero123"
lambda: "TIME: 2024/05/04"
from ...IN import ModDirName
GL_MOB_QUERY_KEY = "Q_{}_GL.MOB_QUERY".format(ModDirName)

class GL_CUSTOM_QUERY:
    GL_QUERYS = [
    ]   # type: list[str]
    """ 全局资源节点 """

class GL_OPT_INSTRUCT:
    OTHER = -1
    """ 其他操作 """
    WRITE = 0
    """ 覆盖资源 """
    DELETE = 1
    """ 删除资源 """

class GL_BASE_RES_OPT:
    """ 资源操作基类 用于管理合并及对抗 """
    def __init__(self):
        self._INSTRUCT_ID = -1
        self._TYPE = GL_OPT_INSTRUCT.OTHER
        self._KEY = None
        self._SHARED_DATA = {}
    
    def CAN_NOT_NULL(self, value):
        if value == None:
            raise Exception("该资源对象禁止使用None值删除")
    
    def _CREAT_TYPE(self, value):
        """ 基于value值计算操作类型 """
        if value == None:
            self._TYPE = GL_OPT_INSTRUCT.DELETE
        else:
            self._TYPE = GL_OPT_INSTRUCT.WRITE
    
    def isTypeSame(self, other):
        # type: (GL_BASE_RES_OPT) -> bool
        """ 计算类型相同 """
        if other == None:
            return False
        return isinstance(other, self.__class__)

    def processing(self, other):
        # type: (GL_BASE_RES_OPT) -> GL_OPT_INSTRUCT
        """ 资源操作处理 """
        if self._TYPE == None:
            return GL_OPT_INSTRUCT.OTHER
        if isinstance(other, self.__class__) and self._KEY == other._KEY:
            # 同类型操作且_KEY值相同
            return GL_OPT_INSTRUCT.WRITE
        return GL_OPT_INSTRUCT.OTHER    # 资源并存
    
    def hashKey(self):
        # type: () -> str | None
        """ 获取并返回哈希键位 适用于基于KEY的资源 """
        return None

    def build(self):
        # (_TYPE _INSTRUCT_ID _SHARED_DATA) 合成操作指令 用于确定如何处理客户端资源
        return [
            self._INSTRUCT_ID,
            self._TYPE,
            self._SHARED_DATA
        ]
    
class GL_KV_RES(GL_BASE_RES_OPT):
    """ 键值对资源 """
    def __init__(self, key, value):
        GL_BASE_RES_OPT.__init__(self)
        self.key = key
        self._KEY = key
        self.value = value
        self._CREAT_TYPE(value)
        self._SHARED_DATA = { "d": [self.key, self.value] }

    def hashKey(self):
        # type: () -> str | None
        return "{}.{}".format(self.__class__.__name__, self.key)

class GL_ONCE_RES(GL_BASE_RES_OPT):
    """ 单元素资源 """
    def __init__(self, value):
        GL_BASE_RES_OPT.__init__(self)
        self._KEY = value
        self.value = value
        self._CREAT_TYPE(value)
        self._SHARED_DATA = { "d": [self.value] }

class GL_RES_OPT:
    """ 公共资源操作 """
    class GL_TEXTURE(GL_KV_RES):
        """ 纹理资源 """
        def __init__(self, key, value):
            GL_KV_RES.__init__(self, key, value)
            self._INSTRUCT_ID = 0
            self.CAN_NOT_NULL(value)

    class GL_GEOMETRY(GL_KV_RES):
        """ 模型资源 """
        def __init__(self, key, value):
            GL_KV_RES.__init__(self, key, value)
            self._INSTRUCT_ID = 1

    class GL_MATERIAL(GL_KV_RES):
        """ 材质资源 """
        def __init__(self, key, value):
            GL_KV_RES.__init__(self, key, value)
            self._INSTRUCT_ID = 2
            self.CAN_NOT_NULL(value)

    class GL_ANIM(GL_KV_RES):
        """ 动画/控制器资源 """
        def __init__(self, key, value):
            GL_KV_RES.__init__(self, key, value)
            self._INSTRUCT_ID = 3

    class GL_PARTICLE_EFFECT(GL_KV_RES):
        """ 粒子资源 """
        def __init__(self, key, value):
            GL_KV_RES.__init__(self, key, value)
            self._INSTRUCT_ID = 4
            self.CAN_NOT_NULL(value)

    class GL_RENDER_CONTROLLER(GL_KV_RES):
        """ 渲染控制器资源 """
        def __init__(self, key, value):
            GL_KV_RES.__init__(self, key, value)
            self._INSTRUCT_ID = 5

    class GL_SCRIPT_ANIMATE(GL_KV_RES):
        """ ANIMATE节点资源 """
        def __init__(self, key, value, autoReplace = False):
            GL_KV_RES.__init__(self, key, value)
            self._INSTRUCT_ID = 6
            self._autoReplace = autoReplace
            self._SHARED_DATA = { "d": [self.key, self.value, autoReplace] }
            self.CAN_NOT_NULL(value)
            
    class GL_SOUND_EFFECT(GL_KV_RES):
        """ 音效资源 """
        def __init__(self, key, value):
            GL_KV_RES.__init__(self, key, value)
            self._INSTRUCT_ID = 7
            self.CAN_NOT_NULL(value)

    class GL_PLAYER_SKIN(GL_KV_RES):
        """ 玩家皮肤纹理资源 """
        def __init__(self, value):
            GL_KV_RES.__init__(self, "__p_skin__", value)
            self._INSTRUCT_ID = 8

class JSONRenderData:
    """ JSON渲染参数 """
    # ======== 一些常用的材料 ========
    ENTITY = "entity"
    ENTITY_ALPHATEST = "entity_alphatest"
    ENTITY_EMISSIVE_ALPHA = "entity_emissive_alpha"
    ENTITY_EMISSIVE ="entity_emissive"

    def __init__(self,
            materials = {}, textures = {},
            geometry = {}, animate = [],
            animations = {}, render_controllers = [],
            particle_effects = {}, sound_effects = {}
        ):
        # type: (dict, dict, dict, list, dict, list, dict, dict) -> None
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
    
    @staticmethod
    def _FORMAT_LIST_MOLANG_KV(lisData, baseValue = "(1.0)"):
        lisData = list(lisData)
        for value in lisData:
            if isinstance(value, str):
                yield (value, baseValue)
            elif isinstance(value, dict):
                for key, molang in value.items():
                    yield (key, molang)
    
    def formatRenderControllers(self):
        """ 获取格式化后的渲染控制器信息 """
        return JSONRenderData._FORMAT_LIST_MOLANG_KV(self._render_controllers)

    def formatAnimate(self):
        """ 获取格式化后的动画播放键位信息 """
        return JSONRenderData._FORMAT_LIST_MOLANG_KV(self._animate)

def loadQueryFromClass(cls):
    # type: (type) -> None
    """ 从Class加载Query """
    for queryName in (getattr(cls, x) for x in dir(cls) if not x.startswith("__")):
        GL_CUSTOM_QUERY.GL_QUERYS.append(queryName)
