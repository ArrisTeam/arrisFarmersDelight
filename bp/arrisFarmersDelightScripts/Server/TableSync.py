# -*- coding: utf-8 -*-
"""TableSync - 下游在服务端追加的数据表发给客户端：玩家进服发一次，之后表又变了补发（服务端）

联动契约（Api/LegacyModAttr.py）把配置表按引用交给下游，它们在服务端的 LoadServerAddonScriptsAfter 里往里追加配方、刀、可烹饪物、炉灶；
客户端有自己的一份表，四个站点的客户端表现读的是那一份（托盘里哪些亮、借哪把刀、食谱书、哪些方块开炉灶站点……），所以要发过去。
怎么算差异、怎么编码、怎么并表见 Shared/Rules/TableDiff.py、TableWire.py、TableMerge.py，哪些表见 SyncTables.py；这里只管什么时候发：
- 本模块导入时记基线（那时下游还没追加）；
- 玩家进服（ClientLoadAddonsFinishServerEvent：客户端刚加载完 Addon，端点已经登记好；dolorContainer 也在这时告诉客户端绑定的方块名）发一次累计的差异——必须在他能开任何站点之前，
  而且"这一下右键开不开站点"是客户端自己先判的（StoveList 里没有的方块客户端不会去请求开站），所以不能等开站时再发；
- 之后每 POLL 秒看一眼表变没变（下游可以随时往表里追加，也可以不经联动接口直接改 obtain 拿到的对象，没有事件可听；
  一次检查是几张表在 C 层比一下，不到一毫秒），变了就把新的一版补发给已经收过的所有人。
- 进服那一份发出去就不知道收没收到（客户端的端点还没登记好时整份丢掉，世界外观广播实机就丢过）：之后的头 RESENDS 轮检查各再整份发一次，
  客户端并表是幂等的，重复的那几份什么都不改；
- 给一个人发的时候出了错（Call 抛异常）只记日志、下一轮再给他发，不耽误后面的人。
没有任何下游追加内容时什么都不发。发的是 Call，端点是客户端的 OnTableSync（Client/TableSync.py）。
"""
import traceback

from .EventRegistry import registerHandler
from .Helpers.Engine import Call, compFactory, levelId, serverApi
from ..Shared.Rules import SyncTables, TableDiff

POLL = 5.0
RESENDS = 2                      # 进服那一份之后再整份发几次（每轮检查一次：进服后约 5 秒、10 秒）
syncer = TableDiff.Syncer()      # 导入时的表就是基线
_known = {}                      # 进过服的玩家 id -> 发给他的版本（rev）；没进服的玩家客户端还没准备好，不能发
_again = {}                      # 玩家 id -> 还要再整份发几次（进服那一份可能丢了）
_reported = []                   # 已经写进日志的问题（同一批问题每次重算都打一遍会刷屏）
_timer = []


def _push(playerId, since):
    """发给他：版本比 since（他已经收过的版本，新进服是 0）新的那几张表的累计差异。发到一半出错：记日志、不记成发过（下一轮再发，
    已经到了的那几条重复并一次不改任何东西），返回 False；不往外抛——后面还有别的人要发。"""
    try:
        for message in syncer.messages(since):
            Call(playerId, SyncTables.ENDPOINT, message)
    except Exception:  # noqa: BLE001 - 发给一个人出错不能耽误别人
        print("[arrisFarmersDelight] 表同步：发给 %s 出错，下一轮再发" % (playerId,))
        traceback.print_exc()
        return False
    _known[playerId] = syncer.rev
    return True


def _refresh():
    """重算差异（表没变就是空操作），传不了而被跳过的条目写进日志——只写还没写过的（下游往表里追加了一条坏的、别的什么也没追加时也要写）。"""
    syncer.refresh()
    for problem in syncer.problems:
        if problem not in _reported:
            print("[arrisFarmersDelight] 表同步：%s" % problem)
    _reported[:] = list(syncer.problems)


def step(everyone=False):
    """看一眼表变没变，变了给收过的人补发新的一版；走掉的人忘掉。定时器每 POLL 秒调一次，调试时也可以直接调。
    everyone：也发给在线却没进过服的人（热重载脚本之后 _known 是空的，他们不会再收到进服事件；平时没进服的人客户端可能还没加载完，不发）。"""
    _refresh()
    online = set(serverApi.GetPlayerList())
    for playerId in list(_known):
        if playerId not in online:
            del _known[playerId]
            _again.pop(playerId, None)
        elif _again.get(playerId):
            _again[playerId] -= 1
            _push(playerId, 0)                # 进服那一份可能丢了：整份再发一次
        elif _known[playerId] != syncer.rev:
            _push(playerId, _known[playerId])
    if everyone:
        for playerId in sorted(online - set(_known)):
            _known[playerId] = 0              # 没发成的也记着，下一轮接着补
            _push(playerId, 0)


def _poll():
    try:
        step()
    except Exception:  # noqa: BLE001 - 定时器边界：出错只打印，下一轮接着来
        print("[arrisFarmersDelight] 表同步出错")
        traceback.print_exc()


def _ensureTimer():
    if not _timer:
        _timer.append(compFactory.CreateGame(levelId).AddRepeatedTimer(POLL, _poll))


@registerHandler("ClientLoadAddonsFinishServerEvent")
def OnTableSyncPlayerJoin(args):
    _ensureTimer()
    _refresh()
    playerId = args["playerId"]
    _known[playerId], _again[playerId] = 0, RESENDS      # 先记着：这一下没发成，下一轮也会补
    _push(playerId, 0)
