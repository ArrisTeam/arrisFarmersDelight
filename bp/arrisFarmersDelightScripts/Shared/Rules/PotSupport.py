# -*- coding: utf-8 -*-
"""PotSupport - 厨锅的支架（FD 的 CookingPotSupport：没有 / 托盘 / 吊把手）：放下、切换、读出来的规则（双端，纯逻辑）

JE（CookingPotBlock，方块状态 support 三选一）：
- 放下时（getStateForPlacement :117-120）：点的是方块的下面（Facing.Down，锅挂在天花板下面）是 HANDLE，否则看正下方是不是托盘热源
  （getTrayState :134-139：熔岩、营火、火）：是 TRAY，不是 NONE；
- 邻居变了（updateShape :128-130）：HANDLE 不动，别的按正下方重算；
- 潜行空手右键（use :71-74）：HANDLE 切回按正下方算的 TRAY / NONE，别的切成 HANDLE，响一声挂灯（LANTERN_PLACE 0.7 / 1.0）。
基岩版记在方块实体数据的两个旗里：handleEnable（吊把手）和 shelfEnable（托盘：Server/Helpers/Heat.RefreshHeat 按正下方算，吊把手挂着时不画），
模型的 variable.mod_handle / mod_shelf 就是这两个旗；锅的世界外观广播（Server/PotLook）带一个 support，值是下面这三个数。
"""
NONE, TRAY, HANDLE = 0, 1, 2           # CookingPotSupport 的 none / tray / handle
DOWN = 0                               # Facing.Down：放置时点的是方块的下面（CookingPotBlock.java:117）
TOGGLE_SOUND = ("block.lantern.place", 0.7, 1.0)      # (声音名, 音量, 音调)：CookingPotBlock.java:74 的 LANTERN_PLACE 0.7 / 1.0
KINDS = (NONE, TRAY, HANDLE)


def hangs(face):
    """放置时点的面是不是方块的下面：是，锅挂在它下面，就是吊把手（CookingPotBlock.java:117）。"""
    return face == DOWN


def kindOf(handle, tray):
    """两个旗 -> 支架：吊把手盖过托盘（HANDLE 时托盘不画）。"""
    return HANDLE if handle else (TRAY if tray else NONE)


def readKind(raw):
    """网络来的值 -> 支架；不是这三个数之一的（缺的、别的类型）当没有。"""
    return int(raw) if isinstance(raw, (int, float)) and not isinstance(raw, bool) and raw in KINDS else NONE
