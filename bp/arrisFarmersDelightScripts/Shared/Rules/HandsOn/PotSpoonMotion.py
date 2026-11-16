# -*- coding: utf-8 -*-
"""PotSpoonMotion - 厨锅勺子的动作：跟手、跟同步、回位、倾斜、搅出的涡流、水波与上报节奏（双端）

移植自 Hands-On Delight：client/PotBehavior.java 的 moveSpoon（1292-1346）、stirEffects（1349-1372）、pose（1375-1392）
与 onEvent 里的点按 / 拖动判定（466-488）。姿势数学在 PotSpoonPose.py（这里再导出一份，调用方只导入本模块）。

坐标：勺尖 (tipX, tipZ) 是"锅局部"（见 PotSpoonPose），px，离锅心；穿过液面的点 (throughX, throughZ) 和水波的位置是场景里相对锅心的
px（锅局部绕 y 转 turn 度，turn 默认 0）。控件 spoon_x / spoon_z 与上报的 x / z 都是 -1..1 的"勺尖偏移 / 勺子够得到的范围 2.3 px"，
也在锅局部里——线上若是世界对齐的，进出时用 toLocal / toScene 换算。时间是秒；Java 的钟用刻（time * 20），上报的钟这里给秒。

用法（每帧）：先 gesture.down/up 管点按、拖动；然后
    spoon.step(dt, time, hand, stirred, aim, synced, surfaceY, turn)
读 tipX / tipZ / grip / swirl / swirlSign / throughX / throughZ（交给 PotDrift）、axis*（手柄方向）、rot / euler() / offset() / matrix()
（驱动勺子模型）、pickAabb()（点它）；ripple / furrow / send 是本帧的一次性标志，附带的位置和载荷在 ripple* / furrow* / send*。
"""
import math

from .Mth import lerp
from .PotSpoonPose import (  # noqa: F401 - 再导出：调用方只导入 PotSpoonMotion
    PICK_HI, PICK_LO, REST_LEAN, SPOON_END, SPOON_REACH, STIR_LEAN, alignMatrix, eulerYXZ, leanSlopes, nodeOffset, pickAabb,
    pickMatrix, restSlope, throughPoint, toLocal, toScene)

SPOON_CLICK = 0.3            # 比这短的一按算"点"：勺子留在手里，下一次点才放下（PotBehavior.java:75）
HAND_MEMORY = 2.5            # 松手后这么久里勺子还算自己的，停在松手处，秒（PotBehavior.java:167）
SPOON_HOME_EASE = 0.6        # 没人管了，勺子要这么久才起步，秒（PotBehavior.java:152）
SPOON_HOME_RATE = 1.8        # 回位的跟随速度（乘 homing）（PotBehavior.java:153）
SPOON_HOME_GRIP = 2.0        # 回位时 grip 往 0 走的速度（乘 homing）（PotBehavior.java:154）
HAND_FOLLOW = 18.0           # 勺尖跟手的速度，每秒（PotBehavior.java:1324）
FOLLOW = 9.0                 # 勺尖跟同步来的位置的速度，每秒（PotBehavior.java:1324）
GRIP_RATE = 7.0              # grip 往 1 走的速度，每秒（PotBehavior.java:1323）
IN_SOUP = 0.5                # grip 超过它算勺子在汤里（PotBehavior.java:1332）
SWIRL_HALF_LIFE = 0.9        # 涡流散掉的半衰期，秒（PotBehavior.java:187）
SWIRL_SPEED = 7.0            # 勺尖每秒走这么多 px 就搅满（moved / dt / 7，PotBehavior.java:1338）
SWIRL_RISE = 2.5             # 涡流只往上涨，每秒追目标的速度（PotBehavior.java:1341）
SWIRL_SIGN_RATE = 1.5        # 转向的符号每秒追叉积符号的速度（PotBehavior.java:1336）
SWIRL_SIGN_MOVED = 0.02      # 这一帧挪了多远才改转向，px（PotBehavior.java:1335）
SWIRL_SIGN_ACROSS = 1.0e-3   # 叉积够大才改转向（PotBehavior.java:1335）
RIPPLE_INTERVAL = 0.09       # 勺尖搅出水波的间隔，秒（PotBehavior.java:171）
RIPPLE_STRENGTH = 0.17       # 水波高度，px（PotBehavior.java:172）
RIPPLE_MOVED = 0.01          # 这一帧挪了多远才起水波，px（PotBehavior.java:1354）
FURROW_MOVED = 0.005         # 这一帧挪了多远才拖出尾迹，px（PotBehavior.java:1350）
SEND_INTERVAL = 0.12         # 勺尖报给服务端的最短间隔，秒（PotBehavior.java:169）
SEND_TRAVEL = 0.2            # 两次上报之间至少挪这么远，px（PotBehavior.java:170）


class SpoonGesture(object):
    """勺子的点按 / 拖动判定：按住拖动搅，一按一松不到 0.3 秒算"点"，勺子留在手里随鼠标搅，下一次按下放下。

    对应 PotBehavior.onEvent 的 Stroke（466-488）与 FocusInput.press 里"留在手里的笔画被下一次按下结束"（360-363）。
    stroking 就是 PotBehavior.stroking，和"镜头在锅前"一起决定 step 的 hand。
    """

    def __init__(self):
        self.stroking = False
        self.heldByClick = False
        self.strokeStart = 0.0

    def reset(self):
        """关站：放下勺子（PotBehavior.onClose，451-457）。"""
        self.stroking = False
        self.heldByClick = False

    def down(self, time):
        """在勺子上按下。返回 True = 拿起勺子（开始一笔）；False = 这一按把手里的勺子放下了。time：秒。"""
        if self.heldByClick:
            self.heldByClick = False
            self.stroking = False
            return False
        self.stroking = True
        self.strokeStart = time
        return True

    def up(self, time):
        """抬起。返回 True = 这是一次"点"，勺子留在手里（Java 的 view.holdStroke()），笔画继续；False = 笔画结束（或本来就没在搅）。"""
        if not self.stroking or self.heldByClick:
            return False
        if time - self.strokeStart < SPOON_CLICK:
            self.heldByClick = True
            return True
        self.stroking = False
        return False


class PotSpoonMotion(object):
    """一把勺子的动作状态。属性（只读，step 之后有效）见模块说明；另有 homing（回位进度 0..1）、moved（本帧勺尖走了多远 px）、
    leanX / leanZ（手柄每升 1 px 的偏移）。"""

    def __init__(self, reach=SPOON_REACH, restLean=REST_LEAN, spoonEnd=SPOON_END):
        self.reach = reach
        self.restLean = restLean
        self.spoonEnd = spoonEnd
        self.tipX = self.tipZ = 0.0
        self.grip = self.homing = self.swirl = self.moved = 0.0
        self.swirlSign = 1.0
        self.handLeft = self.rippleClock = self.sendClock = self.sendTravel = 0.0
        self.leanX = restSlope(restLean)
        self.leanZ = 0.0
        self.axisX = self.axisY = self.axisZ = 0.0
        self.rot = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]       # 勺子模型要加的旋转：从静止的手柄方向转到现在的方向
        self.throughX = self.throughZ = 0.0
        self.ripple = self.furrow = self.send = False
        self.rippleX = self.rippleZ = self.furrowX = self.furrowZ = 0.0
        self.sendX = self.sendZ = self.sendAt = 0.0
        self._pose(5.77, 0.0)

    def step(self, dt, time, hand, stirred, aim=None, synced=None, surfaceY=5.77, turn=0.0):
        """推进一帧。对应 PotBehavior.moveSpoon（1292-1346）。

        dt：帧间隔，秒；time：站点的钟，秒（只用来给上报盖章）；hand：本人握着勺子（SpoonGesture.stroking 且镜头在锅前）；
        stirred：锅算被搅着（控件 stirring）；aim：光标在液面那一层上的点，锅局部 (x, z) px，没有（射线没打到）给 None；
        synced：控件 spoon_x / spoon_z（-1..1，锅局部）；surfaceY：液面高度 y，px（PotLiquid.surfaceY()）；turn：见模块说明。
        """
        wantX = wantZ = 0.0
        if hand:
            if aim is not None:
                distance = math.hypot(aim[0], aim[1])
                shorter = self.reach / distance if distance > self.reach else 1.0
                wantX, wantZ = aim[0] * shorter, aim[1] * shorter
            self.handLeft = HAND_MEMORY
        elif stirred and self.handLeft > 0.0:
            wantX, wantZ = self.tipX, self.tipZ
        elif stirred and synced is not None:
            wantX, wantZ = synced[0] * self.reach, synced[1] * self.reach
        self.handLeft -= dt
        goingHome = not hand and not stirred
        self.homing = min(1.0, self.homing + dt / SPOON_HOME_EASE) if goingHome else 0.0
        gripRate = SPOON_HOME_GRIP * self.homing if goingHome else GRIP_RATE
        self.grip = lerp(min(1.0, dt * gripRate), self.grip, 0.0 if goingHome else 1.0)
        rate = HAND_FOLLOW if hand else (SPOON_HOME_RATE * self.homing if goingHome else FOLLOW)
        follow = 1.0 - math.exp(-dt * rate)
        stepX = (wantX - self.tipX) * follow
        stepZ = (wantZ - self.tipZ) * follow
        across = self.tipX * stepZ - self.tipZ * stepX          # 往哪边转：绕锅心的叉积符号
        self.tipX += stepX
        self.tipZ += stepZ
        moved = self.moved = math.hypot(stepX, stepZ)
        self.ripple = self.furrow = self.send = False
        if self.grip > IN_SOUP and dt > 0.0:
            if moved > SWIRL_SIGN_MOVED and abs(across) > SWIRL_SIGN_ACROSS:
                self.swirlSign = lerp(min(1.0, dt * SWIRL_SIGN_RATE), self.swirlSign, 1.0 if across > 0.0 else -1.0)
            wanted = min(1.0, moved / dt / SWIRL_SPEED)
            if wanted > self.swirl:
                self.swirl = lerp(min(1.0, dt * SWIRL_RISE), self.swirl, wanted)
            self._effects(dt, time, moved, hand, turn)
        self.swirl *= 0.5 ** (dt / SWIRL_HALF_LIFE)
        self._pose(surfaceY, turn)

    def _effects(self, dt, time, moved, hand, turn):
        """勺子在汤里挪动时的一次性效果：尾迹、水波、上报（PotBehavior.stirEffects，1349-1372）。"""
        if moved > FURROW_MOVED:
            self.furrow = True
            self.furrowX, self.furrowZ = self.throughX, self.throughZ      # 用的是上一帧的穿过点（pose 在后面）
        self.rippleClock -= dt
        if moved > RIPPLE_MOVED and self.rippleClock <= 0.0:
            self.rippleClock = RIPPLE_INTERVAL
            self.ripple = True
            self.rippleX, self.rippleZ = toScene(self.tipX, self.tipZ, turn)
        if hand:
            self.sendClock -= dt
            self.sendTravel += moved
            if self.sendClock <= 0.0 and self.sendTravel >= SEND_TRAVEL:
                self.sendClock = SEND_INTERVAL
                self.sendTravel = 0.0
                self.send = True
                self.sendX, self.sendZ, self.sendAt = self.tipX / self.reach, self.tipZ / self.reach, time

    def _pose(self, surfaceY, turn):
        """手柄的方向、模型的旋转、穿过液面的点（PotBehavior.pose，1375-1392）。"""
        rest = restSlope(self.restLean)
        self.leanX, self.leanZ = leanSlopes(self.tipX, self.tipZ, self.grip, self.restLean, self.reach)
        restNorm = math.sqrt(rest * rest + 1.0)
        norm = math.sqrt(self.leanX * self.leanX + 1.0 + self.leanZ * self.leanZ)
        self.axisX, self.axisY, self.axisZ = self.leanX / norm, 1.0 / norm, self.leanZ / norm
        alignMatrix(self.rot, rest / restNorm, 1.0 / restNorm, 0.0, self.axisX, self.axisY, self.axisZ)
        self.throughX, self.throughZ = throughPoint(self.tipX, self.tipZ, self.leanX, self.leanZ, surfaceY, turn, self.spoonEnd)

    def euler(self):
        """勺子节点的旋转 (x 俯仰, y 偏航, z 翻滚)，度，顺序 y、x、z：Java 里 rotateTo 吃的三个角（PotBehavior.java:1383, 1386）。"""
        return eulerYXZ(self.rot)

    def offset(self):
        """勺子节点要平移的量 (x, y, z)，px，锅局部：使勺尖落在 (tipX, spoonEnd, tipZ)（PotBehavior.java:1385）。"""
        return nodeOffset(self.rot, self.tipX, self.tipZ, self.spoonEnd)

    def matrix(self):
        """勺子节点 -> 锅局部的 3x4 列主序矩阵（12 元，见 PotSpoonPose.pickMatrix）。"""
        return pickMatrix(self.rot, self.offset())

    def pickAabb(self):
        """手柄拾取盒现在在锅局部的轴对齐包围盒 ((x0, y0, z0), (x1, y1, z1))；静止时正好是 [2.6,11.5,-1.5]-[6.6,16,1.5]。"""
        return pickAabb(self.rot, self.offset())
