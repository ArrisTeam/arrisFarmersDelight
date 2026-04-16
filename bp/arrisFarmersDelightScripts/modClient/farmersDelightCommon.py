# -*- coding: utf-8 -*-
from ..QuModLibs.Client import *
from ..modCommon.modConfig import *

isJump = None
isClickingBlock = ()

@AllowCall
def OnPlaySound(args):
    # 服务端现在广播给所有玩家，这里按维度本地过滤，跨维度的声音本端直接丢弃
    dmId = args.get("dimensionId")
    if dmId is not None and dmId != compFactory.CreateGame(levelId).GetCurrentDimension():
        return
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
        if itemName in shapedRecipeContainerDict:
            # 只把触发物品名传给服务端；playerId / 维度 / 坐标 / 容器物品 均由服务端自行确定，防止伪造
            Call("PlayerShapedRecipe", {"triggerItemName": itemName})

@Listen("ClientJumpButtonPressDownEvent")
def ClientJumpButtonPressDown(args):
    global isJump
    isJump = True
    # playerId 由服务端通过 @InjectHttpPlayerId 注入，客户端不再传
    Call("SetPlayerIsJumpExtra", {"isJump": isJump})

@Listen("ClientJumpButtonReleaseEvent")
def ClientJumpButtonRelease(args):
    global isJump
    isJump = False
    Call("SetPlayerIsJumpExtra", {"isJump": isJump})

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
