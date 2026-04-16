# -*- coding: utf-8 -*-
from ...Client import clientApi, levelId
from Client import QUIControlFuntion, QUIAutoControlFuntion, QGridData, EasyScreenNodeCls, ScreenNodeWrapper
from math import ceil
lambda: "UI扩展功能 By Zero123"

class QGridAdapter(QUIAutoControlFuntion):
    """ QUI 网格渲染适配器(实时) """
    def __init__(self, uiNode, parentPath, isScrollGrid=False, bindFunc = lambda *_: None, bindGridConName = "", bindUpdateBeforeFunc = lambda *_: None, bindUpdateFinishFunc = lambda *_: None):
        # type: (EasyScreenNodeCls | ScreenNodeWrapper, str, bool, object, str, object, object) -> None
        """
            @uiNode - 绑定的UI节点
            @isScrollGrid - 按网格列表计算(即列表直接引用网格的控件关系)
            @bindFunc - 绑定关联func(viewPath: str, i: int) -> None
            @bindGridConName - 设置绑定网格控件名称 (基于pos计算算法 如果您的控件本身带有数字结尾需设置该属性)
        """
        QUIAutoControlFuntion.__init__(self, uiNode, parentPath)
        self.gridObj = QGridData(
            parentPath,
            isScrollGrid,
            bindFunc=bindFunc,
            bindGridConName=bindGridConName,
            bindUpdateBeforeFunc=bindUpdateBeforeFunc,
            bindUpdateFinishFunc=bindUpdateFinishFunc
        )
        """ Qu网格对象 """
    
    def init(self):
        """ 初始化 (createControl别名) """
        self.createControl()
        return self
    
    def updateRender(self):
        """ 刷新渲染 """
        self.gridObj.updateRender(self.getUiNode())
    
    def getRealPath(self):
        """ 获取实际渲染路径 """
        return self.gridObj.getRealPath(self.getUiNode())
    
    def setGridDimension(self, scale=(2, 2)):
        """ 设置Grid控件的大小(请在初始化之后使用) """
        self.getUiNode().GetBaseUIControl(self.getRealPath()).asGrid().SetGridDimension(scale)
    
    def onCreate(self):
        QUIAutoControlFuntion.onCreate(self)
        self.listenQGridRender(self.gridObj)
    
    def onDestroy(self):
        QUIAutoControlFuntion.onDestroy(self)
        self.unListenQGridRender(self.gridObj)

class IQVirtualControl:
    def update(self, uiNode, path=""):
        # type: (EasyScreenNodeCls | ScreenNodeWrapper, str) -> None
        """ 更新处理 """
        pass

class QVirtualGridManager(QUIControlFuntion):
    """
        QUI 虚拟网格对象管理器 (使用QGridAdapter实现的智能处理)
        网格的渲染处理是异步完成的 尤其是当网格与列表搭配时仅渲染可视区域控件 这对一些固定数据处理表现可能略显繁琐
        QVirtualGridManager 则是自动完成处理的封装工具 允许您像常规控件一样操作
    """
    class QVirtualImage(IQVirtualControl):
        def __init__(self):
            self.sprite = None          # type: str | None
            """ IMG图片 """
            self.clipRatio = None       # type: float | None
            """ 裁剪比例 """
            self.clipDirection = None   # type: str | None
            """ 裁剪方向 """
            self.grayMode = None        # type: bool | None
            """ 置灰模式 """

        def update(self, uiNode, path=""):
            # type: (EasyScreenNodeCls | ScreenNodeWrapper, str) -> None
            if self.sprite != None:
                uiNode.GetBaseUIControl(path).asImage().SetSprite(self.sprite)
            if self.clipDirection != None:
                uiNode.GetBaseUIControl(path).asImage().SetClipDirection(self.clipDirection)
            if self.clipRatio != None:
                uiNode.GetBaseUIControl(path).asImage().SetSpriteClipRatio(self.clipRatio)
            if self.grayMode != None:
                uiNode.GetBaseUIControl(path).asImage().SetSpriteGray(self.grayMode)

    class QVirtualProgressBar(IQVirtualControl):
        def __init__(self):
            self.value = None
            """ 进度值 """

        def update(self, uiNode, path=""):
            # type: (EasyScreenNodeCls | ScreenNodeWrapper, str) -> None
            if self.value != None:
                uiNode.GetBaseUIControl(path).asProgressBar().SetValue(self.value)

    class QVirtualLabel(IQVirtualControl):
        """ 文本信息对象 """
        def __init__(self):
            self.text = None    # type: str | None
            """ 文本信息 """
            self.syncSize = False
        
        def update(self, uiNode, path=""):
            # type: (EasyScreenNodeCls | ScreenNodeWrapper, str) -> None
            if self.text != None:
                uiNode.GetBaseUIControl(path).asLabel().SetText(
                    self.text, self.syncSize
                )

    class QVirtualButton(IQVirtualControl):
        """ 按钮信息对象 """
        def __init__(self):
            self._bindClickFun = None   # type: object | None
        
        def setBindClickFun(self, bindFun=lambda *_: None):
            self._bindClickFun = bindFun

        def update(self, uiNode, path=""):
            # type: (EasyScreenNodeCls | ScreenNodeWrapper, str) -> None
            if self._bindClickFun != None:
                uiNode.QuSetButtonCallback(path, self._bindClickFun)

    class QVirtualControl(IQVirtualControl):
        """ 虚拟控件对象 (托管信息渲染) """
        def __init__(self):
            self.button = QVirtualGridManager.QVirtualButton()
            """ 按钮信息 """
            self.label = QVirtualGridManager.QVirtualLabel()
            """ 文字控件信息 """
            self.progressBar = QVirtualGridManager.QVirtualProgressBar()
            """ 进度条数据 """
            self.image = QVirtualGridManager.QVirtualImage()
            """ 图片数据信息 """
            
            self.childMap = {}  # type: dict[str, QVirtualGridManager.QVirtualControl]
            """ 子节点map """
            self.visible = None
            """ 可见性(None值使用预设可见性) """
        
        def getChild(self, childPath="/"):
            """ 获取Child对象 """
            if childPath in self.childMap:
                return self.childMap[childPath]
            dataObj = QVirtualGridManager.QVirtualControl()
            self.childMap[childPath] = dataObj
            return dataObj
        
        def update(self, uiNode, parentPath=""):
            # type: (EasyScreenNodeCls | ScreenNodeWrapper, str) -> None
            for data in (self.button, self.label, self.progressBar, self.image):
                data.update(uiNode, parentPath)
            if self.visible != None:
                uiNode.GetBaseUIControl(parentPath).SetVisible(self.visible)
            for childPath, childObj in self.childMap.items():
                newPath = parentPath + childPath
                childObj.update(uiNode, newPath)

    def __init__(self, uiNode, parentPath, isScrollGrid=False, bindGridConName=""):
        QUIControlFuntion.__init__(self, uiNode, parentPath)
        self._width = 2
        self._dataList = []         # type: list[QVirtualGridManager.QVirtualControl]
        self.gridAdapter = None     # type: QGridAdapter | None
        self.isScrollGrid = isScrollGrid
        self.bindGridConName = bindGridConName
        self._updateNow = True
        self._hidePathList = []     # type: list[str]
        self._lastTimer = None
    
    def init(self, updateNow=True):
        self._updateNow = updateNow
        self.createControl()
        self._updateNow = True
        return self
    
    def setGridWidth(self, w = 2):
        """ 设置网格大小宽度 """
        self._width = w
        return self
    
    def getVirtualControlWithIndex(self, i=0):
        """ 基于下标拿到虚拟控件对象 """
        return self._dataList[i]

    def addVirtualControl(self):
        """ 添加虚拟控件对象 """
        dataObj = QVirtualGridManager.QVirtualControl()
        self._dataList.append(dataObj)
        return dataObj
    
    def removeVirtualControlWithIndex(self, i=0):
        """ 基于下标删除虚拟控件 """
        del self._dataList[i]
    
    def getDataList(self):
        """ 获取数据列表(引用原始对象) """
        return self._dataList
    
    def size(self):
        """ 元素数量 """
        return len(self._dataList)

    def clear(self):
        """ 清空数据列表 """
        self._dataList = []

    def updateRender(self):
        """ 更新渲染 """
        uiNode = self.getUiNode()
        count = len(self._dataList)
        uiNode.GetBaseUIControl(self.gridAdapter.getRealPath()).asGrid().SetGridDimension(
            (self._width, ceil(float(count) / self._width))
        )
        self.gridAdapter.updateRender()
    
    def renderView(self, viewPath="", index=0):
        if index >= len(self._dataList):
            # 超出渲染区域的数据
            self._hidePathList.append(viewPath)
            return
        data = self._dataList[index]
        data.update(self.getUiNode(), viewPath)
    
    def renderBefore(self):
        if self._lastTimer:
            comp = clientApi.GetEngineCompFactory().CreateGame(levelId)
            comp.CancelTimer(self._lastTimer)
            self._lastTimer = None
        uiNode = self.getUiNode()
        for path in self._hidePathList:
            control = uiNode.GetBaseUIControl(path)
            if not control:
                continue
            control.SetVisible(True)
        self._hidePathList = []

    def renderFinish(self):
        uiNode = self.getUiNode()
        for path in self._hidePathList:
            control = uiNode.GetBaseUIControl(path)
            if not control:
                continue
            control.SetVisible(False)
        self._lastTimer = None
    
    def _renderFinish(self):
        if len(self._hidePathList) > 0:
            comp = clientApi.GetEngineCompFactory().CreateGame(levelId)
            self._lastTimer = comp.AddTimer(0.0, self.renderFinish)

    def onCreate(self):
        QUIControlFuntion.onCreate(self)
        self.gridAdapter = QGridAdapter(
            self.getUiNode(), self._parentPath, self.isScrollGrid,
            bindFunc=self.renderView, bindGridConName=self.bindGridConName,
            bindUpdateBeforeFunc=self.renderBefore,
            bindUpdateFinishFunc=self._renderFinish
        )
        self.gridAdapter.init()
        if self._updateNow:
            self.updateRender()
    
    def onDestroy(self):
        QUIControlFuntion.onDestroy(self)
        self.gridAdapter.removeControl()
        if self._lastTimer:
            comp = clientApi.GetEngineCompFactory().CreateGame(levelId)
            comp.CancelTimer(self._lastTimer)
            self._lastTimer = None