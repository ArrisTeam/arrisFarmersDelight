# -*- coding: utf-8 -*-
"""
布局的绑定表（tools/layouts.py 从布局源文件编译生成，不手改）：布局名 -> 界面模型、两套界面
（经典版、携带版）的屏幕定义名、运行时控件（控件名与参数、路径）、写文字的控件与具名控件的路径（相对屏幕根）、
用到的控件不在标准控件模块里时登记它们的库模块（imports）。
运行时由 dolorContainer/Client/Layouts.py 读；VERSION 是格式版本。
"""

VERSION = 3

LAYOUTS = {}
