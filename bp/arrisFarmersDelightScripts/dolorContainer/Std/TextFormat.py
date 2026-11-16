# -*- coding: utf-8 -*-
"""
文字控件的格式串（布局里文字控件上的 $dc_format，见 Std/Components.py；运行时控件 text 见 Std/Client/Widgets.py）：
{名字} 或 {名字:格式}，格式照 Python 的写法（{arrow:.0%} 写成百分数、{count:>3} 右对齐三格）；名字是界面数据、每位查看者的
状态或客户端界面状态的名字（部件的名字带前缀，可以有点），要写字面的花括号就写两个（{{、}}）。
值是物品（Data.Item）的只能写 {名字:name}：物品的名字（客户端按玩家的语言给，空着时什么都不写）。
值是可本地化的文字（Data.Lang）的照常写 {名字}：客户端按玩家的语言拼好再写。
两端共用、不导入引擎：编译工具用它核对名字，客户端用它写字。
"""
import string

from ..Common import Data

ITEM_NAME = "name"   # 物品在格式串里的写法：{名字:name}


class FormatError(ValueError):
    """格式串写错了（说明是给写布局的人看的）。"""


def parse(pattern):
    """格式串 -> [(字面, 名字或 None, 格式)]。写错时抛 FormatError。"""
    try:
        pieces = list(string.Formatter().parse(pattern))
    except ValueError as error:
        raise FormatError("格式串 %r 写错了（%s）" % (pattern, error))
    out = []
    for literal, name, spec, conversion in pieces:
        if name is not None:
            if not name or name.isdigit() or "[" in name:
                raise FormatError("格式串 %r 里的 {%s} 要写界面数据或状态的名字" % (pattern, name))
            if conversion:
                raise FormatError("格式串 %r 里的 {%s!%s} 不支持转换" % (pattern, name, conversion))
            if "{" in (spec or ""):
                raise FormatError("格式串 %r 里 {%s} 的格式不能再套 {}" % (pattern, name))
        out.append((literal, name, spec or ""))
    return out


def names(pattern):
    """格式串里用到的名字（按出现的先后，不重复）。写错时抛 FormatError。"""
    out = []
    for _, name, _ in parse(pattern):
        if name is not None and name not in out:
            out.append(name)
    return out


def itemNames(pattern):
    """格式串里按物品的名字写的那些名字（{名字:name}）。写错时抛 FormatError。"""
    out = []
    for _, name, spec in parse(pattern):
        if name is not None and spec == ITEM_NAME and name not in out:
            out.append(name)
    return out


def render(pieces, values, convert=str, itemName=None, text=None):
    """
    按 parse 的结果写字：values 是 {名字: 值}；某一项的格式不合它的值（值还没收到、类型不对）时这一项写成空，
    不让整行出错。convert 把每一段转成同一种字符串（py2 的引擎文本接口只收 str）。itemName(物品) 给物品的名字
    （客户端按语言给）：值是物品（物品字典）时只认 {名字:name}，空物品与别的格式写成空。text(键) 查语言文件：值是可本地化的
    文字（Data.LangText）时按它拼好再按格式写（没给 text 时写成空）。
    """
    out = []
    for literal, name, spec in pieces:
        if literal:
            out.append(convert(literal))
        if name is not None:
            value = values.get(name)
            if isinstance(value, Data.LangText):
                if text is not None:
                    try:
                        out.append(convert(format(value.render(text), spec)))
                    except (ValueError, TypeError):
                        pass
                continue
            if isinstance(value, dict):
                if spec == ITEM_NAME and itemName is not None and value.get("newItemName"):
                    out.append(convert(itemName(value)))
                continue
            try:
                out.append(convert(format(value, spec)))
            except (ValueError, TypeError):
                pass
    return "".join(out)
