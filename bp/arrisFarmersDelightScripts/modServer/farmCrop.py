# -*- coding: utf-8 -*-
from serverUtils.serverUtils import *
import random

@Listen("BlockNeighborChangedServerEvent")
def OnBlockNeighborChanged(args):
    # 检测农作物周围方块变化
    blockName = args["blockName"]
    blockPos = (args["posX"], args["posY"], args["posZ"])
    dimensionId = args["dimensionId"]
    neighborPos = (args["neighborPosX"], args["neighborPosY"], args["neighborPosZ"])
    neighborName = args["toBlockName"]
    if blockName in WildCropDict:
        if neighborPos == (args["posX"], args["posY"] - 1, args["posZ"]):
            if neighborName not in WildCropDict[blockName]:
                compFactory.CreateBlockInfo(levelId).SetBlockNew(blockPos, {"name": "minecraft:air"}, 1, dimensionId)

        toBlockName = args["toBlockName"]
        if toBlockName == "minecraft:snow_layer":
            # 当作物上方的方块变化为顶层雪时清除
            if neighborPos == (args["posX"], args["posY"] + 1, args["posZ"]):
                compFactory.CreateBlockInfo(levelId).SetBlockNew(neighborPos, {"name": "minecraft:air"}, 0, dimensionId, False, False)

    elif blockName in cropsDict:
        if neighborPos == (args["posX"], args["posY"] - 1, args["posZ"]):
            if neighborName not in ["minecraft:farmland", "arris:rich_soil_farmland_moist", "arris:rich_soil_farmland", "minecraft:grass_block"]:
                compFactory.CreateBlockInfo(levelId).SetBlockNew(blockPos, {"name": "minecraft:air"}, 1, dimensionId)

    elif blockName in "arris:rice_supporting":
        neighborName = args["toBlockName"]
        if neighborPos == (args["posX"], args["posY"] - 1, args["posZ"]):
            if neighborName not in ["minecraft:farmland", "minecraft:grass_block", "minecraft:dirt"]:
                compFactory.CreateBlockInfo(levelId).SetBlockNew(blockPos, {"name": "minecraft:air"}, 1, dimensionId)
        elif neighborPos == (args["posX"], args["posY"] + 1, args["posZ"]):
            if neighborName not in ["arris:rice_upper_crop_stage0", "arris:rice_upper_crop_stage1", "arris:rice_upper_crop_stage2", "arris:rice_upper_crop_stage3"]:
                compFactory.CreateBlockInfo(levelId).SetBlockNew(blockPos, {"name": "arris:rice_stage3"}, 0, dimensionId, False, False)

    elif blockName in ["arris:red_mushroom_colony", "arris:brown_mushroom_colony"]:
        if neighborPos == (args["posX"], args["posY"] - 1, args["posZ"]):
            compFactory.CreateBlockInfo(levelId).SetBlockNew(blockPos, {"name": "minecraft:air"}, 1, dimensionId)

@Listen("BlockRandomTickServerEvent")
def OnBlockRandomTick(args):
    # 农作物自然生长以及有机肥料变为沃土
    blockName = args["fullName"]
    x, y, z = args["posX"], args["posY"], args["posZ"]
    dimensionId = args["dimensionId"]
    comp = compFactory.CreateBlockInfo(levelId)
    if blockName in cropsDict:
        if 9 <= args["brightness"] <= 15:
            if blockName == "arris:budding_tomatoes_stage6":
                blockDict = comp.GetBlockNew((x, y + 1, z), dimensionId)
                if blockDict["name"] == "arris:rope":
                    comp.SetBlockNew((x, y + 1, z), {"name": "arris:tomatoes_vine_stage0"}, 0, dimensionId, False, False)
            elif blockName == "arris:tomatoes_vine_stage3":
                blockDict = comp.GetBlockNew((x, y + 1, z), dimensionId)
                if blockDict["name"] == "arris:rope":
                    comp.SetBlockNew((x, y + 1, z), {"name": "arris:tomatoes_vine_stage0"}, 0, dimensionId, False, False)
            elif blockName == "arris:rice_stage3":
                blockDict = comp.GetBlockNew((x, y + 1, z), dimensionId)
                if blockDict["name"] == "minecraft:air":
                    comp.SetBlockNew((x, y, z), {"name": "arris:rice_supporting"}, 0, dimensionId, False, False)
                    comp.SetBlockNew((x, y + 1, z), {"name": "arris:rice_upper_crop_stage0"}, 0, dimensionId, False, False)
            else:
                comp.SetBlockNew((x, y, z), {"name": cropsDict[blockName]}, 0, dimensionId, False, False)

    if blockName == "arris:rich_soil_farmland":
        PosList = [(x + testX, y, z + testZ) for testX in xrange(-4, 5) for testZ in xrange(-4, 5)]
        PosList.remove((x, y, z))
        blockList = []
        for pos in PosList:
            blockDict = comp.GetLiquidBlock(pos, dimensionId)
            if not blockDict:
                continue
            blockList.append(blockDict["name"])
        if "minecraft:water" in blockList or "minecraft:flowing_water" in blockList:
            comp.SetBlockNew((x, y, z), {"name": "arris:rich_soil_farmland_moist"}, 0, dimensionId, False, False)

    elif blockName == "arris:rich_soil_farmland_moist":
        PosList = [(x + testX, y, z + testZ) for testX in xrange(-4, 5) for testZ in xrange(-4, 5)]
        PosList.remove((x, y, z))
        blockList = []
        for pos in PosList:
            blockDict = comp.GetLiquidBlock(pos, dimensionId)
            if not blockDict:
                continue
            blockList.append(blockDict["name"])
        if "minecraft:water" not in blockList and "minecraft:flowing_water" not in blockList:
            comp.SetBlockNew((x, y, z), {"name": "arris:rich_soil_farmland"}, 0, dimensionId, False, False)

        upBlock = compFactory.CreateBlockInfo(levelId).GetBlockNew((x, y + 1, z), dimensionId)
        data = {
            "blockName": upBlock["name"],
            "playerId": None,
            "itemDict": None,
            "dimensionId": dimensionId,
            "blockPos": (x, y + 1, z)
        }
        if upBlock["name"] in cropsDict:
            CropAccelerateTheRipening(data, "rich_soil_farmland")

        blockStates = compFactory.CreateBlockState(levelId).GetBlockStates((x, y + 1, z), dimensionId)
        if blockStates:
            growth = blockStates.get("arris:growth")
            if growth and growth < 7:
                blockStates["arris:growth"] += 1
                compFactory.CreateBlockState(levelId).SetBlockStates((x, y + 1, z), blockStates, dimensionId)
                ToAllPlayerPlaySound(dimensionId, (x + 0.5, y + 1.5, z + 0.5), "item.bone_meal.use")
                Call("*", "PlayParticle",(x + 0.5, y + 1.5, z + 0.5))

    elif blockName in ["arris:red_mushroom_colony", "arris:brown_mushroom_colony"]:
        blockStates = compFactory.CreateBlockState(levelId).GetBlockStates((x, y, z), dimensionId)
        growth = blockStates["arris:growth"]
        if growth < 7:
            blockStates["arris:growth"] += 1
            compFactory.CreateBlockState(levelId).SetBlockStates((x, y, z), blockStates, dimensionId)

@Listen("ServerItemUseOnEvent")
def OnServerItemUse(args):
    # 玩家在对方块使用物品之前服务端抛出的事件
    itemDict = args["itemDict"]
    itemName = itemDict["newItemName"]
    dimensionId = args["dimensionId"]
    x = args["x"]
    y = args["y"]
    z = args["z"]
    playerId = args["entityId"]
    blockName = args["blockName"]
    face = args["face"]
    if itemName == "arris:rice":
        if SetPlayerUsedCD(playerId) is True:
            return
        if blockName in ["minecraft:dirt", "minecraft:grass_block", "arris:rich_soil"] and face == 1:
            upBlock = compFactory.CreateBlockInfo(levelId).GetBlockNew((x, y + 1, z), dimensionId)
            if upBlock["name"] == "minecraft:water":
                SetNotCreateItem(playerId, itemDict)
                ToAllPlayerPlaySound(dimensionId, (x + 0.5, y + 1, z + 0.5), "dig.grass")
                compFactory.CreateBlockInfo(levelId).SetBlockNew((x, y + 1, z), {"name": "arris:rice_stage0"}, 0, dimensionId, False, False)
            else:
                compFactory.CreateGame(playerId).SetOneTipMessage(playerId, "水稻需要种植在静止的水中")
        else:
            compFactory.CreateGame(playerId).SetOneTipMessage(playerId, "水稻貌似无法种植在这个方块上...")

    elif itemName == "minecraft:bone_meal":
        if SetPlayerUsedCD(playerId) is True:
            return
        data = {
            "blockName": blockName,
            "playerId": playerId,
            "itemDict": itemDict,
            "dimensionId": dimensionId,
            "blockPos": (x, y, z)
        }
        blockStates = compFactory.CreateBlockState(levelId).GetBlockStates((x, y, z), dimensionId)
        if blockStates:
            growth = blockStates.get("arris:growth")
            if growth is not None and growth < 7:
                blockStates["arris:growth"] += random.randint(2, 4)
                if blockStates["arris:growth"] >= 7:
                    blockStates["arris:growth"] = 7
                compFactory.CreateBlockState(levelId).SetBlockStates((x, y, z), blockStates, dimensionId)
                Call("*", "PlayParticle",(x + 0.5, y + 0.5, z + 0.5))
                ToAllPlayerPlaySound(dimensionId, (x + 0.5, y + 0.5, z + 0.5), "item.bone_meal.use")
                SetNotCreateItem(playerId, itemDict)

        if blockName in cropsDict:
            CropAccelerateTheRipening(data)

    elif face == 1 and blockName in ["arris:organic_compost_stage0", "arris:organic_compost_stage1", "arris:organic_compost_stage2", "arris:organic_compost_stage3", "arris:rich_soil"]:
        if itemName == "minecraft:brown_mushroom":
            if SetPlayerUsedCD(playerId) is True:
                return
            SetNotCreateItem(playerId, itemDict)
            ToAllPlayerPlaySound(dimensionId, (x + 0.5, y + 0.5, z + 0.5), "dig.grass")
            compFactory.CreateBlockInfo(levelId).SetBlockNew((x, y + 1, z), {"name": "arris:brown_mushroom_colony"}, 0, dimensionId, False, False)
        elif itemName == "minecraft:red_mushroom":
            if SetPlayerUsedCD(playerId) is True:
                return
            SetNotCreateItem(playerId, itemDict)
            ToAllPlayerPlaySound(dimensionId, (x + 0.5, y + 0.5, z + 0.5), "dig.grass")
            compFactory.CreateBlockInfo(levelId).SetBlockNew((x, y + 1, z), {"name": "arris:red_mushroom_colony"}, 0, dimensionId, False, False)

@Listen("ItemUseOnAfterServerEvent")
def OnItemUseOnAfter(args):
    # 玩家在对方块使用物品之后服务端抛出的事件
    playerId = args["entityId"]
    itemDict = args["itemDict"]
    dimensionId = args["dimensionId"]
    x = args["x"]
    y = args["y"]
    z = args["z"]
    face = args["face"]
    blockName = args["blockName"]
    itemName = itemDict["newItemName"]
    itemType = GetItemType(itemDict)
    if blockName == "arris:rich_soil":
        if SetPlayerUsedCD(playerId) is True:
            return
        if itemType == "hoe":
            SetCarriedDurability(playerId, itemDict, dimensionId, (x, y, z))
            compFactory.CreateBlockInfo(levelId).SetBlockNew((x, y, z), {"name": "arris:rich_soil_farmland"}, 0, dimensionId, False, False)
            ToAllPlayerPlaySound(dimensionId, (x, y, z), "use.gravel")

    elif blockName == "arris:rich_soil_farmland_moist" or blockName == "arris:rich_soil_farmland":
        if SetPlayerUsedCD(playerId) is True:
            return
        upBlock = compFactory.CreateBlockInfo(levelId).GetBlockNew((x, y + 1, z), dimensionId)
        if upBlock["name"] == "minecraft:air":
            if face == 1:
                seedsDict = {
                    "minecraft:wheat_seeds": "arris:rich_soil_wheat0",
                    "minecraft:beetroot_seeds": "arris:rich_soil_beetroot0",
                    "minecraft:potato": "arris:rich_soil_potatoes0",
                    "minecraft:carrot": "arris:rich_soil_carrots0",
                    "minecraft:torchflower_seeds": "arris:rich_soil_torchflower0",
                }
                if itemName in seedsDict:
                    compFactory.CreateBlockInfo(levelId).SetBlockNew((x, y + 1, z), {"name": seedsDict[itemName]}, 0, dimensionId, False, False)
                    ToAllPlayerPlaySound(dimensionId, (x + 0.5, y + 1, z + 0.5), "dig.grass")
                    SetNotCreateItem(playerId, itemDict)

@Listen("ServerBlockUseEvent")
def OnServerBlockUse(args):
    # 成熟作物采摘
    blockName = args["blockName"]
    x = args["x"]
    y = args["y"]
    z = args["z"]
    dimensionId = args["dimensionId"]
    playerId = args["playerId"]
    carriedDict = compFactory.CreateItem(playerId).GetPlayerItem(serverApi.GetMinecraftEnum().ItemPosType.CARRIED, 0)
    if blockName == "arris:budding_tomatoes_stage6":
        if SetPlayerUsedCD(playerId) is True:
            return
        blockPos = (x + 0.5, y, z + 0.5)
        if carriedDict is None:
            carriedDict = {}
        itemName = carriedDict.get("newItemName")
        if itemName == "minecraft:bone_meal":
            blockDict = compFactory.CreateBlockInfo(levelId).GetBlockNew((x, y + 1, z), dimensionId)
            if blockDict["name"] == "arris:rope":
                ToAllPlayerPlaySound(dimensionId, (x + 0.5, y + 1, z + 0.5), "item.bone_meal.use")
                Call("*", "PlayParticle",(x + 0.5, y + 1, z + 0.5))
        else:
            count = random.randint(1, 2)
            System.CreateEngineItemEntity({"itemName": "arris:tomato", "count": count}, dimensionId, blockPos)
            ToAllPlayerPlaySound(dimensionId, blockPos, "block.sweet_berry_bush.pick")
            compFactory.CreateBlockInfo(levelId).SetBlockNew((x, y, z), {"name": "arris:budding_tomatoes_stage3"}, 0, dimensionId, False, False)
        args["ret"] = True

    elif blockName == "arris:tomatoes_vine_stage3":
        if SetPlayerUsedCD(playerId) is True:
            return
        blockPos = (x + 0.5, y, z + 0.5)
        if carriedDict is None:
            carriedDict = {}
        itemName = carriedDict.get("newItemName")
        if itemName == "minecraft:bone_meal":
            blockDict = compFactory.CreateBlockInfo(levelId).GetBlockNew((x, y + 1, z), dimensionId)
            if blockDict["name"] == "arris:rope":
                ToAllPlayerPlaySound(dimensionId, (x + 0.5, y + 1, z + 0.5), "item.bone_meal.use")
                Call("*", "PlayParticle",(x + 0.5, y + 1, z + 0.5))
                compFactory.CreateBlockInfo(levelId).SetBlockNew((x, y + 1, z), {"name": "arris:tomatoes_vine_stage0"}, 0, dimensionId, False, False)
        else:
            count = random.randint(1, 2)
            System.CreateEngineItemEntity({"itemName": "arris:tomato", "count": count}, dimensionId, blockPos)
            ToAllPlayerPlaySound(dimensionId, blockPos, "block.sweet_berry_bush.pick")
            compFactory.CreateBlockInfo(levelId).SetBlockNew((x, y, z), {"name": "arris:tomatoes_vine_stage0"}, 0, dimensionId, False, False)
        args["ret"] = True

    elif blockName == "arris:cabbages_stage7":
        if SetPlayerUsedCD(playerId) is True:
            return
        blockPos = (x + 0.5, y, z + 0.5)
        count = random.randint(1, 2)
        System.CreateEngineItemEntity({"itemName": "arris:cabbage_leaf", "count": count}, dimensionId, blockPos)
        ToAllPlayerPlaySound(dimensionId, blockPos, "block.sweet_berry_bush.pick")
        compFactory.CreateBlockInfo(levelId).SetBlockNew((x, y, z), {"name": "arris:cabbages_stage3"}, 0, dimensionId, False, False)
        args["ret"] = True

    elif blockName == "arris:rice_stage3":
        if SetPlayerUsedCD(playerId) is True:
            return
        if carriedDict is None:
            return
        itemName = carriedDict.get("newItemName")
        if itemName == "minecraft:bone_meal":
            blockDict = compFactory.CreateBlockInfo(levelId).GetBlockNew((x, y + 1, z), dimensionId)
            if blockDict["name"] == "minecraft:air":
                ToAllPlayerPlaySound(dimensionId, (x + 0.5, y + 1, z + 0.5), "item.bone_meal.use")
                Call("*", "PlayParticle",(x + 0.5, y + 1, z + 0.5))
                compFactory.CreateBlockInfo(levelId).SetBlockNew((x, y + 1, z), {"name": "arris:rice_upper_crop_stage0"}, 0, dimensionId, False, False)

def CropAccelerateTheRipening(data, mode=None):
    # 作物催熟
    blockName = data["blockName"]
    playerId = data["playerId"]
    itemDict = data["itemDict"]
    dimensionId = data["dimensionId"]
    x, y, z = data["blockPos"]
    stage = int(blockName[-1])
    num = random.randint(2, 3)
    if mode == "rich_soil_farmland":
        num = 1
    if playerId:
        SetNotCreateItem(playerId, itemDict)

    if blockName[:-1] == "arris:cabbages_stage":
        if stage < 7:
            stage += num
            if stage > 7:
                stage = 7
            blockName = blockName[:-1] + str(stage)
            compFactory.CreateBlockInfo(levelId).SetBlockNew((x, y, z), {"name": blockName}, 0, dimensionId, False, False)
            ToAllPlayerPlaySound(dimensionId, (x + 0.5, y, z + 0.5), "item.bone_meal.use")
            Call("*", "PlayParticle",(x + 0.5, y, z + 0.5))

    elif blockName[:-1] == "arris:budding_tomatoes_stage":
        if stage < 6:
            stage += num
            if stage >= 6:
                stage = 6
            blockName = blockName[:-1] + str(stage)
            compFactory.CreateBlockInfo(levelId).SetBlockNew((x, y, z), {"name": blockName}, 0, dimensionId, False, False)
            ToAllPlayerPlaySound(dimensionId, (x + 0.5, y, z + 0.5), "item.bone_meal.use")
            Call("*", "PlayParticle",(x + 0.5, y, z + 0.5))

    elif blockName[:-1] == "arris:tomatoes_vine_stage":
        if stage < 3:
            stage += num
            if stage >= 3:
                stage = 3
            blockName = blockName[:-1] + str(stage)
            compFactory.CreateBlockInfo(levelId).SetBlockNew((x, y, z), {"name": blockName}, 0, dimensionId, False, False)
            ToAllPlayerPlaySound(dimensionId, (x + 0.5, y, z + 0.5), "item.bone_meal.use")
            Call("*", "PlayParticle",(x + 0.5, y, z + 0.5))

    elif blockName[:-1] == "arris:onions_stage":
        if stage < 3:
            stage += num
            if stage >= 3:
                stage = 3
            blockName = blockName[:-1] + str(stage)
            compFactory.CreateBlockInfo(levelId).SetBlockNew((x, y, z), {"name": blockName}, 0, dimensionId, False, False)
            ToAllPlayerPlaySound(dimensionId, (x + 0.5, y, z + 0.5), "item.bone_meal.use")
            Call("*", "PlayParticle",(x + 0.5, y, z + 0.5))

    elif blockName[:-1] == "arris:rich_soil_wheat":
        if stage < 7:
            stage += num
            if stage >= 7:
                stage = 7
            blockName = blockName[:-1] + str(stage)
            compFactory.CreateBlockInfo(levelId).SetBlockNew((x, y, z), {"name": blockName}, 0, dimensionId, False, False)
            ToAllPlayerPlaySound(dimensionId, (x + 0.5, y, z + 0.5), "item.bone_meal.use")
            Call("*", "PlayParticle",(x + 0.5, y, z + 0.5))

    elif blockName[:-1] == "arris:rich_soil_beetroot":
        if stage < 3:
            stage += num
            if stage >= 3:
                stage = 3
            blockName = blockName[:-1] + str(stage)
            compFactory.CreateBlockInfo(levelId).SetBlockNew((x, y, z), {"name": blockName}, 0, dimensionId, False, False)
            ToAllPlayerPlaySound(dimensionId, (x + 0.5, y, z + 0.5), "item.bone_meal.use")
            Call("*", "PlayParticle",(x + 0.5, y, z + 0.5))

    elif blockName[:-1] == "arris:rich_soil_carrots":
        if stage < 3:
            stage += num
            if stage >= 3:
                stage = 3
            blockName = blockName[:-1] + str(stage)
            compFactory.CreateBlockInfo(levelId).SetBlockNew((x, y, z), {"name": blockName}, 0, dimensionId, False, False)
            ToAllPlayerPlaySound(dimensionId, (x + 0.5, y, z + 0.5), "item.bone_meal.use")
            Call("*", "PlayParticle",(x + 0.5, y, z + 0.5))

    elif blockName[:-1] == "arris:rich_soil_potatoes":
        if stage < 3:
            stage += num
            if stage >= 3:
                stage = 3
            blockName = blockName[:-1] + str(stage)
            compFactory.CreateBlockInfo(levelId).SetBlockNew((x, y, z), {"name": blockName}, 0, dimensionId, False, False)
            ToAllPlayerPlaySound(dimensionId, (x + 0.5, y, z + 0.5), "item.bone_meal.use")
            Call("*", "PlayParticle",(x + 0.5, y, z + 0.5))

    elif blockName[:-1] == "arris:rice_stage":
        if stage < 3:
            stage += num
            if stage >= 3:
                stage = 3
            blockName = blockName[:-1] + str(stage)
            compFactory.CreateBlockInfo(levelId).SetBlockNew((x, y, z), {"name": blockName}, 0, dimensionId, False, False)
            ToAllPlayerPlaySound(dimensionId, (x + 0.5, y, z + 0.5), "item.bone_meal.use")
            Call("*", "PlayParticle",(x + 0.5, y, z + 0.5))

    elif blockName[:-1] == "arris:rice_upper_crop_stage":
        if stage < 3:
            stage += num
            if stage >= 3:
                stage = 3
            blockName = blockName[:-1] + str(stage)
            compFactory.CreateBlockInfo(levelId).SetBlockNew((x, y, z), {"name": blockName}, 0, dimensionId, False, False)
            ToAllPlayerPlaySound(dimensionId, (x + 0.5, y, z + 0.5), "item.bone_meal.use")
            Call("*", "PlayParticle",(x + 0.5, y, z + 0.5))

    elif blockName[:-1] == "arris:rich_soil_torchflower":
        if stage < 2:
            stage += num
            if stage >= 2:
                stage = 2
            blockName = blockName[:-1] + str(stage)
            compFactory.CreateBlockInfo(levelId).SetBlockNew((x, y, z), {"name": blockName}, 0, dimensionId, False, False)
            ToAllPlayerPlaySound(dimensionId, (x + 0.5, y, z + 0.5), "item.bone_meal.use")
            Call("*", "PlayParticle",(x + 0.5, y, z + 0.5))

@Listen("DestroyBlockEvent")
def OnDestroyBlock(args):
    # 防止精准采集挖掘龙腿掉落
    blockName = args["fullName"]
    if blockName not in ["arris:brown_mushroom_colony", "arris:red_mushroom_colony"]:
        return
    playerId = args["playerId"]
    handItemDict = compFactory.CreateItem(playerId).GetPlayerItem(serverApi.GetMinecraftEnum().ItemPosType.CARRIED, 0, True)
    if handItemDict is None:
        return
    enchantData = handItemDict.get("enchantData")
    if not enchantData:
        return
    for enchant in enchantData:
        if enchant[0] == 16:
            dropItemList = args["dropEntityIds"]
            for Id in dropItemList:
                DestroyEntity(Id)
