# -*- coding: utf-8 -*-
"""CookingPotHost - 厨锅接入 dolorContainer：容器类型、方块宿主、界面数据的读数（服务端）

厨锅的 8 个格子仍是 netease:block_container 的引擎容器格（界面模型里的 ENGINE_CONTAINER 直接读写它），烹饪与热源由
Server/CookingPot.py 照旧推进；本模块让库的方块宿主接管对厨锅的右键：打开库的界面（Shared/Menus/CookingPot.py），
并把方块实体数据里的热源、烹饪计时、预览格读成界面数据。

照 FD 的 CookingPotBlock.use（java:68-90）：潜行空手右键是切吊把手 / 托盘（Server/PotSupport.py），不开界面、不盛菜；
潜行并拿着东西时原版根本不调方块的 use（手里的东西照常用出去、放下），库的缺省规则（sneakPasses）已经放过，到不了这里；
不潜行时右键盛菜：手里拿着这道菜的容器（只比物品名）、预览槽里有煮好的菜时，拿走一个容器、给一份菜（Server/PotServe.py，算做过一份、不给经验），否则开界面。
前置包在场、厨锅站点登记着时普通右键被客户端取消、到不了这里，站点开站那一下（Compat/Diegesis/PotLogic.py 的 onOpen）做同一件事；潜行时客户端不开站（前置包的
sneakFallback），所以和 JE + HoD 一样：装了前置，经典界面只剩 HoD 配置（Shared/Data/HandsOnConfig.py）里关了 cooking_pot 一条路，站点就不登记，
普通右键不再被取消，到这里开界面。
有人开着这口锅的经典界面时（宿主的 onViewers），锅里厨师放的料也按 FD 原样自己煮，不等勺子（HoD 的 isInMenu）。
宿主登记时由库在运行期让引擎报厨锅的移除（ListenOnBlockRemoveEvent），所以方块 JSON 里不再写 netease:listen_block_remove
（两处同时开会让方块和物品图标都不画）；OnCookingPotRemove 照常经 BlockRemoveServerEvent 收到事件。
"""
from ..dolorContainer.Server import Api
from ..dolorContainer.Std.Block import Server as Block
from ..Shared.Menus import CookingPot as PotMenu
from . import HandCooking, PotServe, PotSupport
from .CookingPot import COOKING_POT, COOK_SECONDS
from .Helpers.Engine import GetBlockEntityData

CONTAINER_TYPE = "arris:cooking_pot"
# 界面开关：True 时右键厨锅开库的界面；False 时放行给引擎，开方块 JSON 里 netease:block_container 的 screen_name 旧界面
# （旧界面代理与 rp/ui/arrisCookingPot.json 还在，供实机验证不过时退回）
DOLOR_SCREEN = True


class CookingPotHost(Block.Host):
    """厨锅的方块宿主：右键开界面（缺省的潜行拿着东西放过、按住不重复开都照库的）；DOLOR_SCREEN 关掉时全部放行。
    潜行空手右键是切吊把手（FD 的 CookingPotBlock.use），手里拿着锅里这道菜的容器、锅里有煮好的菜时右键是盛一份，都不开界面。"""

    def use(self, playerId, typeId, key, event=None):
        place = Block.parseKey(key)
        if place is not None:
            if PotSupport.sneaking(playerId):
                return Block.BLOCK if PotSupport.toggle(playerId, place[0], place[1]) else Block.PASS     # 副手拿着东西：JE 不调 use
            if PotServe.serveByHand(playerId, place[0], place[1]):
                return Block.BLOCK
        return Block.OPEN if DOLOR_SCREEN else Block.PASS

    def onViewers(self, key, viewers):
        """看着这口锅的经典界面的人变了（库在有人开、有人关、下线时告诉宿主）：锅的烹饪要知道，有人开着时厨师放的料不等勺子（HandCooking）。"""
        place = Block.parseKey(key)
        if place is not None:
            HandCooking.setMenuViewers(place[0], place[1], viewers)


def taken(playerId, key, stack):
    """经典界面里成品格被拿走了（PotMenu.onTaken）：算盛出，记做过几份（Server/PotServe.py）。"""
    place = Block.parseKey(key)
    if place is not None:
        PotServe.takenFromMenu(playerId, place[0], place[1], stack)


def readState(key):
    """界面数据：读厨锅的方块实体数据换成热源、进度、预览（换算见 PotMenu.stateFrom）；读不到（区块没加载）时什么都不给。"""
    place = Block.parseKey(key)
    data = GetBlockEntityData(place[0], place[1]) if place is not None else None
    return PotMenu.stateFrom(data, COOK_SECONDS) if data else {}


PotMenu.setStateReader(readState)
PotMenu.setTakenHandler(taken)
Api.registerContainerType(Api.ContainerType(CONTAINER_TYPE, "tile.arris:cooking_pot.name", PotMenu.MENU,
                                            host=CookingPotHost((COOKING_POT,))))
