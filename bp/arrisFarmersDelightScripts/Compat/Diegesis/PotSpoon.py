# -*- coding: utf-8 -*-
"""PotSpoon - 厨锅站点里勺子的手感：勺尖跟手、汤带着料转、多久报一次服务端（客户端，纯逻辑）

对应 Hands-On Delight：client/PotBehavior.java 的 moveSpoon / stirEffects。坐标是站点像素里离锅心的 (dx, dz)。
勺尖要么跟着本人的手（aim 给的点），要么跟着同步来的位置（别人在搅），要么回到锅沿靠着；
在汤里挪动时，汤按挪动的快慢和绕锅心的方向转起来（swirl），料跟着转（turn）。
"""
import math

SPOON_REACH = 3.0                 # 勺尖离锅心最远（像素）
SPOON_HOME = (2.6, -1.0)          # 没人搅时勺子靠在锅沿
SEND_INTERVAL = 0.12              # 勺尖报服务端的间隔（秒）和这期间至少挪多远（像素）
SEND_TRAVEL = 0.2
HAND_MEMORY = 2.5                 # 松手后这么久里勺子还算自己的（停在松手处）
SWIRL_HALF_LIFE = 1.0
MAX_TURN = 3.5                    # 搅满时料每秒绕锅心转多少弧度
IDLE_TURN = 0.25                  # 烧着的锅自己慢慢翻


def _sign(value):
    return 1.0 if value > 0.0 else -1.0


def clampToReach(dx, dz, reach=SPOON_REACH):
    distance = math.hypot(dx, dz)
    shorter = reach / distance if distance > reach else 1.0
    return dx * shorter, dz * shorter


class SpoonHand(object):
    def __init__(self):
        self.tip = list(SPOON_HOME)
        self.want = None                  # 本人的手要勺尖去的地方
        self.travel = 0.0                 # 这一按挪了多远（区分"点"和"拖"）
        self.handLeft = 0.0
        self.swirl = 0.0                  # 0..1：汤转得多快
        self.swirlSign = 1.0
        self.turn = 0.0                   # 料绕锅心转到的角度
        self.lift = 1.0                   # 0 在汤里，1 靠在锅沿
        self.sendLeft = 0.0
        self.sendTravel = 0.0

    def press(self):
        """新的一按：挪了多远从这里重新算（上一次搅拌停在哪不算进来，不然搅完再点料会被当成拖动）。"""
        self.travel = 0.0
        self.want = None

    def aim(self, dx, dz):
        """本人的手指着汤面上离锅心 (dx, dz) 的地方（超出勺子够得着的范围就收回来）。"""
        dx, dz = clampToReach(dx, dz)
        if self.want is not None:
            self.travel += math.hypot(dx - self.want[0], dz - self.want[1])
        self.want = (dx, dz)

    def step(self, dt, holding, stirring, synced=None, heated=False):
        """推进一帧。holding：本人握着勺子；stirring：锅算被搅着；synced：同步来的勺尖（别人在搅）。
        返回 True 表示该把勺尖报给服务端了。"""
        if holding and self.want is not None:
            want, self.handLeft = self.want, HAND_MEMORY
        elif stirring and self.handLeft > 0.0:
            want = tuple(self.tip)
        elif stirring:
            want = synced
        else:
            want = None
        self.handLeft -= dt
        moved = self._follow(want, dt, holding)
        self.turn += (self.swirlSign * self.swirl * MAX_TURN + (IDLE_TURN if heated else 0.0)) * dt
        if not holding:
            return False
        self.sendLeft -= dt
        self.sendTravel += moved
        if self.sendLeft <= 0.0 and self.sendTravel >= SEND_TRAVEL:
            self.sendLeft, self.sendTravel = SEND_INTERVAL, 0.0
            return True
        return False

    def _follow(self, want, dt, holding):
        target = want if want is not None else SPOON_HOME
        follow = 1.0 - math.exp(-dt * (18.0 if holding else 6.0))
        stepX, stepZ = (target[0] - self.tip[0]) * follow, (target[1] - self.tip[1]) * follow
        across = self.tip[0] * stepZ - self.tip[1] * stepX
        self.tip[0] += stepX
        self.tip[1] += stepZ
        moved = math.hypot(stepX, stepZ)
        self.lift += ((0.0 if want is not None else 1.0) - self.lift) * min(1.0, dt * 6.0)
        if want is not None and dt > 0.0:
            if moved > 0.02 and abs(across) > 1.0e-3:
                self.swirlSign += (_sign(across) - self.swirlSign) * min(1.0, dt * 1.5)
            wanted = min(1.0, moved / dt / 7.0)
            if wanted > self.swirl:
                self.swirl += (wanted - self.swirl) * min(1.0, dt * 2.5)
        self.swirl *= math.pow(0.5, dt / SWIRL_HALF_LIFE)
        return moved
