# -*- coding: utf-8 -*-
"""TouchFeel - 站点表现里触屏的手感：轻震、双击间隔、点选的东西飞上站点，问前置包的 view，老版本的前置包没有就算了（客户端）

前置包的 view.buzz(种类)（Shared/Haptics）在触屏输入、表现的 sounds 没关时让设备震一下；view.doubleSeconds() 是这种输入方式下托盘双击聚拢的间隔
（触屏 0.4 秒、键鼠 0.25 秒）。两样都是后来加的（Protocol.HAPTICS）：老版本的前置包上没有，这里就不震、双击用调用方给的 JE 的 0.25 秒。
站点表现在自己放拿起 / 放下 / 落刀 / 翻面 / 被拒的声音的地方顺手调 buzz；种类名和前置包的 Shared/Haptics 是同一套（tests/test_touch_feel.py 对着前置包的表查过）。
触屏点选（前置包的 Protocol.FLY_IN，原版基岩版触屏的规矩）：点托盘的一格选中的那一叠画在它的格子里，再点站点把它放上去时，前置包画一件物品从那一格飞到点的地方
（view.flyIn）。砧板、煎锅、炉灶是用自定义动作 place 放东西的，内核不知道那是"放下"，所以在发 place 的地方调这里的 flyIn——只在照客户端的状态放得上去的时候调
（放不上的服务端会拒，东西不该飞过去）；厨锅走内核自己的点击，内核已经替它飞了。键鼠、手柄，手指拖着那一叠的时候，前置包什么都不画。
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


def flyIn(view):
    """手上的东西正放上站点：触屏点选的那一叠从托盘里它那一格飞到点的地方（view.flyIn；老版本的前置包没有就什么都不做）。"""
    ask = getattr(view, "flyIn", None)
    if ask is not None:
        ask()


def doubleClick(view, default):
    """双击的间隔（秒）：前置包按输入方式给的（view.doubleSeconds）；老版本的前置包没有，用 default。"""
    ask = getattr(view, "doubleSeconds", None)
    return ask() if ask is not None else default
