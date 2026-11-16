# -*- coding: utf-8 -*-
"""
物品堆的值语义：空堆、数量、能否叠放、最大堆叠数、是否完全相同。

物品堆用引擎物品字典的四个键：newItemName、newAuxValue、count、userData（没有附加数据时为 None）。
引擎读出的字典里另有附魔列表、耐久等派生键，它们都由 userData 推出来，写回时传了反而会出问题，
所以进容器前一律用 normalize 规整成这四个键；收纳袋的内容同时整理成规范写法（见 Bundles）。

叠放规则（与引擎一致）：同一物品、同一 aux、userData 完全相同（空的 userData 等于没有）；
最大堆叠数为 1 的不叠；可损坏（种类有最大耐久且没有 Unbreakable）并且已经损坏（userData 的 Damage 大于 0）的不叠。
最大堆叠数取 userData 的 ModMaxStackSize，没有时取种类的值，都不超过 254（引擎容器的上限）。
种类的最大堆叠数与最大耐久由使用方注入（服务端、客户端各用自己的引擎接口，测试用假表）。
附加数据的规范文本（canonicalText：键排好序、没有空白、非 ASCII 字转义的 JSON，同样的文字 str 与 unicode 写出来一样）
自己拼：json.dumps 要排键时走纯 Python 的编码器，每次新建一组互相引用的闭包，留下几十个要等解释器的循环回收才释放的对象；
规范文本在种类的键、指纹里用得很频繁，上万种东西时这些垃圾会频繁触发整个解释器的完整回收（一次一百多毫秒）。
纯逻辑，两端共用。
"""
import zlib
from json.encoder import encode_basestring_ascii as _quote

KEYS = ("newItemName", "newAuxValue", "count", "userData")
MAX_STACK_OVERRIDE = "ModMaxStackSize"
CONTAINER_STACK_LIMIT = 254

# 物品锁定（userData 里的 minecraft:item_lock）：锁在格子里的不能离开所在格；两种锁定都不能放进容器、不能丢弃
LOCK_KEY = "minecraft:item_lock"
LOCK_NONE = 0
LOCK_IN_SLOT = 1
LOCK_IN_INVENTORY = 2

try:
    _INTS = (int, long)  # noqa: F821
except NameError:
    _INTS = (int,)


def _isInt(value):
    return isinstance(value, _INTS) and not isinstance(value, bool)


_TEXT = (str, type(u""))
_INF = float("inf")


def _key(item):
    return item[0]


def _number(value):
    if value != value:
        return "NaN"
    if value == _INF:
        return "Infinity"
    if value == -_INF:
        return "-Infinity"
    return repr(value)


def _keyText(key):
    """字典的键照 JSON 写成字符串（与 json.dumps 一样：数、布尔、None 先转成字）。"""
    if isinstance(key, _TEXT):
        return _quote(key)
    if key is True or key is False or key is None:
        return '"%s"' % ("true" if key is True else "false" if key is False else "null")
    if isinstance(key, _INTS):
        return '"%d"' % key
    if isinstance(key, float):
        return '"%s"' % _number(key)
    raise TypeError("key %r is not a string" % (key,))


def canonicalText(value):
    """
    值的规范文本（与 json.dumps(value, sort_keys=True, separators=(",", ":")) 逐字相同，见模块说明）：字典按键排、列表与元组
    照顺序，字符串转义成 ASCII，数照 JSON 写。不认识的类型抛 TypeError，嵌套过深抛 RuntimeError（与 json.dumps 一样）。
    """
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, _TEXT):
        return _quote(value)
    if isinstance(value, _INTS):
        return "%d" % value
    if isinstance(value, float):
        return _number(value)
    if isinstance(value, dict):
        return "{" + ",".join([_keyText(key) + ":" + canonicalText(item)
                               for key, item in sorted(value.items(), key=_key)]) + "}"
    if isinstance(value, (list, tuple)):
        return "[" + ",".join([canonicalText(item) for item in value]) + "]"
    raise TypeError("%r is not JSON serializable" % (value,))


def count(stack):
    return stack.get("count", 0) if stack else 0


def isEmpty(stack):
    return not stack or stack.get("count", 0) <= 0


def withCount(stack, amount):
    """数量改为 amount 的副本；amount <= 0 时得到空格。"""
    if amount <= 0 or not stack:
        return None
    copy = dict(stack)
    copy["count"] = int(amount)
    return copy


_BUNDLE_KEYS = ("storage_item_component_content", "bundle_weight", "bundle_id")   # 见 Bundles


def _hasBundleKeys(userData):
    return isinstance(userData, dict) and any(key in userData for key in _BUNDLE_KEYS)


def canonicalUserData(userData):
    """userData 的规范写法：空的为 None；带收纳袋内容的整理成 Bundles 的规范写法（引擎读出与本框架算出的才比得上）。"""
    if not userData:
        return None
    if _hasBundleKeys(userData):
        from . import Bundles
        return Bundles.canonicalUserData(userData) or None
    return userData


def normalize(stack):
    """规整成四个键；空堆为 None。已经规整过的原样返回。"""
    if isEmpty(stack):
        return None
    if len(stack) == 4 and all(key in stack for key in KEYS) and stack["userData"] != {} \
            and _isInt(stack["count"]) and not _hasBundleKeys(stack["userData"]):
        return stack
    return {
        "newItemName": stack.get("newItemName"),
        "newAuxValue": int(stack.get("newAuxValue") or 0),
        "count": int(stack["count"]),
        "userData": canonicalUserData(stack.get("userData")),
    }


def _userValue(stack, key):
    user = stack.get("userData")
    return user.get(key) if isinstance(user, dict) else None


def _plain(value):
    """userData 里的类型标记值 {"__type__":…, "__value__":…} 取出裸值。"""
    if isinstance(value, dict) and "__value__" in value:
        return value["__value__"]
    return value


def _canonical(value):
    if value in (None, {}, [], ""):
        return None
    return canonicalText(value)


CURSE_OF_BINDING = 27   # 原版附魔编号：绑定诅咒


def enchantments(stack):
    """物品的附魔 [(编号, 等级), ...]（userData 的 ench 列表，照原版的写法）；没有附魔时为空。"""
    if isEmpty(stack):
        return []
    entries = _userValue(stack, "ench")
    out = []
    for entry in entries if isinstance(entries, list) else ():
        if isinstance(entry, dict):
            number, level = _plain(entry.get("id")), _plain(entry.get("lvl"))
            if _isInt(number):
                out.append((int(number), int(level) if _isInt(level) else 0))
    return out


def hasEnchantment(stack, number):
    return any(found == number for found, _ in enchantments(stack))


def customName(stack):
    """自定的名字（userData 的 display.Name，铁砧改的名字）；没有这一项时为 None。"""
    display = _userValue(stack, "display") if not isEmpty(stack) else None
    name = _plain(display.get("Name")) if isinstance(display, dict) else None
    return name if isinstance(name, (str, type(u""))) else None


def shortCount(count):
    """数量的短写法（超堆叠的格子、存储界面用）：999 以下照写，之后 1.2k、12k、123k、1.2M、12M、1.2G。"""
    for limit, suffix in ((1000000000, "G"), (1000000, "M"), (1000, "k")):
        if count >= limit:
            value = count / float(limit)
            text = ("%.1f" % (int(value * 10) / 10.0)) if value < 10 else str(int(value))
            return (text[:-2] if text.endswith(".0") else text) + suffix
    return str(count)


def lockMode(stack):
    if isEmpty(stack):
        return LOCK_NONE
    value = _plain(_userValue(stack, LOCK_KEY))
    return value if value in (LOCK_IN_SLOT, LOCK_IN_INVENTORY) else LOCK_NONE


def identityKey(stack):
    """
    决定能否叠放的那几项，规整成可哈希的元组（不含数量）：(物品名, aux, userData 的规范文本)。
    要把 userData 规整成文本，大的附加数据（收纳袋）很费时间，只在要做字典键、指纹时用；判断是不是同一种用 sameKind。
    """
    if isEmpty(stack):
        return None
    return (stack.get("newItemName"), int(stack.get("newAuxValue") or 0), _canonical(stack.get("userData")))


def sameKind(a, b):
    """
    a、b 是不是同一种东西（物品名、aux、userData 都相同，不看数量）。附加数据直接比较（在 C 层逐层比，不先规整成文本）；
    比出来不同时再按规范文本比一次：py2 下同样的文字可能一边是 str 一边是 unicode。
    带类型标记的值直接比较也更贴近引擎按 NBT 比较的结果（字节型的 True 与 1 是同一个值）。
    """
    if isEmpty(a) or isEmpty(b):
        return False
    if a is b:
        return True
    if a.get("newItemName") != b.get("newItemName") or int(a.get("newAuxValue") or 0) != int(b.get("newAuxValue") or 0):
        return False
    userA, userB = a.get("userData") or None, b.get("userData") or None
    if userA is userB or userA == userB:
        return True
    if userA is None or userB is None:
        return False
    return _canonical(userA) == _canonical(userB)


class ItemRules(object):
    """
    叠放与堆叠数规则。

    maxStackOf(name, aux) -> int：该种物品的最大堆叠数；
    maxDurabilityOf(name, aux) -> int：该种物品的最大耐久，没有耐久时为 0；
    infoOf(name, aux) -> dict：该种物品的引擎信息（GetItemBasicInfo 的结果，标准件按需要取，例如燃烧时长），没有时为空。
    """

    def __init__(self, maxStackOf, maxDurabilityOf=None, infoOf=None):
        self._maxStackOf = maxStackOf
        self._maxDurabilityOf = maxDurabilityOf or (lambda name, aux: 0)
        self._infoOf = infoOf

    def info(self, name, aux=0):
        """该种物品的引擎信息（字典，取不到时为空字典）。"""
        return (self._infoOf(name, aux) if self._infoOf is not None else None) or {}

    def maxStack(self, stack):
        if isEmpty(stack):
            return 0
        override = _plain(_userValue(stack, MAX_STACK_OVERRIDE))
        if _isInt(override) and override > 0:
            return min(int(override), CONTAINER_STACK_LIMIT)
        return min(self.baseMaxStack(stack), CONTAINER_STACK_LIMIT)

    def maxDurability(self, stack):
        """该种物品的最大耐久，没有耐久时为 0。"""
        if isEmpty(stack):
            return 0
        return self._maxDurabilityOf(stack.get("newItemName"), stack.get("newAuxValue", 0)) or 0

    def baseMaxStack(self, stack):
        """种类本身的最大堆叠数（不看 userData）。按字典生成物品时先按它截断数量。"""
        return max(1, int(self._maxStackOf(stack.get("newItemName"), stack.get("newAuxValue", 0)) or 1))

    def isWorn(self, stack):
        """可损坏并且已经损坏。"""
        if isEmpty(stack):
            return False
        if (self._maxDurabilityOf(stack.get("newItemName"), stack.get("newAuxValue", 0)) or 0) <= 0:
            return False
        if _plain(_userValue(stack, "Unbreakable")):
            return False
        damage = _plain(_userValue(stack, "Damage"))
        return _isInt(damage) and damage > 0

    def canStack(self, a, b):
        """a 与 b 能叠成一堆（不看数量与空间）。"""
        if isEmpty(a) or isEmpty(b):
            return False
        if not sameKind(a, b):
            return False
        if self.maxStack(a) <= 1 or self.isWorn(a) or self.isWorn(b):
            return False
        return True

    def identical(self, a, b):
        """完全相同（种类与数量都一样），这时交换没有意义。"""
        if isEmpty(a) or isEmpty(b):
            return isEmpty(a) and isEmpty(b)
        return sameKind(a, b) and count(a) == count(b)

    def room(self, target, stack):
        """target 里还能再放多少个 stack 那种东西；target 为空时是 stack 的最大堆叠数。"""
        if isEmpty(target):
            return self.maxStack(stack)
        if not self.canStack(target, stack):
            return 0
        return max(0, self.maxStack(target) - count(target))


def fingerprint(stack):
    """格子内容的指纹（种类 + 数量），请求里用来声明"我看到的是这个"。空格是空串。"""
    if isEmpty(stack):
        return ""
    payload = canonicalText([identityKey(stack), count(stack)])
    crc = zlib.crc32(payload.encode("utf-8")) & 0xFFFFFFFF
    return "%s:%d:%08x" % (stack.get("newItemName"), count(stack), crc)
