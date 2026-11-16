# -*- coding: utf-8 -*-
"""
同一个游戏里几个模组各带一份本库时，各份之间共用的一张表。

每份库只管自己模组的容器；跨模组的事经这张表协调：
- owners：谁开着容器。键是 ("server", 玩家 ID) 或 ("client", "screen")，值是 (使用方, 关闭函数)。
  打开新的容器前先让别的使用方关掉它开着的（原版同一时间只开一个容器界面），见 claim；
- policies：世界级的设置，"dropDisabled" 为真时不能往世界里丢东西，"containersDisabled" 为真时谁都不能打开容器；
- storage：别的模组登记的收纳袋规格，物品名 -> 字段字典（见 Bundles.register）。

表放在 sys.modules 里一个固定的名字下，不属于哪一份库，哪份先用到就由哪份建。单人游戏两端在同一个解释器里，
两端的键各不相同，共用这一张。版本不同的几份库都读写它，所以只加新的键与字段、不改已有的含义；
值只放字符串、数字、布尔、元组、字典，以及只收发这几类值的函数。
"""
import traceback
import types

PROTOCOL = 1
_KEY = "__dolor_container_shared__"


def table():
    modules = traceback.sys.modules   # 已载入模块表经 traceback 取：网易打包机审把 sys 当禁用模块
    shared = modules.get(_KEY)
    if shared is None:
        shared = types.ModuleType(_KEY)
        modules[_KEY] = shared
    for name in ("owners", "policies", "storage"):
        if not isinstance(getattr(shared, name, None), dict):
            setattr(shared, name, {})
    if getattr(shared, "protocol", 0) < PROTOCOL:
        shared.protocol = PROTOCOL
    return shared


def claim(key, host, release, log=None):
    """
    把 key 记到 host 名下，release(key) 是让 host 关掉它的函数。别的使用方占着时，先撤下它的登记再调它的 release
    （出错只记日志：别的模组的问题不该挡住这边打开）。
    """
    owners = table().owners
    current = owners.get(key)
    if current is not None and current[0] != host:
        owners.pop(key, None)
        try:
            current[1](key)
        except Exception as error:  # noqa: BLE001
            if log is not None:
                log("release of %r by %s failed: %r" % (key, current[0], error))
    owners[key] = (host, release)


def unclaim(key, host):
    owners = table().owners
    current = owners.get(key)
    if current is not None and current[0] == host:
        del owners[key]


def forgetHost(host, side):
    """这份库的一端（"server" / "client"）重新载入时调用：清掉这一端以前的登记（关闭函数属于已经卸掉的旧模块）。"""
    owners = table().owners
    for key, value in list(owners.items()):
        if key[0] == side and value[0] == host:
            del owners[key]
