# -*- coding: utf-8 -*-
from ..Services.Globals import TimerLoader
from random import choice
lambda: "行为树 By Zero123"

class QSharedData:
    def __init__(self):
        self._dataMap = {}

    def getValue(self, key, noneValue=None):
        return self._dataMap.get(key, noneValue)

    def setValue(self, key, value):
        self._dataMap[key] = value

    def removeKey(self, key):
        if key in self._dataMap:
            del self._dataMap[key]

    def hasKey(self, key):
        return key in self._dataMap
    
    def clear(self):
        self._dataMap = {}

class QBaseNode:
    """ 根基类节点 """
    SUCCESS = 0
    """ 状态: 成功 """
    FAILURE = 1
    """ 状态: 失败 """
    RUNNING = 2
    """ 状态: RUNNING """
    def __init__(self):
        pass

    def _evaluate(self, sharedData):
        # type: (QSharedData) -> int
        """ 节点决策评判处理 """
        return self.evaluate(sharedData)

    def evaluate(self, sharedData):
        # type: (QSharedData) -> int
        """ 节点决策评判处理 """
        return QBaseNode.SUCCESS

    def loadNodes(self, sharedData):
        # type: (QSharedData) -> None
        while self._evaluate(sharedData) == 2:
            pass

class QBaseCompositeNode(QBaseNode):
    """ 控制节点基类 """
    def __init__(self, childList=[]):
        # type: (list[QBaseNode]) -> None
        QBaseNode.__init__(self)
        self._childList = childList
        self._index = 0     # 下标计数器

class QSequencerNode(QBaseCompositeNode):
    """ 顺序节点 (有序的执行所有子节点 一旦中途有节点返回失败将终止决策行为并返回失败) """
    def evaluate(self, sharedData):
        # type: (QSharedData) -> int
        if not self._childList:
            self._index = 0
            return QBaseNode.FAILURE
        SUCCESS = QBaseNode.SUCCESS
        FAILURE = QBaseNode.FAILURE
        RUNNING = QBaseNode.RUNNING
        status = self._childList[self._index]._evaluate(sharedData)
        if status == SUCCESS:
            self._index += 1    # 如若成功继续推移
            if self._index >= len(self._childList):
                # 已达末尾 重置下标并汇报成功
                self._index = 0
                return SUCCESS
            return RUNNING
        elif status == FAILURE:
            return FAILURE
        elif status == RUNNING:
            return RUNNING
        return FAILURE

class QSelectorNode(QBaseCompositeNode):
    """ 选择节点 (将尝试从子集中有序匹配选出第一个成功决策的节点 倘若均不符合条件 则返回失败) """
    def evaluate(self, sharedData):
        # type: (QSharedData) -> int
        if not self._childList:
            self._index = 0
            return QBaseNode.FAILURE
        status = self._childList[self._index]._evaluate(sharedData)
        SUCCESS = QBaseNode.SUCCESS
        FAILURE = QBaseNode.FAILURE
        RUNNING = QBaseNode.RUNNING
        if status == SUCCESS:
            # 匹配到成功决策 重置下标
            self._index = 0
            return SUCCESS
        elif status == FAILURE:
            # 匹配到失败决策 下标后移
            self._index += 1
            if self._index >= len(self._childList):
                # 已达末尾 重置下标等待下一轮决策
                self._index = 0
                return FAILURE
            return RUNNING
        elif status == RUNNING:
            # RUNNING
            return RUNNING
        return FAILURE

class QRandomNode(QBaseCompositeNode):
    """ 随机节点 (从子集中随机抽选一个节点作决策) """
    def evaluate(self, sharedData):
        # type: (QSharedData) -> int
        if not self._childList:
            return QBaseNode.FAILURE
        node = choice(self._childList)
        return node._evaluate(sharedData)

class QBaseDecoratorNode(QBaseNode):
    """ 修饰节点基类 """
    def __init__(self, child):
        # type: (QBaseNode) -> None
        self._child = child

class QInverterNode(QBaseDecoratorNode):
    """ 反转节点 (将返回相反的决策结果 如SUCCESS将作为FAILURE) """
    def evaluate(self, sharedData):
        # type: (QSharedData) -> int
        status = self._child._evaluate(sharedData)
        SUCCESS = QBaseNode.SUCCESS
        FAILURE = QBaseNode.FAILURE
        if status == SUCCESS:
            return FAILURE
        elif status == FAILURE:
            return SUCCESS
        return status

class _QBaseTaskNode(QBaseNode, TimerLoader):
    """ 任务节点 (执行具体行为) """
    _TEMP_RUN_SET_KEY = "_TEMP_RUN_SET"

    def __init__(self):
        QBaseNode.__init__(self)
        TimerLoader.__init__(self)

    def _onStart(self):
        self.onStart()

    def _onStop(self):
        self._clearAllTimer()
        self.onStop()

    def _onUpdate(self):
        self._timerUpdate()
        self.onUpdate()

    def onStart(self):
        pass

    def onStop(self):
        pass

    def onUpdate(self):
        pass

    def tagUpdate(self, sharedData):
        # type: (QSharedData) -> None
        if not sharedData.hasKey(_QBaseTaskNode._TEMP_RUN_SET_KEY):
            newSet = set()
            newSet.add(self)
            sharedData.setValue(_QBaseTaskNode._TEMP_RUN_SET_KEY, newSet)
            return
        data = sharedData.getValue(_QBaseTaskNode._TEMP_RUN_SET_KEY)    # type: set
        data.add(self)
        sharedData.setValue(_QBaseTaskNode._TEMP_RUN_SET_KEY, data)

    def _evaluate(self, sharedData):
        # type: (QSharedData) -> int
        state = QBaseNode._evaluate(self, sharedData)
        if state == QBaseNode.SUCCESS:
            self.tagUpdate(sharedData)
        return state