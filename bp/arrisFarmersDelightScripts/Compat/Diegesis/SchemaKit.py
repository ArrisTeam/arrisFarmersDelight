# -*- coding: utf-8 -*-
"""SchemaKit - 四个站点的客户端表现登记时用的声明工具：前置包的 StationSchema / ControlSpec / SlotRules（客户端）

服务端的站点直接用前置包的 Api.Server（它带着这几个名字）；客户端的 Api.Client 上没有 Schema（也没有 ControlSpec），四个站点的
View.register 都经这里取它的 Shared/Schema 模块（接口上带着 Schema 时用接口的：离线测试的替身是这样）。经 Compat/OtherMods 取：
它导入出错时打一次日志、返回 None，站点照"拿不到"处理——不登记表现，这一步记 skipped（四个站点取的是同一个模块，日志只打一次）。
"""
from .. import OtherMods
from ...Client.Engine import clientApi

SCHEMA_MODULE = "arrisDiegesisScripts.Shared.Schema"   # 前置包的声明模块（StationSchema / ControlSpec / SlotRules）


def of(api):
    """站点登记用的声明工具；拿不到是 None。"""
    return getattr(api, "Schema", None) or OtherMods.find(clientApi.ImportModule, SCHEMA_MODULE)
