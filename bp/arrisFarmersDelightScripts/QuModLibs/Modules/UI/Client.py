# -*- coding: utf-8 -*-
from ...Client import _getLoaderSystem, ListenForEvent, UnListenForEvent, Events
from ..EventsPool.Client import POOL_ListenForEvent, POOL_UnListenForEvent
from ...UI import EasyScreenNodeCls, ScreenNodeWrapper
from ...Util import QRAIIDelayed, QBaseRAIIEnv, QTemplate
import weakref
lambda: "UI扩展功能 By Zero123"

class QGridData:
    """ 网格信息 """
    EVENT_NAME = "GridComponentSizeChangedClientEvent"
    def __init__(self, path, isScrollGrid = False, bindFunc = lambda *_: None, incrementalCallback = lambda *_: None, bindUpdateBeforeFunc = lambda *_: None, bindUpdateFinishFunc = lambda *_: None, bindGridConName = "", pushUIMode=False):
        # type: (str, bool, function, function, function, function, str, bool) -> None
        """
            - path 路径
            - isScrollGrid 列表网格渲染模式
            - bindFunc 绑定渲染更新函数 function[str, int] 接收路径与index
            - incrementalCallback 绑定增量更新函数 参数同bindFunc
            - bindUpdateBeforeFunc 绑定一轮更新触发回调之前的前置业务逻辑
            - bindUpdateFinishFunc 绑定一轮更新触发回调完毕后的业务逻辑
            - bindGridConName 绑定网格格子控件名(当名字本身包含数字结尾时会影响index计算 显性声明名字可以解决这个问题)
            - [旧版实现已废弃] pushUIMode 适用于PushUI界面的处理模式 用于修正字节点路径的缺失问题
        """
        self.path = path
        self.isScrollGrid = isScrollGrid
        self.bindFunc = bindFunc
        self.incrementalCallback = incrementalCallback
        self.bindUpdateBeforeFunc = bindUpdateBeforeFunc
        self.bindUpdateFinishFunc = bindUpdateFinishFunc
        self.bindGridConName = bindGridConName
        self._lastRenderCacheSet = set()    # type: set[tuple[str, int]]
        self._pushUIMode = pushUIMode
        self._gridPathBasedOnScrollView = ""
        self._sharedDict = {}

    def setGridPathBasedOnScrollView(self, _path=""):
        """ 设置基于滚动视图的网格路径 (倘若不是直接绑定网格而是有其他父级关系时使用该方法) """
        self._gridPathBasedOnScrollView = _path
        return self

    def getRealPath(self, uiNode):
        # type: (EasyScreenNodeCls | ScreenNodeWrapper) -> str
        """ 获取真实路径 """
        if self.isScrollGrid:
            # 对于网格列表则获取一下实时渲染路径
            return uiNode.GetBaseUIControl(self.path).asScrollView().GetScrollViewContentPath() + self._gridPathBasedOnScrollView
        return self.path

    def getRealComponentPath(self, uiNode):
        # type: (EasyScreenNodeCls | ScreenNodeWrapper) -> str
        componentPath = str(getattr(uiNode, "component_path"))
        return componentPath + self.getRealPath(uiNode)
    
    def getPosWithPath(self, _path = ""):
        """ 基于路径获取Pos """
        if self.bindGridConName:
            _path = _path[_path.rfind(self.bindGridConName)+len(self.bindGridConName):]
        count = 0
        _sum = 0
        for _char in _path[::-1]:
            _c = ord(_char)
            if 48 <= _c and 57 >= _c:
                _sum += (10 ** count) * (_c - 48)
                count += 1
                continue
            break
        return _sum

    def childsGen(self, uiNode):
        """ 创建子节点生成器 包含所有已渲染的子节点根级PATH """
        realPath = self.getRealPath(uiNode)
        for childName in uiNode.GetChildrenName(realPath):
            gridPath = "{}/{}".format(realPath, childName)
            yield (self.getPosWithPath(gridPath) - 1, gridPath)

    def clearIncrementalCache(self):
        """ 清理增量缓存 """
        self._lastRenderCacheSet.clear()

    def updateRender(self, uiNode):
        # type: (EasyScreenNodeCls | ScreenNodeWrapper) -> None
        """ 刷新渲染 """
        self.bindUpdateBeforeFunc()
        lastRenderCache = self._lastRenderCacheSet
        nowRenderSet = set()
        for index, gridPath in self.childsGen(uiNode):
            args = (gridPath, index)
            nowRenderSet.add(args)
            try:
                # 增量渲染更新
                if not args in lastRenderCache:
                    self.incrementalCallback(args[0], args[1])
                self.bindFunc(gridPath, index)
            except Exception:
                import traceback
                traceback.print_exc()
        self._lastRenderCacheSet = nowRenderSet
        self.bindUpdateFinishFunc()

    def updateOnceRender(self, viewPath, index=None):
        # type: (str, int | None) -> None
        """ 单一渲染更新 """
        if index == None:
            index = self.getPosWithPath(viewPath) - 1
        self.bindUpdateBeforeFunc()
        self.incrementalCallback(viewPath, index)
        self.bindFunc(viewPath, index)
        self.bindUpdateFinishFunc()

class QUICanvas:
    """ QUI画布绘制类 """
    def __init__(self, uiNode, parentPath = ""):
        # type: (EasyScreenNodeCls | ScreenNodeWrapper, str) -> None
        self._conPath = None
        self._uiNodeRef = weakref.ref(uiNode)
        """ ui节点弱引用 """
        self._parentPath = parentPath
        """ 节点所在父路径 """
        self.drawDefName = ""
        """ 绑定预制件 namespace.controlName """
        self._T_FORCEUPDATE = True
        self._T_JUST_ON_DESTROY = False

    def getNodeLiveState(self):
        # type: () -> bool
        """ 获取节点存活状态 """
        if self.getUiNode():
            return True
        return False
    
    def getParentLiveState(self):
        # type: () -> bool
        """ 获取父节点存活状态 """
        if not self.getNodeLiveState():
            return False
        return self.getUiNode().GetBaseUIControl(self._parentPath) != None

    def getDrawControlLiveState(self):
        # type: () -> bool
        """ 获取绘制节点存活状态 """
        if not self.getNodeLiveState():
            return False
        return self.getUiNode().GetBaseUIControl(self._conPath) != None

    def getUiNode(self):
        """ 获取ui节点(解弱引用) """
        return self._uiNodeRef()

    def rebuildUiNode(self, newUiNode):
        # type: (EasyScreenNodeCls | ScreenNodeWrapper) -> None
        """ 重新绑定uiNode """
        if self._conPath != None:
            raise Exception("已构建控件的对象无法重新绑定UI节点")
        self._uiNodeRef = weakref.ref(newUiNode)

    def rebuildParentPath(self, _newPath):
        # type: (str) -> None
        """ 重新绑定parent """
        if self._conPath != None:
            raise Exception("已构建控件的对象无法重新绑定父路径")
        self._parentPath = _newPath

    def onCreate(self):
        from uuid import uuid4
        uiNode = self.getUiNode()
        uiName = "q"+str(uuid4().hex)
        childNode = uiNode.CreateChildControl(self.drawDefName, uiName, uiNode.GetBaseUIControl(self._parentPath), self._T_FORCEUPDATE)
        self._conPath = childNode.GetPath()

    def onDestroyBefore(self):
        pass

    def onDestroy(self):
        pass

    def getRandomName(self):
        """ 获取随机名称 """
        from uuid import uuid4
        return "q"+str(uuid4().hex)

    def createChildControl(self, drawDefName = "namespace.controlName", conName = "_default", forceUpdate = True):
        """ 动态创建子控件 """
        uiNode = self.getUiNode()
        return uiNode.CreateChildControl(drawDefName, conName, uiNode.GetBaseUIControl(self._parentPath), forceUpdate)

    def clearParent(self):
        """ 清理parent目录所有控件 """
        uiNode = self.getUiNode()
        realPath = self._parentPath
        for childName in uiNode.GetChildrenName(realPath):
            childPath = "{}/{}".format(realPath, childName)
            uiNode.RemoveComponent(childPath, self._parentPath)

    def listenQGridRender(self, _QGridData):
        # type: (QGridData) -> None
        """ 监听网格渲染 """
        def GridComponentSizeChangedClientEvent(args={}):
            path = str(args["path"])
            uiNode = self.getUiNode()
            if path.endswith(_QGridData.getRealComponentPath(uiNode)):
                _QGridData.updateRender(uiNode)
        from ...Util import RandomUid
        GridComponentSizeChangedClientEvent.__name__ = RandomUid()
        _getLoaderSystem().unsafeUpdate(ListenForEvent(QGridData.EVENT_NAME, self, GridComponentSizeChangedClientEvent))
        _QGridData._sharedDict["listenFun"] = GridComponentSizeChangedClientEvent

    def unListenQGridRender(self, _QGridData):
        # type: (QGridData) -> None
        """ 取消监听网格渲染 """
        UnListenForEvent(QGridData.EVENT_NAME, self, _QGridData._sharedDict["listenFun"])
        _QGridData._sharedDict["listenFun"] = None

    def getBaseUIControl(self):
        """ 获取网易UI控件对象 """
        if not self._conPath:
            return
        return self.getUiNode().GetBaseUIControl(self._conPath)

    def removeControl(self, justOnDestroy = False):
        """ 移除控件 """
        self._T_JUST_ON_DESTROY = justOnDestroy
        if justOnDestroy:
            if self._conPath != None:
                self.onDestroyBefore()
                self._conPath = None
                self.onDestroy()
                return True
            return False
        if self._conPath != None:
            self.onDestroyBefore()
            self.getUiNode().RemoveComponent(self._conPath, self._parentPath)
            self._conPath = None
            self.onDestroy()
            return True
        return False
    
    def createControl(self, forceUpdate = True):
        """ 构建控件 """
        if self._conPath != None:
            return
        self._T_FORCEUPDATE = forceUpdate
        self.onCreate()

class QUIControlFuntion(QUICanvas):
    """ QUI控件功能类(继承QUICanvas 但不再创建新控件而是管理已有控件) """
    def onCreate(self):
        self._conPath = self._parentPath

    def removeControl(self):
        if self._conPath != None:
            self.onDestroyBefore()
            self._conPath = None
            self.onDestroy()

class QRAIICanvas(QUICanvas, QRAIIDelayed, QTemplate):
    """ 【推荐】RAII画布类，自动上下文管理资源
        class CustomCanvas(QRAIICanvas["jsonName.screenName"]):
            pass
    """
    _BIND_JSON_DEF = ""
    _TEMPLATE_ARGS = [ "_BIND_JSON_DEF" ]
    def __init__(self, uiNode, parentPath="", initLoad=True):
        QUICanvas.__init__(self, uiNode, parentPath)
        self.drawDefName = self.drawDefName or self.__class__._BIND_JSON_DEF
        if initLoad and isinstance(uiNode, QBaseRAIIEnv):
            uiNode.addRAIIRes(self)

    def _loadResource(self):
        QRAIIDelayed._loadResource(self)
        self.createControl()

    def _cleanup(self):
        QRAIIDelayed._cleanup(self)
        uiNode = self.getUiNode()
        if isinstance(uiNode, ScreenNodeWrapper) and uiNode._raiiCleanState:
            # UI销毁期间的清理无需销毁控件（避免额外性能开销）
            self.removeControl(True)
        else:
            self.removeControl(False)

class QRAIIControlFuntion(QUIControlFuntion, QRAIIDelayed):
    """ 【推荐】基于RAII上下文资源管理的控件管理类 """
    def __init__(self, uiNode, parentPath="", autoLoad=True):
        QUIControlFuntion.__init__(self, uiNode, parentPath)
        if autoLoad and isinstance(uiNode, QBaseRAIIEnv):
            uiNode.addRAIIRes(self)

    def _loadResource(self):
        QRAIIDelayed._loadResource(self)
        self.createControl()

    def _cleanup(self):
        QRAIIDelayed._cleanup(self)
        self.removeControl()

class QGridBinder(QRAIIControlFuntion):
    """ 网格绑定器 用于自动化管理界面中的网格/列表网格元素更新处理
        self.gridBinder = QGridBinder(self).setGridData(
            QGridData(...)
        )

        若class并未继承DRAII上下文管理，则需要手动start/stop
        def Create(self):
            self.gridBinder.start()
        
        def Destroy(self):
            self.gridBinder.stop()
    """
    def __init__(self, uiNode, gridData=None, parentPath=""):
        self._bindGridData = gridData
        QRAIIControlFuntion.__init__(self, uiNode, parentPath, not gridData is None)

    def setGridData(self, gridData):
        # type: (QGridData) -> QGridBinder
        self._bindGridData = gridData
        return self

    def setGridDimension(self, size=(1, 1)):
        """ 经过封装的网格元素数量调整 """
        self.getUiNode().GetBaseUIControl(self.getRealPath()).asGrid().SetGridDimension(size)
        return self

    def start(self):
        """ 启用绑定器(需手动释放) """
        if not self._bindGridData:
            raise RuntimeError("缺少QGridData绑定 请先通过setGridData绑定管理数据")
        self.createControl()
        return self

    def stop(self):
        """ 停用绑定器(释放) """
        self.removeControl()
        return self

    def updateRender(self):
        """ 主动触发渲染更新 将触发对应的绑定函数 """
        self._bindGridData.updateRender(self.getUiNode())
        return self

    def getRealPath(self):
        """ 获取真实的渲染路径 """
        return self._bindGridData.getRealPath(self.getUiNode())

    def updateOnceRender(self, viewPath, index=None):
        # type: (str, int | None) -> QGridBinder
        """ 单一渲染更新 """
        self._bindGridData.updateOnceRender(viewPath, index)
        return self

    def clearIncrementalCache(self):
        """ 增量缓存清理 """
        self._bindGridData.clearIncrementalCache()
        return self
    
    def setButtonClickHandler(self, buttonPath, onClick=lambda: None):
        """ 封装的设置按钮点击回调 """
        def creatFun(func):
            def _onClick(*_):
                return func()
            return _onClick
        baseUIControl = self.getUiNode().GetBaseUIControl(buttonPath)
        baseUIControl.SetTouchEnable(True)
        buttonUIControl = baseUIControl.asButton()
        buttonUIControl.AddTouchEventParams({"isSwallow":True})
        buttonUIControl.SetButtonTouchUpCallback(creatFun(onClick))
        return self
    
    def bindButtonClickHandler(self, buttonPath):
        """ 封装的装饰器绑定按钮函数调用 """
        def _wrapper(func):
            self.setButtonClickHandler(buttonPath, func)
            return func
        return _wrapper

    def onCreate(self):
        QRAIIControlFuntion.onCreate(self)
        self.listenQGridRender(self._bindGridData)

    def onDestroy(self):
        QRAIIControlFuntion.onDestroy(self)
        if self._bindGridData:
            self._bindGridData.clearIncrementalCache()
        self.unListenQGridRender(self._bindGridData)

class QUIAutoCanvas(QUICanvas):
    """ QUI智能画布绘制类 """
    def _getIsLive(self):
        return self.getDrawControlLiveState()

    def _onTick(self, _={}):
        if not self._getIsLive():
            self.removeControl(True)
            return
        self.onTick()

    def onTick(self):
        pass

    def onCreate(self):
        QUICanvas.onCreate(self)
        POOL_ListenForEvent("OnScriptTickClient", self._onTick)
    
    def onDestroy(self):
        QUICanvas.onDestroy(self)
        POOL_UnListenForEvent("OnScriptTickClient", self._onTick)

class QUIAutoControlFuntion(QUIControlFuntion):
    """ QUI智能控件功能类(适用于非支持RAII管理的界面) """
    def _getIsLive(self):
        return self.getParentLiveState()

    def _onTick(self, _={}):
        if not self._getIsLive():
            self.removeControl()
            return
        self.onTick()

    def onTick(self):
        pass

    def onCreate(self):
        QUIControlFuntion.onCreate(self)
        POOL_ListenForEvent("OnScriptTickClient", self._onTick)
    
    def onDestroy(self):
        QUIControlFuntion.onDestroy(self)
        POOL_UnListenForEvent("OnScriptTickClient", self._onTick)