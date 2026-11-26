# -*- coding: utf-8 -*-
"""AdvBoot - 成就系统（arrisAdvancements，脚本名 dolorAdvancements）的联动入口（服务端）

照它 README 的"方法一"：在本包的加载器系统上听 ("dolorAdvancements", "ExtensionApi", "ServerApiReady")，事件里的 api 就是它的
dolorAdvancementsScripts.Api.Server 模块。它在所有模组加载完以后才广播，这里在导入时（引擎加载期）就挂上监听，两边谁先加载都收得到。
它的 ExtensionApi 系统已经在（热重载以后再导入这里，或者它比本包先加载完）：事件不会再来，直接 ImportModule 它的接口晚接一次（照 Compat/Create/PotatoCannonAmmo）。
这一下是在本模块导入时：经 Compat/OtherMods 取，它的接口导入出错只打日志、当没接上，异常不漏出本模块的导入（本模块是 modMain 登记的入口）。
没装成就系统：事件不来、系统不在，这里只挂了一个空监听、问了一次引擎，什么都不做。接上以后做什么见 AdvBridge。
监听挂在本包的加载器系统上，不挂在 Server/ExtensionSystem：那个系统只用来广播本包自己的 ready（要广播时才建、不挂监听）。
"""
import traceback

from ...QuModLibs.Server import ListenForEvent
from ...QuModLibs.Systems.Loader.Server import LoaderSystem
from ...Server.Helpers.Engine import compFactory, levelId, serverApi, ItemPosType, GetEngineTypeStr
from .. import OtherMods
from . import AdvBridge

NAMESPACE, SYSTEM_NAME, READY_EVENT = "dolorAdvancements", "ExtensionApi", "ServerApiReady"
API_MODULE = "dolorAdvancementsScripts.Api.Server"
READY_METHOD = "arrisFarmersDelightAdvancementsReady"     # 挂在本包加载器系统上的监听方法名（同一个系统上只挂一次）


class Env(object):
    """AdvBridge 要碰引擎的那几样。"""

    @staticmethod
    def typeOf(entityId):
        return GetEngineTypeStr(entityId) if entityId else None

    @staticmethod
    def blockAt(pos, dimensionId):
        info = compFactory.CreateBlockInfo(levelId).GetBlockNew(pos, dimensionId)
        return info.get("name") if info else None

    @staticmethod
    def itemsOf(playerId):
        itemComp = compFactory.CreateItem(playerId)
        names = []
        for posType in (ItemPosType.INVENTORY, ItemPosType.OFFHAND, ItemPosType.ARMOR):
            names.extend(item.get("newItemName") for item in itemComp.GetPlayerAllItems(posType) or () if item)
        return names

    @staticmethod
    def listen(eventName, func):
        ListenForEvent(eventName, None, func)


def _attach(module):
    """接上；成就系统那边出了错只打日志：引擎派发它的事件、导入本模块都不该被它带崩。"""
    try:
        AdvBridge.attach(module, Env)
    except Exception:  # noqa: BLE001 - 别的模组的接口出错，不连累农夫乐事
        print("[arrisFarmersDelight] 接成就系统时出错，不接")
        traceback.print_exc()


def hook(system):
    """在本包的加载器系统上听成就系统的 ready；它已经广播过（它的系统在）就当场晚接。"""
    if getattr(system, READY_METHOD, None) is None:
        def onReady(args):
            _attach((args or {}).get("api"))
        onReady.__name__ = READY_METHOD
        setattr(system, READY_METHOD, onReady)
        system.ListenForEvent(NAMESPACE, SYSTEM_NAME, READY_EVENT, system, onReady)
    if AdvBridge.api() is None and serverApi.GetSystem(NAMESPACE, SYSTEM_NAME):
        _attach(OtherMods.find(serverApi.ImportModule, API_MODULE))


hook(LoaderSystem.getSystem())
