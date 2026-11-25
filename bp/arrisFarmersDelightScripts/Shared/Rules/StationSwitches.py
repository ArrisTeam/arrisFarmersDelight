# -*- coding: utf-8 -*-
"""StationSwitches - 四个站点的玩家开关：登进前置包设置界面的那一组、砧板站点对这个玩家开不开、服务端按玩家记的那一份（双端，纯规则）

前置包（沉浸式交互前置）的设置界面和网易"通用设置"页里，每个使用方可以登一组玩家自己的开关（Api.Client.registerSettings，能力旗 SETTINGS，
docs/diegesis/CINEMA.md §8.4 在前置包工程里）。农夫乐事这一组（组 id GROUP）：总开关一项 + 这一端登记成功的站点各一项，项管着那个站点的
站点 id（stations）；关了（或总开关关了）内核在右键时说不开站，方块照农夫乐事原样用。开关存在玩家自己的客户端，服务端不知道。
只有砧板要服务端也知道：联动着、remove_crafting_recipes 开着时，砧板菜在工作台上被否决（Compat/Diegesis/DishCrafts、TableHooksLink），
配方书里也藏掉（TableClientLink）；关了砧板的玩家开不了砧板站点，这些菜就没处做了。JE 的派生规则是"没有砧板站点就不拿掉合成"
（HandsOnConfig.java:222-225，HandsOnOptions.removeCraftingRecipes），这里按玩家延伸：客户端算出 boardOn、自己不藏、告诉服务端，
服务端按玩家记在 Choices 里、不否决。没报过的玩家当开着（现在的行为）。
"""
GROUP = "farmersdelight"                                              # 设置里这一组的 id（Api.Client.registerSettings）
GROUP_TITLE = {"key": "arris_fd.settings.group", "text": "农夫乐事"}  # 页签上的组名（最多四个字）
MASTER = "enabled"                                                    # 总开关的键（和前置包原版工作站、森罗物语那两组一样）
MASTER_LABEL = {"key": "arris_fd.settings.all", "text": "全部厨具"}
BOARD = "cutting_board"
# 每个站点一项：(键, 名字)，界面上的顺序。键和 HoD 配置（Shared/Data/HandsOnConfig）里这个站点的开关同名
SWITCHES = (
    ("cooking_pot", {"key": "arris_fd.settings.cooking_pot", "text": "厨锅"}),
    (BOARD, {"key": "arris_fd.settings.cutting_board", "text": "砧板"}),
    ("skillet", {"key": "arris_fd.settings.skillet", "text": "煎锅"}),
    ("stove", {"key": "arris_fd.settings.stove", "text": "炉灶"}),
)
BOARD_KEYS = (MASTER, BOARD)                                          # 这两项变了，"砧板站点对我开不开"就可能变了


def playerSwitches(stations):
    """登记给内核的项：stations 是 {键: 站点 id}（这一端登记成功的站点）。总开关一项，加上登记成功的每个站点一项（SWITCHES 的顺序，
    管着它的站点 id）；一个站点都没登上是 []（这一组不登）。"""
    items = [{"key": key, "label": dict(label), "stations": (stations[key],)} for key, label in SWITCHES if key in stations]
    if not items:
        return []
    return [{"key": MASTER, "label": dict(MASTER_LABEL), "master": True}] + items


def boardOn(master, board):
    """砧板站点对这个玩家开不开：总开关和砧板那一项都没关。读出 None（这一项没登记）算开着。"""
    return master is not False and board is not False


class Choices(object):
    """服务端：每个玩家报来的"砧板站点对我开不开"。只记关着的；没报过、报了开、下线清掉的都当开着（否决照旧）。"""

    def __init__(self):
        self._off = set()

    def put(self, playerId, on):
        """玩家报来的值（只当布尔用）。"""
        if on:
            self._off.discard(playerId)
        else:
            self._off.add(playerId)

    def boardOn(self, playerId):
        return playerId not in self._off

    def drop(self, playerId):
        """玩家下线：忘掉。"""
        self._off.discard(playerId)

    def players(self):
        """关着砧板站点的玩家（测试、游戏里看用）。"""
        return sorted(self._off)
