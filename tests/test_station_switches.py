# -*- coding: utf-8 -*-
# runner: both
"""四个站点的玩家开关（Shared/Rules/StationSwitches）：登进前置包设置界面的项是总开关 + 这一端登记成功的站点各一项（厨锅、砧板、煎锅、炉灶的顺序），
每项管着那个站点的站点 id；一个站点都没登上就不登这一组。名字带本包语言文件的键，两份语言文件都有，中文和代码里的一样、英文照主会话定的。
"砧板站点对我开不开" = 总开关 and 砧板那一项（读出 None 算开着）。服务端按玩家记：只记关着的，没报过的当开着，下线清掉。"""
from __future__ import print_function

import io
import os

import fdtest

Rules = fdtest.load("Shared.Rules.StationSwitches")
TEXTS = os.path.join(fdtest.ROOT, "rp", "texts")
ALL = {"cooking_pot": "arris:cooking_pot", "cutting_board": "arris:cutting_board", "skillet": "arris:skillet", "stove": "arris:stove"}
# 主会话定的文案：键 -> (中文, 英文)
WORDS = {
    "arris_fd.settings.group": (u"农夫乐事", u"Farmer's Delight"),
    "arris_fd.settings.all": (u"全部厨具", u"All kitchenware"),
    "arris_fd.settings.cooking_pot": (u"厨锅", u"Cooking Pot"),
    "arris_fd.settings.cutting_board": (u"砧板", u"Cutting Board"),
    "arris_fd.settings.skillet": (u"煎锅", u"Skillet"),
    "arris_fd.settings.stove": (u"炉灶", u"Stove"),
}


def _text(value):
    return value.decode("utf-8") if isinstance(value, bytes) else value


def _lang(name):
    found = {}
    with io.open(os.path.join(TEXTS, name), encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line and not line.startswith("#"):
                key, _, text = line.partition("=")
                found[key] = text
    return found


def testTheGroupIsTheMasterThenTheRegisteredStationsInTheSettingsOrder():
    items = Rules.playerSwitches(ALL)
    assert [item["key"] for item in items] == ["enabled", "cooking_pot", "cutting_board", "skillet", "stove"]
    assert items[0]["master"] is True and "stations" not in items[0], "第一项是总开关，不直接管站点"
    for item in items[1:]:
        assert item["stations"] == (ALL[item["key"]],) and not item.get("master"), item
    assert Rules.MASTER == "enabled" and Rules.BOARD == "cutting_board" and Rules.GROUP == "farmersdelight"


def testOnlyTheStationsRegisteredOnThisSideGetAnItemAndNoStationMeansNoGroup():
    items = Rules.playerSwitches({"cutting_board": "arris:cutting_board", "stove": "arris:stove"})
    assert [item["key"] for item in items] == ["enabled", "cutting_board", "stove"]
    assert Rules.playerSwitches({}) == [], "四个都没登上：这一组不登"


def testEveryLabelIsAKeyBothLanguageFilesHaveWithTheWordsTheLeadChose():
    zh, en = _lang("zh_CN.lang"), _lang("en_US.lang")
    labels = [Rules.GROUP_TITLE] + [item["label"] for item in Rules.playerSwitches(ALL)]
    assert sorted(label["key"] for label in labels) == sorted(WORDS), "组名、总开关、四个站点各一个键"
    for label in labels:
        chinese, english = WORDS[label["key"]]
        assert _text(label["text"]) == chinese, "代码里找不到键时的中文就是语言文件里那一句：%s" % label["key"]
        assert zh.get(label["key"]) == chinese and en.get(label["key"]) == english, label["key"]


def testTheGroupNameFitsATab():
    assert len(_text(Rules.GROUP_TITLE["text"])) <= 4, "设置界面一组一个页签，组名最多四个字"


def testTheBoardIsOnForMeOnlyWhenTheMasterAndTheBoardSwitchAreBothOn():
    assert Rules.boardOn(True, True) is True
    assert Rules.boardOn(False, True) is False and Rules.boardOn(True, False) is False and Rules.boardOn(False, False) is False
    assert Rules.boardOn(None, None) is True and Rules.boardOn(None, True) is True, "没登记的项（读出 None）算开着"
    assert Rules.boardOn(None, False) is False and Rules.boardOn(False, None) is False
    assert set(Rules.BOARD_KEYS) == set([Rules.MASTER, Rules.BOARD]), "这两项变了要重报"


def testTheServerRemembersOnlyWhoTurnedItOffAndForgetsThemWhenTheyLeave():
    choices = Rules.Choices()
    assert choices.boardOn("a") is True and choices.players() == [], "没报过：开着（否决照旧）"
    choices.put("a", False)
    assert choices.boardOn("a") is False and choices.boardOn("b") is True, "只管报的那个玩家"
    choices.put("a", True)
    assert choices.boardOn("a") is True and choices.players() == []
    choices.put("a", False)
    choices.drop("a")
    assert choices.boardOn("a") is True and choices.players() == [], "下线清掉"
    choices.drop("nobody")


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
