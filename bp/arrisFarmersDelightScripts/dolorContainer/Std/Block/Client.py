# -*- coding: utf-8 -*-
"""
标准库：方块宿主在客户端的那一半（docs/ARCHITECTURE.md 第 3.12 节）：对着绑定的方块使用时，手里的东西不用出去。

自定义方块对引擎来说不是能交互的方块：客户端对着它右键时，方块的使用没有被接住，引擎接着把手里的东西当作对空气使用
（扔雪球、打开手里的书），这一步在客户端就做了，服务端拦不住。所以服务端在玩家进游戏时把绑定的方块名与放过的规则发过来
（Std/Block/Server.py 的 tellClients：潜行并拿着东西时放不放过、拿着哪些东西放过），这里在客户端报"对着方块使用"之后、
同一下的"使用物品"时取消它；照同样的规则放过时不取消（那时用的就是手里的东西，不开界面）。只在收到过方块名之后才监听
这两个事件。
引擎在用到时才导入；离线测试换掉 ENGINE。
"""
import time

from ....QuModLibs.Client import AllowCall

SAME_USE = 0.1   # 同一下右键：对着方块使用之后这么多秒之内的"使用物品"

try:
    _TEXT = (str, unicode)  # noqa: F821
except NameError:
    _TEXT = (str,)

_EVENTS = object()   # 动态监听的名字空间（见 Std/Block/Server.py 的说明）
_bound = {}          # 服务端发来的绑定方块名 -> (潜行并拿着东西时放过, 拿着就放过的物品名)
_listening = [False]
_lastUse = [None]    # 最近一次对着绑定方块使用的时刻


def bind(rules):
    """
    记下绑定的方块名与放过的规则（服务端发来的 {方块名: [潜行时放过, [物品名]]}；只给名字的列表照缺省规则：潜行并拿着
    东西时放过），有了就开始监听。
    """
    _bound.clear()
    entries = rules.items() if isinstance(rules, dict) else ((name, None) for name in rules or ())
    for name, rule in entries:
        if not isinstance(name, _TEXT):
            continue
        sneak, items = True, ()
        if isinstance(rule, (list, tuple)) and len(rule) == 2 and isinstance(rule[1], (list, tuple)):
            sneak, items = bool(rule[0]), rule[1]
        _bound[str(name)] = (sneak, frozenset(str(item) for item in items if isinstance(item, _TEXT)))
    if _bound and not _listening[0]:
        _listening[0] = True
        ENGINE.listen(onBlockUse, onItemTryUse)


@AllowCall
def dolorContainerBlocks(names):
    bind(names)


def onBlockUse(args):
    """对着方块使用（按住时引擎一直报）：是绑定的方块、没有放过时，记下这一下。"""
    rule = _bound.get(args.get("blockName"))
    if rule is None:
        return
    held = ENGINE.heldName()
    if held is not None and ((rule[0] and ENGINE.sneaking()) or held in rule[1]):
        return
    _lastUse[0] = ENGINE.now()


def onItemTryUse(args):
    """使用物品：紧跟在对着绑定方块使用之后的（同一下右键）取消掉。"""
    last = _lastUse[0]
    if last is not None and 0 <= ENGINE.now() - last <= SAME_USE:
        args["cancel"] = True


class _Engine(object):
    """真实引擎（用到时才导入）。"""

    @staticmethod
    def listen(blockUse, itemTryUse):
        from ....QuModLibs.Client import ListenForEvent
        ListenForEvent("ClientBlockUseEvent", _EVENTS, blockUse)
        ListenForEvent("ClientItemTryUseEvent", _EVENTS, itemTryUse)

    @staticmethod
    def _player():
        import mod.client.extraClientApi as clientApi
        return clientApi, clientApi.GetLocalPlayerId()

    def sneaking(self):
        api, playerId = self._player()
        return bool(api.GetEngineCompFactory().CreatePlayer(playerId).isSneaking())

    def heldName(self):
        """手里的东西的物品名；空手时为 None。"""
        api, playerId = self._player()
        item = api.GetEngineCompFactory().CreateItem(playerId).GetCarriedItem()
        if not item or item.get("newItemName") in (None, "", "minecraft:air") or not item.get("count"):
            return None
        return item.get("newItemName")

    @staticmethod
    def now():
        return time.time()


ENGINE = _Engine()
