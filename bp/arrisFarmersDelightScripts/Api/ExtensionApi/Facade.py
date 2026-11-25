# -*- coding: utf-8 -*-
"""Facade - 新联动接口的门面 ext：ready 事件把它交给别的模组（双端，不碰引擎）

每端一个，由 getExtensionApi(side) 建、缓存（单机时两端在同一个进程里，各拿各的）；别的模组从 ready 事件的载荷里拿（Events、Ready），不要自己构造。
标识（apiVersion 1 起就有）：
    ext.side                 "server" 或 "client"
    ext.apiVersion           公共接口的版本（Events.EXTENSION_API_VERSION），只有破坏性变更才加一
    ext.hostVersion          农夫乐事的版本号 (主, 次, 修订)，和 manifest 一样（Version.HOST_VERSION），每次发版都变
    ext.capabilities         这一端的全部能力名（frozenset）
    ext.hasCapability(name)  这一端有没有这项能力
以后门面上加的接口各自登记能力名（Events 的两张表），别的模组先 hasCapability 再调。
"""
from . import Events
from .Version import HOST_VERSION

try:
    _STRING_TYPES = (basestring,)  # noqa: F821 - py2
except NameError:
    _STRING_TYPES = (str,)


class ExtensionApiFacade(object):
    """一端的门面。"""

    def __init__(self, side):
        if side not in Events.SIDES:
            raise ValueError("side 只能是 'server' 或 'client'，收到 %r" % (side,))
        self._side = side

    @property
    def side(self):
        return self._side

    @property
    def apiVersion(self):
        return Events.EXTENSION_API_VERSION

    @property
    def hostVersion(self):
        return HOST_VERSION

    @property
    def capabilities(self):
        return Events.SERVER_CAPABILITIES if self._side == "server" else Events.CLIENT_CAPABILITIES

    def hasCapability(self, name):
        """这一端有没有这项能力。名字不是字符串（None、列表……）就是没有，不抛。"""
        return isinstance(name, _STRING_TYPES) and name in self.capabilities

    def __repr__(self):
        return "<arrisFarmersDelight ExtensionApi %s api=%d host=%s>" % (
            self._side, self.apiVersion, ".".join(str(part) for part in self.hostVersion))


_facades = {}


def getExtensionApi(side):
    """这一端的门面，同一端总是同一个对象；side 不是 "server" / "client" 抛 ValueError。"""
    if side not in Events.SIDES:
        raise ValueError("side 只能是 'server' 或 'client'，收到 %r" % (side,))
    facade = _facades.get(side)
    if facade is None:
        facade = _facades[side] = ExtensionApiFacade(side)
    return facade
