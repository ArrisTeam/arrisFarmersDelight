# -*- coding: utf-8 -*-
"""
服务端推给客户端的消息，以及客户端的非操作请求（docs/ARCHITECTURE.md 第 5 节）。都是普通字典，经 QuModLibs 的 Call 传输。

格子内容按容器同步：{"sync": {容器编号: 载荷}}，载荷的写法由那个容器的同步方式定（Common/Sync），容器编号是容器在
界面模型结构里的序号（见 Collections.Structure），线上的键是字符串。

服务端 -> 客户端：
    open    {"s": 会话, "menu": 界面模型名, "params": 参数, "title": 标题, "drop": 能不能丢,
             "sync": {...}, "d": {数据名: 线上的值}}（界面数据的写法由字段类型定，见 Common/Data）
    ack     {"s": 会话, "id": 请求编号, "ok": True|False, "err": 错误码, "sync": {...}, "d": {...}（变了才有）}
    update  {"s": 会话, "sync": {...}, "d": {...}}
    close   {"s": 会话, "reason": 原因}（原因见下面的 CLOSE_*）
客户端 -> 服务端（操作请求见 Ops）：
    req     {"s": 会话, "c": 容器编号, "q": 查询}   按容器的同步方式拉取（例如按窗口拉取的一段）
    close   {"s": 会话}
纯逻辑，两端共用。
"""
from . import Schema

# 关闭原因（close 消息的 reason，docs/ARCHITECTURE.md 第 3.12 节）。关闭时手持物与临时格照常退回背包（放不下的丢在脚下），
# 只有死了且背包已经掉光时手持物整堆丢在原地。SILENT 里的不通知客户端：玩家自己关的（客户端先关了界面）、玩家要离开的
# （客户端已经没了）。
CLOSE_CLIENT = "client"                 # 玩家自己关（ESC、关闭按钮、点到面板外）
CLOSE_HURT = "hurt"                     # 受到生物造成的伤害（原版规则；容器类型的 closeOnHurt）
CLOSE_HOST_GONE = "host_gone"           # 宿主不再有效（走远、方块没了、实体死了、物品离开那一格、权限没了）
CLOSE_DIMENSION = "dimension"           # 玩家换了维度
CLOSE_DEATH = "death"                   # 玩家死了
CLOSE_LEAVE = "leave"                   # 玩家要离开游戏
CLOSE_REPLACED = "replaced"             # 别的模组的容器要为这位玩家打开
CLOSE_REOPEN = "reopen"                 # 这位玩家打开了另一个容器
CLOSE_REOPEN_FAILED = "reopen_failed"   # 按新参数重开时存档读不了
CLOSE_API = "api"                       # 使用方经 Api.closeContainer 关（可以另给原因）
CLOSE_NO_SESSION = "no_session"         # 客户端以为开着的会话服务端已经没有了
CLOSE_SWITCH = "switch"                 # 切换、重开到另一个会话（不发 close：新会话的开屏消息让客户端换界面；界面模型的 onClose 收到）
SILENT = frozenset((CLOSE_CLIENT, CLOSE_LEAVE))


def encodeSync(payloads, structure):
    """{容器名: 载荷} -> 线上的 {容器编号: 载荷}。"""
    return dict((str(structure.containerId(cid)), payload) for cid, payload in payloads.items())


def decodeSync(message, structure):
    """消息里的 sync -> {容器名: 载荷}（客户端收服务端的消息用，不做防御性校验）。"""
    out = {}
    for number, payload in (message.get("sync") or {}).items():
        cid = structure.containerName(int(number))
        if cid is not None:
            out[cid] = payload
    return out


def parseReq(data, structure):
    """校验 req 请求的外层，返回 (会话, 容器名, 查询)；查询由容器的同步方式校验。"""
    if not isinstance(data, dict):
        raise Schema.BadRequest("bad_request")
    session = Schema.integer(data.get("s"), 1, 1 << 62, "bad_session")
    cid = structure.containerName(Schema.integer(data.get("c"), 0, Schema.MAX_COLLECTIONS - 1, "bad_container"))
    if cid is None:
        raise Schema.BadRequest("bad_container")
    return session, cid, data.get("q")


def parseSession(data):
    if not isinstance(data, dict):
        raise Schema.BadRequest("bad_request")
    return Schema.integer(data.get("s"), 1, 1 << 62, "bad_session")
