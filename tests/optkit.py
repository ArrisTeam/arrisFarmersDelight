# -*- coding: utf-8 -*-
"""optkit - HoD 配置表（Shared/Data/HandsOnConfig.py）离线测试的共用小工具（不是测试本身，跑器只收 test_*.py）

Config 是个 with 块：进去时改表里的值，出来时整张表放回原样（用例改表不会漏到别的用例）。MISSING 当值用就是把那个键删掉。
"""
from __future__ import print_function

import fdtest
import linkkit

linkkit.link()        # 配置表的读法在联动了才生效（没联动时 HandsOnOptions 说 HoD 不在）：这里的用例都当装了前置包
Table = fdtest.load("Shared.Data.HandsOnConfig")
Options = fdtest.load("Shared.Rules.HandsOnOptions")
MISSING = object()


class Config(object):
    """with Config(skillet=False, stove_time=2.0): ……"""

    def __init__(self, **values):
        self.values = values
        self.before = None

    def __enter__(self):
        self.before = dict(Table.CONFIG)
        for key, value in self.values.items():
            if value is MISSING:
                Table.CONFIG.pop(key, None)
            else:
                Table.CONFIG[key] = value
        return self

    def __exit__(self, *exc):
        Table.CONFIG.clear()
        Table.CONFIG.update(self.before)
        return False
