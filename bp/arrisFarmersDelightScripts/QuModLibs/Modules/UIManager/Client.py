# -*- coding: utf-8 -*-
from ...Client import ListenForEvent, UnListenForEvent, Events, errorPrint
from ...UI import EasyScreenNodeCls

lambda: "By Zero123"

class UIData:
    """ UI参数 """
    def __init__(self, uiCls, args = tuple(), kwargs = {}):
        # type: (type[EasyScreenNodeCls], tuple[object], dict[str,object]) -> None
        self.uiCls = uiCls
        self.args = args
        self.kwargs = kwargs

class UIManager:
    _uiFinish = False
    def __init__(self):
        self._uiStack = []           # type: list[UIData]
        ListenForEvent(Events.UiInitFinished, self, self._UIINITFINISHED)

    def _UIINITFINISHED(self, _={}):
        """ UI初始化完毕事件 """
        UIManager._uiFinish = True
        for data in self._uiStack:
            try:
                self._creatUI(data)
            except Exception as e:
                errorPrint("UI构造时发生异常 cls: {} ({})".format(data.uiCls, e))

    def free(self):
        """ 释放资源 并销毁监听 """
        UnListenForEvent(Events.UiInitFinished, self, self._UIINITFINISHED)

    def getUIClsStackIndex(self, uiCls):
        # type: (type[EasyScreenNodeCls]) -> int
        """ 获取UI类堆栈索引 如果不存在则返回 -1 """
        _index = -1
        for i, data in enumerate(self._uiStack):
            if data.uiCls is uiCls:
                return i
        return _index
    
    def hasUI(self, uiCls):
        # type: (type[EasyScreenNodeCls]) -> bool
        """ 判断特定UI是否存在管理栈中 """
        return self.getUIClsStackIndex(uiCls) >= 0
    
    def _creatUI(self, data):
        # type: (UIData) -> None
        if not UIManager._uiFinish:
            return
        if not data.uiCls.GetUi():
            data.uiCls(*data.args, **data.kwargs)

    def creatUI(self, uiCls, *args, **kwargs):
        # type: (type[EasyScreenNodeCls], object, object) -> None
        """ 通过管理器创建UI 当切换游戏维度时UI将被自动的重新建立 """
        _index = self.getUIClsStackIndex(uiCls)
        if _index >= 0:
            # 存在UI管理 刷新参数
            data = self._uiStack[_index]
            data.args = args
            data.kwargs = kwargs
            self._creatUI(data)
            return
        # 不存在UI管理栈中 初始化处理
        data = UIData(uiCls, args, kwargs)
        self._uiStack.append(data)
        self._creatUI(data)
    
    def removeUI(self, uiCls):
        # type: (type[EasyScreenNodeCls]) -> bool
        """ 销毁UI 同时销毁管理器内的登记信息 """
        _index = self.getUIClsStackIndex(uiCls)
        if _index < 0:
            return False
        del self._uiStack[_index]
        uiCls.RemoveUi()
        return True
    
    def removeTopUI(self):
        """ 销毁顶部UI 如果存在 """
        size = len(self._uiStack)
        if size <= 0:
            return
        data = self._uiStack[size - 1]
        del self._uiStack[size - 1]
        data.uiCls.RemoveUi()

uiManager = UIManager()
""" 默认的UIManager实例 如有需要也可以另行创建 """
