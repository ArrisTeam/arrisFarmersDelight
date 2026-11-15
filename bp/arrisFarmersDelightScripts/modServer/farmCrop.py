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

    elif blockName == "arris:rice_supporting":
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
            elif cropsDict[blockName]:
                # 成熟阶段（以及沃土）在 cropsDict 里映射到空字符串，不再往下长
                comp.SetBlockNew((x, y, z), {"name": cropsDict[blockName]}, 0, dimensionId, False, False)

    if blockName == "arris:rich_soil_farmland":
        # 找到水源即可停止扫描（干 → 湿），原 81 格全扫现在平均 1-2 次即命中
        found = False
        for dx in xrange(-4, 5):
            for dz in xrange(-4, 5):
                if dx == 0 and dz == 0:
                    continue
                blockDict = comp.GetLiquidBlock((x + dx, y, z + dz), dimensionId)
                if blockDict and blockDict["name"] in ("minecraft:water", "minecraft:flowing_water"):
                    found = True
                    break
            if found:
                break
        if found:
            comp.SetBlockNew((x, y, z), {"name": "arris:rich_soil_farmland_moist"}, 0, dimensionId, False, False)

    elif blockName == "arris:rich_soil_farmland_moist":
        # 只有确认 81 格都无水才能切回干燥；扫描无法短路
        found = False
        for dx in xrange(-4, 5):
            for dz in xrange(-4, 5):
                if dx == 0 and dz == 0:
                    continue
                blockDict = comp.GetLiquidBlock((x + dx, y, z + dz), dimensionId)
                if blockDict and blockDict["name"] in ("minecraft:water", "minecraft:flowing_water"):
                    found = True
                    break
            if found:
                break
        if not found:
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
        growth = blockStates.get("arris:growth") if blockStates else None
        if growth is not None and growth < 7:
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
        ApplyBoneMeal(playerId, itemDict, blockName, (x, y, z), dimensionId)

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
    if blockName == "arris:budding_tomatoes_stage6" or blockName == "arris:tomatoes_vine_stage3":
        if SetPlayerUsedCD(playerId) is True:
            return
        blockPos = (x + 0.5, y, z + 0.5)
        if carriedDict is None:
            carriedDict = {}
        itemName = carriedDict.get("newItemName")
        if itemName == "minecraft:bone_meal":
            # 和 ServerItemUseOnEvent 那条路径共用：谁先触发谁处理（冷却挡住另一条）
            ApplyBoneMeal(playerId, carriedDict, blockName, (x, y, z), dimensionId)
        else:
            count = random.randint(1, 2)
            System.CreateEngineItemEntity({"itemName": "arris:tomato", "count": count}, dimensionId, blockPos)
            ToAllPlayerPlaySound(dimensionId, blockPos, "block.sweet_berry_bush.pick")
            nextName = "arris:budding_tomatoes_stage3" if blockName == "arris:budding_tomatoes_stage6" else "arris:tomatoes_vine_stage0"
            compFactory.CreateBlockInfo(levelId).SetBlockNew((x, y, z), {"name": nextName}, 0, dimensionId, False, False)
        # ServerBlockUseEvent 的拦截字段是 cancel（ret 属于 ServerItemUseOnEvent）
        args["cancel"] = True

    elif blockName == "arris:cabbages_stage7":
        if SetPlayerUsedCD(playerId) is True:
            return
        blockPos = (x + 0.5, y, z + 0.5)
        count = random.randint(1, 2)
        System.CreateEngineItemEntity({"itemName": "arris:cabbage_leaf", "count": count}, dimensionId, blockPos)
        ToAllPlayerPlaySound(dimensionId, blockPos, "block.sweet_berry_bush.pick")
        compFactory.CreateBlockInfo(levelId).SetBlockNew((x, y, z), {"name": "arris:cabbages_stage3"}, 0, dimensionId, False, False)
        args["cancel"] = True

    elif blockName == "arris:rice_stage3":
        if SetPlayerUsedCD(playerId) is True:
            return
        if carriedDict is None:
            return
        if carriedDict.get("newItemName") == "minecraft:bone_meal":
            ApplyBoneMeal(playerId, carriedDict, blockName, (x, y, z), dimensionId)

def _BoneMealEffect(dimensionId, pos):
    ToAllPlayerPlaySound(dimensionId, pos, "item.bone_meal.use")
    Call("*", "PlayParticle", pos)

def ApplyBoneMeal(playerId, itemDict, blockName, blockPos, dimensionId):
    # 对本模组作物使用骨粉。只有真的长了才扣骨粉；返回是否生效
    x, y, z = blockPos
    comp = compFactory.CreateBlockInfo(levelId)
    if blockName in ("arris:budding_tomatoes_stage6", "arris:tomatoes_vine_stage3"):
        # 成熟的番茄：上方有绳子时沿绳子长出一节藤
        if comp.GetBlockNew((x, y + 1, z), dimensionId)["name"] != "arris:rope":
            return False
        comp.SetBlockNew((x, y + 1, z), {"name": "arris:tomatoes_vine_stage0"}, 0, dimensionId, False, False)
        _BoneMealEffect(dimensionId, (x + 0.5, y + 1, z + 0.5))
        SetNotCreateItem(playerId, itemDict)
        return True
    if blockName == "arris:rice_stage3":
        # 成熟的稻苗：上方是空气时长出稻穗，与随机刻长穗的结果一致（下半变为 rice_supporting）
        if comp.GetBlockNew((x, y + 1, z), dimensionId)["name"] != "minecraft:air":
            return False
        comp.SetBlockNew((x, y, z), {"name": "arris:rice_supporting"}, 0, dimensionId, False, False)
        comp.SetBlockNew((x, y + 1, z), {"name": "arris:rice_upper_crop_stage0"}, 0, dimensionId, False, False)
        _BoneMealEffect(dimensionId, (x + 0.5, y + 1, z + 0.5))
        SetNotCreateItem(playerId, itemDict)
        return True
    blockStates = compFactory.CreateBlockState(levelId).GetBlockStates(blockPos, dimensionId)
    growth = blockStates.get("arris:growth") if blockStates else None
    if growth is not None and growth < 7:
        blockStates["arris:growth"] = min(7, growth + random.randint(2, 4))
        compFactory.CreateBlockState(levelId).SetBlockStates(blockPos, blockStates, dimensionId)
        _BoneMealEffect(dimensionId, (x + 0.5, y + 0.5, z + 0.5))
        SetNotCreateItem(playerId, itemDict)
        return True
    if blockName in cropsDict:
        data = {"blockName": blockName, "playerId": playerId, "itemDict": itemDict, "dimensionId": dimensionId, "blockPos": blockPos}
        return CropAccelerateTheRipening(data)
    return False

# 可催熟作物：方块名前缀（去掉末尾阶段数字）→ 最大阶段
CropMaxStageDict = {
    "arris:cabbages_stage": 7,
    "arris:budding_tomatoes_stage": 6,
    "arris:tomatoes_vine_stage": 3,
    "arris:onions_stage": 3,
    "arris:rich_soil_wheat": 7,
    "arris:rich_soil_beetroot": 3,
    "arris:rich_soil_carrots": 3,
    "arris:rich_soil_potatoes": 3,
    "arris:rice_stage": 3,
    "arris:rice_upper_crop_stage": 3,
    "arris:rich_soil_torchflower": 2,
}

def CropAccelerateTheRipening(data, mode=None):
    # 作物催熟：骨粉一次长 2-3 级，湿润沃土耕地每次随机刻额外长 1 级。
    # 已成熟或不认识的方块不处理、不扣骨粉；返回是否长了
    blockName = data["blockName"]
    playerId = data["playerId"]
    itemDict = data["itemDict"]
    dimensionId = data["dimensionId"]
    x, y, z = data["blockPos"]
    prefix, stageText = blockName[:-1], blockName[-1:]
    maxStage = CropMaxStageDict.get(prefix)
    if maxStage is None or not stageText.isdigit():
        return False
    stage = int(stageText)
    if stage >= maxStage:
        return False
    num = 1 if mode == "rich_soil_farmland" else random.randint(2, 3)
    stage = min(maxStage, stage + num)
    compFactory.CreateBlockInfo(levelId).SetBlockNew((x, y, z), {"name": prefix + str(stage)}, 0, dimensionId, False, False)
    _BoneMealEffect(dimensionId, (x + 0.5, y, z + 0.5))
    if playerId:
        SetNotCreateItem(playerId, itemDict)
    return True

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
