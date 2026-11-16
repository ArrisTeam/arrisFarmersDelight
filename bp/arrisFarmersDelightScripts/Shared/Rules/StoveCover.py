# -*- coding: utf-8 -*-
"""StoveCover - 炉灶上面那格算不算盖住了烤架（双端，纯规则）

FD 的 AbstractStoveBlock.isStoveTopCovered：上面那格方块的形状碰到烤架区（那格最底下 1 像素、中间 10x10）就算盖住——
锅（2..14 x 0..10）、煎锅（1..15 x 0..4）、砧板、地毯、火把、花、台阶的下半都碰得到；空气、水、岩浆、顶半砖碰不到。
盖住了：烤架不是烤架（HoD 的炉灶站点不开、摆不上去），FD 每刻把烤架上的东西全丢出来（AbstractStoveBlockEntity.serverTick 的
shouldDropItems -> dropAllItems）。基岩版只认方块名，形状认不出：除了空气和液体都算盖住（顶半砖这类边角会多算）。
站点（GrillStation.opens / GrillLogic）、经典玩法（Server/Stove.py）、客户端开站的判断都用这一个函数，两边对得上。
"""
NOT_COVERING = frozenset(("minecraft:air", "minecraft:cave_air", "minecraft:void_air", "minecraft:water", "minecraft:flowing_water",
                          "minecraft:lava", "minecraft:flowing_lava", "minecraft:light_block"))


def covers(blockName):
    """这个名字的方块放在炉灶正上方，算不算盖住了烤架（没有名字 = 没加载 = 不算）。"""
    return bool(blockName) and blockName not in NOT_COVERING
