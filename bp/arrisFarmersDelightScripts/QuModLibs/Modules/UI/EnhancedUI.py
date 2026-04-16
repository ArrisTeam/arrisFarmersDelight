# -*- coding: utf-8 -*-
from ...UI import ScreenNodeWrapper
from ..Services.Globals import (
    TimerLoader,
    AnnotationLoader,
    LifecycleBind,
    LoopTimerData,
    ContextNode
)
from ...Client import ListenForEvent, UnListenForEvent
from ...Util import QRAIIDelayed, QBaseRAIIEnv
lambda: "增强版UI模块, 提供更为高阶的UI管理逻辑"

class UIEventListener(QRAIIDelayed):
    """ UI事件监听器(RAII) """
    class Binder(LifecycleBind):
        """ 事件绑定器 """
        def __init__(self, eventName=""):
            LifecycleBind.__init__(self)
            self.eventName = eventName

        def onLoad(self, nodeSelf):
            # type: (ContextNode) -> None
            ListenForEvent(self.eventName, nodeSelf.contextNode, nodeSelf.funObj)

        def onUnLoad(self, nodeSelf):
            # type: (ContextNode) -> None
            UnListenForEvent(self.eventName, nodeSelf.contextNode, nodeSelf.funObj)

    def __init__(self, uiNode, eventName, callback):
        """ 创建UI事件监听器
            - uiNode: UI节点
            - eventName: 事件名称
            - callback: 回调函数
        """
        self.uiNode = uiNode
        self.eventName = eventName
        self.callBack = callback
        if isinstance(uiNode, QBaseRAIIEnv):
            uiNode.addRAIIRes(self)

    def _loadResource(self):
        QRAIIDelayed._loadResource(self)
        ListenForEvent(self.eventName, self.uiNode, self.callBack)

    def _cleanup(self):
        QRAIIDelayed._cleanup(self)
        UnListenForEvent(self.eventName, self.uiNode, self.callBack)

class UIButtonClickBinder(LifecycleBind):
    """ 按钮点击绑定器 """
    def __init__(self, buttonPath=""):
        LifecycleBind.__init__(self)
        self.buttonPath = buttonPath

    def onLoad(self, nodeSelf):
        # type: (ContextNode) -> None
        contextNode = nodeSelf.contextNode
        if isinstance(contextNode, ScreenNodeWrapper):
            contextNode.setButtonClickHandler(self.buttonPath, nodeSelf.funObj)

class QEScreenNode(ScreenNodeWrapper, TimerLoader, AnnotationLoader):
    """ 增强版UI界面节点, 提供更为高阶的UI管理逻辑
        - 继承 `TimerLoader` 支持内环境定时器
        - 继承 `AnnotationLoader` 支持上下文注解
    """
    def __init__(self, namespace, name, param):
        ScreenNodeWrapper.__init__(self, namespace, name, param)
        TimerLoader.__init__(self)

    @staticmethod
    def LoopTimer(time=0.1):
        """ [注解] 循环定时任务 """
        return LoopTimerData.creatAnnotationObj(time)

    @staticmethod
    def Listen(eventName):
        """ [注解] 事件监听 """
        return UIEventListener.Binder.creatAnnotationObj(eventName)
    
    @staticmethod
    def OnClick(buttonPath=""):
        """ [注解] 按钮点击 """
        return UIButtonClickBinder.creatAnnotationObj(buttonPath)

    def Update(self):
        ScreenNodeWrapper.Update(self)
        self._timerUpdate()

    def Create(self):
        ScreenNodeWrapper.Create(self)
        self._loadAnnotation()

    def Destroy(self):
        ScreenNodeWrapper.Destroy(self)
        self._unLoadAnnotation()