# -*- coding: utf-8 -*-
"""OtherMods - 取别的模组的模块：对方没装、装的版本里没有这个模块、或者它自己导入时出错，都当它没装（双端，不碰引擎）

引擎的 ImportModule（serverApi / clientApi 各一个，里面调 importlib.import_module）取一个模块有三种结果
（下面写的都是 3.10 实机、两端：2026-11-26 单机的服务端、客户端线程各量一遍，结果一样）：
1. 路径的第一段不是已加载的脚本根（那个模组没装、名字写错）：返回 None，不抛。官方文档"不存在返回 None"只对这一种成立。
2. 脚本根在、下面没有这个模块或子包（比如对方装的是还没有这个模块的旧版本）：抛 ImportError，文字是 "No module named " 加上缺的那一截——
   缺最后一段就是那一段（取 a.b.NoSuch -> No module named NoSuch），缺中间的包是从它起的整截（取 a.NoPkg.Thing -> No module named NoPkg.Thing）。
3. 模块在、它自己导入时出错：把那个异常原样抛给调用的人，类型和文字都不变（森罗物语的一个接口模块就这样一路抛进了前置包内容包的服务端入口，
   那个入口没导入成，它的端点全没了）。同一个坏模块再取，它的模块体从头再跑一遍、再抛同样的异常；不会给导了一半的模块
   （只在第一次导入时出错的模块，第二次取到的是完整的）。
农夫乐事在运行时取别的模组的模块（前置包、机械动力、成就系统、arrisJei）一律经 find，调用的地方都照它本来"没装"的那条路走：
第 1 种原样给 None；第 2 种（isMissing 认）也安静地返回 None——不打日志、不记进 failures，那是正常的配置，不是出错；
第 3 种接住异常，打一行日志（哪个模块）连同调用栈，返回 None：别的模组的错不许带倒农夫乐事。对方的模块在、它 import 的东西不在时，
文字也是 "No module named X"，和第 2 种的区别只在 X 是不是所取路径的结尾（X 恰好和结尾同名时分不出来，当没装）。
有的模组取它的门面时才导入自己的模块（机械动力的 getExtensionApi），那种调用经 call：没有"所取的路径"，抛什么都照第 3 种。
同一个名字出错只打一次日志（有的地方反复取，比如 JEI 的每类配方各取一次、前置包的声明模块四个站点各取一次）；之后照样再取
（它可能只是那一次没导入成，不记成"永远没装"），再出错就不出声地当没装。单机时两端共用这一份记录：同一个模块哪端先出错哪端打。
联机、专用服务器、打包发布以后的加载器都还没量过。引擎的 ImportModule 由调用的人交进来，这里不碰引擎，离线可测。
"""
import traceback

NO_MODULE = "No module named "      # 引擎（Python 2.7 的导入）说"没有这个模块"的文字，后面是缺的那一截
_UNICODE = type(u"")                # py2 的 unicode（py3 里 str 就是它）
_failed = {}        # 出过错的名字（模块路径，或 call 的 模块.函数名）-> 第一次的异常（repr）：打过日志的，不再打


def find(importModule, path):
    """importModule 是那一端引擎的 ImportModule（serverApi.ImportModule / clientApi.ImportModule）。
    返回 path 那个模块；没装（引擎给 None）、对方装着却没有这个模块（isMissing）或者它导入时出错，都返回 None。"""
    try:
        return importModule(path)
    except Exception as error:  # noqa: BLE001 - 别的模组的错不许带倒农夫乐事
        if not isMissing(path, error):
            _report(path, error)
        return None


def isMissing(path, error):
    """error 是不是引擎说"对方的脚本根在、下面没有 path 这个模块"的那一种：ImportError、只有一个参数，文字正好是 "No module named " + T，
    path 以 "." + T 结尾（T 可以带点：缺中间的包时是从它起的整截）。T 等于整个 path 不算（第一段不在时引擎给 None，走不到异常）。
    py2 里本包写的路径是字节串，引擎给的文字实机只看到了内容、没看到是哪一种字符串：哪个是 unicode 就先转成 utf-8 字节串再比，
    不和字节串混着比（非 ASCII 的混着比会抛 UnicodeDecodeError）；py3 的 bytes 不比，不算。"""
    args = error.args if isinstance(error, ImportError) else ()
    text = _native(args[0]) if len(args) == 1 else None
    where = _native(path)
    if text is None or where is None or not text.startswith(NO_MODULE):
        return False
    tail = text[len(NO_MODULE):]
    return bool(tail) and where.endswith("." + tail)


def _native(text):
    """原生的 str 原样给；py2 的 unicode 转成 utf-8 字节串；别的（py3 的 bytes、不是字符串的）给 None。"""
    if isinstance(text, str):
        return text
    return text.encode("utf-8") if isinstance(text, _UNICODE) else None


def call(func, *args):
    """调别的模组的函数（取门面这类，调的时候才导入它自己的模块）：返回它的结果；它抛异常返回 None。"""
    try:
        return func(*args)
    except Exception as error:  # noqa: BLE001 - 别的模组的错不许带倒农夫乐事
        _report("%s.%s" % (getattr(func, "__module__", "?"), getattr(func, "__name__", "?")), error)
        return None


def failures():
    """出过错的名字 -> 第一次的异常（游戏里 execute_code 看哪个模组的东西没取到；没装、没有这个模块的不在这里）。"""
    return dict(_failed)


def _report(name, error):
    """在 except 里调：这个名字第一次出错就打一行日志连同调用栈。"""
    if name not in _failed:
        _failed[name] = repr(error)
        print("[arrisFarmersDelight] 取别的模组的 %s 时它出错，当它没装：%r" % (name, error))
        traceback.print_exc()
