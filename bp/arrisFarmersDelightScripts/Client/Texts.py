# -*- coding: utf-8 -*-
"""Texts - 界面上的几句字按玩家的语言给：语言文件里的键、找不到时用的中文（客户端）

站点界面上我们自己写的字（厨锅的提示、食谱书页脚的秒数；轮盘条目的字由前置包按条目带的键查）原来是写死在代码里的中文。现在每句有一个语言文件的键
（rp/texts/zh_CN.lang、en_US.lang；HoD 有的沿用它的键名：handson_delight.pot.ready / cooking、handson_delight.book.seconds），用的时候问引擎现在这种语言下
是哪一句（CreateGame(levelId).GetChinese(键)：名字叫取中文，给的是当前语言的；找不到原样返回键），找不到就用代码里的那句中文。
引擎给的是 unicode（Py2）：换成 utf-8 字节串再用——物品名（GetItemBasicInfo）也是字节串，混着拼会出错。
"""
from .Engine import compFactory, levelId


def of(key, default):
    """key 这一句在现在的语言下是什么；没给键、语言文件里没有这一句，用 default。"""
    if not key:
        return default
    found = compFactory.CreateGame(levelId).GetChinese(key)
    if not found or found == key:
        return default
    return found if isinstance(found, str) else found.encode("utf-8")


def fill(key, default, values):
    """带占位（%s / %d）的一句填上 values。语言文件是别人能改的（资源包可以盖）：那里的写法填不上（占位的个数、种类对不上）就用代码里的，不让界面出错。"""
    wording = of(key, default)
    if wording is not default:
        try:
            return wording % values
        except (TypeError, ValueError):
            pass
    return default % values
