# -*- coding: utf-8 -*-

from common.component.baseComponent import BaseComponent

class CommandCompServer(BaseComponent):
    def SetCommand(self, cmdStr, playerId=None, showOutput=False):
        # type: (str, str, bool) -> bool
        """
        使用游戏内指令
        """
        pass

    def GetCommandPermissionLevel(self):
        # type: () -> int
        """
        返回设定使用/op命令时OP的权限等级（对应server.properties中的op-permission-level配置）
        """
        pass

    def SetCommandPermissionLevel(self, opLevel):
        # type: (int) -> bool
        """
        设置当玩家使用/op命令时OP的权限等级（对应server.properties中的op-permission-level配置）
        """
        pass

    def GetDefaultPlayerPermissionLevel(self):
        # type: () -> int
        """
        返回新玩家加入时的权限身份（对应server.properties中的default-player-permission-level配置）
        """
        pass

    def SetDefaultPlayerPermissionLevel(self, opLevel):
        # type: (int) -> bool
        """
        设置新玩家加入时的权限身份（对应server.properties中的default-player-permission-level配置）
        """
        pass

