# -*- coding: utf-8 -*-
from ...Server import serverApi
from ..EntityComps.Server import QBaseEntityComp
from Util import SharedBox, _DEFAULT

lambda: "By Zero123"

class ImmuneDamageComp(QBaseEntityComp):
    """ 免疫伤害组件 """
    def __init__(self):
        QBaseEntityComp.__init__(self)
        self.sharedBox = SharedBox()
    
    def onBind(self):
        QBaseEntityComp.onBind(self)
        self.sharedBox = SharedBox(
            lambda: serverApi.GetEngineCompFactory().CreateHurt(self.entityId).ImmuneDamage(True),
            lambda: self.unbind()
        )

    def onUnBind(self):
        QBaseEntityComp.onUnBind(self)
        self.sharedBox.free()
        serverApi.GetEngineCompFactory().CreateHurt(self.entityId).ImmuneDamage(False)

class EntitySharedAPI:
    """ 实体共享API 基于引用计数管理 """
    @staticmethod
    def immuneDamage(entityId, state = True, key = _DEFAULT):
        """ 设置实体是否免疫伤害(该属性不一定存档)
            state 为True时引用次数+1 否则-1 基于Key值处理边界
        """
        if state:
            comp = ImmuneDamageComp.getComp(entityId)
            if not comp:
                ImmuneDamageComp().bind(entityId)
        comp = ImmuneDamageComp.getComp(entityId)
        if comp and state:
            comp.sharedBox.increaseRefCountWithKey(key)
        elif comp and not state:
            comp.sharedBox.decreaseRefCountWithKey(key)