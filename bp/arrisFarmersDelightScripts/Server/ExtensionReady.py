# -*- coding: utf-8 -*-
"""ExtensionReady - 全部 Addon 脚本加载完时发新联动接口的服务端 ready 事件，再读行为包里的配方 JSON（服务端）

ModServer 把 LoadServerAddonScriptsAfter 转给这里（EventRegistry）。每端一次、出错不连累的做法在 Api/ExtensionApi/Ready.py；
广播用的系统在 ExtensionSystem.py：它要引擎的系统基类，到要广播时才导入（离线测试换掉 _system，不用假引擎）。
顺序：交进去"现在就同步"的服务（ext.recipes.syncToClients 用）→ 广播 ready（别的模组在处理函数里登记）→ 读全部行为包里的
farmersdelight_recipes/**.json（Api/ExtensionApi/RecipeFiles.py；跨包读文件的是 Helpers/PackJson.py，离线测试换掉 _files）
→ 调一次 onRecipesChanged 的处理函数（types、recipeIds 都是 None：开服这一轮谁都可能改了什么）。
别的模组在 ready 里往农夫乐事的表里登记的东西，玩家进服时由表同步发给他的客户端（Server/TableSync.py 的基线是模块导入时的表，早于 ready）。
"""
from .EventRegistry import registerHandler
from .Helpers import PackJson
from ..Api.ExtensionApi import Ready, RecipeFiles, Recipes
from ..Api.ExtensionApi.Facade import getExtensionApi
from ..Shared.Rules.RecipeJson import text

_files = PackJson.files
_scan = {"state": None, "files": 0, "loaded": [], "problems": []}     # 最近一次读行为包配方 JSON 的结果（游戏内自检读 scanReport()）


def _system():
    from .ExtensionSystem import getSystem
    return getSystem()


def _syncNow():
    """ext.recipes.syncToClients：现在就把表的改动发给在线的玩家（表同步本来每 5 秒看一次，见 TableSync.py）。"""
    from . import TableSync
    TableSync.step()


def _loadRecipeFiles():
    found = _files(RecipeFiles.DIRECTORY)
    if found is None:
        _scan.update(state="unavailable", files=0, loaded=[], problems=[])
        print("[arrisFarmersDelight] 新联动接口：读不了行为包里的 %s/（引擎没有 server_resource 这条路），不读" % RecipeFiles.DIRECTORY)
        return
    loaded, problems = RecipeFiles.load(found, getExtensionApi("server").recipes.registerFromJson)
    for path, reason in problems:
        print("[arrisFarmersDelight] 行为包里的配方 %s 没有登记：%s" % (text(path), reason))
    _scan.update(state="read", files=len(found), loaded=loaded, problems=problems)


def scanReport():
    """最近一次读行为包配方 JSON 的结果：state（None 还没读、"unavailable" 引擎没有这条路、"read" 读过）、files、loaded、problems。"""
    return dict(_scan)


@registerHandler("LoadServerAddonScriptsAfter")
def OnServerExtensionApiReady(args=None):
    Recipes.provide(syncNow=_syncNow)
    if Ready.publish("server", _system) is None:
        return                               # 这一端已经播过（不会再读一遍文件）
    _loadRecipeFiles()
    Recipes.notify()
