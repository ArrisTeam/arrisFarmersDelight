# -*- coding: utf-8 -*-
"""HoldMenu - 触屏长按菜单（前置包的表现钩子 onHold，Protocol.HOLD_MENU）里四个站点用的条目和返回值的写法（客户端，纯逻辑）

触屏没有右键和 Shift 点击（原版基岩版的触屏就没有）：手指按在站点的场景里按住不动，前置包在按下的那一刻问表现的 onHold(event)，表现可以回
- None：这里按住没有意义，按下立刻生效（和从前一样，一点不变慢）；
- {"take": 目标, "count": n}：站点的一格里有 n > 1 个，弹取份量条，松手发 TAKE（take）；
- {"menu": [条目, ...]}：最多 4 条（menu）。不止一条：弹十字轮盘，滑到一条臂上松手，前置包就在原落点补一下带这个键的按下 + 抬起；
  只有一条（前置包有 Protocol.HOLD_ACT 时）：不弹轮盘，按住到点当场在原落点补那一下——等的时候手指上方一个带进度的小标签写着条目的字，点一下这里头几次
  在物品详情牌上教一句"按住：xx"（条目带 "confirm": True 的才照旧弹一条臂的轮盘；这里的条目都不带）。两种表现的 onPointer 收到的都是一下平常的右键 / Shift 点击。
  老版本的前置包上一条也弹轮盘。在有数量档的前置包上，下面这些菜单处处只有一条——所以字要说清按住做的是什么。
条目 {"label": 几个字, "key": 语言文件里的键, "button": 0 或 1, "quick": 布尔}（key：字按玩家的语言给，rp/texts/*.lang；前置包认它才查——Protocol.TEXT_KEYS，
老版本照 label 画；按住直接做的标签和教的那一句也用它）：只放"和点一下不一样的右键 / Shift 点击变体"，字说这一下在这里做什么；没有新的动作，
都是表现今天本来就认的右键 / Shift 点击。每个站点在自己的 *Hold.py 里按状态判断这里有没有这样的变体（照 JE / HoD 点一下和右键、Shift 点击各做什么）。
老版本的前置包没有这个钩子（Protocol.HOLD_MENU）：它永远不会问，表现照旧。
"拿着一叠只放一个"（PUT_ONE，炉灶拿着一叠时的 PUT_HERE）在有数量档的前置包上不再给（tapMode）：屏幕右下角的"全部 / 单个"按钮管它，"单个"档里点一下就是右键
（用户 2026-11-19 定的：放多少用切换按钮，不用长按出轮盘）。
"""

PUT_ONE = {"label": "放一个", "key": "arris_fd.hold.put_one", "button": 1, "quick": False}             # 拿着一叠点放东西的地方：右键只放一个（左键整叠）
SCOOP_ALL = {"label": "全部盛出", "key": "arris_fd.hold.scoop_all", "button": 0, "quick": True}          # 厨锅：拿着盛这锅菜的容器 / 悬着碗点汤，Shift 一次盛到没菜或没容器
CARVE = {"label": "插在板上", "key": "arris_fd.hold.carve", "button": 0, "quick": True}              # 砧板：Shift 点空板，手上的工具插进去
TAKE_BACK = {"label": "取回", "key": "arris_fd.hold.take_back", "button": 1, "quick": False}             # 砧板：空手右键取回最上一层 / 板上的东西（左键是切 / 做成）
TAKE_ALL_BACK = {"label": "全部取回", "key": "arris_fd.hold.take_all_back", "button": 1, "quick": False}     # 煎锅：右键把锅里的食物全拿回背包（左键是颠）
PUT_HERE = {"label": "只放这一格", "key": "arris_fd.hold.put_here", "button": 1, "quick": False}        # 炉灶：右键只放离光标最近的空位那一件（左键每个空位一件）
TAKE_PIECE = {"label": "取下", "key": "arris_fd.hold.take_piece", "button": 1, "quick": False}            # 炉灶：右键取下这一件（左键是翻面）


def tapMode(view):
    """前置包有触屏的数量档（Protocol.TAP_MODE：视图上有 tap）：拿着不止一个的一叠点一下放多少归那个按钮管，轮盘里不再放"放一个"。
    老版本的前置包没有它：照旧给轮盘条目，不然触屏上够不着右键。"""
    return getattr(view, "tap", None) is not None


def menu(*entries):
    """轮盘：条目按给的次序分给臂（前置包按上、右、左、下的次序放）。"""
    return {"menu": list(entries)}


def take(target, count):
    """取份量条：站点的一格里有 count > 1 个才有份量可取，否则 None（按下立刻生效）。"""
    return {"take": target, "count": int(count)} if count > 1 else None
