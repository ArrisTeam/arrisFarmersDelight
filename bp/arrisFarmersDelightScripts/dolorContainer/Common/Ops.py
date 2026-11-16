# -*- coding: utf-8 -*-
"""
操作（docs/ARCHITECTURE.md 第 3.5 节）：登记表与请求的线上格式。纯逻辑，两端共用。

一个操作是一个按名字登记的 Op 子类：参数格式（params，Common/Schema）、涉及的格子（客户端为它们声明指纹，服务端核对）、
在工作副本上怎么执行（apply），以及客户端表现（丢东西、物品飞行、锁定提示）。操作在代码里写成元组 (名字, 参数...)，
参数按 params 的顺序；线上写成字典 {"t": 名字, 键: 值, ...}。库自带的原版操作在 Std/Operations.py（启动时由
Std/Defaults.py 登记）；使用方登记的操作名带命名空间（"mymod:fill"），不会与库的撞名。

请求：{"id": 请求编号, "op": 操作, "exp": [[集合编号, 下标, 指纹], ...], "p": "classic"|"pocket"}
exp 声明客户端看到的相关格子内容（Items.fingerprint），服务端对不上就整条拒绝。
客户端发来的东西一律不信：类型、范围、条数都在这里与参数格式里查。
"""
import re

from . import Schema
from .Collections import PROFILES
from .Schema import MAX_COLLECTIONS, MAX_CONTAINER_INDEX, BadRequest  # noqa: F401  旧的引用处经 Ops 用

MAX_EXPECTS = 8
MAX_FINGERPRINT = 256

_NAME = re.compile(r"^([a-z0-9_]+:)?[A-Za-z][A-Za-z0-9_]*$")
_ops = {}


class Op(object):
    """
    操作的基类。子类写 params（((线上的键, Schema 格式), ...)，顺序就是元组里参数的顺序）与 apply；按需改写其余几个。
    客户端表现的几个方法只在客户端调用：device 是输入方式（Common/Slots 的 MOUSE / TOUCH / GAMEPAD），
    cursorBefore 是执行前手上的东西。
    """

    name = None
    params = ()
    drops = False   # 会把东西丢进世界：玩家不能丢东西时（访客、世界禁止丢弃）客户端不发，照原版什么都不做
    cost = 1.0      # 每条花几个限频令牌（Api.setRateLimit）：重的操作写大一些

    def check(self, op, structure):
        """参数格式之外的校验（例如格子要是算出的），不成立时抛 BadRequest。"""

    def involved(self, op):
        """操作直接点到的格子。"""
        return []

    def apply(self, ws, op, profile):
        """在工作副本上执行，返回做成了没有。参数本身不成立时抛 Rules.RuleError。"""
        raise NotImplementedError

    def flies(self, op, device, cursorBefore):
        """原版里这个操作有没有物品飞行（按格子前后的变化配对，见 Client/Flights）。"""
        return False

    def flights(self, op, changes, key, device):
        """
        这个操作的物品飞行（客户端，做成之后）：[(物品堆, 来源容器格, 目标容器格, 目标格是不是从空变有)]；缺省 None：照 flies
        按格子前后的变化配对。东西进出收纳袋这类配对看不出来的，改写它直接给。changes 是 {容器格: (之前, 之后)}，key(格) 是
        格子落在的容器格。
        """
        return None

    def flyFrom(self, op):
        """
        飞行时凭空多出来的东西（交易做出来、放进背包的产物）从哪一格飞出来：内容是算出来或来自界面数据的格子；
        None 为不飞（多出来的东西没有起点）。
        """
        return None

    def lockNotice(self, op):
        """手上锁定的东西因锁定没做成时，上方提示的文案键（没有提示为 None）。"""
        return None


def register(name):
    """登记操作类（两端都要执行到）。重新载入时同名的新类替换旧的。"""
    def decorate(cls):
        if not _NAME.match(name):
            raise ValueError("bad op name: %r" % (name,))
        cls.name = name
        _ops[name] = cls()
        return cls
    return decorate


def get(name):
    return _ops.get(name)


def _parseOp(data, structure):
    if not isinstance(data, dict):
        raise BadRequest("bad_op")
    kind = data.get("t")
    op = _ops.get(kind) if Schema.isText(kind) else None
    if op is None:
        raise BadRequest("bad_op")
    values = (op.name,) + tuple(field.parse(data.get(key, Schema.MISSING), structure) for key, field in op.params)
    op.check(values, structure)
    return values


def parseRequest(data, structure):
    """校验请求，返回 (请求编号, 操作元组, 指纹表 {格: 指纹}, 界面档)。格子按界面模型的结构 structure 校验。"""
    if not isinstance(data, dict):
        raise BadRequest("bad_request")
    requestId = Schema.integer(data.get("id"), 1, 1 << 62, "bad_id")
    profile = data.get("p")
    if profile not in PROFILES:
        raise BadRequest("bad_profile")
    expects = data.get("exp") or []
    if not isinstance(expects, (list, tuple)) or len(expects) > MAX_EXPECTS:
        raise BadRequest("bad_expect")
    table = {}
    for entry in expects:
        if not isinstance(entry, (list, tuple)) or len(entry) != 3:
            raise BadRequest("bad_expect")
        fingerprint = entry[2]
        if not Schema.isText(fingerprint) or len(fingerprint) > MAX_FINGERPRINT:
            raise BadRequest("bad_expect")
        table[Schema.ref(entry[:2], structure)] = Schema.text(fingerprint)
    return requestId, _parseOp(data.get("op"), structure), table, Schema.text(profile)


def _op(op):
    found = _ops.get(op[0])
    if found is None:
        raise BadRequest("bad_op")
    return found


def apply(workspace, op, profile):
    """按操作元组执行对应的操作，返回做成了没有。"""
    return _op(op).apply(workspace, op, profile)


def involvedRefs(op):
    """操作直接点到的格子：客户端为它们声明指纹，服务端核对。"""
    return _op(op).involved(op)


def wireRef(ref, structure):
    """(集合名, 下标) -> [集合编号, 下标]。"""
    return Schema.wireRef(ref, structure)


def encodeOp(op, structure):
    """操作元组 -> 线上字典（客户端发请求用，与解析互逆）。"""
    found = _op(op)
    data = {"t": found.name}
    for (key, field), value in zip(found.params, op[1:]):
        data[key] = field.encode(value, structure)
    return data


def costOf(data):
    """请求里操作的花费（Op.cost）：按操作名找，认不出时 1（限频在解析之前问，畸形的请求也照 1 算）。"""
    op = data.get("op") if isinstance(data, dict) else None
    name = op.get("t") if isinstance(op, dict) else None
    kind = _ops.get(name) if Schema.isText(name) else None
    return float(kind.cost) if kind is not None else 1.0


def checkExpects(op, expects):
    """一条请求最多声明 MAX_EXPECTS 个格子：自定义操作的 involved 给多了时当场报错（不发请求），说清是哪个操作。"""
    if len(expects) > MAX_EXPECTS:
        raise ValueError("operation %r involves %d slots; a request may declare at most %d (Ops.MAX_EXPECTS): "
                         "declare fewer in involved()" % (op[0], len(expects), MAX_EXPECTS))


def encodeRequest(requestId, op, expects, profile, structure):
    """请求的线上写法：expects 是 [(格, 指纹), ...]，最多 MAX_EXPECTS 个（checkExpects）。"""
    checkExpects(op, expects)
    return {"id": requestId, "op": encodeOp(op, structure), "p": profile,
            "exp": [wireRef(ref, structure) + [fingerprint] for ref, fingerprint in expects]}
