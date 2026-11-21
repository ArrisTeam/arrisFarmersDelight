# -*- coding: utf-8 -*-
"""Texts - 界面上的几句字按玩家的语言给：语言文件里的键、找不到时用的中文（客户端）

站点界面上我们自己写的字（厨锅的提示、食谱书页脚的秒数；轮盘条目的字由前置包按条目带的键查）、服务端发来的提示（Endpoints.OnTip）、JEI 的分类名和秒数
原来是写死在代码里的中文。现在每句有一个语言文件的键
（rp/texts/zh_CN.lang、en_US.lang；HoD 有的沿用它的键名：handson_delight.pot.ready / cooking、handson_delight.book.seconds），用的时候问引擎现在这种语言下
是哪一句（CreateGame(levelId).GetChinese(键)：名字叫取中文，给的是当前语言的；找不到原样返回键），找不到就用代码里的那句中文。
引擎给的是 unicode（Py2）：换成 utf-8 字节串再用——物品名（GetItemBasicInfo）也是字节串，混着拼会出错。
"""
import re

from .Engine import compFactory, levelId

# 一句里的占位：取出转换的字母（%% 是百分号本身，不算）
_PLACE = re.compile(r"%(?:%|[#0 +-]*\d*(?:\.\d+)?([a-zA-Z]))")
try:
    _NUMBERS = (int, long, float)  # noqa: F821 - py2 的长整数
except NameError:
    _NUMBERS = (int, float)


def of(key, default):
    """key 这一句在现在的语言下是什么；没给键、语言文件里没有这一句，用 default。"""
    if not key:
        return default
    found = compFactory.CreateGame(levelId).GetChinese(key)
    if not found or found == key:
        return default
    return found if isinstance(found, str) else found.encode("utf-8")


def _likeDefault(default, values):
    """值先照代码里那句中文的占位换好：那里写 %d 的一格，数换成整数（和 %d 一样截掉小数）。别的语言常把数字写成 %s
    （HoD、JE 的英文就是），6.0 照原样填进去就写成了 6.0；先换成中文里显示的那个整数，哪种语言写出来都是同一个数。"""
    values = values if isinstance(values, tuple) else (values,)
    kinds = [match.group(1) for match in _PLACE.finditer(default) if match.group(1)]
    return tuple(int(value) if index < len(kinds) and kinds[index] in ("d", "i") and isinstance(value, _NUMBERS) else value
                 for index, value in enumerate(values))


def fill(key, default, values):
    """带占位（%s / %d）的一句填上 values（数照 default 的占位先换好，见 _likeDefault）。语言文件是别人能改的（资源包可以盖）：
    那里的写法填不上（占位的个数、种类对不上）就用代码里的，不让界面出错。"""
    values = _likeDefault(default, values)
    wording = of(key, default)
    if wording is not default:
        try:
            return wording % values
        except (TypeError, ValueError):
            pass
    return default % values
