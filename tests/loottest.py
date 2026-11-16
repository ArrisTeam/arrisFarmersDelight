# -*- coding: utf-8 -*-
"""loottest - 方块战利品表的精确概率计算器（测试用的公共小工具，不是测试本身）

只实现本模组方块掉落表用到的那一小部分写法，按引擎文档（kb/engine/bp/06_loot）的语义：
- 池条件：random_chance（概率）、match_tool（item 相等、count 区间；没有工具 = 不成立）
- 条目：type item / empty，weight；条目条件只支持 match_tool（确定性的）
- 函数：set_count（数字或 {min, max} 均匀整数；函数自己的 conditions 成立才执行），set_data 忽略；
  数量变成 0 条目就作废
- rolls：整数
遇到不认识的写法直接抛错，免得测试悄悄放行。

evaluate(table, tool) → {物品名: {数量: 概率}}：tool 是手里工具的物品名（None = 空手 / 没有工具），
每件物品的数量分布互相独立地累加（不同池各自独立，同一池的几次 roll 也独立）。
"""
from __future__ import print_function

import io
import json
import os

import fdtest


def load(name):
    path = os.path.join(fdtest.BP, "loot_tables", name)
    with io.open(path, encoding="utf-8") as handle:
        return json.load(handle)


def _convolve(a, b):
    out = {}
    for ca, pa in a.items():
        for cb, pb in b.items():
            out[ca + cb] = out.get(ca + cb, 0.0) + pa * pb
    return out


def _range(value):
    if isinstance(value, dict):
        low, high = int(value.get("min", 0)), int(value.get("max", 0))
        return range(low, high + 1)
    return [int(value)]


def _toolMatches(condition, tool):
    if tool is None:
        return False                         # 空手 / 没有工具：count 的区间含不了 0，不成立
    if "item" in condition and condition["item"] != tool:
        return False
    return 1 in _range(condition.get("count", {"min": -(10 ** 9), "max": 10 ** 9}))


def _deterministic(conditions, tool):
    for condition in conditions:
        if condition["condition"] != "match_tool":
            raise ValueError("不支持的条目 / 函数条件 %r" % condition["condition"])
        if not _toolMatches(condition, tool):
            return False
    return True


def _poolGate(conditions, tool):
    """池条件 → (掷骰概率, 确定性的条件是否成立)。"""
    chance = 1.0
    for condition in conditions:
        kind = condition["condition"]
        if kind == "random_chance":
            chance *= condition["chance"]
        elif kind == "match_tool":
            if not _toolMatches(condition, tool):
                return 0.0
        else:
            raise ValueError("不支持的池条件 %r（带 minecraft: 前缀会被引擎丢掉）" % kind)
    return chance


def _entryCount(entry, tool):
    values = _range(1)
    dist = {1: 1.0}
    for function in entry.get("functions", []):
        if not _deterministic(function.get("conditions", []), tool):
            continue
        if function["function"] == "set_count":
            options = list(_range(function["count"]))
            dist = dict((count, 1.0 / len(options)) for count in options)
        elif function["function"] != "set_data":
            raise ValueError("不支持的函数 %r" % function["function"])
    return dist


def _poolDistribution(pool, tool):
    entries = [entry for entry in pool["entries"] if _deterministic(entry.get("conditions", []), tool)]
    total = float(sum(entry.get("weight", 1) for entry in entries))
    perRoll = {}
    if total:
        for entry in entries:
            if entry["type"] == "empty":
                continue
            if entry["type"] != "item":
                raise ValueError("不支持的条目类型 %r" % entry["type"])
            share = entry.get("weight", 1) / total
            counts = perRoll.setdefault(entry["name"], {0: 0.0})
            for count, probability in _entryCount(entry, tool).items():
                counts[count] = counts.get(count, 0.0) + share * probability
    result = {}
    for name, counts in perRoll.items():
        counts[0] = counts.get(0, 0.0) + (1.0 - sum(counts.values()))
        dist = {0: 1.0}
        for _ in range(int(pool.get("rolls", 1))):
            dist = _convolve(dist, counts)
        result[name] = dist
    return result


def evaluate(table, tool=None):
    result = {}
    for pool in table["pools"]:
        chance = _poolGate(pool.get("conditions", []), tool)
        if chance <= 0:
            continue
        for name, dist in _poolDistribution(pool, tool).items():
            gated = dict((count, probability * chance) for count, probability in dist.items())
            gated[0] = gated.get(0, 0.0) + (1.0 - chance)
            result[name] = _convolve(result.get(name, {0: 1.0}), gated)
    # 一件都掉不出来的物品（被剪刀条件整个挡掉）不算掉落
    return dict((name, dist) for name, dist in result.items() if max(dist) > 0 and sum(
        p for count, p in dist.items() if count > 0) > 1e-12)


def mean(dist):
    return sum(count * probability for count, probability in dist.items())


def prob(dist, count):
    return dist.get(count, 0.0)


def spread(dist):
    """(最少, 最多)：概率不为 0 的数量范围。"""
    counts = [count for count, probability in dist.items() if probability > 1e-12]
    return min(counts), max(counts)
