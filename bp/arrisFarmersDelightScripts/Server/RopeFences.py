# -*- coding: utf-8 -*-
"""RopeFences - 绳栅栏门：右键开关、换声音（服务端）

规则在 Shared/Rules/RopeFence.py。栅栏本身不需要脚本：连不连邻居、碰撞盒都由方块 JSON 里的 netease:connection / netease:aabb 和模型的
query.is_connect 在引擎里算。门是两个方块（关着 / 开着），右键就是换成另一个并把朝向写回去。
"""
from .EventRegistry import registerHandler
from .Helpers.Engine import compFactory, levelId
from .Helpers.Fx import ToAllPlayerPlaySound
from .Helpers.Player import SetPlayerUsedCD
from ..Shared.Rules import RopeFence
from ..Shared.Rules.Placement import facingOfYaw


@registerHandler("ServerBlockUseEvent", match=RopeFence.GATES)
def OnUseRopeFenceGate(args):
    args["cancel"] = True                      # 用了门就不再把手里的方块放到门旁边（JE：use 成功后不会再 useOn）
    playerId = args["playerId"]
    if SetPlayerUsedCD(playerId) is True:
        return
    pos = (args["x"], args["y"], args["z"])
    dimensionId = args["dimensionId"]
    states = compFactory.CreateBlockState(levelId).GetBlockStates(pos, dimensionId)
    rot = compFactory.CreateRot(playerId).GetRot()
    if not states or "direction" not in states or not rot:
        return
    name, direction, sound = RopeFence.toggleGate(args["blockName"], states["direction"], facingOfYaw(rot[1]))
    compFactory.CreateBlockInfo(levelId).SetBlockNew(pos, {"name": name}, 0, dimensionId)
    states = compFactory.CreateBlockState(levelId).GetBlockStates(pos, dimensionId) or {}
    states["direction"] = direction
    compFactory.CreateBlockState(levelId).SetBlockStates(pos, states, dimensionId)
    ToAllPlayerPlaySound(dimensionId, (pos[0] + 0.5, pos[1] + 0.5, pos[2] + 0.5), sound)
