# -*- coding: utf-8 -*-
# runner: both
"""表同步的删除（字典表：砧板配方、按标签切的砧板配方、能煎烤的东西……，Shared/Rules/TableDiff.py + TableMerge.py）：

字典表里删掉的键也发给客户端（{"k": 键, "gone": true}），客户端照删：要删的是"基线里有的，或者曾经发出去过的，现在没有了"——
第三方后加的键不在基线里，玩家进服时已经发过去了，之后服务端删了它，光看"现在 - 基线"它只是从差异里消失，客户端只加不减，不会知道。
- 删一个内置的键（基线里有）；删一个已经同步过的后加的键；删了再加回来（内置的那个加回原样也要再发一次：客户端已经删了它）；
- 重复收、晚进服的人收到删他本来没有的键：什么都不变；
- 列表表（刀、炉灶……）照旧只加不删；厨锅配方（按下标）删配方是打墓碑（Disabled），走的是"一行变了"。
"""
from __future__ import print_function

import prereq  # noqa: F401 - 表同步的离线测试要前置包的 Wire 核对载荷（tests/tablekit.py）
import fdtest
import tablekit as K

CABBAGE = ("arris:cabbage", 0)
PEARL = K.CUT_KEY


def _pair():
    server, client = K.Package(), K.Package()
    return server, client, server.load("Shared.Rules.TableDiff").Syncer()


def _sync(syncer, client, since=0):
    syncer.refresh()
    return K.deliver(syncer.messages(since), client)


def _cutting(package):
    return package.load("Shared.Data.Cutting").CuttingBoardDict


def testDeletingABuiltInKeyReachesTheClient():
    server, client, syncer = _pair()
    del _cutting(server)[CABBAGE]
    results = _sync(syncer, client)
    assert CABBAGE not in _cutting(client) and any(result["changed"] for result in results)
    gone = [op for message in syncer.messages() for op in message["ops"] if op.get("gone")]
    assert len(gone) == 1 and gone[0]["gone"] is True and "v" not in gone[0]
    assert all(not result["changed"] for result in _sync(syncer, client)), "重复收：什么都不变"


def testDeletingAKeyThatWasAlreadySentReachesTheClient():
    server, client, syncer = _pair()
    K.downstream(server)
    _sync(syncer, client)
    assert PEARL in _cutting(client)
    rev = syncer.rev
    del _cutting(server)[PEARL]
    assert syncer.refresh() and syncer.rev == rev + 1, "删了也是新的一版：收过上一版的人会收到补发"
    K.deliver(syncer.messages(rev), client)
    assert PEARL not in _cutting(client)
    late = K.Package()
    K.deliver(syncer.messages(), late)
    assert PEARL not in _cutting(late) and CABBAGE in _cutting(late), "晚进服的人收到删一个他本来就没有的键：不变"


def testDeletedAndAddedBackComesBack():
    server, client, syncer = _pair()
    K.downstream(server)
    _sync(syncer, client)
    entry, cabbage = dict(_cutting(server)[PEARL]), dict(_cutting(server)[CABBAGE])
    del _cutting(server)[PEARL]
    del _cutting(server)[CABBAGE]
    _sync(syncer, client)
    assert PEARL not in _cutting(client) and CABBAGE not in _cutting(client)
    _cutting(server)[PEARL] = entry
    _cutting(server)[CABBAGE] = cabbage
    _sync(syncer, client)
    assert _cutting(client)[PEARL]["itemList"] == entry["itemList"]
    assert _cutting(client)[CABBAGE]["itemList"] == cabbage["itemList"], "内置的键加回原样：和基线一样也要再发一次（客户端已经删了它）"


def testListsStayAppendOnlyAndRowsUseTombstones():
    server, client, syncer = _pair()
    K.downstream(server)
    _sync(syncer, client)
    knives = server.load("Shared.Data.Cutting").knifeList
    knives.remove(K.KNIFE)
    rows = server.load("Shared.Data.CookingPotRecipes").CookingPotRecipeList
    rows[-1]["Disabled"] = True
    _sync(syncer, client)
    assert K.KNIFE in client.load("Shared.Data.Cutting").knifeList, "名字列表只加不删（和原来一样）"
    assert client.load("Shared.Data.CookingPotRecipes").CookingPotRecipeList[-1].get("Disabled") is True, "厨锅配方删了是墓碑：一行变了"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
