# -*- coding: utf-8 -*-
"""
标准库的缺省登记（docs/ARCHITECTURE.md 第 2.1 节）：两端服务启动时导入本模块，库自带的原版实现随之登记。
只做登记，不含逻辑。新加一种缺省实现（操作、数据类型、控件……），在这里导入它的模块。
"""
from . import Containers  # noqa: F401  常用的容器种类（Common/Collections 的种类表）
from . import Operations  # noqa: F401  原版的物品操作（Common/Ops 的登记表）
from . import Interactions  # noqa: F401  原版的手势（Common/Slots 的标准交互）
