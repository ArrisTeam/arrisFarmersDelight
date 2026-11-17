# -*- coding: utf-8 -*-
"""LookWatch - 世界外观广播的收件人：谁在这口锅 / 这座灶 32 格内、谁是刚走进来的（服务端）

PanLook / StoveLook 把"锅里、灶上现在是什么样"发给附近的人，各自的客户端照它演。JE 的状态在方块实体的更新包里，走近时一定是对的；
这边靠广播，只发给"发的那一刻在范围里的人"，走进范围的人要等下一次变化才对得上——而等翻面、煎好留在锅里、空锅、烤好等着取这几种
状态不会再变，永远补不上。所以每口锅 / 灶记一份"已经收到当前样子的人"（Audience）：每一步对一遍，新走进来的单发一份当前的样子，
走出去的从名单里划掉（回来时再补一份）。
广播发出去就不管有没有收到：客户端脚本还没就绪、区块还没加载好的时候整份丢掉，服务端却当他收到了（实机：进世界时灶上本来就有东西，
走到灶边客户端的场景一直不知道样子）。所以名单还记着每个人是什么时候收到的，隔 REFRESH_SECONDS 秒再单发一份当前的样子——
客户端收到同样的样子是幂等的（画面不变），丢了的下一轮就补上。
谁在哪是引擎的调用（每个玩家两次），每口锅每一步都问太贵：带时钟问的在 SNAPSHOT_SECONDS 内共用上一份快照。
"""
from .Engine import compFactory, serverApi

RANGE = 32.0               # 与前置包的 WATCH_RANGE 一致（两个包互不导入）
SNAPSHOT_SECONDS = 0.5     # 玩家位置的快照多久换一次
REFRESH_SECONDS = 5.0      # 样子没变时，隔多久把当前的样子再单发给附近的人一份（丢了的就这么补上）；一份几百字节，附近每人每 5 秒一份
_cache = {"at": None, "players": []}


def reset():
    """清掉快照（测试和重载用）。"""
    _cache["at"], _cache["players"] = None, []


def _take():
    found = []
    for playerId in serverApi.GetPlayerList():
        at = compFactory.CreatePos(playerId).GetFootPos()
        if at is not None:
            found.append((playerId, compFactory.CreateDimension(playerId).GetEntityDimensionId(), (at[0], at[1], at[2])))
    return found


def players(now=None):
    """[(玩家 id, 维度, 脚下坐标)]。给了 now（秒）就在 SNAPSHOT_SECONDS 内用上一份快照；不给就现取。"""
    if now is None:
        return _take()
    at = _cache["at"]
    if at is None or not 0.0 <= now - at < SNAPSHOT_SECONDS:      # 时钟倒着走（换了世界、测试）也重取
        _cache["at"], _cache["players"] = now, _take()
    return _cache["players"]


def nearby(dimensionId, blockPos, now=None):
    """同维度、离方块 RANGE 格内的玩家 id。"""
    cx, cy, cz = blockPos[0] + 0.5, blockPos[1] + 0.5, blockPos[2] + 0.5
    return [playerId for playerId, dimension, at in players(now)
            if dimension == dimensionId and (at[0] - cx) ** 2 + (at[1] - cy) ** 2 + (at[2] - cz) ** 2 <= RANGE * RANGE]


class Audience(object):
    """已经收到这口锅 / 灶当前样子的人，和他是什么时候收到的。refresh 给了（秒）：隔了这么久没发给他的人也要再发一份当前的样子。"""

    def __init__(self, refresh=None):
        self.refresh = refresh
        self.known = {}                # 玩家 id -> 上次发给他的时刻（调用方没给时钟时是 None）

    def _due(self, at, now):
        """上次发给他已经隔了 refresh 秒：要再发一份。没有 refresh 或没给时钟不再发；时钟倒着走（换了世界、测试）也再发。"""
        if self.refresh is None or now is None:
            return False
        return at is None or not 0.0 <= now - at < self.refresh

    def arrivals(self, near, now=None):
        """near 里这一步要单发一份当前样子的人：才新走进来的（还没收到），和隔了 refresh 秒的（可能丢了）。
        名单顺手换成 near：走出去的划掉，回来时算新来的。"""
        fresh = [playerId for playerId in near if playerId not in self.known or self._due(self.known[playerId], now)]
        self.known = dict((playerId, now if playerId in fresh else self.known[playerId]) for playerId in near)
        return fresh

    def sent(self, near, now=None):
        """刚把当前样子发给了 near 里的所有人。"""
        self.known = dict((playerId, now) for playerId in near)
