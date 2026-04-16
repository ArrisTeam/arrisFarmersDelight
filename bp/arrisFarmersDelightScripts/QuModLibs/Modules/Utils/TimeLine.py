# -*- coding: utf-8 -*-
from copy import copy
lambda: "By Zero123"

class QTimeLine:
    """ 时间线类型 """
    class Args:
        def __init__(self, timeValue=0.0, data=None):
            # type: (float, object | None) -> None
            self.timeValue = timeValue
            self.data = data

        def __repr__(self):
            return str((self.timeValue, self.data))

    class FArray:
        """ 浮点数运算数组 """
        def __init__(self, dataList=[]):
            # type: (list[float | int]) -> None
            self._dataList = [float(v) for v in dataList]

        def getSize(self):
            return len(self._dataList)

        def getList(self):
            return self._dataList

        def getTuple(self):
            return tuple(self._dataList)

        def __repr__(self):
            return "<{}{}>".format(self.__class__.__name__, str(self._dataList))

        def _addOrSub(self, other, mut=1.0):
            if not isinstance(other, QTimeLine.FArray):
                raise TypeError()
            newFArray = self.__class__(copy(self._dataList))
            for i, v in enumerate(newFArray._dataList):
                newFArray._dataList[i] = v + mut * other._dataList[i]
            return newFArray

        def __add__(self, other=None):
            return self._addOrSub(other)

        def __sub__(self, other=None):
            return self._addOrSub(other, -1.0)

        def __mul__(self, other=1.0):
            newFArray = self.__class__(copy(self._dataList))
            for i, v in enumerate(newFArray._dataList):
                newFArray._dataList[i] = other * v
            return newFArray

    def __init__(self, objDict={}):
        # type: (dict[str, object]) -> None
        self._timeLineList = []     # type: list[QTimeLine.Args]
        self._maxFPS = 0.0
        if objDict:
            self.loadDict(objDict)

    def loadDict(self, objDict={}, updateNow=True):
        # type: (dict[str | float, object], bool) -> None
        """ 从dict解析并合并到时间线表 """
        for key, value in objDict.items():
            if isinstance(value, list):
                # 自动处理容器类型
                value = QTimeLine.FArray(value)
            self.addTimeNode(QTimeLine.Args(float(key), value))
        if updateNow:
            self.updateTimeLine()

    def removeTimeNode(self, args):
        # type: (QTimeLine.Args) -> None
        """ 删除时间节点(不会更新数据结构) """
        try:
            self._timeLineList.remove(args)
        except:
            pass

    def getMaxFpsTime(self):
        # type: () -> float
        """ 获取最大关键帧时间 """
        return self._maxFPS

    def addTimeNode(self, args):
        # type: (QTimeLine.Args) -> None
        """ 添加时间节点(不会更新数据结构) """
        self._timeLineList.append(args)

    def empty(self):
        """ 返回时间线对象是否为空 """
        return bool(self._timeLineList)

    def getLRTimeNode(self, timeValue=0.0):
        # type: (float) -> tuple[QTimeLine.Args, QTimeLine.Args]
        """ 基于时间获取时间线节点左右值 当超出边界时使用边界值 注意:该方法不会判断时间线是否为空 空时间线/异常时间数据可能抛出异常 """
        timeLineList = self._timeLineList   # 经过排序的时间线表
        if timeValue >= self._maxFPS:
            return (timeLineList[-1], timeLineList[-1])
        # 通过二分查找算法匹配左右节点
        leftIndex = 0
        rightIndex = len(timeLineList) - 1
        while leftIndex <= rightIndex:
            mid = (leftIndex + rightIndex) // 2
            value = timeLineList[mid]
            if value.timeValue <= timeValue:  
                leftIndex = mid + 1  
            else:
                rightIndex = mid - 1
        rightIndex = max(rightIndex, 0)
        return (timeLineList[rightIndex], timeLineList[leftIndex])

    def computeFrameAtTime(self, timeValue=0.0):
        # type: (float) -> float | object
        """ 计算指定时间帧(请确保时间线不为空) 帧时间基于简单的加减法和乘法完成 对于自定义类型请确保重载对应运算符 """
        if timeValue >= self.getMaxFpsTime():
            return self._timeLineList[-1].data
        elif timeValue <= self._timeLineList[0].timeValue:
            return self._timeLineList[0].data
        l, r = self.getLRTimeNode(timeValue)
        endTime = r.timeValue
        startTime = l.timeValue
        mut = (timeValue - startTime) / (endTime - startTime)
        newValue = (r.data - l.data) * mut + l.data
        return newValue

    def computeArrayFrameAtTime(self, timeValue=0.0):
        # type: (float) -> list[float]
        """ 适用于Array列表的特化时间帧计算 """
        data = self.computeFrameAtTime(timeValue)
        if isinstance(data, QTimeLine.FArray):
            return data.getList()
        raise RuntimeError("不受支持的类型")

    def getInstantVelocity(self, currentTime=0.0, deltaTime=0.033, unit=1.0):
        # type: (float, float, float) -> float | object
        """ 获取经过计算转换为的瞬时量 """
        nowValue = self.computeFrameAtTime(currentTime)
        lastValue = self.computeFrameAtTime(currentTime - deltaTime)
        return (nowValue - lastValue) * (1.0 / deltaTime) * (1.0 / unit)

    def getArrayInstantVelocity(self, currentTime=0.0, deltaTime=0.033, unit=1.0):
        # type: (float, float, float) -> list[float]
        """ 适用于Array列表的特化瞬时量计算 """
        data = self.getInstantVelocity(currentTime, deltaTime, unit)
        if isinstance(data, QTimeLine.FArray):
            return data.getList()
        raise RuntimeError("不受支持的类型")

    def getAverageVelocity(self, startTime=0.0, endTime=0.033, unit=1.0):
        # type: (float, float, float) -> float | object
        """ 获取指定时间区间内的平均速度 """
        startValue = self.computeFrameAtTime(startTime)
        endValue = self.computeFrameAtTime(endTime)
        deltaTime = endTime - startTime
        if deltaTime == 0.0:
            return 0.0  # 避免除以0
        return (endValue - startValue) * (1.0 / deltaTime) * (1.0 / unit)
    
    def getArrayAverageVelocity(self, startTime=0.0, endTime=0.033, unit=1.0):
        # type: (float, float, float) -> list[float]
        """ 适用于Array列表的特化平均变化量计算 """
        data = self.getAverageVelocity(startTime, endTime, unit)
        if isinstance(data, QTimeLine.FArray):
            return data.getList()
        raise RuntimeError("不受支持的类型")

    def updateTimeLine(self):
        """ 更新时间线 (当动态添加/移除时需要更新数据结构) """
        self._timeLineList.sort(key=lambda x: x.timeValue)
        if self._timeLineList:
            self._maxFPS = self._timeLineList[-1].timeValue
            return
        self._maxFPS = 0.0

    def __str__(self):
        return "<{}_{} {}>".format(self.__class__.__name__, hex(id(self)), [v for v in self._timeLineList])