# -*- coding: utf-8 -*-
"""ItemDrops - 东西从方块里掉出来 / 弹出去时的位置和初速（双端，纯规则）

照 JE：Containers.dropItemStack（ItemUtils.dropItems 对炉灶的每个烤位调它）：一叠东西从方块里随机一点掉出来（x、z 离边至少半个掉落物宽，y 在底下四分之三里），
一次掉 10..30 个，每个掉落物带一点随机的初速（三角分布，横向以 0 为中心、竖直以 0.2 为中心）；FD 的 ItemUtils.spawnItemEntity 烤好弹出时给的初速
（AbstractStoveBlockEntity.cookAndOutputItems:128-130）。初速的单位和 JE 的 setDeltaMovement 一样：每刻几格。随机数由调用方给（random 模块或 random.Random），测试里可以换成定的。
"""
ITEM_WIDTH = 0.25                    # EntityType.ITEM 的宽
CHUNK = (10, 30)                     # stack.split(level.random.nextInt(21) + 10)：一个掉落物的数量范围
DEVIATION = 0.11485000171139836      # level.random.triangle(mode, 0.11485000171139836)
LIFT = 0.2                           # 竖直那一向的中心
POP_SIDE = 0.01                      # 烤好弹出：横向的初速是高斯随机乘它（JE 写的是 (double) 0.01F）
POP_UP = 0.1                         # 烤好弹出：往上的初速


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
