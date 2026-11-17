# -*- coding: utf-8 -*-
"""GrillGhosts - 炉灶烤架上取走和弹回的虚影：借来的三个道具轮着用（客户端）

对应 Hands-On Delight：client/StoveBehavior.java 的 ghost（519-538）、taken（501-517）和 REFUSED（482-490）。
一件被取走：它的虚影从原来的位置升起、缩没；放不上去：虚影从烤架中心上方落下、往后弹开。动作的数学在 HandsOn/StoveMotion.Ghost，
这里给它们配上客户端道具（view.props）：道具的位置、姿态、缩放每帧照虚影的动作摆，虚影走完就收掉。
弹回的动作是"往后"（站点里的 -z，往开着站点的人这边）弹：场景里要换成场景的方向（turn：站点的水平方向 -> 场景的），旁观的人没有这个换法，往 -z 弹。
"""
from ...Shared.Rules.HandsOn import StoveMotion

COUNT = 3                            # 轮着用的虚影个数（StoveBehavior.GHOSTS）


class Ghosts(object):
    def __init__(self, view, scale):
        self.view = view
        self.scale = scale                       # 道具的基础缩放（一件食物画多大）
        self.motions = [StoveMotion.Ghost() for _ in range(COUNT)]
        self.props = [None] * COUNT
        self.bases = [None] * COUNT              # 虚影的基点（站点坐标）：动作的偏移加在它上面
        self.turns = [None] * COUNT              # 虚影的偏移（水平方向）怎么换成场景的方向，None 是不用换
        self.at = 0

    def taken(self, stack, base, yaw):
        """一件被取走：虚影从 base（它躺的地方）升起、缩没。"""
        self._start(stack, base, yaw, False, None)

    def refused(self, stack, base, turn=None):
        """放不上去的一件：虚影从 base（烤架中心）上方落下、往后弹开；turn(dx, dz) 把弹开的方向换成场景的。"""
        self._start(stack, base, 0.0, True, turn)

    def _start(self, stack, base, yaw, refused, turn):
        if not stack or not stack.get("newItemName"):
            return
        self.at = (self.at + 1) % COUNT
        index = self.at
        if self.props[index] is not None:
            self.view.props.remove(self.props[index])
        motion = self.motions[index]
        if refused:
            motion.refused()
        else:
            motion.taken(yaw)
        self.bases[index] = base
        self.turns[index] = turn
        item = {"newItemName": stack["newItemName"], "newAuxValue": stack.get("newAuxValue") or 0, "count": 1}
        self.props[index] = self.view.props.item(item, base, scale=self.scale, matrix=StoveMotion.poseRows(0.0, yaw, 0.0))

    def frame(self, dt):
        for index in range(COUNT):
            motion, prop = self.motions[index], self.props[index]
            if prop is None:
                continue
            motion.update(dt)
            if not motion.visible:
                self.view.props.remove(prop)
                self.props[index] = None
                continue
            base = self.bases[index]
            offset, rotation, scale = motion.pose()
            if self.turns[index] is not None:
                x, z = self.turns[index](offset[0], offset[2])
                offset = (x, offset[1], z)
            prop.move(center=(base[0] + offset[0], base[1] + offset[1], base[2] + offset[2]),
                      matrix=StoveMotion.poseRows(rotation[0], rotation[1], rotation[2]), scale=self.scale * max(scale, 0.001))

    def clear(self):
        """全收掉。"""
        for index in range(COUNT):
            if self.props[index] is not None:
                self.view.props.remove(self.props[index])
                self.props[index] = None
