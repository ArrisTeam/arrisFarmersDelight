# -*- coding: utf-8 -*-
"""TableSync - 服务端发来的"下游追加的数据表内容"并进本端自己的表（客户端）

下游模组在服务端往农夫乐事的配置表里追加配方、刀、可烹饪物、炉灶，客户端是另一个进程、有自己的一份 Shared/Data，站点的客户端表现读的是这一份
（托盘里哪些亮、借哪把刀、点板是切还是敲、食谱书、哪些方块开炉灶站点……）。服务端 Server/TableSync.py 在玩家进服和表变了时发 OnTableSync，
这里交给 Shared/Rules/TableMerge 并表（就地改、幂等、一条一条隔离，并进去有变化的表顺手重算依赖它的缓存：厨锅配方索引、砧板的工具表），
本端没有任何地方要改。收到的消息不对、某个条目换不回来只记日志，不影响别的条目，更不影响站点的其它功能。
"""
import traceback

from ..QuModLibs.Client import AllowCall
from ..Shared.Rules import TableMerge
from ..Shared.Rules.TableWire import isInt

_state = {"messages": 0, "changed": 0, "rev": 0, "problems": 0}


def status():
    """调试用：收了几条消息、其中几条改了表、服务端最新一版的编号、跳过过几个条目。"""
    return dict(_state)


@AllowCall
def OnTableSync(message):
    # 服务端发来的；坏数据、换不回来的条目只进日志
    try:
        result = TableMerge.apply(message)
    except Exception:  # noqa: BLE001 - 网络入口的边界：并表出了意外只打印，别的站点功能照常
        print("[arrisFarmersDelight] 表同步：并表出错")
        traceback.print_exc()
        return
    _state["messages"] += 1
    _state["changed"] += 1 if result["changed"] else 0
    _state["problems"] += len(result["problems"])
    if isinstance(message, dict) and isInt(message.get("rev")):
        _state["rev"] = max(_state["rev"], message["rev"])
    for problem in result["problems"]:
        print("[arrisFarmersDelight] 表同步：%s" % problem)
