# -*- coding: utf-8 -*-
"""Ready - 新联动接口的 ready 广播：每端一次，载荷带这一端的门面；别的模组的处理函数出错不连累农夫乐事（双端，不碰引擎）

两端的入口调 publish(side, systemOf)：服务端 Server/ExtensionReady.py 在 LoadServerAddonScriptsAfter，客户端 Client/ExtensionReady.py 在 LoadClientAddonScriptsAfter。
systemOf() 给出广播用的系统（命名空间、系统名是 Events 里对外公布的那两个，别的模组照它们监听），它的 BroadcastEvent(事件名, 载荷) 在本端当场调完所有监听者。
- 每端只播一次（单机时两端在同一个进程里，按端分开记）：同一端再调什么也不做。
- 拿不到系统（引擎注册不了、注册时抛了异常）：打日志，不播。
- 广播出了异常：接住，打一次完整的调用栈，农夫乐事接着往下走。引擎的事件总线本来给每个监听者单独兜着：一个抛了，引擎往错误日志打一段调用栈、
  接着调下一个，调 BroadcastEvent 的这里收不到那个异常（3.10 实机，2026-11-26，两端，自定义事件和引擎事件都量过）。这里是第二道。
不"冻结"：农夫乐事的表都是活的（旧接口一直允许随时追加，表同步每 5 秒比一次），ready 之后再登记照样生效。
"""
import traceback

from . import Events
from .Facade import getExtensionApi

SENT, NO_SYSTEM, RAISED = "sent", "no-system", "raised"


def payloadOf(side):
    """ready 事件的载荷。"""
    return {"extension": getExtensionApi(side), "side": side, "apiVersion": Events.EXTENSION_API_VERSION}


class Publisher(object):
    """记着每一端播过没有、结果如何。游戏里用本模块的那一个；测试各建各的。"""

    def __init__(self):
        self.states = dict((side, None) for side in Events.SIDES)      # None 是还没播；SENT / NO_SYSTEM / RAISED

    def publish(self, side, systemOf):
        """播这一端的 ready（只播一次），返回这一端的结果；已经播过返回 None。side 不是 "server" / "client" 抛 ValueError。"""
        if side not in Events.SIDES:
            raise ValueError("side 只能是 'server' 或 'client'，收到 %r" % (side,))
        if self.states[side] is not None:
            return None
        system = self._system(side, systemOf)
        if not system:
            self.states[side] = NO_SYSTEM
            print("[arrisFarmersDelight] 新联动接口（%s 端）：拿不到广播用的系统，不发 ready 事件" % side)
            return NO_SYSTEM
        self.states[side] = SENT
        try:
            system.BroadcastEvent(Events.READY_EVENTS[side], payloadOf(side))
        except Exception:  # noqa: BLE001 - 别的模组的 ready 处理函数出错不能连累农夫乐事
            self.states[side] = RAISED
            print("[arrisFarmersDelight] 新联动接口（%s 端）：ready 事件的处理函数出错（别的模组的），农夫乐事照常往下走" % side)
            traceback.print_exc()
        return self.states[side]

    @staticmethod
    def _system(side, systemOf):
        try:
            return systemOf()
        except Exception:  # noqa: BLE001 - 引擎注册系统出错：当作拿不到
            print("[arrisFarmersDelight] 新联动接口（%s 端）：注册广播用的系统出错" % side)
            traceback.print_exc()
            return None


_publisher = Publisher()


def publish(side, systemOf):
    """两端入口调它：播这一端的 ready（每端一次）。"""
    return _publisher.publish(side, systemOf)


def status(side):
    """这一端的 ready 播了没有：None 还没播，SENT / NO_SYSTEM / RAISED（游戏内自检读它）。"""
    return _publisher.states.get(side)


def reset():
    """测试用：两端都当还没播过。"""
    _publisher.states = Publisher().states
