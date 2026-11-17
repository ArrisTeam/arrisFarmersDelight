# -*- coding: utf-8 -*-
"""SkilletHandRules - 手持煎锅烹饪的规则：右键按住状态（客户端报、服务端记）、一次烹饪的计时、滋滋声的概率（双端，纯规则）

JE 的手持烹饪靠"按住使用"（startUsingItem，用满 getUseDuration 刻才算做好，中途松手什么都不发生）。基岩版没有这样的服务端事件，
所以由客户端报告右键的按住：按下时报一次、按住期间每 HOLD_BEAT 秒报一次、松开报一次（Client/Input.py 的 HoldReporter）；
服务端按最后一次"按着"的时间判断还按不按着（HoldTracker），太久没消息就当松手了（掉线、开界面时没发松开事件）。

哪只手拿煎锅（skilletHand）：JE 的 SkilletItem.use 两只手都认——煎锅在哪只手，原料就在另一只手。基岩版的副手只收引擎允许的那几种物品
（盾、图腾、地图、箭……），生肉放不进去（实测 SetEntityItem(OFFHAND, 生牛肉) 返回 False），所以这边常用的是反过来拿：
煎锅放副手（物品 JSON 开了 netease:allow_offhand）、原料拿主手。这时在热源旁按住右键是煎不是吃（JE 里饿着的时候主手的食物会先被吃掉，
这里改成有热源就煎——不然基岩版饿着就没法手持煎东西了；由客户端 Client/Input.py 在 ClientItemTryUseEvent 里取消"吃"）。
"""
TICKS_PER_SECOND = 20
HOLD_BEAT = 0.2
HOLD_TIMEOUT = 0.8
# JE onUseTick：每刻 1/50 的概率播一声滋滋
SIZZLE_PER_TICK = 1.0 / 50
# JE 的翻面（SkilletItem.FLIP_TIME = 12，ModNetworking.FlipSkilletMessage 记 FlipTimeStamp，onUseTick 里 gameTime - 记号 > 12 才翻）：点一下左键，过 13 刻（0.65 秒）
# 翻一次、响一声下料（BLOCK_SKILLET_ADD_FOOD，音量 0.4，音调 0.9 ~ 1.1），翻的过程中再点不算
FLIP_SECONDS = 13.0 / TICKS_PER_SECOND
FLIP_VOLUME = 0.4
FLIP_PITCH = (0.9, 0.2)


MAIN, OFF = "main", "off"


def skilletHand(mainName, offName, skilletName):
    """煎锅在哪只手：MAIN / OFF（主手优先，JE 先试主手的物品）；两只手都没拿返回 None。原料在另一只手。"""
    if mainName == skilletName:
        return MAIN
    if offName == skilletName:
        return OFF
    return None


def cooksInsteadOfEating(mainName, offName, skilletName, cookable, nearHeat):
    """主手这件东西右键时该不该取消"吃"、改成煎：副手是煎锅、主手是有营火配方的原料、身边有热源。"""
    return skilletHand(mainName, offName, skilletName) == OFF and bool(cookable) and bool(nearHeat)


def flipPitch(roll):
    """翻面那一声下料的音调：roll 是 [0, 1) 的随机数（JE 的 random.nextFloat() * 0.2F + 0.9F）。"""
    return FLIP_PITCH[0] + roll * FLIP_PITCH[1]


def sizzleChance(seconds):
    """seconds 秒里至少响一声滋滋的概率（每刻 1/50 逐刻累计）。"""
    return 1.0 - (1.0 - SIZZLE_PER_TICK) ** (seconds * TICKS_PER_SECOND)


class HoldReporter(object):
    """客户端的右键按住上报：决定什么时候给服务端发 held。每个方法返回要发的值（True 按着 / False 松开），None 是什么都不用发。

    只在手里（主手或副手）拿着煎锅时报告（别的物品用不着）；按住期间手里换了东西，到下一次该报告时报一次松开。
    tick 每帧都会调，carrying 传个函数，到点了才去问手里拿的什么（客户端的引擎调用不用每帧都跑）。
    """

    def __init__(self):
        self.down = False
        self._last = 0.0

    def press(self, now, carrying):
        if not carrying:
            return None
        self.down, self._last = True, now
        return True

    def release(self):
        if not self.down:
            return None
        self.down = False
        return False

    def tick(self, now, carrying):
        if not self.down or now - self._last < HOLD_BEAT:
            return None
        self._last = now
        if not carrying():
            self.down = False
            return False
        return True


class HoldTracker(object):
    """服务端：各玩家的右键按住状态。收到"按着"就记下时间，收到"松开"就清掉；太久没消息也算松开。"""

    def __init__(self):
        self._beat = {}

    def beat(self, playerId, now):
        self._beat[playerId] = now

    def release(self, playerId):
        self._beat.pop(playerId, None)

    def held(self, playerId, now):
        last = self._beat.get(playerId)
        return last is not None and now - last <= HOLD_TIMEOUT


class HandCook(object):
    """一次手持烹饪：从开始起 seconds 秒做好一件 food -> result（JE：按住 getUseDuration 刻，煎一件）。flipping 是正在翻面（JE 的 FlipTimeStamp 记着）。"""
    __slots__ = ("food", "result", "seconds", "started", "flipping")

    def __init__(self, food, result, seconds, now):
        self.food = food
        self.result = result
        self.seconds = seconds
        self.started = now
        self.flipping = False

    def finished(self, now):
        return now - self.started >= self.seconds
