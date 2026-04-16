# -*- coding: utf-8 -*-
# >>>>>>>>>>>>>>>>
#  [WAR] CTRender即将在未来废弃 推荐使用GLRender替代相关业务
# <<<<<<<<<<<<<<<<

lambda: "By Zero123"

PlayerRes = {
    "materials":{},
    "textures":{},
    "geometry":{},
    "animate":[],
    "animations":{},
    "render_controllers":[],
    "particle_effects":{},
    "sound_effects": {}
}

QueryList = []  # 自定义节点表

def loadQueryFromClass(cls):
    # type: (type) -> None
    """ 从Class加载Query """
    for queryName in (getattr(cls, x) for x in dir(cls) if not x.startswith("__")):
        QueryList.append(queryName)

def regBaseQuery(_count = 5):
    """ 注册基本节点 (通用) 如: query.mod.qu_ctr_base0 通常搭配预设系统管理预设实体资源 """
    for i in range(_count):
        QueryList.append("query.mod.qu_ctr_base" + str(i))