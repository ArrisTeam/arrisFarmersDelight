# -*- coding: utf-8 -*-

from component.baseComponent import BaseComponent

class QueryVariableComponentClient(BaseComponent):
    def Register(self, variableName, defalutValue):
        # type: (str, float) -> bool
        """
        注册实体计算节点
        """
        pass

    def UnRegister(self, variableName):
        # type: (str) -> bool
        """
        注销实体计算节点
        """
        pass

    def Set(self, variableName, value):
        # type: (str, float) -> bool
        """
        设置某一个实体计算节点的值
        """
        pass

    def Get(self, variableName):
        # type: (str) -> float
        """
        获取某一个实体计算节点的值，如果不存在返回注册时的默认值
        """
        pass

    def GetMolangValue(self, molangName):
        # type: (str) -> Union[float,long]
        """
        获取实体molang变量的值
        """
        pass

    def GetStringHash64(self, key):
        # type: (str) -> long
        """
        返回字符串变量的hash64
        """
        pass


