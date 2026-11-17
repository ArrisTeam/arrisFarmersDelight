# -*- coding: utf-8 -*-
"""TouchFeel - 站点表现里触屏的手感：双击间隔，问前置包的 view，老版本的前置包没有就算了（客户端）

前置包的 view.doubleSeconds() 是这种输入方式下托盘双击聚拢的间隔（触屏 0.4 秒、键鼠 0.25 秒）：后来加的，老版本的前置包上没有，这里就用调用方给的 JE 的 0.25 秒。
"""


def doubleClick(view, default):
    """双击的间隔（秒）：前置包按输入方式给的（view.doubleSeconds）；老版本的前置包没有，用 default。"""
    ask = getattr(view, "doubleSeconds", None)
    return ask() if ask is not None else default
