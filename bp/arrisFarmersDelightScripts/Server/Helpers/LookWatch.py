# -*- coding: utf-8 -*-
"""LookWatch - 世界外观广播的收件人：谁在这口锅 / 这座灶 32 格内、谁是刚走进来的（服务端）

PanLook / StoveLook 把"锅里、灶上现在是什么样"发给附近的人，各自的客户端照它演。JE 的状态在方块实体的更新包里，走近时一定是对的；
这边靠广播，只发给"发的那一刻在范围里的人"，走进范围的人要等下一次变化才对得上——而等翻面、煎好留在锅里、空锅、烤好等着取这几种
状态不会再变，永远补不上。所以每口锅 / 灶记一份"已经收到当前样子的人"（Audience）：每一步对一遍，新走进来的单发一份当前的样子，
走出去的从名单里划掉（回来时再补一份）。
谁在哪是引擎的调用（每个玩家两次），每口锅每一步都问太贵：带时钟问的在 SNAPSHOT_SECONDS 内共用上一份快照。
"""
from .Engine import compFactory, serverApi

RANGE = 32.0               # 与前置包的 WATCH_RANGE 一致（两个包互不导入）
SNAPSHOT_SECONDS = 0.5     # 玩家位置的快照多久换一次
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
    """已经收到这口锅 / 灶当前样子的人。"""

    def __init__(self):
        self.known = set()

    def arrivals(self, near):
        """near 里这一步才新走进来的（还没收到当前样子）；名单顺手换成 near：走出去的划掉，回来时算新来的。"""
        fresh = [playerId for playerId in near if playerId not in self.known]
        self.known = set(near)
        return fresh

    def sent(self, near):
        """刚把当前样子发给了 near 里的所有人。"""
        self.known = set(near)
