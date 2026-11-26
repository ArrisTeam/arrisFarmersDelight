# -*- coding: utf-8 -*-
"""Presence - 沉浸式交互前置的联动：找前置包的接口，够新就按步骤表联动，定本端的运行模式（双端，不碰引擎）

做法和机械动力系列的附属包一样（无中生有的 CreateSDK.Presence）：运行模式每端判定一次、记在 Shared/Rules/HandsOnMode，别处都问那一个地方；
联动的注册写成步骤表（ServerSteps / ClientSteps，执行见 Steps），业务模块在自己的步骤里才导入；一步失败不拦别的步骤。
不一样的是怎么发现前置包：不要联动 SDK 的 ready 事件，照旧用 ImportModule("arrisDiegesisScripts.Api.Server" / ".Api.Client") 取它的接口模块、
读 API_VERSION，可选功能读接口上的功能旗（FACING_HOOK……），写成步骤的条件。
    - 接口在、API_VERSION 够（REQUIRED_API_VERSION）：模式先拨到 LINKED（站点自己的 register 问 HandsOnOptions，没联动时它说 HoD 不在），再跑步骤表；
    - 接口在、API_VERSION 比它低：OUTDATED，一步不跑（客户端提醒玩家更新，见 ClientBoot）；
    - 找不到：服务端导入时找一次（前置包的服务端 Api 是纯 Python，比它的系统先导入也安全），两端都在"全部 Addon 脚本加载完成"
      （LoadServerAddonScriptsAfter / LoadClientAddonScriptsAfter）里找最后一次，还没有就是 STANDALONE，什么也不联动、不提醒。
      客户端不在导入时找：它的接口模块会带进前置包自己的 QuModLibs。
判定只做一次，步骤也只跑一次。引擎的东西都由入口模块（ServerBoot / ClientBoot）交进来，这里不碰引擎，离线可测。
前置包装着、它的接口却导入出错（装坏了、版本混了）：经 Compat/OtherMods 接住、打一次日志，当它没装。
"""
from . import Steps
from .. import OtherMods
from ...Shared.Rules import HandsOnMode

REQUIRED_API_VERSION = 3        # 本包要前置包的 API 至少是它：前置包没有发过更低的版本，所以没有按版本分档的登记
API_MODULE = {"server": "arrisDiegesisScripts.Api.Server", "client": "arrisDiegesisScripts.Api.Client"}
LOADED_EVENT = {"server": "LoadServerAddonScriptsAfter", "client": "LoadClientAddonScriptsAfter"}


class _Side(object):
    """一端的联动状态。"""

    def __init__(self, side, steps, find, load):
        self.side = side
        self.steps = steps              # 这一端的步骤表
        self.find = find                # find(模块路径) -> 模块，没有是 None：引擎的 ImportModule
        self.load = load                # load(模块路径) -> 模块，导不到抛异常：QuModLibs 的 ImportModule，步骤用它导入本包自己的模块
        self.settled = False            # 判定过了（联动 / 太旧 / 没装）：之后的机会不再看
        self.apiVersion = None
        self.results = []               # Steps.run 的结果：[(步骤名, 状态, 说明)]


_sides = {}


def attach(side, steps, listen, find, load):
    """入口模块在导入时调用一次（ServerBoot / ClientBoot）。listen 是这一端 QuModLibs 的 Listen（装饰器工厂），find / load 见 _Side。"""
    state = _sides[side] = _Side(side, steps, find, load)
    listen(LOADED_EVENT[side])(_ON_LOADED[side])
    if side == "server":
        _look(state, False)


def onServerLoaded(args=None):
    _look(_sides["server"], True)


def onClientLoaded(args=None):
    _look(_sides["client"], True)


_ON_LOADED = {"server": onServerLoaded, "client": onClientLoaded}


def _find(state):
    return OtherMods.find(state.find, API_MODULE[state.side])


def _look(state, last):
    """看一眼前置包在不在；last 为真是最后一次机会（全部 Addon 脚本都加载完了）。"""
    if state.settled:
        return
    api = _find(state)
    if api is None:
        if last:
            _settle(state, HandsOnMode.STANDALONE, None)
        return
    state.apiVersion = getattr(api, "API_VERSION", 0)
    _settle(state, HandsOnMode.LINKED if state.apiVersion >= REQUIRED_API_VERSION else HandsOnMode.OUTDATED, api)


def _settle(state, value, api):
    state.settled = True
    HandsOnMode.decide(state.side, value)           # LINKED 先于步骤：站点自己的 register 问 HandsOnOptions，没联动时它说 HoD 不在
    if value == HandsOnMode.LINKED:
        state.results = Steps.run(state.side, state.steps, api, state.load)
    print("[arrisFarmersDelight] 联动（%s 端）：%s%s%s" % (
        state.side, value, "，前置包接口 %s" % state.apiVersion if state.apiVersion is not None else "",
        "".join("，%s=%s" % (name, status) for name, status, _ in state.results)))


def report(side):
    """游戏里看联动到了哪一步（execute_code 里调）：本端的模式、这个进程联动了没有、前置包的接口版本、每一步 [步骤名, 状态, 说明]。"""
    state = _sides.get(side)
    return {"mode": HandsOnMode.mode(side), "linked": HandsOnMode.linked(),
            "apiVersion": state.apiVersion if state else None, "steps": [list(result) for result in state.results] if state else []}
