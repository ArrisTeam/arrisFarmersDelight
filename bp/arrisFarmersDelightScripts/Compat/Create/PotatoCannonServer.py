# -*- coding: utf-8 -*-
"""PotatoCannonServer - 机械动力的土豆加农炮认农夫乐事的弹药：服务端那一份登记（服务端）

做什么见 PotatoCannonAmmo；这里只把本包服务端的加载器系统和 extraServerApi 交给它。没装机械动力时什么都不登记。
"""
from ...QuModLibs.Server import serverApi
from ...QuModLibs.Systems.Loader.Server import LoaderSystem
from . import PotatoCannonAmmo

PotatoCannonAmmo.hook("server", LoaderSystem.getSystem(), serverApi)
