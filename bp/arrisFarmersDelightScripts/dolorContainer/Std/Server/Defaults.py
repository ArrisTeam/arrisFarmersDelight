# -*- coding: utf-8 -*-
"""
标准库在服务端的缺省登记（docs/ARCHITECTURE.md 第 2.1 节）：服务端服务启动时导入本模块。只做登记，不含逻辑，只登记每个界面
都要的。两端共用的那部分在 Std/Defaults.py，这里一并导入。
标准件在服务端要的引擎接口（RecipeQuery、EnchantingEngine、LoomEngine）不在这里：标准件第一次用到时载入（SIDE_MODULES）。
"""
from .. import Defaults  # noqa: F401  两端共用的缺省实现
from . import Containers  # noqa: F401  常用容器种类在服务端的存法
from . import Words  # noqa: F401  服务端的敏感词检查（接给动作参数的文字格式）
