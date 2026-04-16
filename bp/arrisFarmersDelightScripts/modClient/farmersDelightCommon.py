# -*- coding: utf-8 -*-
from ..QuModLibs.Client import *
from ..modCommon.modConfig import *

isJump = None
isClickingBlock = ()

recipeDict = {
    "arris:wheat_dough": {"itemName": "minecraft:bucket", "count": 1, "auxValue": 0},
    "arris:milk_bottle": {"itemName": "minecraft:bucket", "count": 1, "auxValue": 0},
    "arris:honey_cookie": {"itemName": "minecraft:glass_bottle", "count": 1, "auxValue": 0},
    "arris:stuffed_potato": {"itemName": "minecraft:glass_bottle", "count": 1, "auxValue": 0},
    "arris:salmon_roll": {"itemName": "minecraft:bowl", "count": 1, "auxValue": 0},
    "arris:cod_roll": {"itemName": "minecraft:bowl", "count": 1, "auxValue": 0}
}

@AllowCall
def OnPlaySound(args):
    soundName = args["soundName"]
    pos = args["pos"]
    compFactory.CreateCustomAudio(levelId).PlayCustomMusic(soundName, pos, 1, 1, False, None)

@AllowCall
def PlayParticle(pos):
    compFactory.CreateParticleSystem(None).Create("minecraft:crop_growth_emitter", pos)

@AllowCall
def SetEntityBlockMolang(args):
    pos = args["blockPos"]
    molang = args["molang"]
    name = args["name"]
    compFactory.CreateBlockInfo(levelId).SetEnableBlockEntityAnimations(pos, True)
    compFactory.CreateBlockInfo(levelId).SetBlockEntityMolangValue(pos, name, molang)

@AllowCall
def PlayAttackAnimationCommon(args):
    compFactory.CreatePlayer(playerId).Swing()

@Listen("LoadClientAddonScriptsAfter")
def LoadAddon(args):
    compFactory.CreateQueryVariable(levelId).Register('query.mod.item_display_mode', 0.0)
    compFactory.CreateQueryVariable(levelId).Register('query.mod.item_display_animation', 0.0)

@Listen("UiInitFinished")
def UiGuideBookInit(args):
    clientApi.RegisterUI("arris", "farmerDelightGuideBook", uiGuideBookPath, uiGuideBookScreen)
    from ..compat.jei.cutting_board import RegisterCuttingBoardRecipes
    RegisterCuttingBoardRecipes()
    from ..compat.jei.cooking_pot import RegisterCookingPotRecipes
    RegisterCookingPotRecipes()
    from ..compat.jei.skillet import RegisterSkilletRecipes
    RegisterSkilletRecipes()
    from ..compat.jei.stove import RegisterStoveRecipes
    RegisterStoveRecipes()

@Listen("ClientItemTryUseEvent")
def OnClientItemTryUse(args):
    itemDict = args["itemDict"]
    if itemDict["newItemName"] == "arris:farmer_delight_guide_book":
        compFactory.CreateCustomAudio(levelId).PlayCustomMusic("item.book.page_turn", (1, 1, 1), 1, 1, False, playerId)
        clientApi.PushScreen("arris", "farmerDelightGuideBook")

@Listen("ActorAcquiredItemClientEvent")
def OnActorAcquiredItem(args):
    itemDict = args["itemDict"]
    acquireMethod = args["acquireMethod"]
    if acquireMethod == 2:
        itemName = itemDict["newItemName"]
        if itemName in recipeDict:
            dimensionId = compFactory.CreateGame(levelId).GetCurrentDimension()
            playerPos = compFactory.CreatePos(playerId).GetFootPos()
            giveItemDict = recipeDict[itemName]
            data = {
                "itemDict": giveItemDict,
                "playerId": playerId,
                "dimensionId": dimensionId,
                "playerPos": playerPos
            }
            Call("PlayerShapedRecipe", data)

@Listen("ClientJumpButtonPressDownEvent")
def ClientJumpButtonPressDown(args):
    global isJump
    isJump = True
    data = {"playerId": playerId, "isJump": isJump}
    Call("SetPlayerIsJumpExtra", data)

@Listen("ClientJumpButtonReleaseEvent")
def ClientJumpButtonRelease(args):
    global isJump
    isJump = False
    data = {"playerId": playerId, "isJump": isJump}
    Call("SetPlayerIsJumpExtra", data)

@Listen("ModBlockEntityLoadedClientEvent")
def OnBlockEntityLoaded(args):
    blockPos = (args["posX"], args["posY"], args["posZ"])
    blockName = args["blockName"]
    comp = compFactory.CreateBlockInfo(levelId)
    blockEntityData = comp.GetBlockEntityData(blockPos)
    if not blockEntityData:
        return
    if blockName in ["arris:skillet", "arris:cooking_pot"]:
        comp.SetEnableBlockEntityAnimations(blockPos, True)
        heatParticleEnableData = blockEntityData["exData"].get("heatParticleEnable")
        if heatParticleEnableData:
            blockHeatValue = heatParticleEnableData["__value__"]
            comp.SetBlockEntityMolangValue(blockPos, "variable.mod_heat", blockHeatValue)
        shelfEnableData = blockEntityData["exData"].get("shelfEnable")
        if shelfEnableData:
            blockShelfEnable = shelfEnableData["__value__"]
            comp.SetBlockEntityMolangValue(blockPos, "variable.mod_shelf", blockShelfEnable)
    elif blockName in ["arris:apple_pie", "arris:chocolate_pie", "arris:sweet_berry_cheesecake"]:
        blockPieStatus = blockEntityData["exData"]["blockStatus"]["__value__"]
        comp.SetEnableBlockEntityAnimations(blockPos, True)
        comp.SetBlockEntityMolangValue(blockPos, "variable.mod_pie", blockPieStatus)
