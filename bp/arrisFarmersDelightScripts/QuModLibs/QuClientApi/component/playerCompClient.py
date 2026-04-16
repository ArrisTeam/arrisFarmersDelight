# -*- coding: utf-8 -*-

from component.baseComponent import BaseComponent

class PlayerCompClient(BaseComponent):
    def OpenPlayerHitBlockDetection(self, precision):
        # type: (float) -> bool
        """
        开启碰撞方块的检测，开启后碰撞时会触发OnPlayerHitBlockClientEvent事件
        """
        pass

    def ClosePlayerHitBlockDetection(self):
        # type: () -> bool
        """
        关闭碰撞方块的检测，关闭后将不会触发OnPlayerHitBlockClientEvent事件
        """
        pass

    def OpenPlayerHitMobDetection(self):
        # type: () -> bool
        """
        开启玩家碰撞到生物的检测，开启后该玩家碰撞到生物时会触发OnPlayerHitMobClientEvent事件
        """
        pass

    def ClosePlayerHitMobDetection(self):
        # type: () -> bool
        """
        关闭碰撞生物的检测，关闭后将不会触发OnPlayerHitMobClientEvent事件
        """
        pass

    def isGliding(self):
        # type: () -> bool
        """
        是否鞘翅飞行
        """
        pass

    def isSwimming(self):
        # type: () -> bool
        """
        是否游泳
        """
        pass

    def isRiding(self):
        # type: () -> bool
        """
        是否骑乘
        """
        pass

    def isSneaking(self):
        # type: () -> bool
        """
        是否潜行
        """
        pass

    def setSneaking(self):
        # type: () -> bool
        """
        设置是否潜行，只能设置本地玩家（只适用于移动端）
        """
        pass

    def setUsingShield(self, flag=True):
        # type: (bool) -> int
        """
        激活盾牌状态
        """
        pass

    def isSprinting(self):
        # type: () -> bool
        """
        是否在疾跑
        """
        pass

    def setSprinting(self):
        # type: () -> bool
        """
        设置是否疾跑，只能设置本地玩家（只适用于移动端）
        """
        pass

    def isInWater(self):
        # type: () -> bool
        """
        是否在水中
        """
        pass

    def isMoving(self):
        # type: () -> bool
        """
        是否在行走
        """
        pass

    def setMoving(self):
        # type: () -> bool
        """
        设置是否行走，只能设置本地玩家（只适用于移动端）
        """
        pass

    def getUid(self):
        # type: () -> str
        """
        获取本地玩家的uid
        """
        pass

    def Swing(self):
        # type: () -> bool
        """
        本地玩家播放原版攻击动作
        """
        pass


