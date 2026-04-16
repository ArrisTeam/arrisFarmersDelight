# -*- coding: utf-8 -*-

from common.component.baseComponent import BaseComponent

class MsgComponentServer(BaseComponent):
    def SendMsg(self, name, msg):
        # type: (str, str) -> bool
        """
        模拟玩家给所有人发送聊天栏消息
        """
        pass

    def SendMsgToPlayer(self, fromEntityId, toEntityId, msg):
        # type: (str, str, str) -> None
        """
        模拟玩家给另一个玩家发送聊天栏消息
        """
        pass

    def NotifyOneMessage(self, playerId, msg, color='\xc2\xa7f'):
        # type: (str, str, str) -> None
        """
        给指定玩家发送聊天框消息
        """
        pass

