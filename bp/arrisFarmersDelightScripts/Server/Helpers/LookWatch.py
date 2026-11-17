# -*- coding: utf-8 -*-
"""LookWatch - 世界外观广播的收件人：谁在这口锅 / 这座灶 32 格内、谁是刚走进来的（服务端）

PanLook / StoveLook 把"锅里、灶上现在是什么样"发给附近的人，各自的客户端照它演。JE 的状态在方块实体的更新包里，走近时一定是对的；
这边靠广播，只发给"发的那一刻在范围里的人"，走进范围的人要等下一次变化才对得上——而等翻面、煎好留在锅里、空锅、烤好等着取这几种
状态不会再变，永远补不上。所以每口锅 / 灶记一份"已经收到当前样子的人"（Audience）：每一步对一遍，新走进来的单发一份当前的样子，
走出去的从名单里划掉（回来时再补一份）。
广播发出去就不管有没有收到：客户端脚本还没就绪、区块还没加载好的时候整份丢掉，服务端却当他收到了（实机：进世界时灶上本来就有东西，
走到灶边客户端的场景一直不知道样子）。所以名单还记着每个人是什么时候收到的，隔 REFRESH_SECONDS 秒再单发一份当前的样子——
客户端收到同样的样子是幂等的（画面不变），丢了的下一轮就补上。给了 most 的名单每补一次把间隔加倍、到 most 为止：丢是进世界那一阵的事，
几秒内补上就行，站久了的人不用一直每几秒收一份（样子变了、人走出去再回来，间隔从头算）。
谁在哪是引擎的调用（每个玩家两次），每口锅每一步都问太贵：带时钟问的在 SNAPSHOT_SECONDS 内共用上一份快照。
被拒的敲击声（refused）按玩家限速（mayHearRefusal）：砧板 / 煎锅 / 炉灶三种站点的旁观广播共用一份，站点里的人收到的不在这里管（他们的客户端要靠每一个演弹开 / 撤回）。
"""
import time

from .Engine import compFactory, serverApi

RANGE = 32.0               # 与前置包的 WATCH_RANGE 一致（两个包互不导入）
SNAPSHOT_SECONDS = 0.5     # 玩家位置的快照多久换一次
REFRESH_SECONDS = 5.0      # 样子没变时，隔多久把当前的样子再单发给附近的人一份（丢了的就这么补上）；一份几百字节，附近每人每 5 秒一份
REFRESH_MOST = 60.0        # 间隔加倍的名单（Audience 的 most）最长隔这么久：5、10、20、40、60、60……
REFUSED_GAP = 0.3          # 秒：同一个人被拒的敲击声，旁观的人这么久之内至多听一声（真实时间，不受 /time 影响）
_cache = {"at": None, "players": []}
_refusedAt = {}            # 玩家 id -> 上一次把他被拒的敲击声放给旁观的人听的时刻


def reset():
    """清掉快照和被拒的记录（测试和重载用）。"""
    _cache["at"], _cache["players"] = None, []
    _refusedAt.clear()


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


def mayHearRefusal(actor):
    """这个人（actor，被拒的动作是他发的；没有就算一个人）被拒的敲击声，这一次旁观的人该不该听到：被拒的动作每秒能来 40 个（前置包按玩家的令牌桶上限），
    不限的话改过的客户端发一串非法的动作，就能把被拒的敲击声当喇叭、给 32 格内每个人各发一次广播。离他上一次被听到不到 REFUSED_GAP 秒就不发；
    时钟倒着走（换了世界、测试）当作隔够了；记录只留这一阵里被听到过的人，不随玩家来来去去涨。"""
    now = time.time()
    last = _refusedAt.get(actor)
    if last is not None and 0.0 <= now - last < REFUSED_GAP:
        return False
    _refusedAt[actor] = now
    if len(_refusedAt) > 64:
        for key in [key for key, at in _refusedAt.items() if not 0.0 <= now - at < REFUSED_GAP]:
            del _refusedAt[key]
    return True


def nearby(dimensionId, blockPos, now=None):
    """同维度、离方块 RANGE 格内的玩家 id。"""
    cx, cy, cz = blockPos[0] + 0.5, blockPos[1] + 0.5, blockPos[2] + 0.5
    return [playerId for playerId, dimension, at in players(now)
            if dimension == dimensionId and (at[0] - cx) ** 2 + (at[1] - cy) ** 2 + (at[2] - cz) ** 2 <= RANGE * RANGE]


class Audience(object):
    """已经收到这口锅 / 灶当前样子的人，和他是什么时候收到的。refresh 给了（秒）：隔了这么久没发给他的人也要再发一份当前的样子；
    most 也给了：每补发一次间隔加倍，到 most 为止（不给就一直每 refresh 秒一份）。"""

    def __init__(self, refresh=None, most=None):
        self.refresh = refresh
        self.most = most
        self.known = {}                # 玩家 id -> (上次发给他的时刻（调用方没给时钟时是 None）, 下一份隔多久)

    def _due(self, entry, now):
        """上次发给他已经隔够了：要再发一份。没有 refresh 或没给时钟不再发；时钟倒着走（换了世界、测试）也再发。"""
        if self.refresh is None or now is None:
            return False
        at, wait = entry
        return at is None or not 0.0 <= now - at < wait

    def _next(self, entry):
        """补发过一次之后下一份隔多久：有 most 就加倍到 most 为止；上一份没记时刻的（旧调用没给时钟）这一份才算第一份，不加倍。"""
        at, wait = entry
        if self.most is None or at is None:
            return wait
        return min(wait * 2.0, max(self.most, self.refresh))

    def arrivals(self, near, now=None):
        """near 里这一步要单发一份当前样子的人：才新走进来的（还没收到），和隔够了的（可能丢了）。
        名单顺手换成 near：走出去的划掉，回来时算新来的。"""
        fresh, known = [], {}
        for playerId in near:
            entry = self.known.get(playerId)
            if entry is None:
                fresh.append(playerId)
                known[playerId] = (now, self.refresh)
            elif self._due(entry, now):
                fresh.append(playerId)
                known[playerId] = (now, self._next(entry))
            else:
                known[playerId] = entry
        self.known = known
        return fresh

    def sent(self, near, now=None):
        """刚把当前样子发给了 near 里的所有人（样子变了）：间隔从头算。"""
        self.known = dict((playerId, (now, self.refresh)) for playerId in near)
