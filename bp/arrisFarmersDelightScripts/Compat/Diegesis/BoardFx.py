# -*- coding: utf-8 -*-
"""BoardFx - 砧板站点客户端放的声音和碎屑（客户端）

对应 Hands-On Delight：client/BoardBehavior.java 的 chopped（1395-1453）、pop 里的面粉和闪光（1642-1651）、敲一声（WOOD_HIT）。
碎屑是本包自己的粒子 arris:board_dust（rp/particles/arris_board_dust.json）：HoD 的 spawnParticles(起点, 初速, 散布, 个数, 颜色) 的初速、
散布、个数都由 variable.* 给，数在 Shared/Rules/BoardDust（每种工具各一套），颜色按食物的贴图（FoodColors）、不是食物按工具；闪光还是前置包的
arris_diegesis:glint。站点里的人和旁观的人（BoardWatch，没有站点视图）都从 puffAt 放：一阵碎屑的起点和初速是操作者那边的站点像素，按他的朝向
转到世界。USE_OWN_DUST 关掉（粒子出了毛病时）就退回前置包自带的 arris_diegesis:dust（只有颜色和个数，旁观的人则没有碎屑）。
声音经 CustomAudio，名字是原版的；放什么、多大声在 Shared/Rules/BoardSounds（站点里的人 BoardEffects 和旁观的人 BoardWatch 用同一张表），
这里只管放；剪刀头两口和敲一声只有本人听得到，在 BoardCutter / BoardView 里直接放。
"""
from ...Client.Engine import compFactory, levelId
from ...Shared.Data.FoodColors import FoodColors
from ...Shared.Rules import BoardDust as Dust
from ...Shared.Rules import PotModelMath
from ...Shared.Rules.BoardSounds import BOUNCE, KNOCK, snipBite  # noqa: F401 （别的模块从这里拿）
from ...Shared.Rules.HandsOn import BoardScene as Scene
from ...Shared.Rules.HandsOn import Cutting

OWN_DUST = "arris:board_dust"
USE_OWN_DUST = True
DUST, GLINT = "arris_diegesis:dust", "arris_diegesis:glint"       # 前置包自带的：DUST 只在 USE_OWN_DUST 关掉时用
PIXEL = 1.0 / 16.0
# 不是食物时碎屑的颜色（木头、石头、皮革按工具）；食物按贴图（FoodColors）
TOOL_COLORS = {Cutting.TOOL_CHOP: 0x9C7F4E, Cutting.TOOL_STRIP: 0x6B5034, Cutting.TOOL_SMASH: 0x8A8A8A, Cutting.TOOL_DIG: 0xA4A8B8,
               Cutting.TOOL_PRY: 0x9C7F4E, Cutting.TOOL_SNIP: 0x8B5A2B}
FLOUR = 0xEDE3CC
FROST = 0xE8F4FF
DEFAULT_COLOR = 0xE0D0A0


def play(sound, world):
    """放一声 (名字, 音量, 音调)，位置是世界坐标。"""
    compFactory.CreateCustomAudio(levelId).PlayCustomMusic(sound[0], tuple(world), float(sound[1]), float(sound[2]), False, None)


def colorOf(itemName, stroke=None):
    """被切的东西飞出来的碎屑什么颜色：食物按贴图，别的按工具。"""
    return FoodColors.get(itemName, TOOL_COLORS.get(stroke, DEFAULT_COLOR))


def dust(world, velocity, spread, count, color):
    """在世界坐标放一阵本包的碎屑：velocity 是世界方向的初速（格每秒），spread 起点的随机范围（格），color 是 0xRRGGBB。"""
    system = compFactory.CreateParticleSystem(None)
    particleId = system.Create(OWN_DUST, (float(world[0]), float(world[1]), float(world[2])))
    if particleId is None:
        return None
    for name, shift in (("variable.tint_r", 16), ("variable.tint_g", 8), ("variable.tint_b", 0)):
        system.SetVariable(particleId, name, ((int(color) >> shift) & 0xFF) / 255.0)
    system.SetVariable(particleId, "variable.tint_set", 1.0)
    for name, value in (("variable.count", count), ("variable.vx", velocity[0]), ("variable.vy", velocity[1]), ("variable.vz", velocity[2]),
                        ("variable.spread", spread)):
        system.SetVariable(particleId, name, float(value))
    return particleId


def puffAt(geometry, yaw, blockPos, puff, color, view=None):
    """一阵碎屑（Shared/Rules/BoardDust 的 (起点, 初速, 散布, 个数)，操作者那边的站点像素、他朝 yaw 的方向）放到世界里。
    geometry 是前置包的 Geometry；view 是站点视图（旁观的人没有：退路的前置包粒子要靠它换算站点坐标）。"""
    (px, py, pz), velocity, spread, count = puff
    world = geometry.stationPointToWorld(yaw, px, py, pz, blockPos[0], blockPos[1], blockPos[2])
    if USE_OWN_DUST:
        along = geometry.transformDirection(geometry.stationMatrices(yaw)[0], velocity[0], velocity[1], velocity[2])
        return dust(world, along, spread * PIXEL, count, color)
    if view is not None:
        return view.particles(DUST, view.toStation(*world), color, count)
    return None


def flourAt(view, point):
    """做成一道菜时那一点闪光（pop，1642-1651；面粉在 puffAt 里）。"""
    view.particles(GLINT, point, 0xFFE9A0, 5)


def centerOf(blockPos):
    """板面中心的世界坐标：FD 的板底座在方块自己坐标的 (6.5, 8)，按方块朝向换算（BoardView.center 和旁观的人共用）。"""
    block = compFactory.CreateBlockInfo(levelId).GetBlock(tuple(blockPos))
    return PotModelMath.localPoint(PotModelMath.facingOf(block[1] if block else 0), blockPos, Scene.BASE_X, 0.0, Scene.BASE_Z)


def _text(value):
    return value if isinstance(value, (str, type(u""))) else ""


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value == value and abs(value) < 1.0e6


def chopPuffs(geometry, blockPos, data, view=None):
    """chopped 效果的碎屑（所有看得见板的人）：一刀一阵；最后一刀切的是方块，再在方块中心炸开一阵（削皮切出了东西的除外：那根去皮原木往上升，
    由 BoardDraw 画）。data 是 chopped 效果；起点的 x / z 是操作者落刀的位置（站点像素，没带就是板面中心）。返回这一刀的 (笔画, 是不是削出东西来的方块收尾)。"""
    item, tool = _text(data.get("item")), _text(data.get("tool"))
    yields = [name for name in (data.get("yields") if isinstance(data.get("yields"), (list, tuple)) else ()) if _text(name)]
    yaw = data["yaw"] if data.get("yaw") in (0, 90, 180, 270) else 0
    stroke = _text(data.get("stroke")) if _text(data.get("stroke")) in Cutting.STROKES else Cutting.strokeKind([tool], yields)
    block = bool(data.get("block"))
    mx, _, mz = geometry.worldPointToStation(yaw, *(tuple(centerOf(blockPos)) + tuple(blockPos)))
    x = data["at_x"] if _number(data.get("at_x")) else mx
    z = data["at"] if _number(data.get("at")) else mz
    color = colorOf(item, stroke)
    puffAt(geometry, yaw, blockPos, Dust.strokePuff(stroke, block, x, z, mx, mz), color, view)
    stripped = stroke == Cutting.TOOL_STRIP and bool(yields)
    if data.get("done") and block and not stripped:
        puffAt(geometry, yaw, blockPos, Dust.blockDonePuff(stroke, mx, mz), color, view)
    return stroke, stripped
