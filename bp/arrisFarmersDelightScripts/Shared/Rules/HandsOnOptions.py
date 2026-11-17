# -*- coding: utf-8 -*-
"""HandsOnOptions - Hands-On Delight 配置表的读法：缺省值、宽松的读、倍率夹进 0.1 ~ 10、派生规则、按倍率算时间（双端，纯规则）

对应 Hands-On Delight 的 HandsOnConfig.java（read / readTime / 各个取值函数 / scaled）。表是 Shared/Data/HandsOnConfig.py 的 CONFIG，
每次取值现读：表里改了（整合包作者改文件，测试里直接改）下一次取就变。JE 启动时把文件读进静态字段，"只读一次"在这里是调用方的事——
站点登记（Compat/Diegesis 的两个 Boot）只在启动时问一次。

表里的值不对时的兜底照 JE：缺键、类型不对、读不成当缺省值（DEFAULTS，就是 JE 的缺省）；布尔认 true / yes / on / 1 和 false / no / off / 0
（HandsOnConfig.read，字符串不分大小写、两头空白不算；Python 的 True / False 直接用，整数 1 / 0 当 "1" / "0"）；倍率是数或数字串（逗号当小数点），
夹进 0.1 ~ 10，不是有限的数当缺省（HandsOnConfig.readTime）。
"""
from ..Data import HandsOnConfig as Table
from .HandsOn.Mth import clamp, roundInt

try:
    _TEXT = (str, unicode)  # noqa: F821 - py2：脚本里的字符串可能是 unicode
    _NUMBERS = (int, long, float)  # noqa: F821
    _INTEGERS = (int, long)  # noqa: F821
except NameError:
    _TEXT = (str,)
    _NUMBERS = (int, float)
    _INTEGERS = (int,)

# JE 的缺省值（HandsOnConfig.java:58-77 里这几项的初值）：表里缺了、写错了就是它们；表里随包带的值也是它们（tests 核对）
DEFAULTS = {
    "cooking_pot": True,                # :58
    "cutting_board": True,              # :59
    "skillet": True,                    # :60
    "stove": True,                      # :61
    "remove_crafting_recipes": True,    # :71
    "stirring_required": True,          # :72
    "recipe_book": True,                # :73
    "cooking_pot_time": 1.0,            # :74
    "skillet_time": 1.0,                # :75
    "stove_time": 1.0,                  # :76
}
SHORTEST_TIME = 0.1             # 倍率的范围：最短是平常的十分之一，最长是十倍（HandsOnConfig.java:23-24）
LONGEST_TIME = 10.0
_TRUE = ("true", "yes", "on", "1")      # HandsOnConfig.read 的 switch（:133-135）
_FALSE = ("false", "no", "off", "0")
_FLOAT_BOUND = 3.4028235677973366e38    # Float.parseFloat 超过它给无穷大（float 的最大值再加半个间隔），Float.isFinite 不过关


def readFlag(value, fallback):
    """HandsOnConfig.read：一个开关怎么读。真 / 假照上面两组词，别的是 fallback。"""
    if value is True or value is False:
        return value
    if isinstance(value, _TEXT):
        text = value.strip().lower()
    elif isinstance(value, _INTEGERS):
        text = str(value)
    else:
        return fallback
    if text in _TRUE:
        return True
    return False if text in _FALSE else fallback


def readTime(value, fallback):
    """HandsOnConfig.readTime：一个烹饪倍率怎么读。数（或逗号 / 点分的数字串）夹进 0.1 ~ 10；读不成数、不是有限的数是 fallback。"""
    if isinstance(value, bool):
        return fallback              # Java 里 "true" / "false" 读不成数
    try:
        if isinstance(value, _NUMBERS):
            number = float(value)
        elif isinstance(value, _TEXT):
            number = float(value.strip().replace(",", "."))
        else:
            return fallback
    except (ValueError, OverflowError):
        return fallback
    if number != number or abs(number) >= _FLOAT_BOUND:
        return fallback
    return clamp(number, SHORTEST_TIME, LONGEST_TIME)


def _flag(key):
    return readFlag(Table.CONFIG.get(key), DEFAULTS[key])


def _time(key):
    return readTime(Table.CONFIG.get(key), DEFAULTS[key])


# ---------------------------------------------------------------- 站点开关（HandsOnConfig.java:156-175）

def cookingPot():
    """厨锅站点；关了锅照农夫乐事原样用。"""
    return _flag("cooking_pot")


def cuttingBoard():
    return _flag("cutting_board")


def skillet():
    return _flag("skillet")


def stove():
    return _flag("stove")


# ---------------------------------------------------------------- 别的开关与派生规则

def removeCraftingRecipes():
    """砧板上的菜离开玩家的合成格；没有砧板站点就没有地方做，不拿掉（HandsOnConfig.java:222-225）。"""
    return _flag("remove_crafting_recipes") and cuttingBoard()


def stirringRequired():
    """厨师放的料要等勺子；没有厨锅站点就没有勺子，不要求（HandsOnConfig.java:227-229）。"""
    return _flag("stirring_required") and cookingPot()


def recipeBook():
    """站点旁挂不挂食谱书（HandsOnConfig.java:266-269）。"""
    return _flag("recipe_book")


# ---------------------------------------------------------------- 烹饪时间倍率（站点关了算 1.0）

def cookingPotTime():
    """料在锅里煮多久是平常的几倍：搅着的、放着不管的、漏斗放进去的、农夫乐事自己的界面里放的；厨锅站点关了是 1（HandsOnConfig.java:235-237）。"""
    return _time("cooking_pot_time") if cookingPot() else 1.0


def skilletTime():
    """在煎锅站点里煎的食物一面煎多久是平常的几倍（HandsOnConfig.java:240-242）。"""
    return _time("skillet_time") if skillet() else 1.0


def stoveTime():
    """在炉灶站点里烤的食物一面烤多久是平常的几倍（HandsOnConfig.java:245-247）。"""
    return _time("stove_time") if stove() else 1.0


def scaled(ticks, times):
    """ticks 刻按倍率 times 算出的刻数，至少一刻（HandsOnConfig.scaled，:262-264：Math.max(1, Math.round(ticks * times))）。"""
    return max(1, roundInt(ticks * times))
