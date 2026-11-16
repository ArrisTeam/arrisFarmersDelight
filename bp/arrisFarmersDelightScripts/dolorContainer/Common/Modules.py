# -*- coding: utf-8 -*-
"""
按名字导入模块，与可选件用到才载入（docs/ARCHITECTURE.md 第 2.1、2.2 节）。

importModule 照 QuModLibs 的 ImportModule 写（库不靠使用方带的 QuModLibs 有没有它）：网易打包机审不收内置的按名字导入
函数，importlib 不在 Python 模块白名单里、不能直接 import。已载入的从已载入模块表取，没载入的借表里已有的 importlib 导入。
importlib 要等引擎或别的模组导入过才在表里，还没有时退回引擎按路径导入的接口：它只导入已登记的脚本包里的模块，顺带把
importlib 载入，之后都走上一条路。引擎的接口按端提供，由两端服务启动时登记（本模块两端共用、不导入引擎）；单人游戏两端在
同一个解释器里，取得到哪端用哪端。

load 载入库里的可选件（相对库包写，如 "Std.Server.RecipeQuery"），只载入一次：
- 标准件在一端要的模块写在标准件模块的 SIDE_MODULES 里（{"server": (路径, ...), "client": (...)}，vendor 按它保留），
  第一次用到时载入；
- 布局用到的控件不在标准控件模块里的，编译出的绑定表记着它们所在的模块，客户端第一次取这个布局时载入（Client/Layouts.py）。
两端服务登记引擎的接口之前（离线测试没起服务）不载入、返回 False，也不记下。载入出错（拷进使用方时漏了，或模块本身有错）时
记一行日志，以后不再试。
"""
import traceback

from .. import HOST

PACKAGE = __name__.rsplit(".", 2)[0]   # 库包的全名（使用方脚本根.dolorContainer）
_engineImporters = []   # 两端服务登记的引擎按路径导入的接口（导不到返回 None）
_loaded = {}            # 相对库包的路径 -> 载入了没有


def addEngineImporter(importer):
    """两端服务启动时登记引擎按路径导入的接口（extraServerApi / extraClientApi 的 ImportModule）。"""
    if importer not in _engineImporters:
        _engineImporters.append(importer)


def importModule(path):
    """按全名导入模块，返回模块对象；导不到时抛 ImportError。"""
    modules = traceback.sys.modules
    module = modules.get(path)
    if module is not None:
        return module
    importlib = modules.get("importlib")
    if importlib is not None:
        return importlib.import_module(path)
    for importer in _engineImporters:
        module = importer(path)
        if module is not None:
            return module
    raise ImportError("No module named %s" % path)


def load(path):
    """载入库里的模块 path（相对库包），返回载入了没有。"""
    done = _loaded.get(path)
    if done is None:
        if not _engineImporters:
            return False
        try:
            importModule(PACKAGE + "." + path)
            done = True
        except Exception:  # noqa: BLE001  载入不了只让用到它的那件不能用，不连累调用的地方
            print("[dolorContainer:%s] cannot load %s\n%s" % (HOST, path, traceback.format_exc()))
            done = False
        _loaded[path] = done
    return done


def loadAll(paths):
    """依次载入几个模块（标准件 SIDE_MODULES 里一端的，布局的控件模块）。"""
    for path in paths or ():
        load(path)
