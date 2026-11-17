# -*- coding: utf-8 -*-
"""StoveFacing - 炉灶的朝向：方块的 aux -> 站点朝哪（双端，纯规则）

JE 的炉灶站点是 Orientation.BLOCK（HoD 的 StoveStation）：站点的北面永远是炉灶方块的正面（FD 的 FACING 属性），场景按"炉灶朝北"写
（stove.json），从哪一侧右键镜头都飞到正面；厨锅、砧板才是 PLAYER（朝着玩家站的那一侧）。
基岩版的炉灶是 netease:face_directional 的 direction 状态（就是方块的 aux）：0 南、1 西、2 北、3 东，写在 north 的贴图（点着的火口）
出现在世界的那一面（Strata 引擎知识库 BLOCK_LEGACY_ENGINE §10.2），所以炉灶的"正面"朝哪就是 PotModelMath.facingOf(aux)；
站点朝向（度，北 0 / 东 90 / 南 180 / 西 270，Diegesis 的 stationToWorld）就是这一面的方向。
客户端的朝向钩子（GrillView.facingOf，读 GetBlock 的 aux）和服务端的（GrillOpen.facingOf，读 GetBlockNew 的 aux）都过 yawOfAux，说同一个答案。
"""
from . import PotModelMath as Pot

YAWS = {Pot.NORTH: 0, Pot.EAST: 90, Pot.SOUTH: 180, Pot.WEST: 270}      # 正面朝哪 -> 站点朝向（度）


def yawOfAux(aux):
    """炉灶方块的 aux（direction 状态）-> 站点朝向（度）：站点的北面转到炉灶的正面那一侧。aux 读不到按 0（引擎的缺省状态，朝南）。"""
    return YAWS[Pot.facingOf(aux)]
