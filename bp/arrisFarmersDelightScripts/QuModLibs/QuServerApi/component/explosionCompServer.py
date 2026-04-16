# -*- coding: utf-8 -*-

from common.component.baseComponent import BaseComponent


class ExplosionComponentServer(BaseComponent):
    def CreateExplosion(self, pos, radius, fire, breaks, sourceId, playerId):
        # type: (tuple[float,float,float], int, bool, bool, str, str) -> bool
        """
        用于生成爆炸
        """
        pass

