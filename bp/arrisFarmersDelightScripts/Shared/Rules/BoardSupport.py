# -*- coding: utf-8 -*-
"""BoardSupport - 砧板下面撑不撑得住：放得下放不下、会不会掉（双端，纯规则）

JE 的 CuttingBoardBlock（java:121-135）：canSurvive = canSupportRigidBlock(下面) || canSupportCenter(下面, UP)。放的时候不满足就放不下（BlockItem.canPlace），
下面的方块变了（updateShape 的 facing == DOWN）不满足就当场被拆：掉板自己，板上的东西从方块里散落（onRemove 的 Containers.dropItemStack）。
引擎没有"这一面撑得住撑不住"的查询：能用的 GetBlockCollision 对没有碰撞盒的方块回什么、对原版的半砖 / 栅栏 / 楼梯回什么都没实测过，判错了会让板放不下或到处掉，
所以这里只认两件确定的事：下面是空气、下面是液体——这两样的顶面什么也撑不住。别的方块（含 JE 里也撑不住的下半砖、地毯、火把）照旧当撑得住；下面没加载（None）不判。
"""
AIR = "minecraft:air"
LIQUIDS = ("minecraft:water", "minecraft:flowing_water", "minecraft:lava", "minecraft:flowing_lava")


def survives(belowName):
    """下面那一格是 belowName（方块的 identifier，没加载是 None）时，砧板站不站得住。"""
    return belowName is None or (belowName != AIR and belowName not in LIQUIDS)
