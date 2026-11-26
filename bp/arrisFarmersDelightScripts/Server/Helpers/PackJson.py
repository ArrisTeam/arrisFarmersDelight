# -*- coding: utf-8 -*-
"""PackJson - 读全部行为包里某个目录下的 JSON 文件（服务端）

引擎没有公开"列出行为包里的目录"的接口。机械动力（arrisCreate 的 Content/Server/BehaviorPackJson.py）用的是引擎内部的 server_resource 模块：
list_server_directory(目录) 跨全部已加载的行为包列出文件，load_server_file(路径) 读出字节；它的 create_recipes/ 和它的十来个附属包都靠这一条。
这里照它，经 traceback.sys.modules 取（脚本里不许 import sys；QuModLibs 的 ImportModule 也是这么取模块的），只在本模块里碰它：
模块或那两个函数不在、列目录抛了异常时 files() 返回 None，调用的人当这项能力没有（打一行日志）。读出来的文本剥掉 // 和 /* */ 注释（照机械动力），解码 UTF-8。
listing() / read() 是一层目录的条目、一个路径的文件：原版动物读生效的实体定义用（Server/AnimalFood.py，照森罗物语厨房的 entity_definition.py）。
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


def _decoded(raw):
    """文件的字节 -> 文字：UTF-8，开头带 BOM 的也收（Windows 的记事本存出来常带；json 不认 BOM）。"""
    found = raw.decode("utf-8-sig") if isinstance(raw, bytes) else raw
    return found[1:] if found[:1] == u"\ufeff" else found


def _resource():
    module = traceback.sys.modules.get("server_resource")
    if module is None or not hasattr(module, "list_server_directory") or not hasattr(module, "load_server_file"):
        return None
    return module


def _entries(resource, baseDir):
    """baseDir 下的条目（文件和子目录的路径），去重、排好序；列不出来是 None。"""
    try:
        listed = resource.list_server_directory(baseDir) or ()
    except Exception as error:  # noqa: BLE001 - 引擎内部模块，没有文档：抛了就当这条路不通
        print("[arrisFarmersDelight] 列行为包里的 %s/ 出错（%r），不读" % (baseDir, error))
        return None
    return sorted(set(path for path in listed if isinstance(path, _TEXT)))


_MOST_ENTRIES = 4096   # files() 往下列子目录时最多看这么多条（引擎给的路径绕回来也不会转圈）


def _below(resource, entry):
    """往下列一层：条目是文件时引擎可能抛异常、给空的，都当它没有下一层（不打日志）。"""
    try:
        return [path for path in (resource.list_server_directory(entry) or ()) if isinstance(path, _TEXT)]
    except Exception:  # noqa: BLE001 - 条目是个文件：没有下一层
        return []


def _listed(resource, baseDir):
    """baseDir 下（连子目录）的 .json 路径，去重、排好序；列不出来是 None。不是 .json 的条目再列一次，列得出东西就接着往下：成就系统
    （arrisAdvancements 的 AdvancementServer._collectJsonPaths）记着 list_server_directory 不递归、专用服务器上只给一层；农夫乐事 2026-11-26
    只在开发版游戏里量到过它递归，打包后、专用服务器上没量过。引擎本来就递归时结果不变（重复的去掉）。listing() 照旧只列一层。"""
    entries = _entries(resource, baseDir)
    if entries is None:
        return None
    found, seen, pending = set(), set(), list(entries)
    while pending and len(seen) < _MOST_ENTRIES:
        entry = pending.pop(0)
        if entry in seen:
            continue
        seen.add(entry)
        if entry.endswith(SUFFIX):
            found.add(entry)
        else:
            pending.extend(_below(resource, entry))
    return sorted(found)


def listing(baseDir):
    """全部行为包里 baseDir 下的条目（文件和子目录的路径，去重、排好序；引擎只列这一层，子目录要再列）；引擎没有这条路、列不出来是 None。"""
    resource = _resource()
    return None if resource is None else _entries(resource, baseDir)


def read(path):
    """包栈里这个路径的文件，剥了注释的文本；没有这个文件（读出空的）、读不了、引擎没有这条路都是 None。
    几个包都有这个路径时读到的是哪一份：引擎走包管理器的 load，按包栈的先后找第一份，应当是优先级最高的那个包的 [推断：
    读的是 _resource_server.LoadServerFile 的反编译，没在游戏里放两份同路径的文件比过]。"""
    resource = _resource()
    if resource is None:
        return None
    try:
        raw = resource.load_server_file(path)
        return stripComments(_decoded(raw)) if raw else None
    except Exception:  # noqa: BLE001 - 读不了（解码不了）当没有这个文件
        print("[arrisFarmersDelight] 读行为包里的 %s 出错，当没有" % (_str(path),))
        traceback.print_exc()
        return None


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
            found.append((path, stripComments(_decoded(raw))))
        except Exception:  # noqa: BLE001 - 一个文件读不了不耽误别的
            print("[arrisFarmersDelight] 读行为包里的 %s 出错，跳过" % (_str(path),))
            traceback.print_exc()
    return found
