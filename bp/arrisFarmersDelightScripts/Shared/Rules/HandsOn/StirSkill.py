# -*- coding: utf-8 -*-
"""StirSkill - 搅锅评星：按勺尖轨迹给 0-3 星（双端）

移植自 Hands-On Delight 的 station/StirSkill.java。服务端按勺尖位置判分，客户端预测用同一份。
宽圈、稳速、同向的搅拌把星星涨满；绕中心打转、来回抖动、手速忽快忽慢会拉低；勺子停下星星会掉。
只有厨师做过这道菜换来的"开放星数"(openStars，见 PotBonus.openStars)以内的星星能涨。

时间一律是秒（原版以刻计，20 刻/秒），勺尖坐标 x、z 取 -1..1（占勺子能到的范围）。

厨师的钟(at)：客户端每次出手随包带上自己的时钟。包会被网络攒成一批到达，服务器自己也可能掉刻，
所以手速按厨师的钟判；但钟每次最多比服务器的钟多走 SLACK 秒，同一服务器时刻到的包共享这份余量，
灌一堆包也不会让星星涨得更快。服务器自己的时刻仍然决定"勺子是不是停了"。
"""
import math

from .Mth import EPS, NEVER, clamp, isFinite, lerp, sign, wrapRadians, floorInt

MOST = 3.0               # 星星上限
RISE = 0.75              # 星/秒：评分高于当前星数时的上升速度
FALL = 0.5               # 星/秒：评分低于当前星数时的下降速度
DRAIN = 0.75             # 星/秒：勺子停住（过了 GRACE）之后每秒掉的星
GRACE = 0.5              # 原 10 刻：停手后先喘一口气，再开始掉星
WINDOW = 0.25            # 原 5 刻：一段笔画攒够这么久评一次分
BREAK = 0.6              # 原 12 刻：停得比这久，下一段笔画重新开始
SLACK = 0.5              # 原 10 刻：厨师的钟一次最多比服务器的钟多走这么多
NARROW = 0.3             # 离中心不到这个比例算窄圈（宽度分为 0）
WIDE = 0.7               # 离中心超过这个比例算宽圈（宽度分满）
SLOWEST = 1.2            # rad/s：慢于此不得分
SLOW = 3.0               # rad/s：SLOWEST..SLOW 线性爬升，SLOW..FAST 满分
FAST = 13.0              # rad/s
FASTEST = 22.0           # rad/s：FAST..FASTEST 线性下降，快于此不得分
ENOUGH = 0.8             # 质量到 0.8 就算满三星：没人能搅得完美
MIN_RADIUS = 0.15        # 勺尖离中心近于此，这一步不计转角
TURN_NOISE = 0.05        # rad：小于此的转角不算转向（不触发"来回抖"）
STEADY_FREE = 0.2        # 手速变化在此以内（ln 比值）不扣稳定分
STEADY_SPAN = 0.9        # 再多出这么多 ln 比值，稳定分扣到 0
PACE_BLEND = 0.4         # 手速基准每段向新手速靠拢的比例


def clampSpoon(value):
    """服务端对勺尖坐标的清洗：非有限值按中心 0，否则夹进 -1..1（PotLogic.spoon）。"""
    return clamp(value, -1.0, 1.0) if isFinite(value) else 0.0


def _logRatio(speed, pace):
    """|ln(speed / pace)|；基准为 0（上一段没转）时比值无穷大。"""
    if pace <= 0.0:
        return float("inf")
    ratio = speed / pace
    return abs(math.log(ratio)) if ratio > 0.0 else float("inf")


class StirSkill(object):
    """一口锅当前的搅拌星级。move() 喂勺尖位置，stars()/grade() 读星数。"""

    def __init__(self):
        self._stars = 0.0
        self._open = 1
        self._settled = 0.0          # 最近一次 move 的服务器时刻
        self._lastMove = NEVER
        self._lastX = 0.0
        self._lastZ = 0.0
        self._windowStart = 0.0      # 当前笔画窗口的起点（厨师的钟）
        self._lastAt = None          # 厨师的钟（None = 还没有，对应 Java 的 NaN）
        self._lastAtRaw = 0.0        # 客户端上报的原始钟
        self._lastAtServer = 0.0     # 上一包到达时的服务器时刻
        self._allowance = 0.0        # 在当前服务器时刻里，钟还能再多走的余量
        self._turned = 0.0           # 本窗口累计转角（带符号，rad）
        self._wideness = 0.0
        self._steps = 0
        self._shook = False          # 本窗口内来回抖过
        self._way = 0                # 转圈方向：-1 / 0 / 1
        self._pace = None            # 最近几段的手速（rad/s）；None = 还没有

    def stars(self, now):
        """now 时刻的星数（含停手后的衰减）。"""
        idle = now - max(self._lastMove + GRACE, self._settled)
        if idle > EPS:
            return max(0.0, self._stars - DRAIN * idle)
        return self._stars

    def grade(self, now):
        """整星数：此刻出锅按几星算奖励。"""
        return floorInt(self.stars(now) + 1.0e-4)

    def move(self, now, x, z, cooking, openStars, at=None):
        """勺尖在 (x, z)。now 为服务器时刻；at 为厨师的钟（None = 没有，用服务器的）。

        只有锅在煮(cooking)时才攒星；至多 openStars 颗星能涨。
        """
        x = clampSpoon(x)
        z = clampSpoon(z)
        if at is not None and not isFinite(at):
            at = None
        stopped = now - self._lastMove > BREAK + EPS
        clock = self._tick(now, at, stopped)
        self._lastAtRaw = clock if at is None else at
        self._lastAt = clock
        self._lastAtServer = now
        self._open = openStars
        self._stars = min(openStars, self.stars(now))
        self._settled = now
        if stopped:
            self._startStroke(clock)
            self._pace = None
        else:
            self._follow(x, z)
            if clock - self._windowStart >= WINDOW - EPS:
                self._judge(clock, cooking)
        self._lastMove = now
        self._lastX = x
        self._lastZ = z

    def _tick(self, now, at, stopped):
        """厨师的钟走到哪：按上报的钟走，但不超过余量；断了或没钟就跟着服务器走。"""
        if at is None or self._lastAt is None or stopped:
            self._allowance = SLACK
            return now if self._lastAt is None else self._lastAt + (now - self._lastAtServer)
        if abs(now - self._lastAtServer) > EPS:
            self._allowance = (now - self._lastAtServer) + SLACK
        step = clamp(at - self._lastAtRaw, 0.0, self._allowance)
        self._allowance -= step
        return self._lastAt + step

    def _follow(self, x, z):
        """这一步勺尖转了多少角、离中心多远；来回抖会被记下。"""
        radius = min(math.hypot(x, z), math.hypot(self._lastX, self._lastZ))
        if radius > MIN_RADIUS:
            step = wrapRadians(math.atan2(z, x) - math.atan2(self._lastZ, self._lastX))
            if abs(step) > TURN_NOISE and abs(self._turned) > TURN_NOISE and sign(step) != sign(self._turned):
                self._shook = True
            self._turned += step
        self._wideness += clamp((radius - NARROW) / (WIDE - NARROW), 0.0, 1.0)
        self._steps += 1

    def _judge(self, now, cooking):
        """评一段笔画：手速、稳定、同向、宽度相乘成质量，再让星数往质量对应的值靠。"""
        seconds = now - self._windowStart
        speed = abs(self._turned) / seconds
        if speed < SLOW:
            pacing = (speed - SLOWEST) / (SLOW - SLOWEST)
        else:
            pacing = (FASTEST - speed) / (FASTEST - FAST)
        change = 0.0 if self._pace is None or speed <= 0.0 else _logRatio(speed, self._pace)
        steady = 1.0 - max(0.0, change - STEADY_FREE) / STEADY_SPAN
        oneWay = not self._shook and (self._way == 0 or sign(self._turned) == self._way)
        quality = 0.0
        if oneWay:
            quality = clamp(pacing, 0.0, 1.0) * clamp(steady, 0.0, 1.0) * self._wideness / self._steps
        if cooking:
            worth = min(self._open, MOST * min(1.0, quality / ENOUGH))
            if worth > self._stars:
                self._stars = min(worth, self._stars + RISE * seconds)
            else:
                self._stars = max(worth, self._stars - FALL * seconds)
        if abs(self._turned) > 0.1:
            self._way = sign(self._turned)
        self._pace = speed if self._pace is None else lerp(PACE_BLEND, self._pace, speed)
        self._startStroke(now)

    def _startStroke(self, now):
        self._windowStart = now
        self._turned = 0.0
        self._wideness = 0.0
        self._steps = 0
        self._shook = False


def runSamples(samples, cooking=True, openStars=3):
    """把 [(t, x, z)] 或 [(t, x, z, at)] 依次喂给一个新的 StirSkill 并返回它（t、at 单位秒）。"""
    skill = StirSkill()
    for sample in samples:
        skill.move(sample[0], sample[1], sample[2], cooking, openStars, sample[3] if len(sample) > 3 else None)
    return skill


def scoreSamples(samples, cooking=True, openStars=3, endTime=None):
    """一串勺尖采样的评分：返回 (星数, 整星数)，endTime 默认取最后一个采样的时刻。"""
    skill = runSamples(samples, cooking, openStars)
    if endTime is None:
        endTime = samples[-1][0] if samples else 0.0
    return skill.stars(endTime), skill.grade(endTime)
