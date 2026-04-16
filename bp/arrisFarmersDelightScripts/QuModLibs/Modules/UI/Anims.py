# -*- coding: utf-8 -*-
from Client import QUIControlFuntion, QUIAutoControlFuntion, EasyScreenNodeCls, ScreenNodeWrapper
from ...Client import clientApi, ListenForEvent, UnListenForEvent, levelId
from ..Utils.TimeLine import QTimeLine
from copy import copy
lambda: "UI动画模块 By Zero123"

class QEasingData:
    """ Qu缓动数据 """
    def __init__(self, t = 0.0, b = 0.0, c = 1.0, d = 0.8):
        self.t = t
        self.b = b
        self.c = c
        self.d = d

class QTransform:
    """ Qu动画变换类 """
    class EasingMode:
        """ 缓动类型 """
        Default = None
        """ 默认缓动模式 """
        Linear = None
        """ 线性模式 """
        @staticmethod
        def EaseInSide(data = QEasingData()):
            from math import cos
            return -data.c * cos(data.t / data.d * (3.141 / 2.0)) + data.c + data.b

        @staticmethod
        def EaseOutQuad(data = QEasingData()):
            data.t /= data.d  
            return -data.c * data.t * (data.t - 2) + data.b

    def __init__(self, fromValue, toValue, useTime = 1.0):
        self._uiNodeRef = None
        self._uiPath = ""
        self._fromValue = fromValue
        self._toValue = toValue
        self._useTime = useTime
        self._moveValue = toValue - fromValue
        self._nowTime = 0.0
        self._T_FORCEUPDATE = False
        self._finishCallBack = lambda *_: None
        self._easingMode = QTransform.EasingMode.Default
        """ 缓动类型 """
        self._priority = 0
        """ 优先级 越小越靠前执行 """
    
    def setFinishAnimBackCall(self, _callBack = lambda *_: None):
        """ 设置动画完整播放完毕的回调 """
        self._finishCallBack = _callBack
        return self

    def setEasingMode(self, state = None):
        """ 设置缓动模式 """
        self._easingMode = state
        return self
    
    def getUiNode(self):
        # type: () -> EasyScreenNodeCls | ScreenNodeWrapper | None
        """ 获取UINode节点 """
        if self._uiNodeRef == None:
            return None
        return self._uiNodeRef()

    def getParentPath(self):
        # type: () -> str
        """ 获取父节点路径 """
        return self._uiPath
    
    def getRatio(self):
        # type: () -> float
        """ 获取当前进度比率 """
        if self._useTime <= 0.0:
            return 1.0
        if self._easingMode == QTransform.EasingMode.Linear:
            return self._nowTime / self._useTime
        dataObj = QEasingData(self._nowTime, 0.0, 1.0, self._useTime)
        if hasattr(self._easingMode, "im_func"):
            return self._easingMode.im_func(dataObj)
        return self._easingMode(dataObj)
    
    def getValue(self):
        # type: () -> float
        """ 获取当前线性插值结果 """
        return self._fromValue + self.getRatio() * self._moveValue

    def onUpdate(self):
        pass

    def update(self, _time = 0.033, forceUpdate = True):
        # type: (float, bool) -> int
        """ 更新计算数据 """
        self._T_FORCEUPDATE = forceUpdate
        self._nowTime += _time
        if self._nowTime > self._useTime:
            self._nowTime = self._useTime
            self.onUpdate()
            self._finishCallBack()
            return -1
        self.onUpdate()
        return 0

class QLineTransform(QTransform):
    """ Qu线性变换 """
    def __init__(self, useTime = 1.0):
        QTransform.__init__(self, 0.0, 1.0, useTime=useTime)

class QPosTransform(QLineTransform):
    """ Qu位置变换 """
    def __init__(self, _startPos = (0, 0), _toPos = (0, 0), useTime = 1.0):
        QLineTransform.__init__(self, useTime=useTime)
        self._startPos = _startPos
        self._toPos = _toPos

    def onUpdate(self):
        QLineTransform.onUpdate(self)
        uiNode = self.getUiNode()
        conObj = uiNode.GetBaseUIControl(self.getParentPath())
        conObj.SetPosition(
            tuple(self._startPos[i] + (self._toPos[i] - self._startPos[i]) * self.getRatio() for i in range(2))
        )

class QSizeTransform(QLineTransform):
    """ Qu大小变换 """
    def __init__(self, _startSize = (0, 0), _toSize = (0, 0), useTime = 1.0, resizeChildren=False):
        QLineTransform.__init__(self, useTime=useTime)
        self._startSize = _startSize
        self._toSize = _toSize
        self.resizeChildren = resizeChildren

    def onUpdate(self):
        QLineTransform.onUpdate(self)
        uiNode = self.getUiNode()
        conObj = uiNode.GetBaseUIControl(self.getParentPath())
        conObj.SetSize(
            tuple(self._startSize[i] + (self._toSize[i] - self._startSize[i]) * self.getRatio() for i in range(2)), self.resizeChildren
        )

class QFullSizeTransform(QLineTransform):
    """ QuFullSize大小变换，相较于QSizeTransform，该动画类修改大小会保留约束中心点 """
    def __init__(self, startSize = (0, 0), toSize = (0, 0), useTime = 1.0):
        QLineTransform.__init__(self, useTime=useTime)
        self._startSize = startSize
        self._toSize = toSize

    def onUpdate(self):
        QLineTransform.onUpdate(self)
        uiNode = self.getUiNode()
        conObj = uiNode.GetBaseUIControl(self.getParentPath())
        x, y = tuple(self._startSize[i] + (self._toSize[i] - self._startSize[i]) * self.getRatio() for i in range(2))
        conObj.SetFullSize("x", {"absoluteValue": x})
        conObj.SetFullSize("y", {"absoluteValue": y})

class QAlphaTransform(QTransform):
    """ Qu不透明度变换(仅支持图片/文字) """
    def onUpdate(self):
        QTransform.onUpdate(self)
        uiNode = self.getUiNode()
        conObj = uiNode.GetBaseUIControl(self.getParentPath())
        conObj.SetAlpha(self.getValue())

class QuTypeWriter(QLineTransform):
    """ Qu打字机动画(仅支持文字控件) """
    def __init__(self, _text = "", useTime=1, childPath="", syncSize=False):
        QLineTransform.__init__(self, useTime)
        self.syncSize = syncSize
        self.childPath = childPath
        self._text = _text.decode("utf-8")  # 转换为unicode字符串以便中文支持
        self._lastLen = -1

    def onUpdate(self):
        QLineTransform.onUpdate(self)
        uiNode = self.getUiNode()
        ratio = self.getRatio()
        splitLen = int(round(ratio * len(self._text)))
        if splitLen == self._lastLen:
            # 新旧字符串相同 放弃切割
            return
        self._lastLen = splitLen
        splitText = self._text[:splitLen]    # 切片后的字符串
        uiNode.GetBaseUIControl(self.getParentPath()+self.childPath).asLabel().SetText(
            splitText.encode("utf-8"),       # 重新编码回utf8
            self.syncSize
        )

class QNullAnimNode(QLineTransform):
    """ 空动画节点 用于添加回调处理 其优先级靠后可以安全的作为动画的最后回调环节 """
    def __init__(self, useTime=1, bindFunc=None):
        # type: (float | int, function | None) -> None
        QLineTransform.__init__(self, useTime)
        self._priority = 10
        if bindFunc:
            self.setFinishAnimBackCall(bindFunc)

class QTimeLineTransform(QLineTransform):
    """ 时间线变换基类 """
    def __init__(self, lineDic={}):
        # type: (dict[str | float | int, list[float | int] | tuple[float | int]]) -> None
        newLineDic = {}
        for k, v in lineDic.items():
            if not isinstance(v, (list, tuple)):
                v = [v]
            newLineDic[float(k)] = QTimeLine.FArray(v)
        self._timeLine = QTimeLine(newLineDic)
        self._maxTime = self._timeLine.getMaxFpsTime()
        QLineTransform.__init__(self, self._maxTime)
    
    def onUpdate(self):
        QLineTransform.onUpdate(self)
        moveTime = min(self.getRatio() * self._maxTime, self._maxTime)
        self.onLineUpdate(moveTime)

    def onLineUpdate(self, valueTime):
        # type: (float) -> None
        pass
    
    def getLineBlendData(self, valueTime):
        # type: (float) -> list[float]
        return self._timeLine.computeArrayFrameAtTime(valueTime)

class QTimeLinePosTransform(QTimeLineTransform):
    """ 时间线位置移动变换 """
    def onLineUpdate(self, valueTime):
        # type: (float) -> None
        uiNode = self.getUiNode()
        conObj = uiNode.GetBaseUIControl(self.getParentPath())
        conObj.SetPosition(
            tuple(self.getLineBlendData(valueTime))
        )

class QTimeLineAlphaTransform(QTimeLineTransform):
    """ 时间线透明度变换 """
    def onLineUpdate(self, valueTime):
        # type: (float) -> None
        uiNode = self.getUiNode()
        conObj = uiNode.GetBaseUIControl(self.getParentPath())
        conObj.SetAlpha(
            self.getLineBlendData(valueTime)[0]
        )

class QTimeLineSizeTransform(QTimeLineTransform):
    """ 时间线大小变换 """
    def __init__(self, lineData = {}, resizeChildren=False):
        # type: (dict, bool) -> None
        QTimeLineTransform.__init__(self, lineData)
        self.resizeChildren = resizeChildren

    def onLineUpdate(self, valueTime):
        # type: (float) -> None
        uiNode = self.getUiNode()
        conObj = uiNode.GetBaseUIControl(self.getParentPath())
        conObj.SetSize(
            tuple(self.getLineBlendData(valueTime)), self.resizeChildren
        )

class QAnimsControl(QUIControlFuntion):
    """ Qu动画控件资源托管 """
    class QControlINFO:
        """ 控件信息 """
        def __init__(self, _path = ""):
            self._path = _path
            self._basePos = (0, 0)
            """ 初始化的基初POS信息 """
            self._baseScale = (0, 0)
            """ 初始化的基础大小信息 """

    def __init__(self, uiNode, parentPath):
        QUIControlFuntion.__init__(self, uiNode, parentPath)
        self.controlInfo = QAnimsControl.QControlINFO(parentPath)
        """ 控件信息 """
        self._animSet = set()   # type: set[QTransform]
    
    def getPos(self):
        """ 获取当前所在POS """
        return self.getBaseUIControl().GetPosition()

    def getScale(self):
        """ 获取当前Scale """
        return self.getBaseUIControl().GetSize()
    
    def screenPositionToRelativePos(self, screenPosition=(0, 0), pointMode = False):
        # type: (tuple[float, float], bool) -> tuple[float, float]
        """ 屏幕空间位置转相对位置
            @pointMode - 是否为中心坐标模式 默认左上角
        """
        uiNode = self.getUiNode()
        myScreenPosition = uiNode.QuGetControlABSPos(self._conPath) if not pointMode else uiNode.QuGetControlABSPointPos(self._conPath)
        myPos = self.getPos()
        return tuple(screenPosition[i] - myScreenPosition[i] + myPos[i] for i in range(2))
    
    @classmethod
    def bindControl(cls, _self, _path):
        obj = cls(_self, _path)
        obj.createControl()
        return obj
    
    def updateInitConInfo(self):
        """ 更新初始化控件信息 将当前位置记录并登记为初始信息 """
        control = self.getBaseUIControl()
        self.controlInfo._basePos = control.GetPosition()
        self.controlInfo._baseScale = control.GetSize()
    
    def onCreate(self):
        QUIControlFuntion.onCreate(self)
        self.updateInitConInfo()
    
    def matchTransformWithClass(self, _transformCls = QTransform):
        # type: (type[QTransform]) -> QTransform | None
        """ 基于class匹配已存在的动画 """
        for v in self._animSet:
            if issubclass(v.__class__, _transformCls):
                return v
        return None
    
    def playPosAnim(self, toPos = (0, 0), useTime = 1.0, screenPositionMode = False, mode = QTransform.EasingMode.EaseOutQuad):
        # type: (tuple[float, float], float, bool, object) -> QTransform | None
        """ 快捷播放位置动画 """
        if screenPositionMode:
            toPos = self.screenPositionToRelativePos(toPos)
        animObj = QPosTransform(self.getPos(), toPos, useTime=useTime)
        animObj.setEasingMode(mode)
        self.changeTransformAnim(animObj)
        return animObj

    def restPosAnim(self, useTime = 1.0, mode = QTransform.EasingMode.EaseOutQuad):
        # type: (float, object) -> QTransform | None
        """ 快捷播放重置位置动画 """
        animObj = QPosTransform(self.getPos(), self.controlInfo._basePos, useTime=useTime)
        animObj.setEasingMode(mode)
        self.changeTransformAnim(animObj)
        return animObj

    def playScaleAnim(self, toScale = (0, 0), useTime = 1.0, resizeChildren = False, mode = QTransform.EasingMode.EaseOutQuad):
        # type: (tuple[float, float], float, bool, object) -> QTransform | None
        """ 快捷播放大小动画 """
        animObj = QSizeTransform(self.getScale(), toScale, useTime=useTime, resizeChildren=resizeChildren)
        animObj.setEasingMode(mode)
        self.changeTransformAnim(animObj)
        return animObj

    def restScaleAnim(self, useTime = 1.0, resizeChildren = False, mode = QTransform.EasingMode.EaseOutQuad):
        # type: (float, bool, object) -> QTransform | None
        """ 快捷播放重置大小动画 """
        animObj = QSizeTransform(self.getScale(), self.controlInfo._baseScale, useTime=useTime, resizeChildren=resizeChildren)
        animObj.setEasingMode(mode)
        self.changeTransformAnim(animObj)
        return animObj
    
    def addTransformAnim(self, _transformObj):
        # type: (QTransform) -> QTransform
        """ 添加变换动画 """
        _transformObj._uiNodeRef = self._uiNodeRef
        _transformObj._uiPath = self._parentPath
        if not _transformObj in self._animSet:
            self._animSet.add(_transformObj)
        return _transformObj
    
    def changeTransformAnim(self, _transformObj):
        # type: (QTransform) -> QTransform
        """ 切换变换动画(相比直接播放将会打断已播放的同类动画) """
        _oldAnim = self.matchTransformWithClass(_transformObj.__class__)
        if _oldAnim:
            self.removeTransformAnim(_oldAnim)
        return self.addTransformAnim(_transformObj)

    def removeTransformAnim(self, _transformObj):
        # type: (QTransform) -> QTransform
        """ 移除变换动画 """
        _transformObj._uiNodeRef = None
        _transformObj._uiPath = ""
        if _transformObj in self._animSet:
            self._animSet.remove(_transformObj)

    def update(self, _time = 0.033, forceUpdate = True):
        """ 更新计算 """
        animList = list(self._animSet)
        animList.sort(key=lambda x: x._priority)
        for v in animList:
            if v.update(_time, forceUpdate=forceUpdate) == -1:
                if v in self._animSet:
                    self._animSet.remove(v)

    def hasAnim(self):
        return bool(self._animSet)

class QAnimManager(QUIAutoControlFuntion):
    """ Qu动画管理器 """
    def __init__(self, uiNode):
        QUIAutoControlFuntion.__init__(self, uiNode, "")
        self._conAnimDict = {}  # type: dict[str, QAnimsControl]
        """ 控件动画表 """

    def fpsUpdate(self, mut=1.0):
        if self._conAnimDict:
            # 避免空update
            comp = clientApi.GetEngineCompFactory().CreateGame(levelId)
            self.update(1.0 / comp.GetFps() * mut)

    @classmethod
    def bindNode(cls, uiNode):
        """ 绑定节点 """
        obj = cls(uiNode)
        obj.createControl()
        return obj

    def startEventUpdate(self):
        ListenForEvent("OnScriptTickNonChaseFrameClient", self, self.fpsUpdate)

    def stopEventUpdate(self):
        UnListenForEvent("OnScriptTickNonChaseFrameClient", self, self.fpsUpdate)

    def onCreate(self):
        QUIAutoControlFuntion.onCreate(self)
        self.startEventUpdate()

    def onDestroy(self):
        QUIAutoControlFuntion.onDestroy(self)
        self.stopEventUpdate()

    def update(self, dTime=0.033, forceUpdate=True):
        for k, v in copy(self._conAnimDict).items():
            if not v.getParentLiveState():
                del self._conAnimDict[k]
                continue
            v.update(dTime, forceUpdate)
    
    def hasAnim(self):
        for v in self._conAnimDict.values():
            if v.hasAnim():
                return True
        return False

    def getControlAnimObj(self, _path=""):
        # type: (str) -> QAnimsControl
        """ 获取控件动画对象 """
        if not _path in self._conAnimDict:
            # 初始化控件对象
            obj = QAnimsControl.bindControl(self.getUiNode(), _path)
            if not obj.getParentLiveState():
                raise Exception("无效的控件路径")
            self._conAnimDict[_path] = obj
        return self._conAnimDict[_path]