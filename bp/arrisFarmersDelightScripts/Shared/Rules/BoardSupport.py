# -*- coding: utf-8 -*-
"""BoardSupport - 砧板下面撑不撑得住：放得下放不下、会不会掉（双端，纯规则）

JE 的 CuttingBoardBlock（java:121-135）：canSurvive = canSupportRigidBlock(下面) || canSupportCenter(下面, UP)。放的时候不满足就放不下（BlockItem.canPlace），
下面的方块变了（updateShape 的 facing == DOWN）不满足就当场被拆：掉板自己，板上的东西从方块里散落（onRemove 的 Containers.dropItemStack）。
两个条件看的都是下面那格的"支撑形状"贴着顶面（y = 1）的那一片（原版 SupportType）：RIGID 要盖住顶面外圈 2 像素宽的一圈，CENTER 要盖住正中 2x2 像素；
一个长方体盖得住外圈就一定盖得住正中，所以这里只看正中。

引擎的 GetBlockCollision（2026-11-18 实机量的，3.10，双端都有）给的是这一格此刻碰撞盒的包围盒（世界坐标）：没有碰撞盒的（空气、液体、花草、火把、几层薄雪、脚手架）
六个数全是 0；下半砖 0 ~ 0.5、上半砖 0.5 ~ 1、地毯 1/16、耕地 / 土径 15/16、箱子 0.95、附魔台 0.75、灯笼 0.5、活板门贴着哪头算哪头；栅栏 / 墙是正中一根高 1.5 的柱子、
玻璃板是正中 2 像素、铁砧 12 像素宽顶到 1；楼梯、炼药锅、堆肥桶、漏斗是整格的包围盒。拿它照 JE 的规矩判：顶到 y = 1、盖住正中 2x2 像素才撑得住。
包围盒说不准的、基岩版的碰撞盒和 Java 的支撑形状不一样的，按名字另说：
- 撑得住：灵魂沙、泥巴（踩上去陷 2 像素，Java 的支撑形状是整格）、脚手架（没有碰撞盒，Java 顶上是一整块板）、叠满八层的雪；
- 撑不住：树叶（Java 的支撑形状是空的）、蜂蜜块、仙人掌（基岩版顶到 1，Java 只到 15/16）；原版的楼梯倒着放（顶面是整块）撑得住，正着的撑不住。
没查到碰撞盒（box 是 None：调用方没问、接口没给）时退回只认空气和液体；下面没加载（名字是 None）不判——判错了会让板放不下或到处掉。
"""
AIR = "minecraft:air"
LIQUIDS = ("minecraft:water", "minecraft:flowing_water", "minecraft:lava", "minecraft:flowing_lava")
STURDY = ("minecraft:soul_sand", "minecraft:mud", "minecraft:scaffolding")      # 碰撞盒矮一截 / 没有，Java 的支撑形状却是整格
FLIMSY = ("minecraft:honey_block", "minecraft:cactus")                          # 基岩版的碰撞盒顶到 1，Java 的只到 15/16
SNOW = "minecraft:snow_layer"                                                    # aux 的低三位是层数 - 1：八层才是整格
EMPTY = ()                                                                       # 没有碰撞盒
LOW, HIGH, TOP = 7.0 / 16.0 + 1.0e-4, 9.0 / 16.0 - 1.0e-4, 1.0 - 1.0e-4          # 顶面正中的 2x2 像素（SupportType.CENTER 的 box(7, 0, 7, 9, 10, 9)）


def boxOf(collision, pos):
    """引擎 GetBlockCollision 的返回（{"min": [x, y, z], "max": [x, y, z]}，世界坐标）换成相对 pos 这一格的 (minX, minY, minZ, maxX, maxY, maxZ)；
    六个数全是 0（没有碰撞盒）是 EMPTY；没给 / 认不得是 None。"""
    try:
        numbers = [float(collision["min"][axis]) for axis in range(3)] + [float(collision["max"][axis]) for axis in range(3)]
    except (TypeError, KeyError, IndexError, ValueError):
        return None
    if not any(numbers):
        return EMPTY
    return tuple(numbers[index] - pos[index % 3] for index in range(6))


def _leaves(name):
    return "leaves" in name.split(":")[-1]


def survives(belowName, aux=0, box=None):
    """下面那一格是 belowName（方块的 identifier，没加载是 None）、附加值 aux、碰撞盒 box（boxOf 的结果）时，砧板站不站得住。"""
    if belowName is None:
        return True
    if belowName == AIR or belowName in LIQUIDS:
        return False
    if belowName in STURDY or (belowName == SNOW and int(aux or 0) & 7 == 7):
        return True
    if belowName in FLIMSY or _leaves(belowName):
        return False
    if belowName.startswith("minecraft:") and belowName.endswith("_stairs"):
        return bool(int(aux or 0) & 4)                    # upside_down_bit：倒着放的楼梯顶面是整块
    if box is None:
        return True
    if box == EMPTY:
        return False
    return box[1] < TOP <= box[4] and box[0] <= LOW and box[3] >= HIGH and box[2] <= LOW and box[5] >= HIGH
