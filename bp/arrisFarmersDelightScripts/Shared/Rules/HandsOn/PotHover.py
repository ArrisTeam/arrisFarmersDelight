# -*- coding: utf-8 -*-
"""PotHover - 厨锅漂着的料、盛好的那格被光标指着时抬起一点（双端）

移植自 Diegesis：impl/client/scene/NodeInstance.java 的 hoverAmount（33、715、808-810）和 api/scene/NodeDefinition.isInteractive（118-120）。
光标指着的节点有个悬停量：每帧以半衰期 0.06 秒追 1，没指着时追 0；节点是槽 / 输出 / 可拿 / 控制件（isInteractive）又不是控制件时，
位置在 y 上加 0.6 像素乘这个量。厨锅 cooking_pot.json 里 item_0..5 和 served 是槽节点，空手指着就抬；勺柄（只有碰撞盒）和锅口（放置区）
不抬。命中盒用不含抬起的位置（NodeInstance.java:48-52），抬起不挪点击的地方。

用法：开着站点的人的表现每帧把光标指着的那一个序号交给 target（没有给 None），场景每帧 step(dt)，摆道具时让 raised(序号, 姿态) 过一遍。
冻住的悬停（勺子在手里）由表现决定给不给 target，这里只管缓动和抬多少。
"""
from .PotLiquid import approach

HOVER_HALF_LIFE = 0.06       # 悬停量追目标的半衰期，秒（NodeInstance.java:33）
HOVER_LIFT = 0.6             # 悬停量为 1 时抬起多少，px（NodeInstance.java:809）
HOVER_MIN = 0.001            # 悬停量大过它才抬（NodeInstance.java:808）


class HoverLift(object):
    """一排节点各自的悬停量（0..1）。target：光标现在指着第几个，没有是 None。"""

    def __init__(self, count):
        self.amount = [0.0] * count
        self.target = None

    def step(self, dt):
        """推进 dt 秒：指着的追 1，别的追 0（NodeInstance.update 的 Easing.approach）。"""
        for index in range(len(self.amount)):
            self.amount[index] = approach(self.amount[index], 1.0 if index == self.target else 0.0, HOVER_HALF_LIFE, dt)

    @property
    def active(self):
        """还有东西在动（光标指着、或抬起的还没落回去）：场景不能歇着。"""
        return self.target is not None or any(value > HOVER_MIN for value in self.amount)

    def raised(self, index, pose):
        """第 index 个的姿态 (x, y, z, ...) 加上它此刻的抬起量（y 方向）。"""
        amount = self.amount[index]
        if amount <= HOVER_MIN:
            return pose
        return (pose[0], pose[1] + HOVER_LIFT * amount) + tuple(pose[2:])
