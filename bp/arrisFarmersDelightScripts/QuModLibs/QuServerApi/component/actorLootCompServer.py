# -*- coding: utf-8 -*-

from common.component.baseComponent import BaseComponent


class ActorLootComponentServer(BaseComponent):
    def SpawnLootTable(self, pos, identifier, playerKillerId=None, damageCauseEntityId=None):
        # type: (tuple[int,int,int], str, str, str) -> bool
        """
        使用生物类型模拟一次随机掉落，生成的物品与json定义的概率有关
        """
        pass

    def SpawnLootTableWithActor(self, pos, entityId, playerKillerId=None, damageCauseEntityId=None):
        # type: (tuple[int,int,int], str, str, str) -> bool
        """
        使用生物实例模拟一次随机掉落，生成的物品与json定义的概率有关
        """
        pass

