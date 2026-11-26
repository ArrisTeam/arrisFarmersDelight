# -*- coding: utf-8 -*-
# runner: both
"""经典厨锅界面搜索的游戏内自检（Client/Debug/McdkPotSearchTest.py、Server/Debug/McdkPotSearchTest.py）离线跑得通：显示名用假的口，
缺省的几条查询词都过滤得出来（"番茄"至少一道），服务端那份过滤出来的每一行 pick 都收；每个口在这个线程里给什么也报得出（抛异常的照样报）。
真正的数在游戏里跑（两个文件的说明：先客户端线程、后服务端线程）。"""
from __future__ import print_function

import fdtest

ClientTest = fdtest.load("Client.Debug.McdkPotSearchTest")
ServerTest = fdtest.load("Server.Debug.McdkPotSearchTest")
Names = fdtest.load("Shared.Rules.ItemNames")
Search = fdtest.load("Shared.Rules.PotSearch")


def _named(name, aux):
    return u"番茄" if name == "arris:tomato" else None


def _wrongThread(name, aux):
    raise RuntimeError("wrong thread")


def _reset():
    Names.setPort(None)
    Names.forget()
    Search.forget()


def testBothSelfTestsRunOfflineAndReportWhatTheyFound():
    _reset()
    Names.setPort(_wrongThread)
    Names.setPort(_named)
    try:
        client = ClientTest.mcdk_test_pot_search_probe()
        assert client["ok"] and client["thread"] == "client" and client["fuzzy"] == Search.CJK, client
        assert [probe["query"] for probe in client["probes"]] == list(ClientTest.QUERIES) and client["probes"][0]["count"] > 0
        assert client["named"] == repr(u"番茄") and client["ports"][1] == repr(u"番茄") and client["ports"][0].startswith("raised")
        assert all(probe["firstMs"] >= 0 and probe["rememberedMs"] >= 0 for probe in client["probes"])
        server = ServerTest.mcdk_test_pot_search_probe()
        assert server["ok"] and server["thread"] == "server" and all(probe["allPickable"] for probe in server["probes"]), server
        assert ServerTest.QUERIES == ClientTest.QUERIES, "两端的查询词一样（各写一份）"
        stew = ClientTest.mcdk_test_pot_search_probe(u"牛炖")
        assert stew["ok"] and [probe["query"] for probe in stew["probes"]] == [u"牛炖"] and stew["probes"][0]["count"] >= 1, "牛肉炖"
        nothing = ServerTest.mcdk_test_pot_search_probe(u"绝对没有这道菜")
        assert nothing["ok"] and nothing["probes"][0]["count"] == 0
    finally:
        _reset()


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
