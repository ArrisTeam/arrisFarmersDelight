# -*- coding: utf-8 -*-
"""BoardFinishKit - 做成一道菜之前的收尾动画的底：JE 的常量、每种收尾演多久、一份排好的动作 Plan（双端，纯规则）

移植自 Hands-On Delight 的 client/BoardBehavior.java：类头的常量（95-163）和 assembled 里每种收尾多长（1521-1540）。层凑成菜时，先照菜的种类演一套收尾
（十种：压 = 什么也不演，拌 / 卷 / 串 / 揉 / 摆 / 夹 / 成形 / 冻 / 一起切），演完各层才沉进去、菜弹出来（pop，那一刻放面粉 / 霜、闪光、做成的两声，Shared/Rules/BoardSounds.ASSEMBLED）。
十种各自怎么演在 BoardFinishGroup（拌、卷、揉、一起切：各层一起动）和 BoardFinishPlace（串、摆、夹、成形、冻：一片片放上去），入口是 BoardFinish.plan。

Plan 是这套动作的全部：cues 是 [(第几秒, 操作, 目标, 参数)]，秒从收尾开始（层都落定那一刻）算；目标是层号（0 是底座），夹的盖子是 LID，声音 / 粒子没有目标。
位置是离板面中心的偏移 (x, 离板面的高, z)，和 BoardMotion.Mover 一个坐标（JE 的节点偏移是从层自己的高度 i * LAYER_STEP 算起，这里换成离板面的高）；角度是 JE 节点的欧拉角
（度，先 Y 再 X 再 Z，BoardMotion.Mover.rotateTo）。rest 是每一层动作做完躺的地方：pop 把各层从那里往板中间沉（BoardMotion.melt）。
"""
import random

from . import Assembly
from . import BoardMotion as Motion
from .Mth import TICK

MELT_TIME = Motion.MELT_TIME         # :95
LAYER_STEP = Motion.LAYER_STEP       # :165
MOST_LAYERS = Assembly.MOST_LAYERS
# 拌（98-105）：碗里的料飞多高、在空中多久、歇多久；碗自己颠一下的高、用多久、后仰多少度；料翻滚多少度
TOSS_HEIGHT, TOSS_TIME, TOSS_REST, TOSS_JERK, TOSS_JERK_TIME, TOSS_TILT, TOSS_TUMBLE = 4.0, 0.42, 0.12, 0.9, 0.16, 12.0, 40.0
# 卷（106-111）：各层合拢、来回滚几趟、一趟多久、位移、转角
ROLL_GATHER, ROLLS, ROLL_STROKE, ROLL_TRAVEL, ROLL_TURN = 0.12, 3, 0.14, 1.6, 25.0
# 串（112-124）：每片滑到签子尖的时间、相隔、一起推向柄的时间；片落在签子上的位置（离尖占全长的比例，柄那头留空）；立起来的角度、缩小
SKEWER_SLIDE, SKEWER_STAGGER, SKEWER_PUSH, SKEWER_FIRST, SKEWER_LAST, SKEWER_STAND, SKEWER_SCALE = 0.18, 0.1, 0.16, 0.12, 0.62, -60.0, 0.7
# 摆（125-129）：主料滑到碗中央、其余依次间隔、摆一圈的半径、缩小
ARRANGE_SLIDE, ARRANGE_STAGGER, ARRANGE_RING, ARRANGE_SCALE = 0.18, 0.08, 2.4, 0.8
# 夹（130-134）：上半抬起、盖过馅、压一下、抬多高
LID_LIFT, LID_CLOSE, LID_PRESS, LID_HEIGHT = 0.16, 0.16, 0.1, 3.0
# 成形（135-138）：米饭压成块、片一片片放上去、最后压一下
SHAPE_GATHER, SHAPE_LAY, SHAPE_PRESS = 0.14, 0.12, 0.1
# 冻（139-143）：水果聚到签子顶、冰化成霜；聚在签子上离尖多远；霜的颜色（JE 的 0xFFE8F4FF 去掉不透明度）
FREEZE_GATHER, FREEZE_SET, FREEZE_AT, FROST = 0.2, 0.3, 0.28, 0xE8F4FF
# 一起切（144-147）：刀过几次、一次多久、两半分开多远
CHOPS, CHOP_STROKE, CHOP_PART = 2, 0.16, 0.9
# 揉（158-163）：压成一坨、推平几次、一次多久、扭多少度、摊开多远
KNEAD_PRESS, KNEAD_PUSHES, KNEAD_PUSH, KNEAD_TURN, KNEAD_SPREAD = 0.12, 3, 0.09, 22.0, 1.2

MOVE, ROTATE, SCALE, SHOW, SOUND, DUST, GLINT = "move", "rotate", "scale", "show", "sound", "dust", "glint"
LID = "lid"                          # 夹的盖子（面包的上半，BoardBehavior.sandwich 里借的 lift 节点）
ICES = ("minecraft:ice", "minecraft:packed_ice")        # :1912 冻的时候冰缩没、别的水果缩到 0.75


def finishing(finish, count):
    """这种收尾（Assembly.FINISH_*）从层落定到开始沉要多久，秒（assembled 的 switch，1528-1539）；count 是做成的层数。压和认不出的收尾名是 0。"""
    if finish == Assembly.FINISH_TOSS:
        return TOSS_TIME + TOSS_REST
    if finish == Assembly.FINISH_ROLL:
        return ROLL_GATHER + (ROLLS + 1) * ROLL_STROKE
    if finish == Assembly.FINISH_SKEWER:
        return SKEWER_SLIDE + (count - 1) * SKEWER_STAGGER + SKEWER_PUSH
    if finish == Assembly.FINISH_KNEAD:
        return KNEAD_PRESS + KNEAD_PUSHES * KNEAD_PUSH * 2.0
    if finish == Assembly.FINISH_ARRANGE:
        return ARRANGE_SLIDE + max(0, count - 2) * ARRANGE_STAGGER
    if finish == Assembly.FINISH_SANDWICH:
        return LID_LIFT + LID_CLOSE + LID_PRESS
    if finish == Assembly.FINISH_SHAPE:
        return SHAPE_GATHER + max(1, count - 1) * SHAPE_LAY + SHAPE_PRESS
    if finish == Assembly.FINISH_FREEZE:
        return FREEZE_GATHER + FREEZE_SET
    if finish == Assembly.FINISH_CHOP:
        return CHOPS * CHOP_STROKE
    return 0.0


def sinking(finish, count):
    """这道菜做成要等多久各层才算沉完（assembled 的 melting 去掉等层落完的那一段，1540）：收尾演完再沉 MELT_TIME，再加一刻（JE 的 melting 是每刻减一刻数的）。"""
    return finishing(finish, count) + MELT_TIME + TICK


class Plan(object):
    """一种收尾排出来的动作。rest[i] 开头是层刚摆好的样子（assembled 开头的 rest(i, jitterX, i * LAYER_STEP, jitterZ)，1522-1524），各种收尾再改它。"""

    def __init__(self, finish, count, rng=random.random):
        self.finish, self.count, self.seconds, self.rng = finish, count, finishing(finish, count), rng
        self.rest = [(Motion.layerJitter(i)[0], i * LAYER_STEP, Motion.layerJitter(i)[1]) for i in range(MOST_LAYERS)]
        self.cues = []
        self.lid = False

    def move(self, at, target, pos, seconds=0.0, hop=0.0):
        self.cues.append((at, MOVE, target, (tuple(pos), seconds, hop)))

    def rotate(self, at, target, rotation, seconds=0.0):
        self.cues.append((at, ROTATE, target, (tuple(rotation), seconds)))

    def scale(self, at, target, factor, seconds=0.0):
        self.cues.append((at, SCALE, target, (factor, seconds)))

    def show(self, at, target, visible):
        self.cues.append((at, SHOW, target, bool(visible)))

    def sound(self, at, sound):
        self.cues.append((at, SOUND, None, tuple(sound)))

    def dust(self, at, puff, color):
        """一阵粒子：puff 是 (起点离板面中心的 (x, 站点高度, z), 初速, 散布, 个数)，color 是 0xRRGGBB（BoardFx.puffAt 放）。"""
        self.cues.append((at, DUST, None, (puff, color)))

    def glint(self, at, point, color, count):
        self.cues.append((at, GLINT, None, (tuple(point), color, count)))

    def ordered(self):
        """按时刻先后排好的动作（同一时刻的保持排进来的先后）。"""
        return sorted(self.cues, key=lambda cue: cue[0])

    def effects(self):
        """只要声音和粒子（旁观的人看不到层动，可 JE 里人人听得到、看得到这些）。"""
        return [cue for cue in self.ordered() if cue[1] in (SOUND, DUST, GLINT)]
