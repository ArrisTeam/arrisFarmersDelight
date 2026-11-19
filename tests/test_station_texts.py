# -*- coding: utf-8 -*-
# runner: both
"""站点界面上我们自己写的字按玩家的语言给（Client/Texts.py；rp/texts/zh_CN.lang、en_US.lang）：轮盘条目带着语言文件的键（前置包按键查，Protocol.TEXT_KEYS），
厨锅的提示、食谱书页脚的秒数自己查（HoD 有的沿用它的键：handson_delight.pot.ready / cooking、handson_delight.book.seconds）。原来都是写死的中文。
语言文件是别人能盖的（资源包）：找不到的键、填不上的写法都退回代码里的中文，界面不出错、不露键名。假引擎的 world.lang 就是语言文件。
"""
from __future__ import print_function

import io
import os
import re

import prereq  # noqa: F401 - 前置包不在这个仓库里：旁边没有它就跳过（tests/prereq.py）
import panclient as C

import fdtest

world = C.install()
Texts = C.load("Client.Texts")
HoldMenu = C.load("Compat.Diegesis.HoldMenu")
PotHud = C.load("Compat.Diegesis.PotHud")
Books = C.load("Shared.Rules.StationBooks")
TEXTS = os.path.join(fdtest.ROOT, "rp", "texts")
ENTRIES = (HoldMenu.PUT_ONE, HoldMenu.SCOOP_ALL, HoldMenu.CARVE, HoldMenu.TAKE_BACK, HoldMenu.TAKE_ALL_BACK, HoldMenu.PUT_HERE, HoldMenu.TAKE_PIECE)
PLACEHOLDER = re.compile(r"%[sd]")


def _lang(name):
    """语言文件：{键: 那一句}（## 开头的是注释）。"""
    found = {}
    with io.open(os.path.join(TEXTS, name), encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line and not line.startswith("#"):
                key, _, text = line.partition("=")
                found[key] = text
    return found


def _same(text, default):
    return text == (default.decode("utf-8") if isinstance(default, bytes) else default)


def _ours():
    """代码里用到的每一句：[(键, 找不到时的中文)]。"""
    words = [(entry["key"], entry["label"]) for entry in ENTRIES]
    words += [pair for pair in PotHud.TIPS.values() if pair[0]] + [PotHud.SCOOP_TIP, PotHud.TAKE_TIP]
    return words + [(Books.SECONDS_KEY, "%d 秒")]


def testEveryWordIsInBothLanguageFilesAndTheChineseOneSaysWhatTheCodeSays():
    chinese, english = _lang("zh_CN.lang"), _lang("en_US.lang")
    words = _ours()
    assert len(words) == 12 and len(set(key for key, _ in words)) == 12
    for key, default in words:
        assert key in chinese and key in english, key
        assert _same(chinese[key], default), "中文的语言文件和代码里的那句一样：%s" % key
        text = default.decode("utf-8") if isinstance(default, bytes) else default
        assert len(PLACEHOLDER.findall(english[key])) == len(PLACEHOLDER.findall(text)), "占位的个数对得上：%s" % key
        assert english[key] % tuple([1] * len(PLACEHOLDER.findall(english[key]))), "英文的那句填得上：%s" % key


def testAWordTheLanguageFileKnowsIsUsedAndAnyOtherFallsBackToTheBuiltInOne():
    world.lang.clear()
    assert Texts.of("arris_fd.pot.scoop", "盛出 %s") == "盛出 %s" and Texts.of(None, "x") == "x"
    world.lang["arris_fd.pot.scoop"] = u"Serve %s"
    found = Texts.of("arris_fd.pot.scoop", "盛出 %s")
    assert found == "Serve %s" and isinstance(found, str), "引擎给的是 unicode：换成字节串（Py2），和物品名一个类型"
    assert Texts.fill("arris_fd.pot.scoop", "盛出 %s", "Soup") == "Serve Soup"
    world.lang["arris_fd.pot.scoop"] = u"Serve"
    assert Texts.fill("arris_fd.pot.scoop", "盛出 %s", "Soup") == "盛出 Soup", "语言文件里的写法填不上：用代码里的，不出错"
    world.lang["handson_delight.pot.cooking"] = u"%s in %s s"
    assert Texts.fill("handson_delight.pot.cooking", "%s，还要 %d 秒", ("Soup", 7)) == "Soup in 7 s"
    world.lang["handson_delight.pot.cooking"] = u"%d in %d"
    assert Texts.fill("handson_delight.pot.cooking", "%s，还要 %d 秒", ("Soup", 7)) == "Soup，还要 7 秒", "占位的种类不对也一样"
    world.lang.clear()


def testThePotsTipsKeepHandsOnDelightsKeysAndOrder():
    assert PotHud.TIPS[PotHud.PotBadge.TIP_READY] == ("handson_delight.pot.ready", "%d × %s")
    assert PotHud.TIPS[PotHud.PotBadge.TIP_COOKING] == ("handson_delight.pot.cooking", "%s，还要 %d 秒")
    assert PotHud.TIPS[PotHud.PotBadge.TIP_NAME] == (None, "%s"), "只有菜名的那种不用查"


def testTheBooksSecondsFollowTheLanguageAndABrokenWordingIsRefused():
    before = Books._seconds(30)
    assert before == "30 秒"
    try:
        assert Books.wordSeconds("%s s") is True and Books._seconds(30) == "30 s" and Books._seconds(2.5) == "3 s"
        assert Books.wordSeconds("seconds") is False and Books.wordSeconds("%s of %s") is False, "填不上的不换"
        assert Books._seconds(30) == "30 s"
    finally:
        Books.wordSeconds("%d 秒")
    assert Books._seconds(30) == before


def testEveryWheelEntryCarriesAKeyAndStillItsChineseLabel():
    for entry in ENTRIES:
        assert entry["key"].startswith("arris_fd.hold.") and entry["label"], entry
        assert set(entry) == set(("label", "key", "button", "quick")), "老版本的前置包只看 label / button / quick，多一个 key 不碍事"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
