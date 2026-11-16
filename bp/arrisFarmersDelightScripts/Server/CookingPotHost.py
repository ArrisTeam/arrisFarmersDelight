# -*- coding: utf-8 -*-
"""CookingPotHost - 厨锅接入 dolorContainer：容器类型、方块宿主、界面数据的读数（服务端）

厨锅的 8 个格子仍是 netease:block_container 的引擎容器格（界面模型里的 ENGINE_CONTAINER 直接读写它），烹饪与热源由
Server/CookingPot.py 照旧推进；本模块让库的方块宿主接管对厨锅的右键：打开库的界面（Shared/Menus/CookingPot.py），
并把方块实体数据里的热源、烹饪计时、预览格读成界面数据。

宿主登记时由库在运行期让引擎报厨锅的移除（ListenOnBlockRemoveEvent），所以方块 JSON 里不再写 netease:listen_block_remove
（两处同时开会让方块和物品图标都不画）；OnCookingPotRemove 照常经 BlockRemoveServerEvent 收到事件。
"""
from ..dolorContainer.Server import Api
from ..dolorContainer.Std.Block import Server as Block
from ..Shared.Menus import CookingPot as PotMenu
from .CookingPot import COOKING_POT, COOK_SECONDS
from .Helpers.Engine import GetBlockEntityData

CONTAINER_TYPE = "arris:cooking_pot"
# 界面开关：True 时右键厨锅开库的界面；False 时放行给引擎，开方块 JSON 里 netease:block_container 的 screen_name 旧界面
# （旧界面代理与 rp/ui/arrisCookingPot.json 还在，供实机验证不过时退回）
DOLOR_SCREEN = True


class CookingPotHost(Block.Host):
    """厨锅的方块宿主：右键开界面（缺省的潜行拿着东西放过、按住不重复开都照库的）；DOLOR_SCREEN 关掉时全部放行。"""

    def use(self, playerId, typeId, key, event=None):
        return Block.OPEN if DOLOR_SCREEN else Block.PASS


def readState(key):
    """
    界面数据：厨锅方块实体数据里的热源、烹饪进度（计时从 COOK_SECONDS 倒数，没在烹饪时是满值，进度为 0）、预览格里
    煮好还没装进容器的成品。厨锅 /setblock 出来、区块没加载时读不到数据，什么都不给。
    """
    place = Block.parseKey(key)
    data = GetBlockEntityData(place[0], place[1]) if place is not None else None
    if not data:
        return {}
    heated = bool(data["heatEnable"])
    timer = data["timer"]
    progress = 0.0
    if heated and isinstance(timer, (int, float)):
        progress = max(0.0, min(1.0, 1.0 - float(timer) / COOK_SECONDS))
    stack = (data["previewItemSlot"] or [None])[0]
    preview = None
    if stack and stack.get("newItemName"):
        # 引擎对象里读出的堆换成普通字典再交给界面（与 Server/CookingPot.py 读预览格用的是同样的取法）
        preview = {"newItemName": stack.get("newItemName"), "newAuxValue": stack.get("newAuxValue", 0),
                   "count": stack.get("count", 0)}
    return {"heated": heated, "progress": progress, "preview": preview}


PotMenu.setStateReader(readState)
Api.registerContainerType(Api.ContainerType(CONTAINER_TYPE, "tile.arris:cooking_pot.name", PotMenu.MENU,
                                            host=CookingPotHost((COOKING_POT,))))
