# -*- coding: utf-8 -*-
"""Composter - 原版堆肥桶收本包的物品：涨不涨一层、收不收（双端，纯规则）

照 JE 的 ComposterBlock（基岩原版 2026-11-26 实测一样，INGAME-FACTS-1 §3：小麦种子 30%）：
- 空桶（0 层）放第一件必成（JE insertItem：i == 0 时不掷骰子）；1~6 层按物品的概率涨一层；成不成都扣一件；
- 7 层不收、不扣（JE use：i < 7 才放；实测 7 层右键层数不变、物品不扣）；8 层是取骨粉，交给原版；
- 涨到 7 层后过 1 秒变成可取的 8 层（JE scheduleTick 20 刻；脚本设的 7 层引擎会不会自己变 8 没核实，所以自己排一个定时器，
  到点还是 7 层才变）。
"""
READY = 7                 # 到这一层就不收了，等它变成 FULL
FULL = 8                  # 可以取骨粉
READY_SECONDS = 1.0


def accepts(level):
    """这一层还收不收东西（收了就扣一件）。"""
    return 0 <= level < READY


def nextLevel(level, lucky):
    """放进一件后的层数；lucky 是按物品概率掷的结果（0 层不看它）。"""
    return level + 1 if level == 0 or lucky else level
