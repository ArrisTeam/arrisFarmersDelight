# -*- coding: utf-8 -*-
"""ItemDrops - 东西从方块里掉出来 / 弹出去时的位置和初速（双端，纯规则）

照 JE：Containers.dropItemStack（ItemUtils.dropItems 对炉灶的每个烤位调它）：一叠东西从方块里随机一点掉出来（x、z 离边至少半个掉落物宽，y 在底下四分之三里），
一次掉 10..30 个，每个掉落物带一点随机的初速（三角分布，横向以 0 为中心、竖直以 0.2 为中心）；FD 的 ItemUtils.spawnItemEntity 烤好弹出时给的初速
（AbstractStoveBlockEntity.cookAndOutputItems:128-130）。初速的单位和 JE 的 setDeltaMovement 一样：每刻几格。随机数由调用方给（random 模块或 random.Random），测试里可以换成定的。
砧板切出来的一件、煎锅煎好的一件不是随机的：从方块的侧面弹出去，朝哪边看方块的朝向（boardPop / panPop）。
"""
from .Placement import FACING_VECTORS

ITEM_WIDTH = 0.25                    # EntityType.ITEM 的宽
CHUNK = (10, 30)                     # stack.split(level.random.nextInt(21) + 10)：一个掉落物的数量范围
DEVIATION = 0.11485000171139836      # level.random.triangle(mode, 0.11485000171139836)
LIFT = 0.2                           # 竖直那一向的中心
POP_SIDE = 0.01                      # 烤好弹出：横向的初速是高斯随机乘它（JE 写的是 (double) 0.01F）
POP_UP = 0.1                         # 烤好弹出：往上的初速
BOARD_SIDE, BOARD_HEIGHT = 0.2, 0.2  # 砧板切出来：离方块中心往侧面偏 0.2（stepX * 0.2）、离方块底 0.2（CuttingBoardBlockEntity.java:91）
BOARD_SPEED = 0.2                    # 砧板切出来：侧面方向的初速（stepX * 0.2F，竖直 0.0F，java:92）
PAN_HEIGHT = 0.3                     # 煎锅煎好：离方块底 0.3，在方块中心正上（SkilletBlockEntity.java:104）
PAN_SPEED, PAN_UP = 0.08, 0.25       # 煎锅煎好：侧面方向 stepX * 0.08F、往上 0.25F（java:105）


def triangle(mode, deviation, rand):
    """level.random.triangle：以 mode 为中心、最多偏 deviation 的三角分布。"""
    return mode + deviation * (rand.random() - rand.random())


def scatter(count, rand):
    """count 个一起掉出方块：[(数量, 方块里的位置 (x, y, z，占方块边长的比例), 初速)]；一叠的位置只掷一次，初速每个掉落物各掷一次。"""
    room = 1.0 - ITEM_WIDTH
    at = (rand.random() * room + ITEM_WIDTH / 2, rand.random() * room, rand.random() * room + ITEM_WIDTH / 2)
    drops = []
    while count > 0:
        amount = min(count, rand.randint(*CHUNK))
        drops.append((amount, at, (triangle(0.0, DEVIATION, rand), triangle(LIFT, DEVIATION, rand), triangle(0.0, DEVIATION, rand))))
        count -= amount
    return drops


def popMotion(rand):
    """烤好的东西弹出时的初速：横向一点点高斯随机，往上 0.1。"""
    return (rand.gauss(0.0, 1.0) * POP_SIDE, POP_UP, rand.gauss(0.0, 1.0) * POP_SIDE)


def _side(direction):
    """方块侧面那一向的水平单位向量 (x, z)：direction 是方块的 direction 状态（0 南 1 西 2 北 3 东，也是 Placement.FACING_VECTORS 的下标）。
    砧板的 direction 就是 JE 的 FACING（朝着放它的玩家），切出来的弹向 FACING.getCounterClockWise()（CuttingBoardBlockEntity.java:89）；
    煎锅的 direction 是锅柄朝的方向（也朝着放它的玩家），JE 的 FACING 是反过来的（玩家面朝的方向，SkilletBlock.getStateForPlacement），
    煎好的弹向 FACING.getClockWise()（SkilletBlockEntity.java:102）：两个都是 direction 逆时针转一格，即下标减 1。"""
    step = FACING_VECTORS[(direction - 1) & 3]
    return step[0], step[2]


def boardPop(direction):
    """砧板切出来的一件：(离方块角的位置 (x, y, z)，占方块边长的比例, 初速)。"""
    dx, dz = _side(direction)
    return (0.5 + dx * BOARD_SIDE, BOARD_HEIGHT, 0.5 + dz * BOARD_SIDE), (dx * BOARD_SPEED, 0.0, dz * BOARD_SPEED)


def panPop(direction):
    """煎锅煎好的一件：(离方块角的位置 (x, y, z)，占方块边长的比例, 初速)。"""
    dx, dz = _side(direction)
    return (0.5, PAN_HEIGHT, 0.5), (dx * PAN_SPEED, PAN_UP, dz * PAN_SPEED)
