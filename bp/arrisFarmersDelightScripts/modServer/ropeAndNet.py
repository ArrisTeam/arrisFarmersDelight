# -*- coding: utf-8 -*-
from serverUtils.serverUtils import *

@AllowCall
@InjectHttpPlayerId
def SetPlayerIsJumpExtra(playerId, data):
    # 安全加固：playerId 由服务端从 HTTP 上下文注入，不再信任客户端传入
    if not playerId:
        return
    isJump = data.get("isJump") if isinstance(data, dict) else None
    if isJump is None:
        return
    compFactory.CreateExtraData(playerId).SetExtraData("isJump", isJump)

@Listen("OnEntityInsideBlockServerEvent")
def OnEntityInsideBlockServer(args):
    # 攀爬绳子
    blockName = args["blockName"]
    entityId = args["entityId"]
    if blockName in canClimbList:
        isJump = compFactory.CreateExtraData(entityId).GetExtraData("isJump")
        if isJump is True:
            compFactory.CreateActorMotion(entityId).SetPlayerMotion((0, 0.15, 0))
        else:
            isFly = compFactory.CreateFly(entityId).IsPlayerFlying()
            if isFly is False:
                compFactory.CreateActorMotion(entityId).SetPlayerMotion((0, -0.15, 0))

@Listen("MobGriefingBlockServerEvent")
def OnMobGriefingBlockRope(args):
    # 取消玩家在攀爬绳子掉落时，踩坏耕地
    entityId = args["entityId"]
    blockName = args["blockName"]
    if blockName == "minecraft:farmland":
        dimensionId = args["dimensionId"]
        x, y, z = compFactory.CreatePos(entityId).GetPos()
        upBlockName = compFactory.CreateBlockInfo(levelId).GetBlockNew((x // 1, (y // 1), z // 1), dimensionId)["name"]
        if upBlockName in canClimbList:
            args["cancel"] = True

@Listen("OnBeforeFallOnBlockServerEvent")
def OnBeforeFallOnSafetyNet(args):
    # 将掉落在安全网上的实体弹起来，并取消伤害
    entityId = args["entityId"]
    blockName = args["blockName"]
    if blockName == "arris:safety_net":
        fallDistance = args["fallDistance"]
        entityName = compFactory.CreateEngineType(entityId).GetEngineTypeStr()
        if entityName == "minecraft:player":
            isSneaking = serverApi.GetEngineCompFactory().CreatePlayer(entityId).isSneaking()
            if isSneaking is False and fallDistance > 0.5:
                if fallDistance <= 10:
                    fallDistance *= 0.1
                elif 10 < fallDistance <= 50:
                    fallDistance *= 0.05
                else:
                    fallDistance *= 0.01
                compFactory.CreateActorMotion(entityId).SetPlayerMotion((0, fallDistance, 0))
                args["cancel"] = True
        else:
            if fallDistance > 0.5:
                if fallDistance <= 10:
                    fallDistance *= 0.1
                elif 10 < fallDistance <= 50:
                    fallDistance *= 0.05
                else:
                    fallDistance *= 0.01
                compFactory.CreateActorMotion(entityId).SetMotion((0, fallDistance, 0))
                args["cancel"] = True

@Listen("ServerBlockUseEvent")
def OnServerRopeUse(args):
    blockName = args["blockName"]
    x = args["x"]
    y = args["y"]
    z = args["z"]
    playerId = args["playerId"]
    dimensionId = args["dimensionId"]
    if blockName == "arris:rope":
        if SetPlayerUsedCD(playerId) is True:
            return
        # 通过绳子连接的钟可以敲响
        blockList = []
        for i in range(y, y + 25):
            blockDict = compFactory.CreateBlockInfo(levelId).GetBlockNew((x, i, z), dimensionId)
            blockList.append(blockDict["name"])
        if "minecraft:bell" in blockList:
            index = blockList.index("minecraft:bell")
            blockList = blockList[0:index + 1]
            count = blockList.count("arris:rope")
            length = len(blockList) - 1
            if count == length:
                System.CreateEngineEntityByTypeStr("arris:toll_entity", (x + 0.5, y + index + 0.6, z + 0.5), (0, 0), dimensionId)

@Listen("DamageEvent")
def OnFallDamageInClimb(args):
    # 取消玩家在攀爬绳子时的掉落伤害
    entityId = args["entityId"]
    identifier = compFactory.CreateEngineType(entityId).GetEngineTypeStr()
    if identifier == "minecraft:player":
        if args["cause"] == "fall":
            x, y, z = compFactory.CreatePos(entityId).GetPos()
            dimensionId = compFactory.CreateDimension(entityId).GetEntityDimensionId()
            blockName = compFactory.CreateBlockInfo(levelId).GetBlockNew((x // 1, (y // 1), z // 1), dimensionId)["name"]
            if blockName in canClimbList:
                args["damage"] = 0
