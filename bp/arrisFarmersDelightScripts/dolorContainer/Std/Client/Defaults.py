# -*- coding: utf-8 -*-
"""
标准库在客户端的缺省登记（docs/ARCHITECTURE.md 第 2.1 节）：客户端服务启动时导入本模块。只做登记，不含逻辑，只登记每个界面
都要的。两端共用的那部分在 Std/Defaults.py，这里一并导入。
不在这里的：标准件在客户端要的引擎接口（RecipeQuery、EnchantInfo）由标准件第一次用到时载入（SIDE_MODULES）；交易与创造栏
搜索框的控件（Trading、Creative）由用到它们的布局载入（组件的 widgetModule，记在绑定表里）；方块宿主的客户端一半
（Std/Block/Client.py）由用方块宿主的使用方在客户端导入。
"""
from .. import Defaults  # noqa: F401  两端共用的缺省实现
from . import Widgets  # noqa: F401  库带的运行时控件（格子区、文字、按钮、列表……）
