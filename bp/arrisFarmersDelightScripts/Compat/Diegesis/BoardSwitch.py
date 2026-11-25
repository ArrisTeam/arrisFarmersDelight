# -*- coding: utf-8 -*-
"""BoardSwitch - 每个玩家报来的"砧板站点对我开不开"：关着的玩家工作台照旧出砧板菜（服务端）

砧板的玩家开关只在客户端（前置包的设置，Compat/Diegesis/SettingsClientLink）：关了的玩家开不了砧板站点。联动着、remove_crafting_recipes
开着时工作台对所有人否决砧板菜（DishCrafts.onCraft、前置包原版工作台上的 TableHooksLink.dishVeto），他就没处做了——所以客户端把这个开关
报上来（端点 BoardSwitchReport：玩家 id 只信框架注入的，值只当布尔用），这两处否决先问 boardOn。缺省是开着：刚进服、客户端那一下还没到，
或者前置包太旧没有设置（客户端那一步 skipped、什么都不报）时，否决照旧。按玩家记（Shared/Rules/StationSwitches.Choices），下线清掉。
只在联动时有：本模块只由站点的步骤模块导入（DishCrafts、TableHooksLink），board 那一步登否决时调 enable 才开始收、才挂下线的处理。
"""
from ...QuModLibs.Server import AllowCall, InjectHttpPlayerId
from ...Server.EventRegistry import registerHandler
from ...Shared.Rules import StationSwitches as Rules

choices = Rules.Choices()
_state = {"on": False}


def enable():
    """board 那一步登工作台否决时调：开始收玩家报来的值，玩家下线清掉（同一个处理函数登记按模块 + 函数名去重，调几次都一样）。"""
    _state["on"] = True
    registerHandler("DelServerPlayerEvent")(onPlayerLeft)


def boardOn(playerId):
    """这个玩家的砧板站点开着（没报过算开着）：两处否决先问它。"""
    return choices.boardOn(playerId)


@AllowCall
@InjectHttpPlayerId
def BoardSwitchReport(playerId, data):
    """客户端报来的 {"on": 布尔}：进世界联动完报一次，之后总开关或砧板那一项改了再报。没登否决时不收。"""
    if not _state["on"] or not playerId or not isinstance(data, dict) or "on" not in data:
        return
    choices.put(playerId, bool(data["on"]))


def onPlayerLeft(args):
    choices.drop(args.get("id"))
