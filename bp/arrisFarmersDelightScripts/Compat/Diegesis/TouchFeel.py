# -*- coding: utf-8 -*-
"""TouchFeel - 站点表现里触屏的手感：轻震和双击间隔，问前置包的 view，老版本的前置包没有就算了（客户端）

前置包的 view.buzz(种类)（Shared/Haptics）在触屏输入、表现的 sounds 没关时让设备震一下；view.doubleSeconds() 是这种输入方式下托盘双击聚拢的间隔
（触屏 0.4 秒、键鼠 0.25 秒）。两样都是后来加的（Protocol.HAPTICS）：老版本的前置包上没有，这里就不震、双击用调用方给的 JE 的 0.25 秒。
站点表现在自己放拿起 / 放下 / 落刀 / 翻面 / 被拒的声音的地方顺手调 buzz；种类名和前置包的 Shared/Haptics 是同一套（tests/test_touch_feel.py 对着前置包的表查过）。
"""
PICK, PUT, CUT, FLIP, REFUSE = "pick", "put", "cut", "flip", "refuse"     # 拿起 / 放下 / 一刀落下 / 翻面 / 被拒
SETTLED = {"placed": PUT, "refused": REFUSE}      # 服务端回的结果里本人该震的（煎锅、炉灶的放进来 / 被拒；自己的颠、翻、取是点下去那一刻就震的）


def buzz(view, kind):
    """触屏的一下轻震（view.buzz；老版本的前置包没有就什么都不做）。"""
    ask = getattr(view, "buzz", None)
    if ask is not None:
        ask(kind)


def settled(feel, name):
    """场景收到服务端的一次性表现 name 时：本人开着站点（feel 是表现交进来的震动函数，没开着是 None）就按 SETTLED 震一下。"""
    if feel is not None and name in SETTLED:
        feel(SETTLED[name])


def doubleClick(view, default):
    """双击的间隔（秒）：前置包按输入方式给的（view.doubleSeconds）；老版本的前置包没有，用 default。"""
    ask = getattr(view, "doubleSeconds", None)
    return ask() if ask is not None else default
