# -*- coding: utf-8 -*-
"""Basket - 篮子吸掉落物的规则：收集区、往 27 格里塞的次序、吸一件之后的冷却（双端，纯规则）

照 JE 的 Basket 接口与 BasketBlockEntity（FD 1.3.4）：
- 收集区 Basket.COLLECTION_AREA_SHAPES：篮子自己那一格，加上朝向的那一格（朝上就是 1×2×1 的一根柱子）；
  收集时取掉落物碰撞盒与收集区相交的（getEntitiesOfClass，边贴边不算）。
- 塞进去 putStackInInventoryAllSlots：从 0 号格往后逐格试，遇到空格整堆放进去、遇到同种且没满的补满；
  是"哪一格先遇到用哪一格"，不是"先补同种再找空格"。
- 冷却 transferCooldown：整个掉落物都吸进去之后 8 刻内不再吸；没吸进去（满了、被红石锁了）每刻重试，这里放宽成隔一小会儿。
- 红石：邻居有信号时篮子不工作（BasketBlock.neighborChanged 把 ENABLED 置假），不在这里。
"""
import math

SLOTS = 27
# 掉落物碰撞盒边长（格）
ITEM_SIZE = 0.25
# 朝向序号同 JE Direction.get3DDataValue
DOWN, UP, NORTH, SOUTH, WEST, EAST = range(6)
# 收集区：相对篮子所在方块西北下角的 ((x0, y0, z0), (x1, y1, z1))，单位格（JE 的 Block.box 除以 16）
AREAS = {
    DOWN: ((0, -1, 0), (1, 1, 1)),
    UP: ((0, 0, 0), (1, 2, 1)),
    NORTH: ((0, 0, -1), (1, 1, 1)),
    SOUTH: ((0, 0, 0), (1, 1, 2)),
    WEST: ((-1, 0, 0), (1, 1, 1)),
    EAST: ((0, 0, 0), (2, 1, 1)),
}
# 吸到一整个掉落物之后 8 刻（0.4 秒）内不再吸
COOLDOWN = 8 / 20.0
# 没吸成时多久再试一次（JE 每刻都试；这边每次试要读 27 格，放宽一点）
RETRY = 0.2

# 判断"同一种物品"看的键（JE：ItemStack.isSameItemSameTags）
_IDENTITY = ("newItemName", "newAuxValue", "userData", "enchantData", "modEnchantData", "customTips", "extraId")


def collectionBox(blockPos, facing=UP):
    """篮子在 blockPos 时的收集区：((x0, y0, z0), (x1, y1, z1))，世界坐标。"""
    low, high = AREAS[facing]
    return (tuple(blockPos[i] + low[i] for i in range(3)), tuple(blockPos[i] + high[i] for i in range(3)))


def itemBox(footPos, size=ITEM_SIZE):
    """脚底坐标在 footPos 的掉落物的碰撞盒。"""
    half = size / 2.0
    return ((footPos[0] - half, footPos[1], footPos[2] - half), (footPos[0] + half, footPos[1] + size, footPos[2] + half))


def overlaps(boxA, boxB):
    """两个盒子是否相交（边贴边不算，与 AABB.intersects 一致）。"""
    return all(boxA[0][i] < boxB[1][i] and boxA[1][i] > boxB[0][i] for i in range(3))


def basketCells(footPos, facing=UP, size=ITEM_SIZE):
    """脚底在 footPos 的掉落物，收集区能碰到它的篮子可能在哪几格：[(x, y, z), ...]（篮子自己那一格排最前）。"""
    low, high = AREAS[facing]
    box = itemBox(footPos, size)
    ranges = []
    for axis in range(3):
        # 篮子在 c：收集区占 [c + low, c + high]，与 [box0, box1] 严格相交 <=> box0 - high < c < box1 - low
        first = int(math.floor(box[0][axis] - high[axis])) + 1
        last = int(math.ceil(box[1][axis] - low[axis])) - 1
        ranges.append(list(range(first, last + 1)))
    own = tuple(int(math.floor(footPos[i])) for i in range(3))
    cells = [(x, y, z) for x in ranges[0] for y in ranges[1] for z in ranges[2]]
    cells.sort(key=lambda cell: (cell != own, cell))
    return cells


def _same(a, b):
    for key in _IDENTITY:
        left, right = a.get(key), b.get(key)
        if key == "newAuxValue":
            left, right = left or 0, right or 0
        else:
            left, right = left or None, right or None      # None / {} / [] / "" 都当"没有"
        if left != right:
            return False
    return True


def isFull(slots, maxStackOf):
    """27 格全有东西、且每格都正好是满堆（JE BasketBlockEntity.isFull，数量不等于满堆就不算满）。"""
    for stack in slots:
        if stack is None or stack["count"] != maxStackOf(stack):
            return False
    return True


def insertAll(slots, stack, maxStackOf):
    """把 stack 塞进 slots（长度 27 的列表，空格是 None），照 JE putStackInInventoryAllSlots。

    返回 (新的格子表, 动过的格号, 塞不下的剩余堆或 None)；传进来的东西不会被改。
    """
    result = list(slots)
    left = dict(stack)
    changed = []
    for index in range(len(result)):
        if left["count"] <= 0:
            break
        current = result[index]
        if current is None:
            result[index] = dict(left)
            left["count"] = 0
            changed.append(index)
        elif current["count"] <= maxStackOf(current) and _same(current, left):
            moved = min(left["count"], maxStackOf(left) - current["count"])
            if moved > 0:
                merged = dict(current)
                merged["count"] = current["count"] + moved
                result[index] = merged
                left["count"] -= moved
                changed.append(index)
    return result, changed, (left if left["count"] > 0 else None)


class Gate(object):
    """每个篮子"下次可以动手的时间"（真实时间，不受 /time set 影响）。key 一般是 (维度, 坐标)。"""

    def __init__(self, cooldown=COOLDOWN, retry=RETRY):
        self.cooldown = cooldown
        self.retry = retry
        self._until = {}

    def ready(self, key, now):
        return now >= self._until.get(key, 0)

    def captured(self, key, now):
        """吸进了一整个掉落物：冷却 8 刻。"""
        self._until[key] = now + self.cooldown

    def idle(self, key, now):
        """这一轮什么都没吸成：过一会儿再试。"""
        self._until[key] = now + self.retry

    def prune(self, now):
        """丢掉已经过期的记录（篮子被拆了也不会一直占着）。"""
        for key in [k for k, until in self._until.items() if now >= until]:
            del self._until[key]

    def __len__(self):
        return len(self._until)
