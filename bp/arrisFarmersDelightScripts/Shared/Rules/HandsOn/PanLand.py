# -*- coding: utf-8 -*-
"""PanLand - 食物进锅、出锅的动作：从上面落进锅、从背包飞进来、被拿走时飞走或化掉、被拒时弹开、蛋在锅沿敲开打进去（双端）

移植自 Hands-On Delight 的 client/SkilletBehavior.java：常量 65-72、89-93 行，land / landings / landing（424-463）、cracks（386-421）、
leaves / ghost（928-986）、被拒的那一下（896-904），和 client/FromPlayer.java（从玩家屏幕底边飞来）。时间是秒，位置是场景像素
（落的、飞的在锅节点的坐标里，离锅心；蛋的手 hand_N 和蛋液 spill_N 在场景坐标里）。

- 落：一块块放进来，已经躺着的不动、新来的从 LAND_FROM 高处 0.2 秒落到自己的位置，跳 0.8 像素；几块一起来（一叠、书里点的）错开
  PIECE_STAGGER 0.14 秒、从玩家屏幕底边的那一点起飞，0.32 秒、跳 2 像素。落的过程中锅里变多了，落点会跟着新的摆法改；
- 蛋：不连壳躺着，从光标（或屏幕底边）飞到锅右沿磕一下、移到它的位置上方裂开，蛋液落下来，落稳了才露出那一块（Crack 在 PotServeHands）；
- 走：取出去的，每块错开 0.04 秒 0.3 秒里抬起来缩没（"到手上了"），煎好跳出锅的往锅右边抛出去；
- 被拒：放不进去的那一件落到锅心又弹开，挂灯"当"的一声。
"""
import math

from .Items import make
from .PanLayout import FLOOR, PIECES, counts, height, place, size, yaw
from .PotServeHands import Crack

LAND_TIME = 0.2            # 自己放的一块落进来用多久（SkilletBehavior 66）
LAND_FROM = 4.0            # 从多高落下来（67）
PIECE_STAGGER = 0.14       # 一起来的几块错开多久（69）
PLAYER_LAND_TIME = 0.32    # 从屏幕底边飞来的用多久（70）
AWAY_TIME = 0.3            # 走的用多久（71）
AWAY_Z = 12.0              # 抛出去的往右多远（72）
GLIDE = 0.16               # 锅里别的块挪到新位置用多久（105）
RIM_OUT = 6.2              # 蛋磕在锅右沿：离锅心多远、多高（89-90）
RIM_TOP = 2.4
CRACK_FROM = 6.0           # 蛋从锅底上方多高的地方飞来（91）
EGG_SIZE = 3.4             # 蛋多大（92）
EGG_YAW = 180.0            # 镜头朝 -z 看，蛋面朝镜头（405 行传给 Crack 的 180）
REFUSED_AT = (0.0, LAND_FROM + 2.0, 0.0)


def single(stack):
    """展示用的一件（数量 1，只带名字和 aux）。"""
    return make(stack["newItemName"], stack.get("newAuxValue") or 0)


class Landings(object):
    """正在往锅里落的块：piece_i 是下标 i，under_i 是 PIECES + i；age 为 None 是已经躺下了。"""

    def __init__(self, show):
        self.show = show
        count = PIECES * 2
        self.age = [None] * count
        self.at = [(0.0, 0.0, 0.0)] * count
        self.time = [0.0] * count
        self.hop = [0.0] * count

    @staticmethod
    def key(index, under):
        return PIECES + index if under else index

    def landing(self, index, under):
        return self.age[self.key(index, under)] is not None

    def reset(self):
        self.age = [None] * (PIECES * 2)

    def land(self, node, index, under, offset):
        """从 LAND_FROM 高处（或从玩家那边）落进自己的位置，跳一下（424-435）。offset 是 (dx, dz) 或 None。"""
        show = self.show
        at = place(index, show.shownPieces)
        k = self.key(index, under)
        dx, dz = offset if offset is not None else (0.0, 0.0)
        self.age[k] = 0.0
        self.at[k] = (at[0] + dx, height(under, show.shownUnders) + LAND_FROM, at[1] + dz)
        self.time[k] = LAND_TIME if offset is None else PLAYER_LAND_TIME
        self.hop[k] = 0.8 if offset is None else 2.0
        node.moveTo(self.at[k][0], self.at[k][1], self.at[k][2], 0.0)

    def step(self, dt):
        """落着的块往新摆法的位置落（438-459）：落点每帧重算。"""
        show = self.show
        for k in range(PIECES * 2):
            if self.age[k] is None:
                continue
            index, under = k % PIECES, k >= PIECES
            self.age[k] += dt
            t = min(1.0, self.age[k] / self.time[k])
            at = place(index, max(1, show.shownPieces))
            eased = t * (2.0 - t)
            start = self.at[k]
            x = start[0] + (at[0] - start[0]) * eased
            z = start[2] + (at[1] - start[2]) * eased
            y = start[1] + (height(under, show.shownUnders) - start[1]) * t + self.hop[k] * math.sin(t * math.pi)
            show.nodes[("under_%d" if under else "piece_%d") % index].moveTo(x, y, z, 0.0)
            if t >= 1.0:
                self.age[k] = None


class Egg(object):
    """一个蛋在锅沿敲开、蛋液落进锅里（cracks 386-421）：一只手 hand_i 拿蛋，蛋液 spill_i，一人一个，几个蛋一个接一个。"""

    def __init__(self, show, index, offset, hot):
        self.show, self.index, self.hot = show, index, hot
        self.landed = False
        at = place(index, max(1, show.shownPieces))
        top = FLOOR + CRACK_FROM
        if offset is not None:
            start = (8.0 + at[0] + offset[0], top, 8.0 + at[1] + offset[1])
        else:
            start = (show.cursorOn(top) if show.focused else None) or (8.0 + at[0], top + 2.0, 8.0 + at[1])
        rim = (8.0 + RIM_OUT, RIM_TOP, 8.0 + at[1] * 0.5)
        show.waitingIn[index] = True
        show.nodes["piece_%d" % index].setVisible(False)
        self.hand, self.spill = show.nodes["hand_%d" % index], show.nodes["spill_%d" % index]
        self.hand.item = single(show.shown)
        self.spill.item = show.openedLook(show.shown)
        self.hand.size = EGG_SIZE
        self.spill.size = size(show.shownPieces)
        self.crack = Crack(start, rim, (8.0 + at[0], 0.0, 8.0 + at[1]), FLOOR + height(False, show.shownUnders), EGG_SIZE, size(show.shownPieces),
                           False, EGG_YAW, yaw(index, False))

    def frame(self, dt):
        """推进一帧；返回 False 表示这个蛋演完了。"""
        show = self.show
        poses, events = self.crack.step(dt)
        for key, node in (("egg", self.hand), ("inside", self.spill)):
            pose = poses[key]
            node.place(pose["pos"], pose["rot"], pose["scale"])
            node.visible = pose["visible"]
        for event in events:
            kind = event["type"]
            if kind == "dust":
                show.particles("dust", event["pos"], event["rise"], event["spread"], event["count"], event["color"])
            elif kind == "sound":
                show.sound(event["name"], event["volume"], event["pitch"])
            elif kind == "shake":
                (self.hand if event["node"] == "egg" else self.spill).shake(event["amount"], event["seconds"])
        if self.crack.landed and not self.landed:
            self.landed = True
            self._landed()
        if self.crack.done:
            self.stop()
            return False
        return True

    def _landed(self):
        """蛋液落稳：这一块躺在它的位置上（408-418）。"""
        show, index = self.show, self.index
        show.waitingIn[index] = False
        if index < show.shownPieces:
            node = show.nodes["piece_%d" % index]
            now = place(index, show.shownPieces)
            node.moveTo(now[0], height(False, show.shownUnders), now[1], 0.0)
            node.rotateTo(0.0, yaw(index, False), 0.0, 0.0)
            node.setVisible(True)
        if self.hot:
            show.heat.hitsTheFat()

    def stop(self):
        self.hand.visible = False
        self.spill.visible = False


def ghost(show, stack, index, scale):
    """leaves / 被拒用的替身（ghost 968-986）：lift_N 节点摆成 stack 的样子回到原点、等着被抬走。"""
    node = show.nodes["lift_%d" % (index % PIECES)]
    node.item = single(stack)
    node.size = scale
    node.rotateTo(0.0, 0.0, 0.0, 0.0)
    node.scaleTo(1.0, 0.0)
    node.moveTo(0.0, 0.0, 0.0, 0.0)
    node.setVisible(True)
    return node


def refused(show, stack):
    """放不进去的那一件落到锅心又弹开（896-904）。"""
    node = ghost(show, stack, 0, size(1))
    node.moveTo(REFUSED_AT[0], REFUSED_AT[1], REFUSED_AT[2], 0.0)
    node.moveTo(0.0, 1.5, 0.0, 0.09)
    show.steps.after(0.09, lambda: node.hopTo(0.0, LAND_FROM + 2.0, AWAY_Z * 0.5, 1.2, 0.22))
    show.steps.after(0.31, lambda: node.setVisible(False))
    show.sound("lantern_hit", 0.4, 1.3)


def _gone(node, at, toCook):
    if toCook:
        node.hopTo(at[0], 2.5, at[1], 1.5, AWAY_TIME)                       # 抬起来、缩没：到手上了
        node.scaleTo(0.0, AWAY_TIME)
    else:
        node.hopTo(at[0] + AWAY_Z, 2.0, at[1], 5.0, AWAY_TIME)             # 煎好了跳出锅外


def leaves(show, stack, toCook):
    """锅里的东西走了（928-961）：每块的替身从原位抬起缩没（toCook）或抛向锅右边，真的那几块马上藏起来。"""
    if not stack:
        return
    pieces = show.shownPieces or counts(stack.get("count") or 1)[1]      # 状态比这条消息先到、锅里已经画空了：照走的那叠数块数
    for i in range(max(1, pieces)):
        at = place(i, max(1, pieces))
        node = ghost(show, stack, i, size(pieces))
        node.moveTo(at[0], 0.0, at[1], 0.0)
        node.rotateTo(0.0, yaw(i, False), 0.0, 0.0)
        show.steps.after(i * 0.04, lambda node=node, at=at: _gone(node, at, toCook))
        show.steps.after(i * 0.04 + AWAY_TIME, lambda node=node: node.setVisible(False))
    for i in range(PIECES):
        show.nodes["piece_%d" % i].setVisible(False)
        show.nodes["under_%d" % i].setVisible(False)
    show.shownPieces = 0
    show.shownUnders = 0
    show.shown = show.item = None
