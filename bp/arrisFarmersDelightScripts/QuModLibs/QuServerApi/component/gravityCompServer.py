# -*- coding: utf-8 -*-


class GravityComponentServer(object):
    def SetGravity(self, gravity):
        # type: (float) -> bool
        """
        设置实体的重力因子，当生物重力因子为0时则应用世界的重力因子
        """
        pass

    def GetGravity(self):
        # type: () -> float
        """
        获取实体的重力因子，当生物重力因子为0时则应用世界的重力因子
        """
        pass

    def SetJumpPower(self, jumpPower):
        # type: (float) -> bool
        """
        设置生物跳跃力度，0.42表示正常水平
        """
        pass

