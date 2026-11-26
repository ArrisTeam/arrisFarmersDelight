# -*- coding: utf-8 -*-
"""OtherMods - 取别的模组的模块：对方没装、或者它自己导入时出错，都当它没装（双端，不碰引擎）

引擎的 ImportModule（serverApi / clientApi 各一个）：模块不存在时返回 None（官方文档只写了这一条）；模块在、它自己导入时出错，
不返回 None，而是把那个异常原样抛给调用的人（3.10 实机，2026-11-26：森罗物语的一个接口模块导入时 ImportError，一路抛进了
前置包内容包的服务端入口模块，那个入口没导入成，它的端点全没了）。
农夫乐事在运行时取别的模组的模块（前置包、机械动力、成就系统、arrisJei）一律经 find：接住异常，打一行日志（哪个模块）连同调用栈，
返回 None，调用的地方照它本来"没装"的那条路走——别的模组的错不许带倒农夫乐事。有的模组取它的门面时才导入自己的模块
（机械动力的 getExtensionApi），那种调用经 call，一样处理。
同一个名字出错只打一次日志（有的地方反复取，比如 JEI 的每类配方各取一次、前置包的声明模块四个站点各取一次）；之后照样再取
（它可能只是那一次没导入成，不记成"永远没装"），再出错就不出声地当没装。单机时两端共用这一份记录：同一个模块哪端先出错哪端打。
引擎的 ImportModule 由调用的人交进来，这里不碰引擎，离线可测。
"""
import traceback

_failed = {}        # 出过错的名字（模块路径，或 call 的 模块.函数名）-> 第一次的异常（repr）：打过日志的，不再打


def find(importModule, path):
    """importModule 是那一端引擎的 ImportModule（serverApi.ImportModule / clientApi.ImportModule）。
    返回 path 那个模块；没装（引擎给 None）或者它导入时出错，都返回 None。"""
    return _guarded(path, importModule, path)


def call(func, *args):
    """调别的模组的函数（取门面这类，调的时候才导入它自己的模块）：返回它的结果；它抛异常返回 None。"""
    return _guarded("%s.%s" % (getattr(func, "__module__", "?"), getattr(func, "__name__", "?")), func, *args)


def failures():
    """出过错的名字 -> 第一次的异常（游戏里 execute_code 看哪个模组的东西没取到）。"""
    return dict(_failed)


def _guarded(name, func, *args):
    try:
        return func(*args)
    except Exception as error:  # noqa: BLE001 - 别的模组的错不许带倒农夫乐事
        if name not in _failed:
            _failed[name] = repr(error)
            print("[arrisFarmersDelight] 取别的模组的 %s 时它出错，当它没装：%r" % (name, error))
            traceback.print_exc()
        return None
