# -*- coding: utf-8 -*-
from ui.NativeScreenManager import NativeScreenManager
from ui.screenNode import ScreenNode
from component.engineCompFactoryClient import EngineCompFactoryClient
from ui.viewRequest import ViewRequest
from ui.CustomUIControlProxy import CustomUIControlProxy
from ui.viewBinder import ViewBinder

def RegisterComponent(nameSpace, name, clsPath):
    # type: (str, str, str) -> bool
    """
    用于将组件注册到引擎中
    """
    pass

def RegisterSystem(nameSpace, systemName, clsPath):
    # type: (str, str, str) -> object
    """
    用于将系统注册到引擎中，引擎会创建一个该系统的实例，并在退出游戏时回收。系统可以执行我们引擎赋予的基本逻辑，例如监听事件、执行Tick函数、与服务端进行通讯等。
    """
    pass

def GetSystem(nameSpace, systemName):
    # type: (str, str) -> object
    """
    用于获取其他系统实例
    """
    pass

def CreateComponent(entityId, nameSpace, name):
    # type: (object, str, str) -> object
    """
    给实体创建客户端组件
    """
    pass

def GetComponent(entityId, nameSpace, name):
    # type: (str, str, str) -> object
    """
    获取实体的客户端组件。一般用来判断某个组件是否创建过，其他情况请使用CreateComponent
    """
    pass

def DestroyComponent(entityId, nameSpace, name):
    # type: (str, str, str) -> None
    """
    删除实体的客户端组件
    """
    pass

def GetEngineCompFactory():
    # type: () -> EngineCompFactoryClient
    """
    获取引擎组件的工厂，通过工厂可以创建客户端的引擎组件
    """
    pass

def RegisterUI(nameSpace, uiKey, clsPath, uiScreenDef=None):
    # type: (str, str, str, str) -> bool
    """
    注册UI，创建UI前，需要先注册UI。同一UI只需要注册一次即可。详见界面创建流程及生命周期
    """
    pass

def CreateUI(nameSpace, uiKey=None, createParams=None):
    # type: (str, str, dict) -> ScreenNode
    """
    创建UI，详见界面创建流程及生命周期
    """
    pass

def GetUI(nameSpace, uiKey=None):
    # type: (str, str) -> ScreenNode
    """
    获取UI节点，详见界面创建流程及生命周期
    """
    pass

def CheckCanBindUI(entityId):
    # type: (str) -> bool
    """
    检查实体是否可以绑定头顶UI，如何将UI与实体绑定详见CreateUI接口
    """
    pass

def HideHudGUI(isHide):
    # type: (bool) -> None
    """
    隐藏HUD游戏界面的游戏原生UI。与原版F1按钮效果一致，只隐藏显示，但点击跳跃键等位置依然会响应
    """
    pass

def HideWalkGui(isHide):
    # type: (bool) -> None
    """
    隐藏游戏中右上角的移动类型按钮。隐藏后点击相应位置不会响应
    """
    pass

def HideJumpGui(isHide):
    # type: (bool) -> None
    """
    隐藏游戏中右下角的跳跃按钮。隐藏后点击相应位置不会响应
    """
    pass

def HideSlotBarGui(isHide):
    # type: (bool) -> None
    """
    隐藏游戏中底部中间的物品栏界面
    """
    pass

def HideSneakGui(isHide):
    # type: (bool) -> None
    """
    隐藏游戏中左下角方向键的中心处潜行按钮。隐藏后点击相应位置不会响应
    """
    pass

def HideNeteaseStoreGui(isHide):
    # type: (bool) -> None
    """
    隐藏游戏中的网易商店按钮。隐藏后点击相应位置不会响应
    """
    pass

def OpenNeteaseStoreGui(categoryName, itemName):
    # type: (str, str) -> None
    """
    打开游戏中的网易商店购买商品界面
    """
    pass

def HideSwimGui(isHide):
    # type: (bool) -> None
    """
    隐藏游戏中的浮潜按钮。隐藏后点击相应位置不会响应
    """
    pass

def HideChangePersonGui(isHide):
    # type: (bool) -> None
    """
    隐藏切换人称的按钮。隐藏后点击相应位置不会响应
    """
    pass

def HideNameTag(isHide):
    # type: (bool) -> None
    """
    隐藏场景内所有名字显示，包括玩家名字，生物的自定义名称，物品展示框与命令方块的悬浮文本等
    """
    pass

def HideInteractGui(isHide):
    # type: (bool) -> None
    """
    隐藏交互按钮。隐藏后点击相应位置不会响应
    """
    pass

def HideHealthGui(isHide):
    # type: (bool) -> bool
    """
    隐藏hud界面的血量显示
    """
    pass

def HideHorseHealthGui(isHide):
    # type: (bool) -> bool
    """
    隐藏hud界面的坐骑的血量显示
    """
    pass

def HideHungerGui(isHide):
    # type: (bool) -> bool
    """
    隐藏hud界面的饥饿值显示
    """
    pass

def HideArmorGui(isHide):
    # type: (bool) -> bool
    """
    隐藏hud界面的护甲值显示
    """
    pass

def SetResponse(response):
    # type: (bool) -> None
    """
    设置原生UI是否响应
    """
    pass

def GetMinecraftEnum():
    """
    用于获取枚举值文档中的枚举值
    """
    pass

def GetClientSystemCls():
    # type: () -> object
    """
    用于获取客户端system基类。实现新的system时，需要继承该接口返回的类
    """
    pass

def GetComponentCls():
    # type: () -> object
    """
    用于获取客户端component基类。实现新的component时，需要继承该接口返回的类
    """
    pass

def GetEngineNamespace():
    # type: () -> str
    """
    获取引擎事件的命名空间。监听引擎事件时，namespace传该接口返回的namespace
    """
    pass

def GetEngineSystemName():
    # type: () -> str
    """
    获取引擎系统名。监听引擎事件时，systemName传该接口返回的systemName
    """
    pass

def GetLevelId():
    # type: () -> str
    """
    获取levelId。某些组件需要levelId创建，可以用此接口获取levelId。其中level即为当前地图的游戏。
    """
    pass

def GetLocalPlayerId():
    # type: () -> str
    """
    获取本地玩家的id
    """
    pass

def GetScreenNodeCls():
    # type: () -> object
    """
    获得ScreenNode类
    """
    pass

def GetViewBinderCls():
    # type: () -> ViewBinder
    """
    获得ViewBinder类
    """
    pass

def GetViewViewRequestCls():
    # type: () -> ViewRequest
    """
    获得ViewRequest类
    """
    pass

def GetNativeScreenManagerCls():
    # type: () -> NativeScreenManager
    """
    获得NativeScreenManager类
    """
    pass

def GetCustomUIControlProxyCls():
    # type: () -> CustomUIControlProxy
    """
    获得原生界面自定义UI代理基类
    """
    pass

def GetMiniMapScreenNodeCls():
    # type: () -> object
    """
    获取小地图ScreenNode基类
    """
    pass

def GetDirFromRot(rot):
    # type: (tuple[float,float]) -> tuple[float,float,float]
    """
    通过旋转角度获取朝向
    """
    pass

def GetTouchPos():
    # type: () -> tuple[float,float]
    """
    获取点击的屏幕坐标。可以监听TapBeforeClientEvent或TapOrHoldReleaseClientEvent事件，调用本API获取点击坐标。
    """
    pass

def GetNavPath(pos, maxTrimNode=16, maxIteration=800, isSwimmer=False):
    # type: (tuple[float,float,float], int, int, bool) -> list[tuple[float,float,float]]
    """
    获取本地玩家到目标点的寻路路径，开发者可以通过该接口定制自定义的导航系统。
    """
    pass

def StartNavTo(pos, sfxPath, callback=None, sfxIntl=2, sfxMaxNum=16, sfxScale=(0.5, 0.5), maxIteration=800, isSwimmer=False, fps=20, playIntl=8, duration=60, oneTurnDuration=90, sfxDepthTest=False):
    # type: (tuple[float,float,float], str, function, float, int, tuple[float,float], int, bool, int, int, int, int, bool) -> int
    """
    我们提供了一个基于GetNavPath的导航系统实现，做法是在路径上生成序列帧以引导玩家通向目标点，并且当玩家偏离路径会重新进行导航。
    """
    pass

def StopNav():
    # type: () -> None
    """
    终止当前的导航
    """
    pass

def GetIP():
    # type: () -> str
    """
    获取本地玩家的ip地址
    """
    pass

def StartProfile():
    # type: () -> bool
    """
    开始启动客户端脚本性能分析，启动后调用StopProfile即可在路径fileName生成函数性能火焰图，此接口只支持PC端。生成的火焰图可以用浏览器打开，推荐chrome浏览器。
    """
    pass

def StopProfile(fileName=None):
    # type: (str) -> bool
    """
    停止客户端脚本性能分析并生成火焰图，与StartProfile配合使用，此接口只支持PC端
    """
    pass

def StartMemProfile():
    # type: () -> bool
    """
    开始启动客户端脚本内存分析，启动后调用StopMemProfile即可在路径fileName生成函数内存火焰图，此接口只支持PC端。生成的火焰图可以用浏览器打开，推荐chrome浏览器。
    """
    pass

def StopMemProfile(fileName=None):
    # type: (str) -> bool
    """
    停止客户端脚本内存分析并生成火焰图，与StartMemProfile配合使用，此接口只支持PC端
    """
    pass

def StartMultiProfile():
    # type: () -> bool
    """
    开始启动服务端与客户端双端脚本性能分析，启动后调用StopMultiProfile即可在路径fileName生成函数性能火焰图。双端采集时数据误差较大，建议优先使用StartProfile单端版本，此接口只支持PC端
    """
    pass

def StopMultiProfile(fileName=None):
    # type: (str) -> bool
    """
    停止双端脚本性能分析并生成火焰图，与StartMultiProfile配合使用，此接口只支持PC端
    """
    pass

def HideAirSupplyGUI(isHide):
    # type: (bool) -> bool
    """
    隐藏玩家氧气值界面
    """
    pass

def HideExpGui(isHide):
    # type: (bool) -> None
    """
    非创造者模式下隐藏经验条显示
    """
    pass

def HideMoveGui(isHide):
    # type: (bool) -> None
    """
    隐藏游戏中左下角的移动按钮。隐藏后点击相应位置不会响应
    """
    pass

def SetCrossHair(visible):
    # type: (bool) -> None
    """
    设置是否使用“准星瞄准”，即设置->触摸屏->准星瞄准
    """
    pass

def SetHudChatStackVisible(visible):
    # type: (bool) -> None
    """
    设置HUD界面左上小聊天窗口可见性
    """
    pass

def SetHudChatStackPosition(pos):
    # type: (tuple[float,float]) -> None
    """
    设置HUD界面左上小聊天窗口位置
    """
    pass

def ReloadAllMaterials():
    # type: () -> bool
    """
    重新加载所有材质文件
    """
    pass

def ReloadAllShaders():
    # type: () -> bool
    """
    重新加载所有Shader文件
    """
    pass

def ReloadOneShader(shaderName):
    # type: (str) -> bool
    """
    重新加载某个Shader文件
    """
    pass

def SetKeepResourceWhenTransfer(keep=True):
    # type: (bool) -> bool
    """
    设置快速切服
    """
    pass

def SetEnableReconnectNetgame(keep=True):
    # type: (bool) -> bool
    """
    设置是否允许断线重连
    """
    pass

def GetKeepResourceWhenTransfer():
    # type: () -> bool
    """
    获取快速切服设置
    """
    pass

def SetResourceFastload(fastload=True):
    # type: (bool) -> bool
    """
    设置资源快速加载
    """
    pass

def GetResourceFastload():
    # type: () -> bool
    """
    获取资源快速加载设置
    """
    pass

def GetEnableReconnectNetgame():
    # type: () -> bool
    """
    获取是否允许断线重连
    """
    pass

def GetModConfigJson():
    # type: () -> dict
    """
    以字典形式返回指定路径的json格式配置文件的内容，文件必须放置在资源包的/modconfigs目录下
    """
    pass

def PushScreen(namespace, uiname, createParams=None):
    # type: (str, str, dict) -> ScreenNode
    """
    使用堆栈管理的方式创建UI
    """
    pass

def PopScreen():
    # type: () -> bool
    """
    使用堆栈管理的方式关闭UI
    """
    pass

def GetTopScreen():
    # type: () -> ScreenNode
    """
    获取UI堆栈栈顶的UI节点
    """
    pass

def GetPlatform():
    # type: () -> int
    """
    获取脚本运行的平台
    """
    pass

def OpenChatGui():
    # type: () -> None
    """
    打开原版聊天栏
    """
    pass

def StartCoroutine(iterOrFunc, callback=None):
    """
    开启客户端协程，实现函数分段式执行，可用于缓解复杂逻辑计算导致游戏卡顿问题
    """
    pass

def StopCoroutine(iter):
    """
    停止客户端协程
    """
    pass

def OpenInventoryGui(categoryName=''):
    # type: (str) -> None
    """
    打开原版背包界面，并支持选中某个分页(支持自定义分页名称)
    """
    pass

def GetBookManager():
    """
    获取书本管理对象
    """
    pass

