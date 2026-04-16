# -*- coding: utf-8 -*-

from common.component.baseComponent import BaseComponent

class GameComponentServer(BaseComponent):
    def GetGameType(self):
        # type: () -> int
        """
        获取默认游戏模式
        """
        pass

    def GetGameDiffculty(self):
        # type: () -> int
        """
        获取游戏难度
        """
        pass

    def SetHurtCD(self, cdTime):
        # type: (int) -> bool
        """
        设置伤害CD
        """
        pass

    def SetNotifyMsg(self, msg, color='\xc2\xa7f'):
        # type: (str, str) -> bool
        """
        设置消息通知
        """
        pass

    def SetPopupNotice(self, message, subtitle):
        # type: (str, str) -> bool
        """
        在所有玩家物品栏上方弹出popup类型通知，位置位于tip类型消息下方
        """
        pass

    def SetTipMessage(self, message):
        # type: (str) -> bool
        """
        在所有玩家物品栏上方弹出tip类型通知，位置位于popup类型通知上方
        """
        pass

    def SetOnePopupNotice(self, playerId, message, subtitle):
        # type: (str, str, str) -> bool
        """
        在具体某个玩家的物品栏上方弹出popup类型通知，位置位于tip类型消息下方，此功能更建议客户端使用game组件的对应接口SetPopupNotice
        """
        pass

    def SetOneTipMessage(self, playerId, message):
        # type: (str, str) -> bool
        """
        在具体某个玩家的物品栏上方弹出tip类型通知，位置位于popup类型通知上方，此功能更建议在客户端使用game组件的对应接口SetTipMessage
        """
        pass

    def GetEntitiesInSquareArea(self, entityId, startPos, endPos, dimensionId=-1):
        # type: (None, tuple[int,int,int], tuple[int,int,int], int) -> list[str]
        """
        获取区域内的entity列表
        """
        pass

    def GetEntitiesAround(self, entityId, radius, filters):
        # type: (str, int, dict) -> list[str]
        """
        获取区域内的entity列表
        """
        pass

    def SetDisableHunger(self, isDisable):
        # type: (bool) -> bool
        """
        设置是否屏蔽饥饿度
        """
        pass

    def SetDisableContainers(self, isDisable):
        # type: (bool) -> bool
        """
        禁止所有容器界面的打开，包括玩家背包，各种包含背包界面的容器方块如工作台与箱子，以及包含背包界面的实体交互如马背包与村民交易
        """
        pass

    def SetDisableDropItem(self, isDisable):
        # type: (bool) -> bool
        """
        设置禁止丢弃物品
        """
        pass

    def SetDisableCommandMinecart(self, isDisable):
        # type: (bool) -> bool
        """
        设置停止/开启运行命令方块矿车内置逻辑指令，当前仅Apollo网络服可用
        """
        pass

    def IsDisableCommandMinecart(self):
        # type: () -> bool
        """
        获取当前是否允许运行命令方块矿车内置逻辑指令，当前仅Apollo网络服可用
        """
        pass

    def SetLevelGravity(self, data):
        # type: (float) -> bool
        """
        设置重力因子
        """
        pass

    def GetLevelGravity(self):
        # type: () -> float
        """
        获取重力因子
        """
        pass

    def CanSee(self, fromId, targetId, viewRange=8.0, onlySolid=True, angleX=180.0, angleY=180.0):
        # type: (str, str, float, bool, float, float) -> bool
        """
        判断起始对象是否可看见目标对象,基于对象的Head位置判断
        """
        pass

    def DisableVineBlockSpread(self, disable):
        # type: (bool) -> None
        """
        设置是否禁用藤曼蔓延生长
        """
        pass

    def GetPlayerGameType(self, playerId):
        # type: (str) -> int
        """
        获取指定玩家的游戏模式
        """
        pass

    def LockDifficulty(self, lock):
        # type: (bool) -> bool
        """
        锁定当前世界游戏难度（仅本次游戏有效），锁定后任何玩家在游戏内都无法通过指令或暂停菜单修改游戏难度
        """
        pass

    def IsLockDifficulty(self):
        # type: () -> bool
        """
        获取当前世界的游戏难度是否被锁定
        """
        pass

    def SetGameDifficulty(self, difficulty):
        # type: (int) -> bool
        """
        设置游戏难度
        """
        pass

    def GetEntitiesAroundByType(self, entityId, radius, entityType):
        # type: (str, int, int) -> list[str]
        """
        获取区域内的某类型的entity列表
        """
        pass

    def PickUpItemEntity(self, playerEntityId, itemEntityId):
        # type: (str, str) -> bool
        """
        某个Player拾取物品ItemEntity
        """
        pass

    def KillEntity(self, entityId):
        # type: (str) -> bool
        """
        杀死某个Entity
        """
        pass

    def SetDefaultGameType(self, gameType):
        # type: (int) -> bool
        """
        设置默认游戏模式
        """
        pass

    def SetDisableGravityInLiquid(self, isDisable):
        # type: (bool) -> bool
        """
        是否屏蔽所有实体在液体（水、岩浆）中的重力
        """
        pass

    def SetGameRulesInfoServer(self, gameRuleDict):
        # type: (dict) -> bool
        """
        设置游戏规则。所有参数均可选。
        """
        pass

    def GetGameRulesInfoServer(self):
        # type: () -> dict
        """
        获取游戏规则
        """
        pass

    def CheckWordsValid(self, words):
        # type: (str) -> bool
        """
        检查语句是否合法，即不包含敏感词
        """
        pass

    def CheckNameValid(self, name):
        # type: (str) -> bool
        """
        检查昵称是否合法，即不包含敏感词
        """
        pass

    def AddTimer(self, delay, func, *args, **kwargs):
        # type: (float, function, object, object) -> object
        """
        添加服务端触发的定时器，非重复
        """
        pass

    def AddRepeatedTimer(self, delay, func, *args, **kwargs):
        # type: (float, function, object, object) -> object
        """
        添加服务端触发的定时器，重复执行
        """
        pass

    def CancelTimer(self, timer):
        # type: (object) -> None
        """
        取消定时器
        """
        pass

    def PlaceStructure(self, playerId, pos, structureName, dimensionId=-1, rotation=0):
        # type: (None, tuple[float,float,float], str, int, int) -> bool
        """
        放置结构
        """
        pass

    def OpenCityProtect(self):
        # type: () -> bool
        """
        开启城市保护，包括禁止破坏方块，禁止对方块使用物品，禁止怪物攻击玩家，禁止玩家之间互相攻击，禁止日夜切换，禁止天气变化，禁止怪物群落刷新
        """
        pass

    def ForbidLiquidFlow(self, forbid):
        # type: (bool) -> bool
        """
        禁止/允许地图中的流体流动
        """
        pass

    def AddBlockProtectField(self, dimensionId, startPos, endPos):
        # type: (int, tuple[int,int,int], tuple[int,int,int]) -> int
        """
        设置一个方块无法被玩家/实体破坏的区域
        """
        pass

    def RemoveBlockProtectField(self, field):
        # type: (int) -> bool
        """
        取消一个方块无法被玩家/实体破坏的区域
        """
        pass

    def CleanBlockProtectField(self):
        # type: () -> bool
        """
        取消全部已设置的方块无法被玩家/实体破坏的区域
        """
        pass

    def UpgradeMapDimensionVersion(self, dimension, version):
        # type: (int, int) -> bool
        """
        提升指定地图维度的版本号，版本号不符的维度，地图存档信息将被废弃。使用后存档的地图版本均会同步提升至最新版本，假如希望使用此接口清理指定维度的地图存档，需要在保证该维度区块都没有被加载时调用。
        """
        pass

    def SetCanBlockSetOnFireByLightning(self, enable):
        # type: (bool) -> bool
        """
        禁止/允许闪电点燃方块
        """
        pass

    def SetCanActorSetOnFireByLightning(self, enable):
        # type: (bool) -> bool
        """
        禁止/允许闪电点燃实体
        """
        pass

    def LookupItemByName(self, itemName):
        # type: (str) -> bool
        """
        判定指定identifier的物品是否存在
        """
        pass

    def GetSpawnPosition(self):
        # type: () -> tuple[int,int,int]
        """
        获取世界出生点坐标
        """
        pass

    def GetSpawnDimension(self):
        # type: () -> int
        """
        获取世界出生维度
        """
        pass

    def SetSpawnDimensionAndPosition(self, dimensionId=None, pos=None):
        """
        设置世界出生点维度与坐标
        """
        pass

    def IsEntityAlive(self, entityId):
        # type: (str) -> bool
        """
        判断生物实体是否存活或非生物实体是否存在
        """
        pass

    def SetMergeSpawnItemRadius(self, radius):
        # type: (int) -> bool
        """
        设置新生成的物品是否合堆
        """
        pass

    def GetChinese(self, langStr):
        # type: (str) -> str
        """
        获取langStr对应的中文，可参考PC开发包中\handheld\bed-loc\handheld\data\resource_packs\vanilla\texts\zh_CN.lang
        """
        pass

    def OpenMobHitBlockDetection(self, entityId, precision):
        # type: (str, float) -> bool
        """
        开启碰撞方块的检测，开启后，生物（不包括玩家）碰撞到方块时会触发OnMobHitBlockServerEvent事件
        """
        pass

    def CloseMobHitBlockDetection(self, entityId):
        # type: (str) -> bool
        """
        关闭碰撞方块的检测，关闭后，生物（不包括玩家）碰撞到方块时将不会触发OnMobHitBlockServerEvent事件
        """
        pass

