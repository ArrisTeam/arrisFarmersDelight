# -*- coding: utf-8 -*-
"""HandsOnMode - 场景交互前置（Hands-On Delight 的站点）在本端联动了没有：等着判定、联动着、前置太旧、没装前置（双端，纯逻辑）

联动的判定只在 Compat/Diegesis/Presence.py 做，结果经 decide 记在这里；本包别的地方都问这里，不自己去找前置包
（和机械动力系列的附属包问 CreateSDK.Presence.mode 是同一个做法）。判定之前一律当没联动：农夫乐事就是原样的农夫乐事。
    PENDING     还没判定（加载期到判定点之前）
    LINKED      前置包在、接口够新，联动的步骤表在跑或跑完了（个别步骤可能失败或被跳过，Presence.report 里看每一步）
    OUTDATED    前置包在，但接口比本包要的老，一步也不联动（客户端会提醒玩家更新）
    STANDALONE  判定点到了还是没有前置包，什么也不联动、不提醒
每端一个模式，服务端、客户端各自判定。linked() 问"这个进程里联动了没有"：服务端的代码和 Shared 的规则不知道自己在哪一端，
而一个进程只会联动它自己跑的那一端（单机两端同进程，两端都联动），所以任何一端联动了就是联动了。
没联动时 HandsOnOptions 说 Hands-On Delight 不在（站点开关是假、倍率是 1.0），HoD 自己的记账也不写（Server/HandCooking.addMade）。
"""
import traceback

PENDING = "pending"
LINKED = "linked"
OUTDATED = "outdated"
STANDALONE = "standalone"
MODES = (PENDING, LINKED, OUTDATED, STANDALONE)
SIDES = ("server", "client")

_modes = {"server": PENDING, "client": PENDING}
_callbacks = {"server": [], "client": []}


def mode(side):
    """side（"server" / "client"）端现在的模式。"""
    return _modes[side]


def linked():
    """这个进程里联动了没有：任何一端是 LINKED 就是。判定之前、前置包没装、太旧都是假。"""
    return LINKED in _modes.values()


def decide(side, value):
    """记下 side 端的模式（只有 Compat/Diegesis/Presence 调）。模式真的变了才通知 whenDecided 登记的回调；回到 PENDING 不通知。"""
    if value not in MODES:
        raise ValueError("不认识的联动模式 %r" % (value,))
    if _modes[side] == value:
        return
    _modes[side] = value
    if value != PENDING:
        for callback in list(_callbacks[side]):
            _call(callback, value)


def whenDecided(side, callback):
    """判定出了结果就调 callback(模式)：已经判定了现在就调；之后模式又变了（先 STANDALONE 后找到了前置包）带着新模式再调一次，所以回调要能重复执行。"""
    _callbacks[side].append(callback)
    if _modes[side] != PENDING:
        _call(callback, _modes[side])


def _call(callback, value):
    try:
        callback(value)
    except Exception:  # noqa: BLE001 - 回调的边界：一个出错不能拖垮别的回调，更不能拖垮判定
        traceback.print_exc()
