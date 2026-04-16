# -*- coding: utf-8 -*-
from random import randint, choice
lambda: "WeightUtil By Zero123 TIME:2024/6/12"

class QWeightObject:
    """ 权重对象 """
    def __init__(self, value, weight = 1):
        self.weight = int(weight)
        self.value = value
        if self.weight <= 0:
            raise Exception("权重值不是有效的")

class IQWeightContainer:
    def addQWeightObject(self, _QWeightObject):
        # type: (QWeightObject) -> None
        pass

    def removeQWeightObject(self, _QWeightObject):
        # type: (QWeightObject) -> None
        pass

    def update(self):
        pass

    def randomSelection(self):
        # type: () -> object
        pass

class QWeightSelector(IQWeightContainer):
    """ 权重选择器 """
    def __init__(self):
        self._weightObjectList = []    # type: list[QWeightObject]
        self.needUpdate = False
        self.totalWeight = 0

    @staticmethod
    def buildWeightSelector(*_QWeightObjects):
        # type: (QWeightObject) -> QWeightSelector
        """ 基于权重对象可变长参数构造选择器 """
        _obj = QWeightSelector()
        for v in _QWeightObjects:
            _obj.addQWeightObject(v)
        return _obj

    def add(self, value, weight = 1):
        # type: (object, int) -> QWeightObject
        """ 添加对象到权重池 返回QWeightObject """
        _obj = QWeightObject(value, weight)
        self.addQWeightObject(_obj)
        return _obj

    def addQWeightObject(self, _QWeightObject):
        # type: (QWeightObject) -> None
        """ 添加权重对象到权重池 """
        self.needUpdate = True
        self._weightObjectList.append(_QWeightObject)

    def removeQWeightObject(self, _QWeightObject):
        # type: (QWeightObject) -> None
        """ 从权重池中删除特定权重对象 """
        if _QWeightObject in self._weightObjectList:
            self._weightObjectList.remove(_QWeightObject)
            self.needUpdate = True

    def update(self):
        """ 更新数据 """
        self.needUpdate = False
        self.totalWeight = 0
        def _sort(x):
            # type: (QWeightObject) -> int
            self.totalWeight += x.weight
            return x.weight
        self._weightObjectList.sort(
            key=_sort, reverse=True
        )

    def randomSelection(self):
        # type: () -> object
        """ 随机抽取 """
        if self.needUpdate:
            self.needUpdate = False
            self.update()
        wV = randint(0, int(self.totalWeight))
        for v in self._weightObjectList:
            wV -= v.weight
            if wV <= 0:
                return v.value
        raise Exception("随机摇取错误 剩余权重值 {}".format(wV))

class QWeightPool(IQWeightContainer):
    """ 权重池
        适用于大量相同权重的选择结果摇取
    """
    def __init__(self):
        self._weightDIC = {}        # type: dict[int, list[QWeightObject]]
        self._weightList = []       # type: list[list[QWeightObject]]
        self.needUpdate = False
        self.totalWeight = 0

    @staticmethod
    def buildWeightPool(*_QWeightObjects):
        # type: (QWeightObject) -> QWeightPool
        """ 基于权重对象可变长参数构造权重池 """
        _obj = QWeightPool()
        for v in _QWeightObjects:
            _obj.addQWeightObject(v)
        return _obj

    def update(self):
        """ 更新数据 """
        self.needUpdate = False
        self.totalWeight = 0
        self._weightList = []
        for k, v in self._weightDIC.items():
            self.totalWeight += len(v) * k
            self._weightList.append(v)
        def _sort(x):
            # type: (list[QWeightObject]) -> int
            return x[0].weight * len(x)
        self._weightList.sort(key=_sort, reverse=True)

    def add(self, value, weight = 1):
        # type: (object, int) -> QWeightObject
        """ 添加对象到权重池 返回QWeightObject """
        _obj = QWeightObject(value, weight)
        self.addQWeightObject(_obj)
        return _obj

    def addQWeightObject(self, _QWeightObject):
        # type: (QWeightObject) -> None
        """ 添加权重对象到权重池 """
        self.needUpdate = True
        weight = _QWeightObject.weight
        if not weight in self._weightDIC:
            self._weightDIC[weight] = []
        self._weightDIC[weight].append(_QWeightObject)

    def removeQWeightObject(self, _QWeightObject):
        # type: (QWeightObject) -> None
        """ 从权重池中删除特定权重对象 """
        if _QWeightObject.weight in self._weightDIC:
            dataList = self._weightDIC[_QWeightObject.weight]
            if _QWeightObject in dataList:
                self.needUpdate = True
                dataList.remove(_QWeightObject)
            if len(dataList) <= 0:
                del self._weightDIC[_QWeightObject.weight]

    def randomSelection(self):
        # type: () -> object
        """ 从池中随机抽取 """
        if self.needUpdate:
            self.needUpdate = False
            self.update()
        wV = randint(0, int(self.totalWeight))
        for lis in self._weightList:
            lisWS = lis[0].weight *  len(lis)
            wV -= lisWS
            if wV <= 0:
                # 抽取结果位于此处
                return choice(lis).value
        raise Exception("随机摇取错误 剩余权重值 {}".format(wV))