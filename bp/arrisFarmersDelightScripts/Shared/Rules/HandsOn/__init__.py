# -*- coding: utf-8 -*-
"""HandsOn - Hands-On Delight 规则内核的 Python 2.7 移植（双端）

不依赖任何引擎模块，服务端逻辑与客户端预测共用同一份。时间一律是秒（原版以刻计，每个常量旁注明原值）。

    Mth         数学与取整小工具（Java 的取整、取余语义）
    Items       网易物品字典 -> 数量 / (名字, aux) 身份
    StirSkill   搅锅评星（勺尖轨迹 -> 0-3 星）
    Spoon       一把勺子一只手
    PotBonus    星级奖励份数、开星门槛、出锅结算
    PotCooking  厨锅批量烹饪计时、搅拌门控、FD 原样兜底
    PotMatch    锅里的料能凑出几份配方（增广路匹配）
    Cutting     切菜板切法规划、刀口布局、落刀校验、整批切、工具判定
    Frying      煎锅两面煎制状态机
    Grill       灶台六个位置的两面烧烤状态机
    Assembly    摆盘：前缀匹配、可否继续加料、底座/收尾分类

本目录的规则移植自 Hands-On Delight（https://github.com/Pocky-l/handson-delight），原作的许可如下：

    MIT License

    Copyright (c) 2026 Pocky

    Permission is hereby granted, free of charge, to any person obtaining a copy
    of this software and associated documentation files (the "Software"), to deal
    in the Software without restriction, including without limitation the rights
    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
    copies of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in all
    copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
    SOFTWARE.
"""
