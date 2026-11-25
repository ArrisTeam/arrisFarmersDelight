# -*- coding: utf-8 -*-
"""SettingsClientLink - 联动步骤 settings（客户端）：四个站点的玩家开关登进前置包的设置界面，砧板那一项告诉服务端

前置包的设置界面（站点上的齿轮）和网易"通用设置"页里登一组玩家自己的开关（Api.Client.registerSettings，能力旗 SETTINGS：老的前置包没有，
步骤表的条件挡掉、这一步 skipped、什么都不登）：总开关 + 这一端登记成功的站点各一项（前面几步的状态 ctx.done；项和名字在
Shared/Rules/StationSwitches），每项管着那个站点登记用的站点 id（各站点的 View 登记时用的同一个常量）。关了的站点内核替我们拦：
右键不开站、不取消，方块照农夫乐事原样用（厨锅就是经典界面）。一个站点都没登上就不登这一组，记 skipped。
砧板要服务端也知道（Compat/Diegesis/BoardSwitch）："砧板站点对我开不开" = 总开关 and 砧板那一项（Api.Client 只给 settingValue，自己与）。
登记时内核不调 onChange（前置包 Client/SettingsKeep._changed 只在玩家改一项、恢复默认时调），所以登记完自己算一遍、发一次；
设置存在本机、进哪个存档都是同一份，所以每次进世界联动完都发；本地玩家进了世界（OnLocalPlayerStopLoading）再发一次同样的值，
免得联动那一刻发的丢了（服务端只记最新的，多发一次没有坏处；联动时发的会不会丢没在游戏里量过）。
算出来的值记在这里，TableClientLink 判"配方书里藏不藏"时现读：玩家拨开关的那一下，"不藏了"和发给服务端的上报是同一次算出来的。
"""
from . import Steps
from ...QuModLibs.Client import Call, Listen
from ...Shared.Rules import BoardStation, GrillStation, PanStation, PotStation, StationSwitches as Rules

REPORT = "BoardSwitchReport"           # 服务端的端点（Compat/Diegesis/BoardSwitch.py）
# 开关的键 -> (步骤名, 那个站点登记用的站点 id：各站点 View 里 api.registerBehavior(Rules.STATION_ID, ...) 的同一个常量)
STATIONS = {
    "cooking_pot": ("pot", PotStation.STATION_ID),
    Rules.BOARD: ("board", BoardStation.STATION_ID),
    "skillet": ("pan", PanStation.STATION_ID),
    "stove": ("grill", GrillStation.STATION_ID),
}
_state = {"api": None, "board": False, "on": True}


def registered(done):
    """这一端登记成功的站点：{开关的键: 站点 id}（done 是前面几步的状态）。"""
    return dict((key, stationId) for key, (step, stationId) in STATIONS.items() if done.get(step) == Steps.OK)


def boardOnForMe():
    """砧板站点对这个玩家开不开（缺省开着：这一步没跑、前置包没有设置、砧板没登上都是开着）。"""
    return _state["on"]


def _sync():
    """现读总开关和砧板那一项，记下、报给服务端。"""
    api = _state["api"]
    _state["on"] = Rules.boardOn(api.settingValue(Rules.GROUP, Rules.MASTER), api.settingValue(Rules.GROUP, Rules.BOARD))
    Call(REPORT, {"on": _state["on"]})


def onChange(key, value):
    """内核：玩家改了这一组的一项（或恢复默认，逐项调）。总开关、砧板那一项变了要重算重发。"""
    if _state["board"] and key in Rules.BOARD_KEYS:
        _sync()


@Listen("OnLocalPlayerStopLoading")
def OnLocalPlayerStopLoading(args=None):
    if _state["board"]:
        Call(REPORT, {"on": _state["on"]})


def link(ctx):
    _state["api"], _state["board"], _state["on"] = None, False, True
    stations = registered(ctx.done)
    items = Rules.playerSwitches(stations)
    if not items:
        return False
    ctx.api.registerSettings(Rules.GROUP, dict(Rules.GROUP_TITLE), items, onChange=onChange)
    _state["api"], _state["board"] = ctx.api, Rules.BOARD in stations
    if _state["board"]:
        _sync()
    return True
