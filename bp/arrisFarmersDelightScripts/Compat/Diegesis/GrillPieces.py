# -*- coding: utf-8 -*-
"""GrillPieces - 开着炉灶站点的人看到的烤架：六件食物、落下 / 翻面 / 取走 / 弹回的动作、热气蒸汽烟和声音（客户端）

对应 Hands-On Delight：client/StoveBehavior.java 的 refresh / draw / turned / taken / onEffect / heat。状态来自站点
（grill 槽组里是什么，data 里 down / up / hand 是每件两面烤到哪了、是不是手放的），动作的数学在 Shared/Rules/HandsOn/StoveMotion.py，
热气的日程在 StoveFx.py，这里只把它们接到前置包的客户端道具（view.props，客户端掉落物）和粒子声音（GrillFx.py）上：
- 每件一个道具，平躺在烤位上，每件朝向不同；朝上那面熟了画熟的图，否则画生的（掉落物不能染色，JE 的焦色染不了）；
- 一件新放上来：从上面落下带一跳，落地冒汽、嗞一声；一次放好几件（Shift 点托盘、拿着一叠点烤架）从屏幕下沿飞来，一件接一件；
- 点一件翻面：跳起 3 px、转到立起来、换成另一面的样子、转回来落下；别人翻的也这么演（服务端发 turned），自己翻的不重复；
- 取走：虚影升起缩没（GrillGhosts）；放不上去：虚影从上面落下往后弹开；
- 点着的烤架：在烤的冒蒸汽、该翻的冒烟，嗞嗞声（热浪暂缺）。
放上去、取下、烤好的"叮"这几声，世界里的广播（服务端的 ToAllPlayerPlaySound）已经有了，这里不重复。
"""
import random

from . import GrillFx
from .GrillGhosts import Ghosts
from ...Shared.Rules import GrillStation as Rules
from ...Shared.Rules.HandsOn import StoveFx, StoveLayout, StoveLook, StoveMotion

PLACES = StoveLayout.PLACES
SCALE = StoveLayout.SIZE / 8.0       # 一件 5 像素宽（客户端掉落物缩放 1 时边长 8 像素）
GRACE = 0.1                          # 朝上那面的样子变了、又没见到翻面的效果：等这么久再重画（前置包先发状态、后发表现事件）


def _one(name, aux=0):
    return {"newItemName": name, "newAuxValue": aux or 0, "count": 1}


def _same(a, b):
    """两个物品字典是同一种（None = 空）。"""
    if a is None or b is None:
        return a is None and b is None
    return a.get("newItemName") == b.get("newItemName") and (a.get("newAuxValue") or 0) == (b.get("newAuxValue") or 0)


class Pieces(object):
    """一个打开着的炉灶站点的烤架。space 是 GrillSpace.Space。"""

    def __init__(self, view, space):
        self.view, self.space = view, space
        self.clock = 0.0
        self.began = False                                   # 第一帧过了没有（镜头到位之后才有帧）
        self.shown = [None] * PLACES                         # 每个位置现在画的是什么（JE 的 shown）
        self.up = [-1.0] * PLACES                            # 画的时候朝上那面烤到哪（shownUp），-1 = 没画过
        self.heldUntil = [0.0] * PLACES                      # 翻到一半之前沿用画着的 up，不用服务端发来的
        self.turnedAt = [-10.0] * PLACES
        self.newUp = [0.0] * PLACES                          # 这一翻翻过来之后朝上那面的进度
        self.settleAt = [0.0] * PLACES                       # 朝上那面的样子变了、等到这时还没有翻面的效果就重画（0 = 没在等）
        self.yaws = [StoveLayout.yawOf(place) + view.yaw for place in range(PLACES)]        # 世界里的朝向换到站点空间（站点按玩家所在的一侧转）
        self.motion = [StoveMotion.Piece(yaw) for yaw in self.yaws]
        self.props = [None] * PLACES                         # (物品名 key, 道具)
        self.last = [None] * PLACES
        self.ghosts = Ghosts(view, SCALE)
        self.heat = StoveFx.Heat(random.random)
        self.pending = []                                    # 开站时一起摆上来的位置：第一帧起从玩家那边飞来
        self.quiet = True                                    # 站点刚开：已经在烤架上的不演落下

    def datum(self, key, place, default=0.0):
        values = self.view.data.get(key)
        return values[place] if isinstance(values, list) and place < len(values) else default

    def free(self):
        return [self.view.state.getItem((Rules.GROUP_GRILL, place)) is None for place in range(PLACES)]

    # ---------------------------------------------------------------- 状态 -> 画面

    def refresh(self):
        """六件照站点的状态：换了东西或朝上那面熟了一档就重画，新来的演落下（StoveBehavior.refresh）。"""
        state = self.view.state
        nows = [state.getItem((Rules.GROUP_GRILL, place)) for place in range(PLACES)]
        arriving = [place for place in range(PLACES) if self.shown[place] is None and nows[place] is not None]
        together = len(arriving) > 1 and not self.quiet
        landing = 0
        for place in range(PLACES):
            now = nows[place]
            up = self.up[place] if self.clock < self.heldUntil[place] else self.datum("up", place)
            if _same(now, self.shown[place]):
                if StoveLook.look(up) == StoveLook.look(self.up[place]):
                    self.settleAt[place] = 0.0
                    continue
                if self.shown[place] is not None and self._waits(place):
                    continue
            self.settleAt[place] = 0.0
            arrives = self.shown[place] is None and now is not None
            self.shown[place] = dict(now) if now else None
            self.up[place] = up
            if arrives and not self.quiet:
                delay = landing * StoveMotion.STAGGER if together else 0.0
                self.motion[place].arrive(delay, self.space.fromPlayer(landing, len(arriving)) if together else None)
                landing += 1
            elif now is None:
                self.motion[place].timers = []
            self.draw(place)
        self.quiet = False

    def _waits(self, place):
        """只是朝上那面变了样：翻面的效果可能紧跟着到（状态先发、效果后发），先等 GRACE 秒，别在翻起来之前就换成另一面的样子。"""
        if self.settleAt[place] == 0.0:
            self.settleAt[place] = self.clock + GRACE
        return self.clock < self.settleAt[place]

    def draw(self, place):
        """第 place 件现在该画成什么样：画（或换）道具，没有东西或还没轮到就收掉；位置、转角照动作摆（StoveBehavior.draw）。"""
        item, motion = self.shown[place], self.motion[place]
        if item is None or not motion.visible:
            self._drop(place)
            return
        name = item["newItemName"]
        look = StoveLook.shownName(name, Rules.grilledOf(name) or name, self.up[place])
        if not motion.moving:
            motion.settle()
        key = (look, item.get("newAuxValue") or 0)
        if self.props[place] is None or self.props[place][0] != key:
            self._drop(place)
            prop = self.view.props.item(_one(look, key[1]), self.space.centers()[place], scale=SCALE,
                                        matrix=StoveMotion.poseRows(0.0, motion.yaw, 0.0))
            self.props[place] = (key, prop)
        self.pose(place)

    def _drop(self, place):
        if self.props[place] is not None:
            self.view.props.remove(self.props[place][1])
            self.props[place] = None
            self.last[place] = None

    def pose(self, place):
        """把这一件的动作摆到道具上（只有变了才碰引擎）。"""
        entry = self.props[place]
        if entry is None or not self.motion[place].visible:
            return
        offset, rotation, scale = self.motion[place].pose()
        if (offset, rotation, scale) == self.last[place]:
            return
        self.last[place] = (offset, rotation, scale)
        base = self.space.centers()[place]
        entry[1].move(center=(base[0] + offset[0], base[1] + offset[1], base[2] + offset[2]),
                      matrix=StoveMotion.poseRows(rotation[0], rotation[1], rotation[2]), scale=SCALE * scale)

    # ---------------------------------------------------------------- 每帧

    def frame(self, dt, hovered):
        """前进 dt 秒：状态、动作、虚影、热气。hovered 是光标悬着的那件（或 None）。每帧都对一遍状态（JE 每刻 refresh）：
        翻到一半被服务端退回、状态比效果晚到这类，下一帧就画回服务端说的样子。"""
        self.clock += dt
        self.refresh()
        if not self.began:
            self.began = True
            self._arrivePending()
        for place in range(PLACES):
            for name in self.motion[place].update(dt, hovered == place):
                self._event(place, name)
            self.pose(place)
        self.ghosts.frame(dt)
        self._heat(dt)

    def _arrivePending(self):
        """开站时一起摆上来的几件（右键拿着食物开站）：镜头到位了才演，从玩家那边飞来、一件接一件。"""
        places = [place for place in self.pending if self.shown[place] is not None]
        self.pending = []
        for rank, place in enumerate(places):
            together = len(places) > 1
            self.motion[place].arrive(rank * StoveMotion.STAGGER if together else 0.0,
                                      self.space.fromPlayer(rank, len(places)) if together else None)
            self.draw(place)

    def _event(self, place, name):
        """动作走到点的事件：晚到的现身、落到烤架上冒汽嗞一声、翻到一半换另一面的样子、翻完落回烤架。"""
        if self.shown[place] is None:
            return
        if name == "appear":
            self.draw(place)
        elif name == "landed":
            self._play(StoveFx.hitsTheGrill(place, random.random))
        elif name == "swap":
            self.heldUntil[place] = 0.0
            self.up[place] = self.newUp[place]
            self.draw(place)
        elif name == "turned":
            self._play(StoveFx.turnLands(place, random.random))

    def _heat(self, dt):
        info = []
        for place in range(PLACES):
            item = self.shown[place]
            done = item is not None and Rules.isDone(item["newItemName"])
            info.append(None if item is None or done else (self.datum("hand", place, False), self.datum("down", place),
                                                           self.datum("up", place)))
        cooking, waiting = StoveLook.sortHeat(info, self.clock, self.turnedAt)
        self._play(self.heat.step(dt, cooking, waiting))

    def _play(self, effects):
        GrillFx.play(effects, self.space.world)

    # ---------------------------------------------------------------- 动作和效果

    def turned(self, place, up=None):
        """第 place 件翻面（自己点的、或服务端说别人翻的）：记下翻过来之后朝上那面的进度，跳起转半圈（StoveBehavior.turned）。
        自己点的取现在贴烤架那面的进度（翻过来它就在上面）；服务端的效果带着翻过来之后朝上那面的进度（状态比效果先到，数据里已经是翻过的）。"""
        if self.shown[place] is None:
            return
        self.turnedAt[place] = self.clock
        self.settleAt[place] = 0.0
        self.newUp[place] = up if isinstance(up, (int, float)) and not isinstance(up, bool) else self.datum("down", place)
        self.heldUntil[place] = self.clock + StoveMotion.FLIGHT / 2.0
        self.motion[place].turn()
        self._play(StoveFx.turnStarts())

    def unturned(self, place):
        """服务端没接这一翻（它还在空中）：画回服务端说的样子。"""
        self.heldUntil[place] = 0.0
        self.up[place] = -1.0
        self.refresh()

    def taken(self, place, stack):
        """一件被取走：虚影升起缩没，真的马上收掉（取走的状态可能晚一点才到）。"""
        self.ghosts.taken(stack, self.space.centers()[place], self.yaws[place])
        self.shown[place] = None
        self.motion[place].timers = []
        self.draw(place)

    def refused(self, stack):
        """放不上去的一件：虚影从烤架中心上方落下，往后弹开。"""
        self.ghosts.refused(stack, self.space.middle())
        self._play(StoveFx.refused())

    def grilled(self, place):
        """一件两面都烤好了：蒸汽和闪光。"""
        self._play([effect for effect in StoveFx.grilled(place, random.random) if not isinstance(effect, StoveFx.Sound)])

    def placed(self, places):
        """放上去了。站点刚开（右键拿着食物）时摆上来的在第一份状态里就有了，镜头到位之后才演落下。"""
        if not self.began and places:
            self.pending = [place for place in places if isinstance(place, int) and 0 <= place < PLACES]
