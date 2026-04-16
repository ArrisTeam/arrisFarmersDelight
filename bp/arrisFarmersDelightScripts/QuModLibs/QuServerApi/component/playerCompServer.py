# -*- coding: utf-8 -*-

from common.component.baseComponent import BaseComponent

class PlayerCompServer(BaseComponent):
    def GetPlayerHunger(self):
        # type: () -> float
        """
        获取玩家饥饿度，展示在UI饥饿度进度条上，初始值为20，即每一个鸡腿代表2个饥饿度。 **饱和度(saturation)** ：玩家当前饱和度，初始值为5，最大值始终为玩家当前饥饿度(hunger)，该值直接影响玩家**饥饿度(hunger)**。<br>1）增加方法：吃食物。<br>2）减少方法：每触发一次**消耗事件**，该值减少1，如果该值不大于0，直接把玩家 **饥饿度(hunger)** 减少1。
        """
        pass

    def SetPlayerHunger(self, value):
        # type: (float) -> bool
        """
        设置玩家饥饿度。
        """
        pass

    def GetPlayerMaxExhaustionValue(self):
        # type: () -> float
        """
        获取玩家foodExhaustionLevel的归零值，常量值，默认为4。**消耗度（exhaustion）**是指玩家当前消耗度水平，初始值为0，该值会随着玩家一系列动作（如跳跃）的影响而增加，当该值大于最大消耗度（maxExhaustion）后归零，并且把饱和度（saturation）减少1（为了说明饥饿度机制，我们将此定义为**消耗事件**）
        """
        pass

    def SetPlayerMaxExhaustionValue(self, value):
        # type: (float) -> bool
        """
        设置玩家**最大消耗度(maxExhaustion)**，通过调整 **最大消耗度(maxExhaustion)** 的大小，就可以调整 **饥饿度(hunger)** 的消耗速度，当 **最大消耗度(maxExhaustion)** 很大时，饥饿度可以看似一直不下降
        """
        pass

    def GetPlayerHealthLevel(self):
        # type: () -> int
        """
        获取玩家健康临界值，当饥饿值大于等于健康临界值时会自动恢复血量，开启饥饿值且开启自然恢复时有效。原版默认值为18
        """
        pass

    def SetPlayerHealthLevel(self, healthLevel):
        # type: (int) -> bool
        """
        设置玩家健康临界值，当饥饿值大于等于健康临界值时会自动恢复血量，开启饥饿值且开启自然恢复时有效.原版默认值为18
        """
        pass

    def GetPlayerHealthTick(self):
        # type: () -> int
        """
        获取玩家自然恢复速度，当饥饿值大于等于健康临界值时会自动恢复血量，开启饥饿值且开启自然恢复时有效。原版默认值为80刻（即每4秒）恢复1点血量
        """
        pass

    def SetPlayerHealthTick(self, healthTick):
        # type: (int) -> bool
        """
        设置玩家自然恢复速度，当饥饿值大于等于健康临界值时会自动恢复血量，开启饥饿值且开启自然恢复时有效.原版默认值为80刻（即每4秒）恢复1点血量
        """
        pass

    def IsPlayerNaturalRegen(self):
        # type: () -> bool
        """
        是否开启玩家自然恢复，当饥饿值大于等于健康临界值时会自动恢复血量，开启饥饿值且开启自然恢复时有效。原版默认开启
        """
        pass

    def SetPlayerNaturalRegen(self, value):
        # type: (bool) -> bool
        """
        设置是否开启玩家自然恢复，当饥饿值大于等于健康临界值时会自动恢复血量，开启饥饿值且开启自然恢复时有效.原版默认开启
        """
        pass

    def GetPlayerStarveLevel(self):
        # type: () -> int
        """
        获取玩家饥饿临界值，当饥饿值小于饥饿临界值时会自动扣除血量，开启饥饿值且开启饥饿掉血时有效。原版默认值为1
        """
        pass

    def SetPlayerStarveLevel(self, starveLevel):
        # type: (int) -> bool
        """
        设置玩家饥饿临界值，当饥饿值小于饥饿临界值时会自动扣除血量，开启饥饿值且开启饥饿掉血时有效。原版默认值为1
        """
        pass

    def GetPlayerStarveTick(self):
        # type: () -> int
        """
        获取玩家饥饿掉血速度，当饥饿值小于饥饿临界值时会自动扣除血量，开启饥饿值且开启饥饿掉血时有效。原版默认值为80刻（即每4秒）扣除1点血量
        """
        pass

    def SetPlayerStarveTick(self, starveTick):
        # type: (int) -> bool
        """
        设置玩家饥饿掉血速度，当饥饿值小于饥饿临界值时会自动扣除血量，开启饥饿值且开启饥饿掉血时有效.原版默认值为80刻（即每4秒）扣除1点血量
        """
        pass

    def IsPlayerNaturalStarve(self):
        # type: () -> bool
        """
        是否开启玩家饥饿掉血，当饥饿值小于饥饿临界值时会自动恢复血量，开启饥饿值且开启饥饿掉血时有效。原版默认开启
        """
        pass

    def SetPlayerNaturalStarve(self, value):
        # type: (bool) -> bool
        """
        设置是否开启玩家饥饿掉血，当饥饿值小于饥饿临界值时会自动扣除血量，开启饥饿值且开启饥饿掉血时有效.原版默认开启
        """
        pass

    def OpenPlayerCritBox(self):
        # type: () -> None
        """
        开启玩家爆头，开启后该玩家头部被击中后会触发ProjectileCritHitEvent事件。
        """
        pass

    def ClosePlayerCritBox(self):
        # type: () -> None
        """
        关闭玩家爆头，关闭后将无法触发ProjectileCritHitEvent事件。
        """
        pass

    def SetPlayerMovable(self, isMovable):
        # type: (bool) -> bool
        """
        设置玩家是否可移动
        """
        pass

    def SetPlayerJumpable(self, isJumpable):
        # type: (bool) -> bool
        """
        设置玩家是否可跳跃
        """
        pass

    def SetPlayerGameType(self, gameType):
        # type: (int) -> bool
        """
        设置玩家个人游戏模式
        """
        pass

    def OpenPlayerHitBlockDetection(self, precision):
        # type: (float) -> bool
        """
        开启碰撞方块的检测，开启后碰撞时会触发OnPlayerHitBlockServerEvent事件
        """
        pass

    def ClosePlayerHitBlockDetection(self):
        # type: () -> bool
        """
        关闭碰撞方块的检测，关闭后将不会触发OnPlayerHitBlockServerEvent事件
        """
        pass

    def OpenPlayerHitMobDetection(self):
        # type: () -> bool
        """
        开启玩家碰撞到生物的检测，开启后该玩家碰撞到生物时会触发OnPlayerHitMobServerEvent事件
        """
        pass

    def ClosePlayerHitMobDetection(self):
        # type: () -> bool
        """
        关闭碰撞生物的检测，关闭后将不会触发OnPlayerHitMobServerEvent事件
        """
        pass

    def SetPickUpArea(self, area):
        # type: (tuple[float,float,float]) -> bool
        """
        设置玩家的拾取物品范围，设置后该玩家的拾取物品范围会在原版拾取范围的基础上进行改变。
        """
        pass

    def EnableKeepInventory(self, enable):
        # type: (bool) -> bool
        """
        设置玩家死亡不掉落物品
        """
        pass

    def isSneaking(self):
        # type: () -> bool
        """
        获取玩家是否处于潜行状态
        """
        pass

    def isSwimming(self):
        # type: () -> bool
        """
        获取玩家是否处于游泳状态。
        """
        pass

    def ClearDefinedLevelUpCost(self, level):
        # type: (int) -> bool
        """
        接口用于重置升级经验。使用ChangeLevelUpCostServerEvent事件设置升级经验后，升级经验无法调整。需要调整升级经验时，可使用该接口。使用步骤如下：1、使用ClearDefineLevelUpconst，2、在升级抛出ChangeLevelUpCostServerEvent事件后重新设置经验。
        """
        pass

    def ChangeSelectSlot(self, slot):
        # type: (int) -> bool
        """
        设置玩家当前选中快捷栏物品的index
        """
        pass

    def GetPlayerOperation(self):
        # type: () -> int
        """
        获取玩家权限类型信息
        """
        pass

    def GetPlayerAbilities(self):
        # type: () -> dict
        """
        获取玩家具体权限
        """
        pass

    def GetPlayerExhaustionRatioByType(self, type):
        # type: (int) -> float
        """
        获取玩家某行为饥饿度消耗倍率
        """
        pass

    def SetPlayerExhaustionRatioByType(self, type, ratio):
        # type: (int, float) -> bool
        """
        设置玩家某行为饥饿度消耗倍率
        """
        pass

    def SetPlayerRespawnPos(self, pos, dimensionId=0):
        # type: (tuple[int,int,int], int) -> bool
        """
        设置玩家复活的位置与维度
        """
        pass

    def GetPlayerRespawnPos(self):
        # type: () -> dict
        """
        获取玩家复活点
        """
        pass

    def CollectOnlineClientData(self, collectTypes, callback, extraArgs=None):
        # type: (list[str], function, dict) -> None
        """
        收集在线玩家客户端数据，用于判断玩家是否作弊
        """
        pass

    def SetPlayerAttackSpeedAmplifier(self, amplifier):
        # type: (float) -> bool
        """
        设置玩家攻击速度倍数，1.0表示正常水平，1.2表示速度减益20%，0.8表示速度增益20%
        """
        pass

    def GetIsBlocking(self):
        # type: () -> bool
        """
        获取玩家激活盾牌状态
        """
        pass

    def GetRelevantPlayer(self, List=None):
        """
        获取附近玩家id列表
        """
        pass

