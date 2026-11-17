# -*- coding: utf-8 -*-
"""HoldMenu - 触屏长按菜单（前置包的表现钩子 onHold，Protocol.HOLD_MENU）里四个站点用的条目和返回值的写法（客户端，纯逻辑）

触屏没有右键和 Shift 点击（原版基岩版的触屏就没有）：手指按在站点的场景里按住不动，前置包在按下的那一刻问表现的 onHold(event)，表现可以回
- None：这里按住没有意义，按下立刻生效（和从前一样，一点不变慢）；
- {"take": 目标, "count": n}：站点的一格里有 n > 1 个，弹取份量条，松手发 TAKE（take）；
- {"menu": [条目, ...]}：弹十字轮盘，最多 4 条，滑到一条臂上松手，前置包就在原落点补一下带这个键的按下 + 抬起，表现的 onPointer 收到的是一下平常的右键 / Shift 点击（menu）。
条目 {"label": 几个字, "button": 0 或 1, "quick": 布尔}：只放"和点一下不一样的右键 / Shift 点击变体"，字说这一下在这里做什么；没有新的动作，
都是表现今天本来就认的右键 / Shift 点击。每个站点在自己的 *Hold.py 里按状态判断这里有没有这样的变体（照 JE / HoD 点一下和右键、Shift 点击各做什么）。
老版本的前置包没有这个钩子（Protocol.HOLD_MENU）：它永远不会问，表现照旧。
"""

PUT_ONE = {"label": "放一个", "button": 1, "quick": False}             # 拿着一叠点放东西的地方：右键只放一个（左键整叠）
SCOOP_ALL = {"label": "全部盛出", "button": 0, "quick": True}          # 厨锅：拿着盛这锅菜的容器 / 悬着碗点汤，Shift 一次盛到没菜或没容器
CARVE = {"label": "插在板上", "button": 0, "quick": True}              # 砧板：Shift 点空板，手上的工具插进去
TAKE_BACK = {"label": "取回", "button": 1, "quick": False}             # 砧板：空手右键取回最上一层 / 板上的东西（左键是切 / 做成）
TAKE_ALL_BACK = {"label": "全部取回", "button": 1, "quick": False}     # 煎锅：右键把锅里的食物全拿回背包（左键是颠）
PUT_HERE = {"label": "只放这一格", "button": 1, "quick": False}        # 炉灶：右键只放离光标最近的空位那一件（左键每个空位一件）
TAKE_PIECE = {"label": "取下", "button": 1, "quick": False}            # 炉灶：右键取下这一件（左键是翻面）


def menu(*entries):
    """轮盘：条目按给的次序分给臂（前置包按上、右、左、下的次序放）。"""
    return {"menu": list(entries)}


def take(target, count):
    """取份量条：站点的一格里有 count > 1 个才有份量可取，否则 None（按下立刻生效）。"""
    return {"take": target, "count": int(count)} if count > 1 else None
