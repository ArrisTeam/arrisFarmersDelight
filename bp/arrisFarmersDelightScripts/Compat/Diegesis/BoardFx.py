# -*- coding: utf-8 -*-
"""BoardFx - 砧板站点客户端放的声音和碎屑（客户端）

对应 Hands-On Delight：client/BoardBehavior.java 的 chopped（1395-1453）、pop 里的面粉和闪光（1642-1651）、敲一声（WOOD_HIT）。
碎屑是本包自己的粒子 arris:board_dust（rp/particles/arris_board_dust.json）：HoD 的 spawnParticles(起点, 初速, 散布, 个数, 颜色) 的初速、
散布、个数都由 variable.* 给，数在 Shared/Rules/BoardDust（每种工具各一套），颜色是被切的东西自己图标的主色（JE 的 FoodColors.main，Shared/Data/BrothColors.MainColors：
砧板能切的每一件都有）；闪光还是前置包的
arris_diegesis:glint。站点里的人和旁观的人（BoardWatch，没有站点视图）都从 puffAt 放：一阵碎屑的起点和初速是操作者那边的站点像素，按他的朝向
转到世界。USE_OWN_DUST 关掉（粒子出了毛病时）就退回前置包自带的 arris_diegesis:dust（只有颜色和个数，旁观的人则没有碎屑）。
声音经 CustomAudio，名字是原版的；放什么、多大声在 Shared/Rules/BoardSounds（站点里的人 BoardEffects 和旁观的人 BoardWatch 用同一张表），
这里只管放；剪刀头两口和敲一声只有本人听得到，在 BoardCutter / BoardView 里直接放。放液体层时手倒下的水滴（dropletsAt）和磕蛋的蛋壳碎屑（puffAt）在 BoardHandDraw 里放。
"""
from . import PotFx
from ...Client.Engine import compFactory, levelId
from ...Shared.Data.BrothColors import MainColors
from ...Shared.Rules import BlockDisplay, PotModelMath, StoveFacing
from ...Shared.Rules import BoardDust as Dust
from ...Shared.Rules import SoundMix
from ...Shared.Rules.BoardSounds import BOUNCE, KNOCK, snipBite  # noqa: F401 （别的模块从这里拿）
from ...Shared.Rules.HandsOn import BoardScene as Scene
from ...Shared.Rules.HandsOn import Cutting

OWN_DUST = "arris:board_dust"
USE_OWN_DUST = True
DUST, GLINT = "arris_diegesis:dust", "arris_diegesis:glint"       # 前置包自带的：DUST 只在 USE_OWN_DUST 关掉时用
PIXEL = 1.0 / 16.0
# MainColors 里没有的东西（下游往砧板配方里追加的）碎屑的颜色：木头、石头、皮革按工具
TOOL_COLORS = {Cutting.TOOL_CHOP: 0x9C7F4E, Cutting.TOOL_STRIP: 0x6B5034, Cutting.TOOL_SMASH: 0x8A8A8A, Cutting.TOOL_DIG: 0xA4A8B8,
               Cutting.TOOL_PRY: 0x9C7F4E, Cutting.TOOL_SNIP: 0x8B5A2B}
FLOUR = 0xEDE3CC
FROST = 0xE8F4FF
GLINT_COLOR, GLINT_COUNT = 0xFFE9A0, 5           # 做成一道菜那一点闪光（pop，1649）：每一道都有
DEFAULT_COLOR = 0xE0D0A0


def play(sound, world):
    """放一声 (名字, 音量, 音调)，位置是世界坐标。音量音调是 JE 的数：定义里每个采样自带的那一份引擎会乘上去，先除掉（Shared/Rules/SoundMix）。"""
    volume, pitch = SoundMix.engineArgs(sound[0], sound[1], sound[2])
    compFactory.CreateCustomAudio(levelId).PlayCustomMusic(sound[0], tuple(world), volume, pitch, False, None)


def colorOf(itemName, stroke=None):
    """被切的东西飞出来的碎屑什么颜色：它自己图标的主色（BoardBehavior.chopped 的 FoodColors.main(worked)，原木、石头、花、船、皮甲也一样）；
    表里没有的（下游追加的配方）才按工具。"""
    return MainColors.get(itemName, TOOL_COLORS.get(stroke, DEFAULT_COLOR))


def dust(world, velocity, spread, count, color):
    """在世界坐标放一阵本包的碎屑：velocity 是世界方向的初速（格每秒），spread 起点的随机范围（格），color 是 0xRRGGBB。"""
    system = compFactory.CreateParticleSystem(None)
    particleId = system.Create(OWN_DUST, (float(world[0]), float(world[1]), float(world[2])))
    if not particleId:                    # 没有这个粒子、进世界头几秒粒子系统还没好：引擎回 0（不是 None），不能当编号去设变量
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


def dropletsAt(geometry, yaw, blockPos, point, velocity, color, count):
    """在站点像素 point 放一阵水滴（倒液体的水柱、倒空时瓶口的两滴：前置包的 droplet 粒子，和厨锅倒液体同一个）：velocity 是站点像素每秒、转到世界方向，
    color 是 0xRRGGBB。起点和速度是操作者那边的站点像素，按他的朝向 yaw 转到世界（旁观的人没有手的动画，不放水滴）。"""
    world = geometry.stationPointToWorld(yaw, point[0], point[1], point[2], blockPos[0], blockPos[1], blockPos[2])
    along = geometry.transformDirection(geometry.stationMatrices(yaw)[0], velocity[0], velocity[1], velocity[2])
    return PotFx.particle(PotFx.DROPLET, world, color=color, count=count, velocity=tuple(16.0 * part for part in along))


def finishPuff(geometry, yaw, blockPos, x, z, finish, view=None):
    """做成一道菜时从板面中心（站点像素 x, z）飞出的面粉 / 霜（pop，1640-1648）：飞什么由收尾定（BoardDust.crumbsOf：冰棒是霜，拌 / 摆 / 一起切开的不飞，别的是面粉）。
    站点里的人（BoardEffects）和旁观的人（BoardWatch）都从这里放。"""
    kind = Dust.crumbsOf(finish)
    if kind is None:
        return None
    frost = kind == Dust.FROST_KIND
    return puffAt(geometry, yaw, blockPos, Dust.flourPuff(x, z, frost), FROST if frost else FLOUR, view)


def glintAt(view, point):
    """站点里的人看到的做成一道菜时那一点闪光（pop，1649；前置包的 view.particles）。"""
    view.particles(GLINT, point, GLINT_COLOR, GLINT_COUNT)


def glintInWorld(world):
    """旁观的人看到的那一点闪光：没有站点视图，直接按世界坐标放同一个前置包粒子（厨锅场景里的闪光也是这样放的）。"""
    PotFx.particle(GLINT, world, color=GLINT_COLOR, count=GLINT_COUNT)


def centerOf(blockPos):
    """板面中心的世界坐标：FD 的板底座在方块自己坐标的 (6.5, 8)，按方块朝向换算（BoardView.center 和旁观的人共用）。"""
    block = compFactory.CreateBlockInfo(levelId).GetBlock(tuple(blockPos))
    return PotModelMath.localPoint(PotModelMath.facingOf(block[1] if block else 0), blockPos, Scene.BASE_X, 0.0, Scene.BASE_Z)


def frontOf(view):
    """板上插着的工具的贴图正面朝哪（站点里的方向 x, z）：世界里是 BlockDisplay.carvedFront（没开站时 Client/BlockItems 摆的就是它），
    这里换到站点里（两点做差，和站点朝向的符号约定无关）：站点里画的和世界里摆的朝着同一边，开站、关站不转。"""
    block = compFactory.CreateBlockInfo(levelId).GetBlock(tuple(view.pos))
    dx, dz = BlockDisplay.carvedFront(StoveFacing.yawOfAux(block[1] if block else 0))
    x, y, z = view.pos[0] + 0.5, view.pos[1], view.pos[2] + 0.5
    here, there = view.toStation(x, y, z), view.toStation(x + dx, y, z + dz)
    return (there[0] - here[0], there[2] - here[2])


def _text(value):
    return value if isinstance(value, (str, type(u""))) else ""


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value == value and abs(value) < 1.0e6


def chopPuffs(geometry, blockPos, data, view=None):
    """chopped 效果的碎屑（所有看得见板的人）：一刀一阵；最后一刀切的是方块，再在方块中心炸开一阵（削皮切出了东西的除外：那根去皮原木往上升，
    由 BoardDraw 画）。data 是 chopped 效果；起点的 x / z 是操作者落刀的位置（站点像素，没带就是板面中心）。返回这一刀的 (笔画, 切出来的东西的名字)。"""
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
    return stroke, yields
