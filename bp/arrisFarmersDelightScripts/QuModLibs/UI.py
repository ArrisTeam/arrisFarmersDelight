# -*- coding: utf-8 -*-
from QuClientApi.ui.screenNode import ScreenNode as BaseScreenNode
from mod.client.ui.screenNode import ScreenNode
import mod.client.extraClientApi as clientApi
from Util import (
    ModDirName,
    RandomUid,
    ExceptionHandling,
    getObjectPathName,
    TRY_EXEC_FUN,
    QDRAIIEnv
)
from Client import ListenForEvent, UnListenForEvent
from types import MethodType
from functools import wraps
lambda: "By Zero123"

__all__ = [
    "ScreenNodeWrapper", "EasyScreenNodeCls", "ESNC"
]

_BASE_SCREEN_NODE_CLS = ScreenNode

class ScreenNodeWrapper(_BASE_SCREEN_NODE_CLS, QDRAIIEnv, BaseScreenNode):
    """ 封装界面节点类 按类隔离命名空间与Key名 """
    # 若需要更加复杂的功能支持, 请使用: Modules/UI/EnhancedUI.py
    _AUTO_REGISTER_UI_MAP = {}

    def __init__(self, namespace, name, param):
        _BASE_SCREEN_NODE_CLS.__init__(self, namespace, name, param)
        QDRAIIEnv.__init__(self)
        self._raiiCleanState = False

    @staticmethod
    def _AUTO_REGISTER_UI_FINISH_EVENT(_={}):
        for func in ScreenNodeWrapper._AUTO_REGISTER_UI_MAP.values():
            TRY_EXEC_FUN(func)

    @staticmethod
    def autoRegister(uiScreenDef):
        """ 自动注册装饰器 """
        def _autoRegister(cls):
            uiCls = cls # type: type[ScreenNodeWrapper]
            key = uiCls._createUiKey()
            if not ScreenNodeWrapper._AUTO_REGISTER_UI_MAP:
                # 初始化内部监听管理
                ListenForEvent("UiInitFinished", ScreenNodeWrapper, ScreenNodeWrapper._AUTO_REGISTER_UI_FINISH_EVENT)
            if not key in ScreenNodeWrapper._AUTO_REGISTER_UI_MAP:
                ScreenNodeWrapper._AUTO_REGISTER_UI_MAP[key] = lambda: uiCls.registerUI(uiScreenDef=uiScreenDef)
            return cls
        return _autoRegister

    @classmethod
    def createUI(cls, uiKey="", createParams=None, isHud=1):
        """ 创建HUD_UI """
        if 1 > 2:
            return cls.getUiNode()
        if not isHud is None:
            createParams = createParams or dict()
            createParams["isHud"] = isHud
        return clientApi.CreateUI(ModDirName, cls._createUiKey(uiKey), createParams)

    @classmethod
    def pushScreen(cls, uiKey="", createParams=None):
        """ 使用栈管理的方式创建UI """
        if 1 > 2:
            return cls.getUiNode()
        return clientApi.PushScreen(ModDirName, cls._createUiKey(uiKey), createParams)

    @staticmethod
    def popScreen():
        """ 关闭POP界面(栈顶) """
        return clientApi.PopScreen()

    @staticmethod
    def nativePopTopUI():
        """ 弹出UI栈顶的UI """
        return clientApi.PopTopUI()

    @classmethod
    def removeClsUI(cls, uiKey=""):
        """ 删除用户的当前UI实例 """
        uiNode = cls.getUiNode(uiKey)
        if uiNode:
            uiNode.SetRemove()
            return True
        return False

    @classmethod
    def registerUI(cls, uiKey="", uiScreenDef=None):
        return clientApi.RegisterUI(ModDirName, cls._createUiKey(uiKey), getObjectPathName(cls), uiScreenDef)

    @classmethod
    def getUiNode(cls, uiKey=""):
        if 1 > 2:
            return cls("none", "none", {})
        uiNode = clientApi.GetUI(ModDirName, cls._createUiKey(uiKey))
        if uiNode:
            return uiNode
        return None

    @classmethod
    def _createUiKey(cls, uiKey=""):
        return "{}_{}_{}".format(cls.__name__, hash(getObjectPathName(cls)), uiKey)

    def setButtonClickHandler(self, buttonPath, onClick=lambda: None):
        """ 封装的设置按钮点击回调 """
        def creatFun(func):
            def _onClick(*_):
                return func()
            return _onClick
        baseUIControl = self.GetBaseUIControl(buttonPath)
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

    def Create(self):
        """ UI_CREATE方法 请确保重写后调用父级 """
        # RAII资源管理初始化
        self.setDRAIIEnvState(True)
        self.loadALLDRAIIRes()
    
    def Update(self):
        pass

    def Destroy(self):
        """ UI_DESTROY方法 请确保重写后调用父级 """
        # RAII资源管理析构
        if self._draiiEnvState:
            self.setDRAIIEnvState(False)
            self._raiiCleanState = True
            self.freeALLRAIIRes()
            self._raiiCleanState = False

# ================================================
# 因历史原因 以下功能将在未来逐步废弃 不推荐继续使用
# 替代模块: Modules.UI.*
# ================================================

class QuGridObject(object):
    """ 网格对象 """
    def __init__(self, uiNode, Path, IsScrollGrid=False, DelayUpdate=False):
        # type: (EasyScreenNodeCls, str, bool, bool) -> None
        self.uiNode = uiNode        # type: EasyScreenNodeCls
        self.Path = Path            # type: str
        self.IsScrollGrid = IsScrollGrid
        self.RenderChildList = [] # type: list
        """ 子控件渲染列表 """
        self.__FLoadE = True
        self.RenItemPanelName = ""   # 渲染项目的画布名
        self.DelayUpdate = DelayUpdate
        """ 是否启用延迟界面更新 """
        self.ViewRenderCount = {
        }       # 视图渲染次数
    
    def GridUpDate(self, CallBack=lambda *_:None, ChildPathList=None):
        """ 网格更新处理 """
        if self.DelayUpdate:
            self.uiNode.UpdateScreen(False)
        ChildPathList = ChildPathList if ChildPathList else self.uiNode.GetAllChildrenPath(self.Path)  # type: list[str]
        Key = "/"   # 路径关键字
        for ConPath in ChildPathList:
            ABSConPath = ConPath[len(self.Path):]
            if ABSConPath.count(Key) == 1:
                # 是渲染项目中的Parent
                if self.__FLoadE:
                    self.RenItemPanelName = ABSConPath[:-1]
                    self.__FLoadE = False
                try:
                    Pos = int(ABSConPath[len(self.RenItemPanelName):])-1
                except Exception as e:
                    print(e)
                    continue
                ViewPath = "{0}{1}{2}".format(self.Path, self.RenItemPanelName, Pos+1)
                self.ViewRenderCount[ViewPath] = self.ViewRenderCount.get(ViewPath, 0) + 1
                CallBack(ViewPath, Pos)
        if self.DelayUpdate:
            self.uiNode.UpdateScreen(True)

class EasyScreenNodeCls(BaseScreenNode):
    """ 简易界面类 可继承并开发 """
    UiName = "Ui_"+RandomUid()              # Ui名字 默认随机
    UiDef = None                            # 用来标识json ui的命名空间和界面名 如 zeroui.main
    ParamDict = {"isHud" : 1}               # 界面参数字典
    CreateParams = None                     # 堆栈管理的界面参数
    IsPushScreen = False                    # 是否为 PushScreen 界面
    RandomSc = "Sc"+RandomUid()
    UiInitListen = {}
    DeBugMode = 0                           # 调试模式

    @classmethod
    def CreatUIBindEntity(cls, entityId, bindOffset = (0, 0, 0), autoScale = True):
        """
            为特定实体创建UI并绑定, 如若成功则返回uiNode否则None
        """
        oldParm = cls.ParamDict
        cls.ParamDict = {
            "bindEntityId": entityId,
            "bindOffset": bindOffset,
            "autoScale": int(autoScale)
        }
        uiNode = None
        try:
            uiNode = cls()
        except:
            import traceback
            traceback.print_exc()
        finally:
            cls.ParamDict = oldParm
        return uiNode

    @classmethod
    def GetUi(cls, Ui=None):
        # type: (object|EasyScreenNodeCls) -> EasyScreenNodeCls | None
        """ 获取Ui 参数为UiName或继承EasyScreenNodeCls的子类 """
        if isinstance(Ui,str):
            return clientApi.GetUI(ModDirName, Ui)
        elif Ui == None:
            return cls.GetUi(cls)
        elif issubclass(Ui,EasyScreenNodeCls):
            return clientApi.GetUI(ModDirName, Ui.UiName)

    @classmethod
    def RemoveUi(cls):
        """ [静态] 删除Ui节点 """
        UiNode = cls.GetUi() # type: EasyScreenNodeCls
        if UiNode:
            UiNode.SetRemove()

    @staticmethod
    def GridRenderAdapter(ConPath, IsScrollGrid=False, DelayUpdate=False):
        """ 网格渲染适配器 支持列表网格 PS:注册的方法名不能和当前静态方法一致否则无效 """
        def __Do(Met):
            Key = "__OnGridRender__"
            if not hasattr(Met,Key):setattr(Met,Key,[])
            List = getattr(Met,Key) # type: list[tuple[str,str]]
            List.append((ConPath, IsScrollGrid, DelayUpdate))
            return Met
        return __Do

    @staticmethod
    def OnClick(ConPath,isSwallow=True):
        """ 
            [装饰器] 注册按钮点击回调 参数: Button控件路径, (选填) isSwallow=True # False为点击穿透
            回调参数: 无
        """
        def __OnClick(Met):
            OnClickKey = "__OnClick__"
            if not hasattr(Met,OnClickKey):setattr(Met,OnClickKey,[])
            List = getattr(Met,OnClickKey) # type: list[tuple[str,str]]
            List.append((ConPath,isSwallow,))
            return Met
        return __OnClick

    @staticmethod
    def OnTouch(ConPath,isSwallow=True):
        """ 
            [装饰器] 注册按钮Touch回调 参数: Button控件路径, (选填) isSwallow=True # False为点击穿透
            回调参数: Args:Dict 详细描述触碰信息
        """
        def __OnTouch(Met):
            OnTouchKey = "__OnTouch__"
            if not hasattr(Met,OnTouchKey):setattr(Met,OnTouchKey,[])
            List = getattr(Met,OnTouchKey) # type: list[tuple[str,str]]
            List.append((ConPath,isSwallow,))
            return Met
        return __OnTouch

    @staticmethod
    def Listen(__Event):
        """ 
            [装饰器] 注册UI界面的事件监听,并在UI销毁时自动结束监听
            参数: Event:str  回调参数:Args:dict|无
        """
        Event = __Event if isinstance(__Event, str) else __Event.__name__
        def __Listen(Met):
            ListenKey = "__ListenEvents__"
            if not hasattr(Met,ListenKey):setattr(Met,ListenKey,[])
            List = getattr(Met,ListenKey) # type: list[str]
            List.append(Event)
            return Met
        return __Listen

    @staticmethod
    def Binding(
            UiDef=None,
            ParamDict={"isHud" : 1},
            UiName= None, 
            CreateParams=None,
            IsPushScreen=False
        ):
        UiName = UiName if UiName else RandomUid()
        from Client import creatTemporaryContainer
        """ 
            [装饰器] 用于绑定界面类与UI.json文件的操作
            大多数情况下只要设置 UiDef="xxx.main"即可
            UiName不指定即为随机 ParamDict不指定则为 {"isHud" : 1}
            例: @EasyScreenNodeCls.Binding("test.main")
        """
        def NewCls(Cls):
            NowPath = Cls.__module__+"."+Cls.__name__
            Cls.UiName = UiName
            Cls.UiDef = UiDef
            Cls.ParamDict = ParamDict
            Cls.CreateParams = CreateParams
            Cls.IsPushScreen = IsPushScreen   
            def Register(Args={}):
                # 智能注册UI
                ScreenNodeClsPath = ModDirName+".QuModLibs.UI."+Cls.RandomSc
                clientApi.RegisterUI(ModDirName, Cls.UiName, ScreenNodeClsPath, Cls.UiDef)

            if NowPath in EasyScreenNodeCls.UiInitListen:
                Data = EasyScreenNodeCls.UiInitListen[NowPath]
                UnListenForEvent("UiInitFinished", Data[0], Data[1])
                print("[%s] 重载注册: %s"%(Cls.__name__,NowPath))
                Register()

            TC = creatTemporaryContainer()
            TC.Register = Register
            # System.ListenForEvent(EnSp,EnSy,"UiInitFinished", TC, Register)
            ListenForEvent("UiInitFinished", TC, Register)
            EasyScreenNodeCls.UiInitListen[NowPath] = (TC, Register)
            return Cls
        return NewCls

    class ScreenNodeCls(ScreenNode):
        def __init__(self, namespace, name, param):
            ScreenNode.__init__(self, namespace, name, param)
            self.QUGRIDRENDER = [] # type: list[tuple[str, str, QuGridObject]]

        def Create(self):
            pass

        def Destroy(self):
            pass

        def QuGetScrollGridObject(self, path):
            # type: (str) -> QuScrollGrid
            return QuScrollGrid(self, path)

        def QuSetButtonCallback(self, buttonCont, callBack):
            # type: (str, object) -> bool
            def creatFun(func):
                def newFun(*_):
                    return func()
                return newFun
            baseUIControl = self.GetBaseUIControl(buttonCont)
            baseUIControl.SetTouchEnable(True)
            buttonUIControl = baseUIControl.asButton()
            buttonUIControl.AddTouchEventParams({"isSwallow":True})
            buttonUIControl.SetButtonTouchUpCallback(creatFun(callBack))

        def QuSetControlABSPos(self, __conPath, __pos):
            # type: (str, tuple[float, float]) -> None
            x, y = __pos
            parentPath = __conPath[:__conPath.rfind("/")]
            px, py = self.QuGetControlABSPos(parentPath)
            self.GetBaseUIControl(__conPath).SetPosition((x - px, y - py))
            
        def QuSetSuperButton(self, buttonPath, clickCall = lambda *_: None, longPressDragTime = None, deviceVibrate = 20):
            # type: (str, object, float | int | None, int) -> None
            def creatFun(func):
                playerId = clientApi.GetLocalPlayerId()
                levelId = clientApi.GetLevelId()
                comp = clientApi.GetEngineCompFactory().CreateGame(levelId)
                disClick = [False]                                        # 禁止点击 (拖动期间)
                timer = [None]                                            # 系统定时器
                def startMove():
                    timer[0] = None
                    disClick[0] = True
                    # 震动触发
                    if deviceVibrate > 0:
                        comp = clientApi.GetEngineCompFactory().CreateDevice(playerId)
                        comp.SetDeviceVibrate(deviceVibrate)
                
                def newFun(args):
                    # type: (dict) -> None
                    touchEvent = args["TouchEvent"]
                    # 执行点击方法
                    if touchEvent == 0 and not disClick[0]:
                        if timer[0]:
                            comp.CancelTimer(timer[0])
                            timer[0] = None
                        return func()
                    if longPressDragTime == None:
                        # 不启用长按触摸
                        return

                    # 触摸移动
                    if touchEvent == 4 and disClick[0]:
                        newX = args["TouchPosX"]
                        newY = args["TouchPosY"]
                        con = self.GetBaseUIControl(buttonPath)
                        sx, sy = con.GetSize()
                        self.QuSetControlABSPos(buttonPath, (newX - sx / 2, newY - sy / 2))
                        
                    # TOUCH START 按压按钮开始计算
                    elif touchEvent == 1:
                        timer[0] = comp.AddTimer(longPressDragTime, startMove)
                        # 清空坐标记录
                        # lastTouchPos = None

                    # TOUCH END 释放时间计算
                    elif touchEvent in (0, 3):
                        if timer[0]:
                            comp.CancelTimer(timer[0])
                            timer[0] = None
                        disClick[0] = False
                return newFun
            baseUIControl = self.GetBaseUIControl(buttonPath)
            baseUIControl.SetTouchEnable(True)
            buttonUIControl = baseUIControl.asButton()
            buttonUIControl.AddTouchEventParams({"isSwallow":True})
            funcObject = creatFun(clickCall)
            buttonUIControl.SetButtonTouchDownCallback(funcObject)      # 按下按钮 (START)
            buttonUIControl.SetButtonTouchUpCallback(funcObject)        # 释放按钮 (内 CLICK/END)
            buttonUIControl.SetButtonTouchCancelCallback(funcObject)    # 释放按钮 (外 END)
            buttonUIControl.SetButtonScreenExitCallback(funcObject)     # 释放按钮 (END)
            buttonUIControl.SetButtonTouchMoveCallback(funcObject)      # MOVE

        def QuUpdateMeshRendering(self):
            RenderCall = self.QUGRIDRENDER
            for GridPath, MetName, GridObject in RenderCall:
                def Do(GridPath, ChilList=None):
                    GridObject.Path = GridPath
                    ChilList = GridObject.RenderChildList if not ChilList else ChilList
                    GridObject.GridUpDate(CallBack=getattr(self, MetName), ChildPathList=ChilList)
                if GridObject.IsScrollGrid:   # 是网格列表
                    scrollViewUIControl = self.GetBaseUIControl(GridPath).asScrollView()
                    Path = scrollViewUIControl.GetScrollViewContentPath()
                    CHIL = self.GetAllChildrenPath(Path)
                    Do(Path, CHIL)
                    continue
                Do(GridPath)
        
        def QuGetControlABSPos(self, Path):
            # type: (str) -> tuple[float,float]
            x, y = 0.0, 0.0
            while Path:
                xp, yp = self.GetBaseUIControl(Path).GetPosition()
                x+=xp; y+=yp
                Path = Path[:Path.rfind("/")]
            return (x, y)
        
        def QuGetGridRenderObj(self, GridPath="/"):
            # type: (str) -> None | QuGridObject
            for __GridPath, _, Obj in self.QUGRIDRENDER:
                if GridPath == __GridPath:
                    return Obj
            return None
        
        def QuGetGridViewRenderCount(self, GridViewPath="/"):
            ParentPath = GridViewPath[:GridViewPath.rfind("/")]
            Obj = self.QuGetGridRenderObj(ParentPath)
            if not Obj: return 0
            return Obj.ViewRenderCount.get(GridViewPath, 0)

        def QuGetControlABSPointPos(self, __Path):
            # type: (str) -> tuple[float,float]
            x, y = self.QuGetControlABSPos(__Path)
            con = self.GetBaseUIControl(__Path)
            sx, sy = con.GetSize()
            return (x - sx / 2, y - sy / 2)
        
        def QuSetControlABSPointPos(self, __conPath, __pos):
            # type: (str, tuple[float, float]) -> None
            x, y = __pos
            con = self.GetBaseUIControl(__conPath)
            sx, sy = con.GetSize()
            self.QuSetControlABSPos(__conPath, (x + sx / 2, y + sy / 2))
    
    def QuSetSuperButton(self, buttonPath, clickCall = lambda *_: None, longPressDragTime = None, deviceVibrate = 20):
        # type: (str, object, float | int | None, int) -> None
        """ 超级按键设置
        @buttonPath - 按钮路径
        @clickCall - 点击回调函数
        @longPressDragTime - 长按拖拽时间 (设置非None数值可实现长按拖动, 单位:秒)
        @deviceVibrate - 长按震动(毫秒)
        """
        pass

    def QuGetGridRenderObj(self, GridPath="/"):
        # type: (str) -> None | QuGridObject
        """ 获取网格渲染对象 """
        pass
    
    def QuGetScrollGridObject(self, path):
        # type: (str) -> QuScrollGrid
        """ 获取Qu网格管理对象 """
        pass

    def QuSetButtonCallback(self, buttonCont, callBack):
        # type: (str, object) -> bool
        """ 快捷设置按钮点击回调 """
        pass
    
    def QuGetGridViewRenderCount(self, GridViewPath="/"):
        # type: (str) -> int
        """ 获取网格视图渲染次数 可以用来判断是否为第一次渲染 """
        pass

    def QuUpdateMeshRendering(self):
        """ 更新当前界面的网格渲染 """
        pass

    def QuGetControlABSPos(self, __Path):
        # type: (str) -> tuple[float,float]
        """ 获取控件绝对位置信息 """
        pass

    def QuSetControlABSPos(self, __conPath, __pos):
        # type: (str, tuple[float, float]) -> None
        """ 设置控件绝对位置信息 """
        pass

    def QuGetControlABSPointPos(self, __Path):
        # type: (str) -> tuple[float,float]
        """ 获取控件绝对点坐标(中心位置) """
        pass

    def QuSetControlABSPointPos(self, __conPath, __pos):
        # type: (str, tuple[float, float]) -> None
        """ 设置控件绝对点坐标(中心位置) """
        pass

    @staticmethod
    def __CREAT__(uiNode,Data):
        # type: (EasyScreenNodeCls, dict) -> None
        # ======= 界面创建完毕后自动执行 ========
        uiNode.QUGRIDRENDER = []
        OnClick = Data["OnClick"] # type: dict
        OnTouch = Data["OnTouch"] # type: dict
        ListenEvents = Data["ListenEvents"] # type: list
        OnGridRender = Data["OnGridRender"] # type: dict
        # ===== Click处理 =====
        def creatFun(func):
            def newFun(*_):
                return func()
            return newFun
        for FunName, DataLis in OnClick.items():
            Func = getattr(uiNode,FunName) # 回调方法
            newFun = creatFun(Func)
            for ButtonPath, isSwallow in DataLis:
                baseUIControl = uiNode.GetBaseUIControl(ButtonPath)
                baseUIControl.SetTouchEnable(True)
                buttonUIControl = baseUIControl.asButton()
                buttonUIControl.AddTouchEventParams({"isSwallow":isSwallow})
                buttonUIControl.SetButtonTouchUpCallback(newFun)
        # ===== Touch处理 =====
        for FunName, DataLis in OnTouch.items():
            Func = getattr(uiNode,FunName) # 回调方法
            for ButtonPath, isSwallow in DataLis:
                baseUIControl = uiNode.GetBaseUIControl(ButtonPath)
                baseUIControl.SetTouchEnable(True)
                buttonUIControl = baseUIControl.asButton()
                buttonUIControl.AddTouchEventParams({"isSwallow":isSwallow})
                buttonUIControl.SetButtonTouchDownCallback(Func)
                buttonUIControl.SetButtonTouchUpCallback(Func)
                buttonUIControl.SetButtonTouchCancelCallback(Func)
                buttonUIControl.SetButtonTouchMoveCallback(Func)
                buttonUIControl.SetButtonTouchMoveInCallback(Func)
                buttonUIControl.SetButtonTouchMoveOutCallback(Func)
                buttonUIControl.SetButtonScreenExitCallback(Func)
        
        # ===== 监听事件处理 ======
        for EventName,FunName in ListenEvents:
            ListenForEvent(EventName,uiNode,getattr(uiNode,FunName))
            # System.ListenForEvent(EnSp,EnSy,EventName,uiNode,getattr(uiNode,FunName))
        
        # ===== GridRender处理 =====
        if len(OnGridRender):
            # 渲染回调信息列表
            RenderCall = []     # type: list[tuple[str, str, QuGridObject]]
            for FunName, DataLis in OnGridRender.items():
                for GridPath, IsScrollGrid, DelayUpdate in DataLis:
                    # GridPath 网格路径
                    RenderCall.append((GridPath, FunName, QuGridObject(uiNode, GridPath, IsScrollGrid, DelayUpdate)))
            uiNode.QUGRIDRENDER = RenderCall
            def __OnGridRender(uiNode):
                # type: (EasyScreenNodeCls) -> None
                """ 网格更新事件 """
                for GridPath, MetName, GridObject in RenderCall:
                    def Do(GridPath, ChilList=None):
                        GridObject.Path = GridPath
                        ChilList = ChilList if ChilList else uiNode.GetAllChildrenPath(GridPath)
                        if GridObject.RenderChildList != ChilList:
                            # UpDate 网格渲染更新
                            GridObject.RenderChildList = ChilList
                            GridObject.GridUpDate(CallBack=getattr(uiNode, MetName), ChildPathList=ChilList)
                    if GridObject.IsScrollGrid:   # 是网格列表
                        scrollViewUIControl = uiNode.GetBaseUIControl(GridPath).asScrollView()
                        Path = scrollViewUIControl.GetScrollViewContentPath()
                        CHIL = uiNode.GetAllChildrenPath(Path)
                        if CHIL:    # 有子节点 更新绘制
                            Do(Path, CHIL)
                        continue
                    Do(GridPath)
            RanDomName = "QuSystemGridComponentSizeChangedClientEvent"
            newFun = creatFun(lambda: __OnGridRender(uiNode))
            def QuSystemGridComponentSizeChangedClientEvent(args={}):
                return __OnGridRender(uiNode)
            EventName = "GridComponentSizeChangedClientEvent"
            setattr(uiNode, RanDomName, QuSystemGridComponentSizeChangedClientEvent)
            # System.ListenForEvent(EnSp, EnSy, EventName,uiNode, getattr(uiNode,RanDomName))
            from Client import _loaderSystem
            _loaderSystem.unsafeUpdate(
                ListenForEvent(EventName,uiNode,getattr(uiNode,RanDomName))
            )
            ListenEvents.append((EventName, RanDomName))

        # ==== 注册界面销毁监听 ====    
        def NewDestroy(Met):
            @wraps(Met)
            def __Destroy(*Args,**Kwargs):
                EasyScreenNodeCls.__DESTROY__(uiNode,Data)
                return Met(*Args,**Kwargs)
            return __Destroy
        uiNode.Destroy = NewDestroy(uiNode.Destroy)

    @staticmethod
    def __DESTROY__(uiNode,Data):
        # ======= 界面销毁后自动执行 ========
        ListenEvents = Data["ListenEvents"] # type: list
        for EventName,FunName in ListenEvents:
            # System.UnListenForEvent(EnSp,EnSy,EventName,uiNode,getattr(uiNode,FunName))
            UnListenForEvent(EventName,uiNode,getattr(uiNode,FunName))

    def __new__(cls, *Args, **Kwargs):
        if not cls.UiDef:
            print("[Error] (Class.%s) 你不能创建一个未绑定的界面 !!"%(cls.__name__))
            return None
        GetUi = cls.GetUi()
        if not GetUi:
            from copy import deepcopy
            import UI
            NewCls = deepcopy(cls.ScreenNodeCls)
            setattr(UI, cls.RandomSc, NewCls)
            # 创建UI界面
            if cls.IsPushScreen:
                uiNode = clientApi.PushScreen(ModDirName, cls.UiName, cls.CreateParams)
            else:
                uiNode = clientApi.CreateUI(ModDirName, cls.UiName, cls.ParamDict)
                if not uiNode:
                    ScreenNodeClsPath = ModDirName+".QuModLibs.UI."+cls.RandomSc
                    clientApi.RegisterUI(ModDirName, cls.UiName, ScreenNodeClsPath, cls.UiDef)
                    uiNode = clientApi.CreateUI(ModDirName, cls.UiName, cls.ParamDict)
            # ==== 添加后处理数据信息 ====
            PostProcessing = {
                "OnClick":{},
                "OnTouch":{},
                "OnGridRender": {},
                "ListenEvents":[],
            }
            OnClick = PostProcessing["OnClick"] # type: dict
            OnGridRender = PostProcessing["OnGridRender"] # type: dict
            OnTouch = PostProcessing["OnTouch"] # type: dict
            ListenEvents = PostProcessing["ListenEvents"] # type: list
            for FunName, Fun in (
                (x,y) for x,y in cls.__dict__.items()
                if not hasattr(EasyScreenNodeCls, x) or x in ['__init__','Create','OnActive','OnDeactive','Destroy']
            ):
                if not hasattr(Fun, "__call__"): continue
                setattr(uiNode, FunName,
                    MethodType(Fun, uiNode)
                ) # 动态添加方法到Ui实例对象
                
                if hasattr(Fun,'__OnClick__'):
                    __FunName = Fun.__name__
                    OnClick[__FunName] = getattr(Fun,'__OnClick__')
                    
                if hasattr(Fun,'__OnGridRender__'):
                    __FunName = Fun.__name__
                    OnGridRender[__FunName] = getattr(Fun,'__OnGridRender__')

                if hasattr(Fun,'__OnTouch__'):
                    __FunName = Fun.__name__
                    OnTouch[__FunName] = getattr(Fun,'__OnTouch__')
                        
                if hasattr(Fun,'__ListenEvents__'):
                    __FunName = Fun.__name__
                    Append = ListenEvents.append
                    for Event in getattr(Fun,'__ListenEvents__'):
                        Append((Event, __FunName))
            EasyScreenNodeCls.__CREAT__(uiNode, PostProcessing)
            # uiNode.__class__ = cls
            uiNode.__init__(*Args, **Kwargs)
            if hasattr(uiNode,"Creat"):
                uiNode.Creat()
            return uiNode
        return GetUi

    def __init__(self):
        self.QUGRIDRENDER = [] # type: list[tuple[str, str, QuGridObject]]
    
    def Destroy(self):
        pass

    def Create(self):
        pass

    def __AddTouchEventHandler(self, ConPath, Fun, Data):
        """ [已废弃] 设置按钮点击事件 Data一般写{"isSwallow":True} """
        pass

class QuScrollGrid(object):
    """ 滚动网格 """
    def __init__(self, uiNode, path):
        self.uiNode = uiNode # type: EasyScreenNodeCls
        self.path = path
    
    @ExceptionHandling(lambda: False)
    def redrawLayoutSize(self, baseX=1, baseY=2, count=2):
        # type: (int, int, int) -> bool
        """ 重绘布局大小
        
            baseX: 基准宽度大小 即宽度可填充数量
            baseY: 基准高度大小 以一整页高度为准的可填充数量
            count: 需要绘制的数量 (不代表真实绘制容量,基于网格特性一定会绘制: n*baseX*baseY 个, 多余内容需自行控制隐藏)
        """
        scrollView = self.uiNode.GetBaseUIControl(self.path)
        size1, size2 = scrollView.GetSize()
        viewPath = scrollView.asScrollView().GetScrollViewContentPath()
        grid = self.uiNode.GetBaseUIControl(viewPath)
        yCount = count // baseX + (1 if count % baseX else 0)
        itemH = size2 / baseY     # 每行分配的高度
        grid.asGrid().SetGridDimension((baseX, yCount))
        grid.SetSize((size1, itemH*yCount), True)

ESNC = EasyScreenNodeCls # EasyScreenNodeCls的缩写