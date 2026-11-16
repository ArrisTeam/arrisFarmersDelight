# -*- coding: utf-8 -*-
"""
标准库：服务端的敏感词检查，接给动作参数的文字格式（Common/Schema.Text 的 words）。玩家在文本框里打的字会显示给别人看
（命名这类），服务端按引擎的敏感词表再查一遍，含敏感词的请求拒绝：按语句查（CheckWordsValid），给东西起的名字按名字查
（CheckNameValid，原版铁砧改名这样查）。服务端服务启动时经 Std/Server/Defaults.py 导入。
"""
import mod.server.extraServerApi as serverApi

from ...Common import Schema

_component = []


def _game():
    """引擎的游戏组件：第一次查时再建。"""
    if not _component:
        _component.append(serverApi.GetEngineCompFactory().CreateGame(serverApi.GetLevelId()))
    return _component[0]


def check(words):
    """语句可以用（不含敏感词）为真。"""
    return bool(_game().CheckWordsValid(words))


def checkName(name):
    """名字可以用（不含敏感词）为真。"""
    return bool(_game().CheckNameValid(name))


Schema.setWordCheck(check, checkName)
