# -*- coding: utf-8 -*-
"""PackJson - 读全部行为包里某个目录下的 JSON 文件（服务端）

引擎没有公开"列出行为包里的目录"的接口。机械动力（arrisCreate 的 Content/Server/BehaviorPackJson.py）用的是引擎内部的 server_resource 模块：
list_server_directory(目录) 跨全部已加载的行为包列出文件，load_server_file(路径) 读出字节；它的 create_recipes/ 和它的十来个附属包都靠这一条。
这里照它，经 traceback.sys.modules 取（脚本里不许 import sys；QuModLibs 的 ImportModule 也是这么取模块的），只在本模块里碰它：
模块或那两个函数不在、列目录抛了异常时 files() 返回 None，调用的人当这项能力没有（打一行日志）。读出来的文本剥掉 // 和 /* */ 注释（照机械动力），解码 UTF-8。
2026-11-26 在游戏里核过：另一个行为包里的 farmersdelight_recipes/ 文件读得到（Api/ExtensionApi/Events.RECIPE_JSON_FILES_VERIFIED）。
没单独看过的：给的路径带不带目录那一层（RecipeFiles 两种都认）、目录在哪个包里都没有时列出来是什么（空的还是抛异常：抛了照样当这条路不通）。
"""
import re
import traceback

_TOKENS = re.compile(r'"(?:\\.|[^"\\])*"|//[^\r\n]*|/\*[\s\S]*?\*/|/\*[\s\S]*')
SUFFIX = ".json"

try:
    _TEXT = (str, unicode)  # noqa: F821 - py2
except NameError:
    _TEXT = (str,)


def _str(value):
    """py2 的 unicode 换成 utf-8 的 str 再往中文的日志里拼（不然拼的时候按 ascii 解码中文那几个字节出错）。"""
    return value.encode("utf-8") if not isinstance(value, str) and isinstance(value, _TEXT) else value


def _strip(match):
    token = match.group(0)
    if token[0] == '"':
        return token
    if token[1] == "/":
        return ""
    return "".join(char for char in token if char in "\r\n")


def stripComments(text):
    """JSON 文本里的 // 和 /* */ 注释去掉（字符串里的不动，块注释里的换行留着，报错的行号还对得上）。"""
    if "//" not in text and "/*" not in text:
        return text
    return _TOKENS.sub(_strip, text)


def _resource():
    module = traceback.sys.modules.get("server_resource")
    if module is None or not hasattr(module, "list_server_directory") or not hasattr(module, "load_server_file"):
        return None
    return module


def _listed(resource, baseDir):
    """baseDir 下的 .json 路径，去重、排好序；列不出来是 None。"""
    try:
        listed = resource.list_server_directory(baseDir) or ()
    except Exception as error:  # noqa: BLE001 - 引擎内部模块，没有文档：抛了就当这条路不通
        print("[arrisFarmersDelight] 列行为包里的 %s/ 出错（%r），不读" % (baseDir, error))
        return None
    return sorted(set(path for path in listed if isinstance(path, _TEXT) and path.endswith(SUFFIX)))


def files(baseDir):
    """全部行为包里 baseDir 下的 .json：[(包里的路径, 剥了注释的文本)]，按路径排；读不了的那个记日志、跳过。引擎没有这条路是 None。"""
    resource = _resource()
    if resource is None:
        return None
    paths = _listed(resource, baseDir)
    if paths is None:
        return None
    found = []
    for path in paths:
        try:
            raw = resource.load_server_file(path)
            found.append((path, stripComments(raw.decode("utf-8") if isinstance(raw, bytes) else raw)))
        except Exception:  # noqa: BLE001 - 一个文件读不了不耽误别的
            print("[arrisFarmersDelight] 读行为包里的 %s 出错，跳过" % (_str(path),))
            traceback.print_exc()
    return found
