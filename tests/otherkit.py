# -*- coding: utf-8 -*-
"""otherkit - "取别的模组的模块"（Compat/OtherMods）离线测试的共用小工具（不是测试本身，跑器只收 test_*.py）

- Importer：假的引擎 ImportModule。answers 按路径回答：异常对象就抛它（模块在、它自己导入时出错——3.10 实机的引擎就是原样抛给调用的人），
  别的原样给（没写的路径、写 None 都是没装）；asked 记下问过什么。
- kinds(module)：每一处都要测的四种回答——抛 ImportError、抛别的异常、返回 None、返回正常的模块（就是 module）。
- Captured：with 里打印的东西（stdout、stderr 都收）记下来；logged(名字) 数 OtherMods 那行日志为这个名字打了几次，tracebacks() 数几段调用栈。
"""
from __future__ import print_function

import sys

import fdtest

OtherMods = fdtest.load("Compat.OtherMods")
TRACEBACK = "Traceback (most recent call last)"
OTHER_HEAD = "[arrisFarmersDelight] 取别的模组的 "        # OtherMods 那行日志的开头，后面是名字


class Importer(object):
    def __init__(self, answers=None):
        self.answers = dict(answers or {})
        self.asked = []

    def __call__(self, path):
        self.asked.append(path)
        answer = self.answers.get(path)
        if isinstance(answer, Exception):
            raise answer
        return answer


def kinds(module):
    """[(名字, 回答, 当不当没装)]：四种回答，最后一种是正常的模块。"""
    return [("ImportError", ImportError("No module named broken_dependency"), True),
            ("NameError", NameError("name 'oops' is not defined"), True),
            ("None", None, True),
            ("module", module, False)]


def fresh():
    """OtherMods 记过的"打过日志的名字"清掉：每个用例都从没出过错开始（游戏里一个进程只有一份）。"""
    OtherMods._failed.clear()


class Captured(object):
    """with Captured() as out: ……  里面打印到 stdout / stderr 的都记进 out.text；出来时放回原样。"""

    def __init__(self):
        self.parts = []
        self.saved = None
        self.softspace = 0          # py2 的 print 语句要读写它

    def __enter__(self):
        self.saved = (sys.stdout, sys.stderr)
        sys.stdout = sys.stderr = self
        return self

    def __exit__(self, *exc):
        sys.stdout, sys.stderr = self.saved
        return False

    def write(self, text):
        if not isinstance(text, str):           # py2 的 unicode：转成和本文件的字面量一样的 utf-8 字节
            text = text.encode("utf-8")
        self.parts.append(text)

    def flush(self):
        pass

    @property
    def text(self):
        return "".join(self.parts)

    def logged(self, name):
        """OtherMods 为 name 打的日志行数。"""
        head = OTHER_HEAD + name + " "
        return len([line for line in self.text.splitlines() if line.startswith(head)])

    def tracebacks(self):
        return self.text.count(TRACEBACK)
