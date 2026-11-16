# -*- coding: utf-8 -*-
"""BoardFx - 砧板站点客户端放的声音和碎屑（客户端）

对应 Hands-On Delight：client/BoardBehavior.java 的 chopped（1395-1453）、pop 里的面粉和闪光（1642-1651）、敲一声（WOOD_HIT）。
粒子是前置包自带的 arris_diegesis:dust（HoD 的 DiegesisParticles.DUST，按 0xRRGGBB 染色、个数可调）和 arris_diegesis:glint；
声音经 CustomAudio，名字是原版的；放什么、多大声在 Shared/Rules/BoardSounds（站点里的人 BoardEffects 和旁观的人 BoardWatch 用同一张表），
这里只管放；剪刀头两口和敲一声只有本人听得到，在 BoardCutter / BoardView 里直接放。
"""
from ...Client.Engine import compFactory, levelId
from ...Shared.Data.FoodColors import FoodColors
from ...Shared.Rules.BoardSounds import BOUNCE, KNOCK, snipBite  # noqa: F401 （别的模块从这里拿）
from ...Shared.Rules.HandsOn import Cutting

DUST, GLINT = "arris_diegesis:dust", "arris_diegesis:glint"
# 每一下飞几颗碎屑（chopped 的 switch，1410-1421）：刀 4、斧 7、削皮 12、镐 10、锹 9、锄 4、剪 3
DUST_COUNT = {Cutting.TOOL_CUT: 4, Cutting.TOOL_CHOP: 7, Cutting.TOOL_STRIP: 12, Cutting.TOOL_SMASH: 10, Cutting.TOOL_DIG: 9,
              Cutting.TOOL_PRY: 4, Cutting.TOOL_SNIP: 3}
# 不是食物时碎屑的颜色（木头、石头、皮革按工具）；食物按贴图（FoodColors）
TOOL_COLORS = {Cutting.TOOL_CHOP: 0x9C7F4E, Cutting.TOOL_STRIP: 0x6B5034, Cutting.TOOL_SMASH: 0x8A8A8A, Cutting.TOOL_DIG: 0xA4A8B8,
               Cutting.TOOL_PRY: 0x9C7F4E, Cutting.TOOL_SNIP: 0x8B5A2B}
FLOUR = 0xEDE3CC
DEFAULT_COLOR = 0xE0D0A0


def play(sound, world):
    """放一声 (名字, 音量, 音调)，位置是世界坐标。"""
    compFactory.CreateCustomAudio(levelId).PlayCustomMusic(sound[0], tuple(world), float(sound[1]), float(sound[2]), False, None)


def dustAt(view, point, stroke, itemName, count=None):
    """在站点像素 point 处飞一阵碎屑：食物按贴图的颜色，别的按工具；个数按工具。"""
    color = FoodColors.get(itemName, TOOL_COLORS.get(stroke, DEFAULT_COLOR))
    view.particles(DUST, point, color, count if count is not None else DUST_COUNT.get(stroke, 4))


def flourAt(view, point):
    """做成一道菜时那一阵面粉和一点闪光（pop，1642-1651）。"""
    view.particles(DUST, point, FLOUR, 12)
    view.particles(GLINT, point, 0xFFE9A0, 5)
