# -*- coding: utf-8 -*-

from common.component.baseComponent import BaseComponent

class RideCompServer(BaseComponent):
    def SetEntityRide(self, playerId, tamedEntityId):
        # type: (str, str) -> bool
        """
        驯服可骑乘生物
        """
        pass

    def SetRidePos(self, tamedEntityId, pos):
        # type: (str, tuple[float,float,float]) -> bool
        """
        设置生物骑乘位置
        """
        pass

    def SetControl(self, tamedEntityId, isControl):
        # type: (str, bool) -> bool
        """
        设置该生物无需装备鞍就可以控制行走跳跃
        """
        pass

    def SetCanOtherPlayerRide(self, tamedEntityId, canRide):
        # type: (str, bool) -> bool
        """
        设置其他玩家是否有权限骑乘，True表示每个玩家都能骑乘，False只有驯服者才能骑乘
        """
        pass

    def SetShowRideUI(self, tamedEntityId, isShowUI):
        # type: (str, bool) -> bool
        """
        设置是否显示马匹的UI界面
        """
        pass

    def SetPlayerRideEntity(self, playerId, rideEntityId):
        # type: (str, str) -> bool
        """
        设置玩家骑乘生物
        """
        pass

    def IsEntityRiding(self):
        # type: () -> bool
        """
        检查玩家是否骑乘。
        """
        pass

    def GetEntityRider(self):
        # type: () -> str
        """
        获取玩家正在骑乘的实体的id。
        """
        pass

    def StopEntityRiding(self):
        # type: () -> bool
        """
        强制玩家下坐骑。
        """
        pass

    def SetRiderRideEntity(self, riderId, riddenEntityId):
        # type: (str, str) -> bool
        """
        设置实体骑乘生物
        """
        pass

