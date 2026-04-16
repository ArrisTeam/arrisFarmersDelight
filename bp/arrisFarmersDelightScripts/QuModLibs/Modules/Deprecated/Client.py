# -*- coding: utf-8 -*-
from ...Client import *
lambda: "By Zero123"
# 以下功能计划与未来移除并提供对应的替代方案

class EntityCompCls(object):
    """ QuMod提供的实体组件类 开发者可以继承并开发实体组件功能"""
    # UserList 用作记录使用者Id,防止同组件复用现象
    UserList = {} # type: dict[str,EntityCompCls]
    @classmethod
    def GetComp(cls, entityId):
        # type: (str) -> EntityCompCls|None
        """ 
                [静态方法] 获取指定实体的组件实例
                直接调用 cls.GetComp(xxx) 即可
                cls表示类 而不是 实例化的数据对象
        """
        if cls.UserList is EntityCompCls.UserList:
            cls.UserList = {}
        try:
            return cls.UserList[entityId]
        except Exception:
            return None
        
    def __new__(cls, entityId, *Args, **Kwargs):
        if cls.UserList is EntityCompCls.UserList:
            cls.UserList = {}
        if entityId in cls.UserList:
            return None
        Obj = object.__new__(cls, entityId, *Args, **Kwargs)
        cls.UserList[entityId] = Obj
        Obj.entityId = entityId
        ListenForEvent("OnScriptTickClient", Obj, Obj.OnTick)
        ListenForEvent("RemoveEntityClientEvent", Obj, Obj.WhenEntityRemove)
        return Obj
    
    def __init__(self,entityId):
        """ [可覆写] 初始化 需要确保第一个参数为实体id """
        self.entityId = entityId

    def OnRemove(self):
        """ [可覆写] 组件移除后自动执行 """
        pass
    
    def OnTick(self,Args={}):
        """ [可覆写] Tick 一秒30次 如有需要可以覆写此方法 """
        pass
    
    def RemoveComp(self):
        """ 删除组件方法,可以手动调用 生物死亡后也会自动调用 """
        try:
            del self.__class__.UserList[self.entityId]
            UnListenForEvent("OnScriptTickClient", self, self.OnTick)
            UnListenForEvent("RemoveEntityClientEvent", self, self.WhenEntityRemove)
            self.OnRemove()
        except Exception:
            pass

    def WhenEntityRemove(self, Args):
        """
                判断被Remove的实体是否为自己
                并调用 OnRemove 方法 进行回收处理
        """
        if Args["id"] == self.entityId:
            self.RemoveComp()

class EasyThread:
    """ QuMod提供的简易多线程 """
    from ...Util import ThreadLock
    @classmethod
    def IsThread(cls, *Args, **Kwargs):
        """ 用于将函数装饰为多线程下执行的函数 @IsThread 无参数"""
        from ...Util import IsThread
        return IsThread(*Args, **Kwargs)
    
    @classmethod
    def NextTick(cls, Fun, Args=tuple(), Kwargs={}, WaitReturn=False):
        """ 
                添加函数到下一游戏Tick运行 用于解决线程下无法使用API的现象
                选填参数 WaitReturn=False(默认值) 设置为True后将会等待返回结果后再执行后续代码
                Args=tuple(),Kwargs={} 可传参
        """
        cls.ThreadLock.acquire() # 上锁
        Back = []
        Obj = EasyThread()
        def Tick(_={}):
            UnListenForEvent(TickEvent, Obj, Tick)
            RunBack = Fun(*Args,**Kwargs)
            Back.append(RunBack)
            
        ListenForEvent(TickEvent, Obj, Tick)
        cls.ThreadLock.release() # 释放锁
        # 返回值处理
        if WaitReturn:
            while not len(Back):
                pass
            return Back[0]
