# -*- coding: utf-8 -*-

from component.baseComponent import BaseComponent

class ParticleEntityBindComp(BaseComponent):
    def Bind(self, bindEntityId, offset, rot, correction=False):
        # type: (str, tuple[float,float,float], tuple[float,float,float], bool) -> bool
        """
        绑定entity
        """
        pass


