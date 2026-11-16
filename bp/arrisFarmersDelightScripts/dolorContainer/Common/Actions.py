# -*- coding: utf-8 -*-
"""
动作（docs/ARCHITECTURE.md 第 3.7 节）：格子操作以外、客户端请服务端做的事（按钮、开关、循环、选择、文字……）。
纯逻辑，两端共用。

界面模型里用 @action(名字, 参数格式...) 把一个方法声明成动作，参数格式是 Common/Schema 的字段，按顺序对应方法的参数：

    @Menus.register("mymod:stonecutter")
    class Stonecutter(Menus.Menu):
        @Actions.action("select", Schema.Int(0, 255))
        def select(self, ctx, index):            # 只在服务端调用；ctx 见 Server/Session.ActionContext
            ctx.state["selected"] = index

        @select.predicting
        def select(self, view, index):           # 可预测：客户端先改显示的数据，应答为准
            view.data["selected"] = index

        @select.requiring
        def select(self, ctx, index):            # 动作自己的条件（距离、维度、状态）：返回假时拒绝
            return index < len(RECIPES)

服务端先由内核集中校验（会话、宿主仍有效、权限、限频、参数格式；不认识的动作、多出来的参数一律拒绝），条件成立才调用。
动作抛 Refused(错误码) 表示不做：格子与实例状态都不改。返回值（只能是简单值）随应答带回客户端。

请求：{"s": 会话, "id": 请求编号, "a": 动作名, "args": [参数...]}（参数是线上的写法，见各字段的 encode）。
应答与格子操作的一样（ack），成了时可以带 "r"（动作的返回值）。请求编号与格子操作共用一个序列。
"""
import re

from . import Schema
from .Schema import BadRequest

MAX_ARGS = 16

_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]*(\.[A-Za-z][A-Za-z0-9_]*)*$")   # 部件的动作带前缀：craft.select
_TABLE = "_dcActions"


class Refused(Exception):
    """动作不做（错误码随应答发给客户端）。"""

    def __init__(self, code="refused"):
        Exception.__init__(self, code)
        self.code = code


class Action(object):
    """
    一个动作：名字、参数格式、服务端的处理（handler(界面模型, ctx, *参数)），可选的预测（predict(界面模型, view, *参数)，
    在客户端改 view.data）与条件（condition(界面模型, ctx, *参数) -> 真假）。
    """

    def __init__(self, name, fields, handler, cost=1.0):
        if not _NAME.match(name or ""):
            raise ValueError("bad action name: %r" % (name,))
        if len(fields) > MAX_ARGS or not all(isinstance(field, Schema.Field) for field in fields):
            raise ValueError("action %s: parameters must be Schema fields (at most %d)" % (name, MAX_ARGS))
        if not cost > 0:
            raise ValueError("action %s: cost must be positive: %r" % (name, cost))
        self.name = name
        self.fields = tuple(fields)
        self.handler = handler
        self.cost = float(cost)   # 每条花几个限频令牌（Api.setRateLimit）
        self.predict = None
        self.condition = None

    def predicting(self, function):
        """装饰器：可预测（客户端先改显示的数据）。"""
        self.predict = function
        return self

    def requiring(self, function):
        """装饰器：动作自己的条件。"""
        self.condition = function
        return self

    def bound(self, name, owner):
        """同一个动作换成名字 name、绑到 owner 上（部件的动作：调用时 self 是部件，不是界面模型）。"""
        handler, predict, condition = self.handler, self.predict, self.condition
        result = Action(name, self.fields, lambda menu, ctx, *args: handler(owner, ctx, *args), self.cost)
        if predict is not None:
            result.predict = lambda menu, view, *args: predict(owner, view, *args)
        if condition is not None:
            result.condition = lambda menu, ctx, *args: condition(owner, ctx, *args)
        return result

    def parseArgs(self, args, structure):
        """线上的参数 -> 值的元组。多了参数、不是列表、格式不对时抛 BadRequest；少了的按字段的缺省值。"""
        if not isinstance(args, (list, tuple)) or len(args) > len(self.fields):
            raise BadRequest("bad_args")
        return tuple(field.parse(args[index] if index < len(args) else Schema.MISSING, structure)
                     for index, field in enumerate(self.fields))

    def encodeArgs(self, values, structure):
        return [field.encode(value, structure) for field, value in zip(self.fields, values)]


def action(name, *fields, **options):
    """装饰器：把界面模型的方法声明成动作。options 只有 cost：每条花几个限频令牌（缺省 1，重的动作写大一些）。"""
    cost = options.pop("cost", 1.0)
    if options:
        raise TypeError("action %s: unknown options %r" % (name, sorted(options)))

    def decorate(function):
        return Action(name, fields, function, cost)
    return decorate


def costOf(data, actions):
    """动作请求的花费：按动作名在动作表里找，认不出时 1（限频在解析之前问）。"""
    name = data.get("a") if isinstance(data, dict) else None
    found = actions.get(name) if Schema.isText(name) else None
    return found.cost if found is not None else 1.0


def table(menuClass):
    """界面模型类的动作表 {名字: 动作}：连同基类的，同名时子类的为准。按类算一次。"""
    cached = menuClass.__dict__.get(_TABLE)
    if cached is not None:
        return cached
    found = {}
    for klass in reversed(menuClass.__mro__):
        own = {}
        for value in vars(klass).values():
            if isinstance(value, Action):
                if value.name in own:
                    raise ValueError("%s declares action %r twice" % (klass.__name__, value.name))
                own[value.name] = value
        found.update(own)
    setattr(menuClass, _TABLE, found)
    return found


def parseCall(data, actions, structure):
    """校验动作请求，返回 (请求编号, 动作, 参数元组)。actions 是会话的界面模型的动作表。"""
    if not isinstance(data, dict):
        raise BadRequest("bad_request")
    requestId = Schema.integer(data.get("id"), 1, 1 << 62, "bad_id")
    name = data.get("a")
    found = actions.get(Schema.text(name)) if Schema.isText(name) else None
    if found is None:
        raise BadRequest("bad_action")
    return requestId, found, found.parseArgs(data.get("args", ()), structure)


def encodeCall(requestId, name, args):
    """动作请求的线上写法（args 已经是线上的写法）。"""
    return {"id": requestId, "a": name, "args": list(args)}
