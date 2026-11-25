# -*- coding: utf-8 -*-
"""PotatoCannonClient - 机械动力的土豆加农炮认农夫乐事的弹药：客户端那一份登记（弹丸怎么画）（客户端）

做什么见 PotatoCannonAmmo；这里只把本包客户端的加载器系统和 extraClientApi 交给它。没装机械动力时什么都不登记。
"""
from ...QuModLibs.Client import clientApi
from ...QuModLibs.Systems.Loader.Client import LoaderSystem
from . import PotatoCannonAmmo

PotatoCannonAmmo.hook("client", LoaderSystem.getSystem(), clientApi)
