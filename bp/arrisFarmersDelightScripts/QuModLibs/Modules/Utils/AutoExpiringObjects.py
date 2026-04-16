# -*- coding: utf-8 -*-
from time import time
lambda: "By Zero123 2024/07/08"

class QTimedExpiryArgs:
    def __init__(self, saveObj, timeout = 60.0, allowRefresh = True):
        self.saveObj = saveObj
        self.timeout = timeout
        self.allowRefresh = allowRefresh
        self._delTime = time() + timeout

    @classmethod
    def create(cls):
        return cls(None)
    
    def refresh(self):
        """ 刷新超时间隔 """
        if not self.allowRefresh:
            return
        self._delTime = time() + self.timeout

    def get(self):
        return self.saveObj
    
    def getTimeoutState(self, _time = -1):
        """ 获取超时状态 """
        if _time < 0:
            _time = time()
        return _time >= self._delTime

class QTimedExpiryMap:
    """ QTimedExpiryMap 提供定时储存元素的回收机制 """
    def __init__(self, gcMinTriggerCount = 1000, gcMinInterval = 30.0):
        self.gcMinTriggerCount = gcMinTriggerCount
        """ 垃圾回收最小触发条数(key存活数量) """
        self.gcMinInterval = gcMinInterval
        """ 垃圾回收最小触发间隔 """
        self._lastAutoGcTime = 0
        self._saveMap = {}      # type: dict[str, QTimedExpiryArgs]
    
    @classmethod
    def create(cls):
        return cls()
    
    @staticmethod
    def loads(_dic):
        # type: (dict) -> QTimedExpiryMap
        """ 加载dict对象 """
        from ...Util import ObjectConversion
        return ObjectConversion.loadDumpsObject(_dic)

    def dumps(self):
        # type: () -> dict
        """ 格式化输出对象 (转换成Dict) """
        from ...Util import ObjectConversion
        return ObjectConversion.dumpsObject(self)
    
    def __str__(self):
        _dictText = str({k:v.get() for k, v in self._saveMap.items()})
        return "{}({})<{}>".format(self.__class__.__name__, self.length(), _dictText[1:-1])
    
    def length(self):
        """ 获取map长度 """
        return len(self._saveMap)

    def keys(self, refresh=False):
        """ Keys生成器 """
        for k, _ in self.items(refresh):
            yield k

    def values(self, refresh=False):
        """ Values生成器 """
        for _, v in self.items(refresh):
            yield v

    def items(self, refresh=False):
        """ items生成器 """
        for key in self._saveMap:
            _obj = self._saveMap[key]
            if refresh:
                _obj.refresh()
            yield (key, _obj.get())
    
    def pop(self, key):
        # type: (str) -> object
        """ 取出元素 """
        if self.hasKey(key):
            _obj = self.get(key, refresh=False)
            self.remove(key)
            return _obj
        raise Exception("找不到Key: {}".format(key))

    def hasKey(self, key):
        # type: (str) -> bool
        """ 获取特定key是否存在 """
        return key in self._saveMap

    def hasLiveKey(self, key):
        # type: (str) -> bool
        """ 获取特定key是否存活 (相比hasKey还会计算对象是否超时) """
        _hasKey = self.hasKey(key)
        if not _hasKey:
            return False
        _state = self._saveMap[key].getTimeoutState()
        return not _state
    
    def tryComputeAndReleaseKey(self, key):
        # type: (str) -> bool
        """ 尝试计算并释放某个单独的key """
        if not self.hasKey(key):
            return False
        _state = self._saveMap[key].getTimeoutState()
        if _state:
            del self._saveMap[key]
            return True
        return False

    def save(self, key, saveObj, timeout = 60.0, allowRefresh = True):
        # type: (str, object, float, bool) -> bool
        """ 储存数据(若存在相同Key将会覆盖) """
        self._saveMap[key] = QTimedExpiryArgs(
            saveObj, timeout, allowRefresh
        )
        self._onChange()

    def refreshData(self, key):
        # type: (str) -> bool
        """ 刷新数据 """
        if self.hasKey(key):
            self._saveMap[key].refresh()
            return True
        return False

    def get(self, key, errorBack = None, refresh = True):
        # type: (str, object, bool) -> object
        """ 访问数据 """
        if self.hasKey(key):
            _obj = self._saveMap[key]
            if refresh:
                _obj.refresh()
            self._onChange()
            return _obj.get()
        return errorBack

    def remove(self, key):
        # type: (str) -> None
        """ 删除元素 """
        if not self.hasKey(key):
            return
        del self._saveMap[key]
        self._onChange()
    
    def calculateGC(self):
        """ 计算垃圾回收 """
        from copy import copy
        _time = time()
        copyMap = copy(self._saveMap)
        for key in copyMap:
            saveObj = copyMap[key]
            if saveObj.getTimeoutState(_time):
                del self._saveMap[key]

    def _onChange(self):
        if len(self._saveMap) < self.gcMinTriggerCount:
            return
        _nowTime = time()
        if _nowTime < self._lastAutoGcTime + self.gcMinInterval:
            return
        self._lastAutoGcTime = _nowTime
        self.calculateGC()
