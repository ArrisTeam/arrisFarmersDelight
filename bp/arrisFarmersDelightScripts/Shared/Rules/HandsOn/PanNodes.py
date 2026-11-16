# -*- coding: utf-8 -*-
"""PanNodes - 煎锅场景里节点的动作：moveTo / hopTo / rotateTo / scaleTo 的补间、shake、定时的小步骤（双端）

移植自 Diegesis 的 impl/client/anim/Tween.java、Easing.inOutCubic 和 impl/client/scene/NodeInstance.java（moveTo / hopTo / rotateTo /
scaleTo / isMoving / shake，172-258 行，update 700-720 行）：HoD 的 SkilletBehavior 靠这几条命令摆食物、颠锅，这里照原样给一份，
SkilletBehavior 的逻辑（PanShow）就能逐条照着写、离线测。再加 SkilletBehavior.after / steps（169、473-478、844-846 行）：
"过多少秒做一件事"的排队器。时间一律是秒，位置是场景像素（节点自己的坐标，相对节点在场景文件里的位置）。

补间 start(x, y, z, seconds, height)：从"此刻的值"出发（所以半路改道不跳），按 inOutCubic(已过 / 总) 走向目标，
再在 y 上加 height * sin(pi * 已过 / 总)（hop 的弧，用的是不缓动的时间）；seconds 为 0 就是一步到位。
"""
import math

from .Mth import clamp


def inOutCubic(t):
    """Easing.inOutCubic：慢起慢停。"""
    t = clamp(t, 0.0, 1.0)
    return 4.0 * t * t * t if t < 0.5 else 1.0 - math.pow(-2.0 * t + 2.0, 3.0) / 2.0


class Tween(object):
    """三个数从当前值缓动到目标，可选在中点抬一个弧（Tween.java）。"""

    def __init__(self, x=0.0, y=0.0, z=0.0):
        self.value = [float(x), float(y), float(z)]
        self._from = list(self.value)
        self._to = list(self.value)
        self._elapsed = 0.0
        self._duration = 0.0
        self._arc = 0.0

    def start(self, x, y, z, seconds, height=0.0):
        self._arc = float(height)
        self._from = list(self.value)
        self._to = [float(x), float(y), float(z)]
        self._elapsed = 0.0
        self._duration = max(float(seconds), 0.0)
        if self._duration == 0.0:
            self.value = list(self._to)

    @property
    def running(self):
        return self._elapsed < self._duration

    def update(self, dt):
        if self._elapsed < self._duration:
            self._elapsed = min(self._elapsed + dt, self._duration)
            t = inOutCubic(self._elapsed / self._duration)
            self.value = [self._from[i] + (self._to[i] - self._from[i]) * t for i in range(3)]
            self.value[1] += self._arc * math.sin(math.pi * self._elapsed / self._duration)
        return self.value


class Node(object):
    """场景里的一个节点：基准位置（场景文件里的 pos）+ 代码给的位移 / 转角 / 缩放，可见与否，画什么（item）。

    pos 是位移加上基准；rot 是欧拉角（度，x、y、z，Diegesis 按 y、x、z 的次序转）；scale 是整体缩放。
    """

    def __init__(self, name, base=(0.0, 0.0, 0.0), visible=True):
        self.name = name
        self.base = tuple(base)
        self.visible = visible
        self.item = None                 # 此刻画哪件物品（物品字典），None = 不画
        self.size = 0.0                  # 画多大（物品的边长，像素；缩放 scale 另乘）
        self._offset = Tween(0.0, 0.0, 0.0)
        self._rotation = Tween(0.0, 0.0, 0.0)
        self._scale = Tween(1.0, 1.0, 1.0)
        self._shakeAmount = 0.0
        self._shakeTime = 0.01
        self._shakeLeft = 0.0
        self._shakeOffset = (0.0, 0.0, 0.0)

    # ---- 命令（NodeView）----

    def moveTo(self, x, y, z, seconds):
        self._offset.start(x, y, z, seconds)

    def hopTo(self, x, y, z, height, seconds):
        self._offset.start(x, y, z, seconds, height)

    def rotateTo(self, x, y, z, seconds):
        self._rotation.start(x, y, z, seconds)

    def scaleTo(self, factor, seconds):
        self._scale.start(factor, factor, factor, seconds)

    def shake(self, pixels, seconds):
        """NodeInstance.shake：在 seconds 秒里随机抖，幅度从 pixels 线性减到 0。"""
        self._shakeAmount = max(0.0, pixels)
        self._shakeTime = max(0.01, seconds)
        self._shakeLeft = self._shakeTime

    def setVisible(self, visible):
        self.visible = visible

    def place(self, pos, rot=(0.0, 0.0, 0.0), scale=1.0):
        """一步到位地摆在 pos（相对基准）、转到 rot、缩到 scale：Crack 这类每帧自己算姿态的动作用（等于每帧 moveTo(..., 0)）。"""
        self._offset.start(pos[0] - self.base[0], pos[1] - self.base[1], pos[2] - self.base[2], 0.0)
        self._rotation.start(rot[0], rot[1], rot[2], 0.0)
        self._scale.start(scale, scale, scale, 0.0)

    @property
    def moving(self):
        """moveTo / hopTo 还没到（NodeView.isMoving）。"""
        return self._offset.running

    # ---- 读 ----

    @property
    def pos(self):
        move, shake = self._offset.value, self._shakeOffset
        return (self.base[0] + move[0] + shake[0], self.base[1] + move[1] + shake[1], self.base[2] + move[2] + shake[2])

    @property
    def rot(self):
        return tuple(self._rotation.value)

    @property
    def scale(self):
        return self._scale.value[0]

    def update(self, dt, rand=None):
        """每帧：补间往前走，shake 在剩下的时间里给一个随机偏移（rand 是 0..1 的随机数，缺省不抖）。"""
        self._offset.update(dt)
        self._rotation.update(dt)
        self._scale.update(dt)
        if self._shakeLeft > 0.0 and rand is not None:
            self._shakeLeft = max(0.0, self._shakeLeft - dt)
            amount = self._shakeAmount * self._shakeLeft / self._shakeTime
            self._shakeOffset = tuple((rand() * 2.0 - 1.0) * amount for _ in range(3))
        else:
            self._shakeOffset = (0.0, 0.0, 0.0)


class Steps(object):
    """SkilletBehavior 的 after(seconds, run) 与 frame 里按次序执行到期的小步骤（169、473-478、844-846 行）。"""

    def __init__(self):
        self.clock = 0.0
        self._steps = []

    def after(self, seconds, run):
        self._steps.append((self.clock + seconds, run))

    def clear(self):
        del self._steps[:]

    def __len__(self):
        return len(self._steps)

    def advance(self, dt):
        """钟走 dt 秒，到期的按排进来的次序执行（不是按时刻排：Java 是 filter 后 forEach）。"""
        self.clock += dt
        self.run()

    def run(self):
        if not self._steps:
            return
        due = [step for step in self._steps if step[0] <= self.clock]
        self._steps = [step for step in self._steps if step[0] > self.clock]
        for _, run in due:
            run()
