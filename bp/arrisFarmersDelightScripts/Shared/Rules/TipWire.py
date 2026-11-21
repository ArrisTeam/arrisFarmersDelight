# -*- coding: utf-8 -*-
"""TipWire - 服务端提示发给客户端的写法：哪一句、填什么（双端，纯规则）

服务端 Server/Helpers/Engine.ShowTip 用 message 把 Shared/Data/Tips 里的一句和要填的值打成载荷，Call(那个玩家, ENDPOINT, 载荷) 只发给他；
客户端 Client/Endpoints.OnTip 用 read 拆开，按自己的语言查出这一句和值里的词（Client/Texts），填好再弹。
载荷：{"key": 键, "text": 中文, "values": [值, ...]}，每个值是 {"v": 数或字}，或者一个词 {"key": 键, "text": 中文}。
网易 Call 载荷的规矩（Shared/Rules/TableWire 的说明里那一组）：列表里元素的类型要一样、不能有 unicode、元组到对端变列表——所以值一个个包成字典、字都换成 str。
中文跟着句子一起发：语言文件里没有这一句时客户端照样有字可显示、不露键名，两端也不用各留一张表对着。
"""
from .TableWire import toStr

ENDPOINT = "OnTip"      # 客户端端点的名字（Client/Endpoints.OnTip；tests/test_architecture 核对客户端有这个同名端点）


def message(tip, values=()):
    """服务端：一句提示 (键, 中文) 和要填的值 -> 载荷。值是数、字，或者一个词 (键, 中文)。"""
    key, text = tip
    return {"key": toStr(key), "text": toStr(text), "values": [_value(value) for value in values]}


def _value(value):
    if isinstance(value, tuple):
        return {"key": toStr(value[0]), "text": toStr(value[1])}
    return {"v": toStr(value)}


def read(payload):
    """客户端：载荷 -> (键, 中文, 值的元组)，值里的词换回 (键, 中文)。py2 收到的字可能是 unicode：都换回 utf-8 的 str，
    和 Texts 查到的字、引擎给的物品名一个类型，拼在一起不出错。"""
    values = []
    for value in payload.get("values") or ():
        if "key" in value:
            values.append((toStr(value["key"]), toStr(value.get("text")) or ""))
        else:
            values.append(toStr(value.get("v")))
    return toStr(payload.get("key")) or "", toStr(payload.get("text")) or "", tuple(values)
