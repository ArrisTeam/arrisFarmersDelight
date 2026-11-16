# -*- coding: utf-8 -*-
"""PotDrift - 厨锅里浮着的料：绕圈、让勺子、互相推开、起伏摇晃、翻身、飞入（双端）

移植自 Hands-On Delight：client/PotBehavior.java 的 drift（1395-1479）、itemWakes（1482-1501）、shoulder / shift（1509-1538）、
tumble（1541-1551）、place（1554-1576）、turnToBlock 里跟着朝向转圈的那段（1283-1288），和 SceneRenderer.renderSlotItem 的平放抖动（814-820）。
到达的计时在 PotDriftArrive.py。坐标是站点像素（锅心 (8, *, 8)，+x 在画面左边），角度是度，时间是秒；转圈的角度 angle 是弧度，
x = cos(angle) * 2.2，z = sin(angle) * 2.2（相对锅心）。Mth.sin 的查表在这里用 math.sin（差在 1e-4 以内）。

用法（每帧，先 PotLiquid 再 PotSpoonMotion 最后本模块）：
    drift.step(dt, time, present, liquid.surfaceY(), spoon.throughX, spoon.throughZ, spoon.grip, spoon.swirl, spoon.swirlSign, rand)
present[i]：第 i 格有一件浮着的整料（有东西、没沉、没在演倒 / 打）。读 x / y / z（站点 px）、yaw / pitch / roll（度，Java 节点的欧拉角，
顺序 y、x、z）、scale、visible；current 交给 PotLiquid.step；events 里攒着落水等事件，读完 del drift.events[:]。
"""
import math

from .Mth import TWO_PI, clamp, lerp, wrapRadians
from .PotDriftArrive import (  # noqa: F401 - 再导出：调用方只导入 PotDrift
    ADD_FOOD_PITCH, ADD_FOOD_VOLUME, ARRIVE_ARC, ARRIVE_FROM, ARRIVE_ROLL, ARRIVE_STAGGER, ARRIVE_TIME, EVENT_LANDED, EVENT_POUR,
    LAND_RIPPLE, LAND_SPLASH, PLOP_PITCH, PLOP_PITCH_STEP, PLOP_VOLUME, Arrivals, landingEffects)

SLOTS = 6                    # 厨锅六个食材格（CookingPotStation.SLOTS）
MIDDLE = 8.0                 # 锅心在站点里的 x、z，px
DRIFT_RADIUS = 2.2           # 料绕圈的半径，px（PotBehavior.java:81）
ITEM_REST = 7.75             # 料节点的高度 8 减去沉在水下的那 0.25 px（79 行）
ITEM_LIFT = 8.0 - ITEM_REST  # 料浮在液面上方这么高，px
SPOON_RADIUS = 1.05          # 勺子（手柄）的半径，px（150 行）
ITEM_CLEARANCE = 2.1         # 料的中心离勺子穿过液面的点至少这么远，px（155 行）
ITEM_ROOM = 2.9              # 料的中心离锅心最远（每个轴），px（156 行）
ITEM_RADIUS = 1.15           # 一件料的半径，两件靠得近于 2 * 这个就互相推开（157 行）
PUSH_HALF_LIFE = 0.35        # 被推开的偏移回到原路的半衰期，秒（165 行）
CALM_DRIFT = 0.05            # 静水里圈转的速度，rad/s（199 行）；126 秒一圈
SWIRL_SPEED = 1.5            # 搅满时再加的速度，rad/s（198 行）
PLACE_EASE = 2.5             # 各件在圈上的位置、圈的起点追目标的速度，每秒（1407, 1414 行）
REST_GRIP = 0.05             # grip 小于它算勺子靠着（1404 行）
SPOON_FAR = 0.01             # 穿过点离锅心的平方超过它，圈才给勺子留空（1404 行）
TUMBLE_FROM = 0.3            # 涡流超过它，料才会翻身（160 行）
TUMBLE_RATE = 0.35           # 涡流满时每秒翻身的机会（161 行）
TUMBLE_TIME = 0.7            # 一次翻身多久，秒（162 行）
TUMBLE_HOP = 0.7             # 翻身时跳多高，px（163 行）
BOB, BOB_RATE, BOB_PHASE = 0.07, 0.9, 1.3                     # 起伏：0.07 * sin(0.9 t + 1.3 i)，px（1440 行）
ROCK, ROCK_PITCH_RATE, ROCK_ROLL_RATE = 3.0, 0.5, 0.4         # 晃：俯仰 3 sin(0.5 t + i)、翻滚 3 cos(0.4 t + i)，度（1458 行）
ITEM_WAKE = 0.7              # 整料拖出的尾迹最清楚是多少（189 行）；速度从 0.4 px/s 起、再多 1.6 px/s 满，宽 1.4 px
ITEM_WAKE_WIDTH, ITEM_WAKE_FROM, ITEM_WAKE_RANGE = 1.4, 0.4, 1.6


class PotDrift(object):
    """六格浮料的状态。输出（只读，step 之后有效）按格子下标：x / y / z、yaw / pitch / roll、scale（1 或 0）、visible、
    waiting（飞入前在等轮到，Java 这时料已经画在圈上）、wake（尾迹强度 0..0.7）；整体：current（圈转速 rad/s）、turned、events。"""

    def __init__(self, slots=SLOTS):
        self.slots = slots
        self.arrivals = Arrivals(slots)
        self.events = []
        self.turned = 0.0                 # PotBehavior.turned：圈转过的弧度，随朝向变化修正
        self.circleStart = None           # 圈的起点（弧度）：勺子靠着时留一个缺口；None = 还没见过勺子靠着
        self.current = 0.0
        self.shownFacing = None
        self.spoonX = self.spoonZ = 0.0
        self.places, self.itemX, self.itemZ = [0.0] * slots, [0.0] * slots, [0.0] * slots      # 圈上的位置、落点（相对锅心）
        self.pushX, self.pushZ, self.tumbling = [0.0] * slots, [0.0] * slots, [0.0] * slots    # 被推开的偏移、翻身进度
        self.lastX, self.lastZ, self.wakes = [0.0] * slots, [0.0] * slots, [False] * slots     # 尾迹用：上一帧的落点、itemFloating
        self.x, self.y, self.z = [MIDDLE] * slots, [0.0] * slots, [MIDDLE] * slots             # 输出：站点 px
        self.yaw, self.pitch, self.roll = [0.0] * slots, [0.0] * slots, [0.0] * slots          # 输出：度
        self.scale, self.visible, self.waiting = [0.0] * slots, [False] * slots, [False] * slots
        self.wake = [0.0] * slots
        self._buf = [0.0, 0.0, 0.0, 0.0]

    def reset(self):
        """安静地重画（场景重建）：不再有到达、翻身、待取的事件；圈的状态保留（PotBehavior.onSceneReady）。"""
        for i in range(self.slots):
            self.arrivals.clear(i)
            self.tumbling[i] = 0.0
        del self.events[:]

    def clear(self, slot):
        """第 slot 格空了：取消它的到达（PotBehavior.java:725-727）。"""
        self.arrivals.clear(slot)

    def more(self, slot, busy):
        """第 slot 格里又放进了同种的、会沉的东西：见 Arrivals.more。busy：这格的手正忙着。"""
        self.arrivals.more(slot, self.events, busy)

    def handDone(self, slot):
        """第 slot 格的手走完了：排着队的还有就再来一次，见 Arrivals.handDone。"""
        self.arrivals.handDone(slot, self.events)

    def setFacing(self, facing):
        """场景朝向变了（换了个人从另一边打开）：圈跟着反转同样的角度，料留在世界里原来的位置。facing：度。对应 PotBehavior.java:1283-1288。"""
        if facing != self.shownFacing:
            if self.shownFacing is not None:
                self.turned -= math.radians(facing - self.shownFacing)
            self.shownFacing = facing

    def arrive(self, slotList, starts=None, sinking=None):
        """一次放进了 slotList 这几格：见 Arrivals.begin。事件进 self.events。"""
        self.arrivals.begin(slotList, self.events, starts, sinking)

    def step(self, dt, time, present, surfaceY, spoonX=0.0, spoonZ=0.0, grip=0.0, swirl=0.0, swirlSign=1.0, rand=None):
        """推进一帧：到达的计时，然后圈、勺子、互相推开，最后每件的姿势。对应 PotBehavior.arrivals + drift（850-870, 1395-1479）。

        dt：秒；time：站点的钟，秒（起伏、晃用）；present：每格是否有一件浮着的整料；surfaceY：液面高度 y，px（PotLiquid.surfaceY()）；
        spoonX / spoonZ：勺子穿过液面的点，相对锅心的 px（PotSpoonMotion.throughX / throughZ）；grip、swirl、swirlSign：勺子的；
        rand：随机数 rand() -> 0..1，用来决定谁翻身（None = 不翻）。
        """
        self.arrivals.advance(dt, present, self.events)
        self.current = current = (CALM_DRIFT + swirl * SWIRL_SPEED) * swirlSign
        self.turned += dt * current
        self.spoonX, self.spoonZ = spoonX, spoonZ
        count = 0
        for i in range(self.slots):
            if present[i]:
                count += 1
        ease = min(1.0, dt * PLACE_EASE)
        if grip < REST_GRIP and spoonX * spoonX + spoonZ * spoonZ > SPOON_FAR:
            wanted = math.atan2(spoonZ, spoonX) + math.pi / max(count, 1)
            if self.circleStart is None:
                self.circleStart = wanted
            else:
                self.circleStart += wrapRadians(wanted - self.circleStart) * ease
        start = 0.0 if self.circleStart is None else self.circleStart
        rank = 0
        for i in range(self.slots):
            if present[i]:
                self.places[i] = lerp(ease, self.places[i], rank * TWO_PI / max(count, 1))
                rank += 1
                angle = self.turned + start + self.places[i]
                self._place(i, math.cos(angle) * DRIFT_RADIUS, math.sin(angle) * DRIFT_RADIUS, dt)
        self._shoulder(present)
        self._wakes(dt, present)
        self._poses(dt, time, present, surfaceY + ITEM_LIFT, start, swirl, rand)

    def _place(self, index, x, z, dt):
        """一件料落在哪：圈上的位置加上被推开的偏移，不进勺子 2.1 px 内，也不出 +-2.9 px 的方框。对应 place（1554-1576）。"""
        settle = 0.5 ** (dt / PUSH_HALF_LIFE)
        self.pushX[index] *= settle
        self.pushZ[index] *= settle
        px = x + self.pushX[index]
        pz = z + self.pushZ[index]
        for _ in (0, 1):
            dx = px - self.spoonX
            dz = pz - self.spoonZ
            away = math.hypot(dx, dz)
            if away < ITEM_CLEARANCE:
                out = ITEM_CLEARANCE / max(away, 0.01)
                px = self.spoonX + dx * out
                pz = self.spoonZ + dz * out
            px = clamp(px, -ITEM_ROOM, ITEM_ROOM)
            pz = clamp(pz, -ITEM_ROOM, ITEM_ROOM)
        self.pushX[index] = px - x
        self.pushZ[index] = pz - z
        self.itemX[index] = px
        self.itemZ[index] = pz

    def _shoulder(self, present):
        """两件靠得近于 2 * 1.15 px 就各让一半，做两遍（shoulder，1509-1529）。"""
        for _ in (0, 1):
            for i in range(self.slots):
                if not present[i]:
                    continue
                for j in range(i + 1, self.slots):
                    if not present[j]:
                        continue
                    dx = self.itemX[j] - self.itemX[i]
                    dz = self.itemZ[j] - self.itemZ[i]
                    apart = math.hypot(dx, dz)
                    if apart < ITEM_RADIUS * 2.0:
                        nx = dx / apart if apart > 0.001 else math.cos(i + j)
                        nz = dz / apart if apart > 0.001 else math.sin(i + j)
                        move = (ITEM_RADIUS * 2.0 - apart) / 2.0
                        self._shift(i, -nx * move, -nz * move)
                        self._shift(j, nx * move, nz * move)

    def _shift(self, index, x, z):
        """把一件料挪一下，不出方框，挪了多少记进被推开的偏移（shift，1531-1538）。"""
        nx = clamp(self.itemX[index] + x, -ITEM_ROOM, ITEM_ROOM)
        nz = clamp(self.itemZ[index] + z, -ITEM_ROOM, ITEM_ROOM)
        self.pushX[index] += nx - self.itemX[index]
        self.pushZ[index] += nz - self.itemZ[index]
        self.itemX[index] = nx
        self.itemZ[index] = nz

    def _wakes(self, dt, present):
        """整料拖尾迹：越快越清楚，静水上没有；飞入中的不算（itemWakes，1482-1501）。结果在 wake[i]（0 = 没有）。"""
        for i in range(self.slots):
            self.wake[i] = 0.0
            if not present[i] or self.arrivals.arriving[i]:
                self.wakes[i] = False
                continue
            if self.wakes[i] and dt > 0.0:
                speed = math.hypot(self.itemX[i] - self.lastX[i], self.itemZ[i] - self.lastZ[i]) / dt
                self.wake[i] = max(0.0, ITEM_WAKE * min(1.0, (speed - ITEM_WAKE_FROM) / ITEM_WAKE_RANGE))
            self.lastX[i] = self.itemX[i]
            self.lastZ[i] = self.itemZ[i]
            self.wakes[i] = True

    def _tumble(self, index, dt, swirl, rand):
        """一件料翻身翻到哪了 0..1：涡流够强时偶尔翻一个，翻 0.7 秒（tumble，1541-1551）。"""
        phase = self.tumbling[index]
        if phase > 0.0:
            phase += dt / TUMBLE_TIME
            if phase >= 1.0:
                phase = 0.0
            self.tumbling[index] = phase
        elif swirl > TUMBLE_FROM and rand is not None and rand() < dt * TUMBLE_RATE * swirl:
            phase = self.tumbling[index] = 0.001
        return phase

    def _poses(self, dt, time, present, base, start, swirl, rand):
        """每件的位置与姿势（drift 的第二个循环，1421-1459）：高度 = 液面 + 0.25 + 起伏 + 翻身的跳，飞入中改用弧线。"""
        buf = self._buf
        for i in range(self.slots):
            if not present[i]:
                self.visible[i] = False
                self.scale[i] = 0.0
                self.waiting[i] = False
                continue
            angle = self.turned + start + self.places[i]
            roll = self._tumble(i, dt, swirl, rand)
            over = roll * roll * (3.0 - 2.0 * roll) * 360.0
            x = self.itemX[i]
            y = math.sin(time * BOB_RATE + i * BOB_PHASE) * BOB + math.sin(roll * math.pi) * TUMBLE_HOP
            z = self.itemZ[i]
            if self.arrivals.flying(i):
                self.arrivals.blend(i, x, y, z, buf)
                x, y, z = buf[0], buf[1], buf[2]
                over += buf[3]
            self.x[i] = MIDDLE + x
            self.y[i] = base + y
            self.z[i] = MIDDLE + z
            self.yaw[i] = (-math.degrees(angle) + 180.0) % 360.0 - 180.0
            self.pitch[i] = math.sin(time * ROCK_PITCH_RATE + i) * ROCK + over
            self.roll[i] = math.cos(time * ROCK_ROLL_RATE + i) * ROCK
            self.visible[i] = True
            self.scale[i] = 1.0
            self.waiting[i] = self.arrivals.waiting(i)
