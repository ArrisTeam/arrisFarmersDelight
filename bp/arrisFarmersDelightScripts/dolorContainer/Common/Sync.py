# -*- coding: utf-8 -*-
"""
同步方式（docs/ARCHITECTURE.md 第 3.9 节）：一个容器的格子内容怎么从服务端到客户端。纯逻辑，两端共用。

每个容器在界面模型里声明用哪种（Structure.container 的 sync，缺省整份）。会话为每个容器建一份同步方式（服务端那一半），
镜像也建一份（客户端那一半）；消息里每个容器的内容是这一种同步方式的载荷：
    {"sync": {容器编号: 载荷}}
载荷的写法由同步方式定。会话与镜像只调用这里的方法，不认识具体的同步方式。
客户端还可以为某个容器发拉取（req {"s": 会话, "c": 容器编号, "q": 查询}），查询的写法同样由同步方式定、由它校验。

这里有接口与缺省的整份同步；按窗口拉取（上万格的不设上限的容器）在标准库 Std/Windowed。
"""
from . import Items

_strategies = {}


def register(cls):
    """登记同步方式（两端都要执行到），返回它的名字。"""
    _strategies[cls.name] = cls
    return cls.name


def get(name):
    return _strategies.get(name)


def create(spec):
    """为容器 spec 建一份同步方式（每个会话、每个镜像各一份）。"""
    return _strategies[spec.sync](spec)


def _entries(values):
    return [[index, stack] for index, stack in sorted(values.items())]


class SyncStrategy(object):
    """
    同步方式的基类。name：登记用的名字；unbounded：能不能用在不设上限的容器上。
    服务端的一半收会话的容器对象（Server/Containers.Container），客户端的一半收镜像里这个容器的格子表 {下标: 物品堆}。
    """

    name = None
    unbounded = False

    def __init__(self, spec):
        self.spec = spec

    # ---------------------------------------------------------------- 服务端

    def opened(self, container):
        """开屏：返回 (载荷, 发出去的格子 {下标: 物品堆，空格为 None})。"""
        raise NotImplementedError

    def changed(self, container, values):
        """格子变了（values 是 {下标: 物品堆}）：返回载荷。"""
        raise NotImplementedError

    def requested(self, container, query):
        """客户端的拉取：返回 (载荷, 发出去的格子)；不支持或查询不合格时抛 Schema.BadRequest。"""
        from .Schema import BadRequest   # Schema 要用 Collections，而 Collections 导入本模块：在这里取，免得循环导入
        raise BadRequest("bad_request")

    # ---------------------------------------------------------------- 客户端

    def apply(self, slots, payload):
        """把载荷写进格子表。"""
        raise NotImplementedError

    def highestUsed(self, slots):
        """这个容器最后一个非空格的下标（空为 -1）。"""
        raise NotImplementedError

    def findKind(self, slots, stack):
        """格子表里放着 stack 那种东西的下标，没有为 None（Rules.SlotState.findKind 的客户端一半；缺省逐格找）。"""
        for index, item in slots.items():
            if Items.sameKind(item, stack):
                return index
        return None

    def freeIndex(self, slots):
        """格子表里最前面的空格（没有空格时是末尾之后；Rules.SlotState.freeIndex 的客户端一半；缺省逐格找）。"""
        index = 0
        while not Items.isEmpty(slots.get(index)):
            index += 1
        return index

    def wants(self, start, end, now):
        """界面要显示 [start, end) 这一段：还要向服务端拉的话返回查询，否则 None。"""
        return None


class Full(SyncStrategy):
    """整份：开屏全发，之后发改动。载荷是 [[下标, 物品堆], ...]（物品堆为 None 表示空了）。"""

    name = "full"

    def opened(self, container):
        size = self.spec.size
        shown = dict(container.items(0, size))
        return _entries(shown), dict((index, shown.get(index)) for index in range(size))

    def changed(self, container, values):
        return _entries(values)

    def apply(self, slots, payload):
        for index, stack in payload or ():
            stack = Items.normalize(stack)
            if stack is None:
                slots.pop(int(index), None)
            else:
                slots[int(index)] = stack

    def highestUsed(self, slots):
        used = [index for index, stack in slots.items() if not Items.isEmpty(stack)]
        return max(used) if used else -1


FULL = register(Full)
