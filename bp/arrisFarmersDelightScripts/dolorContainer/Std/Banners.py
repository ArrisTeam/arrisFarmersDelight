# -*- coding: utf-8 -*-
"""
标准库：旗帜（原版旗帜物品、织布机，docs/PARTS.md 第 11 节）。两端共用，不导入引擎。

PATTERNS 是引擎里的旗帜图案表，照引擎的顺序：下标就是引擎给图案的编号（原版旗帜图案渲染器按编号取贴图，织布机的图案列表
照这个顺序），每一项 Pattern(编号的写法, 名字, 图案物品, 织布机里列不列)。图案物品是织布机里要放在图案格里才能织的那几种
（旗帜图案物品，堆叠数 1，织的时候不用掉）；base 与 illager 不出现在织布机里。
DYES 是染料物品 -> 颜色（引擎的颜色编号 0–15）：照 1.20.10 起的世界，只有 16 种染料算染料（墨囊、可可豆、青金石、骨粉不算）。
模组的东西经登记表加进来（两端都要登记）：registerDye(物品名, 颜色) 算染料，registerPatternItem(物品名, 图案的编号写法) 是引擎
图案表里已有的那种图案的图案物品（一种图案可以有几种图案物品；原来不要图案物品的图案登记了也要，织布机只在背包里有它时列出）。
新的图案引擎画不出来，不能登记。

旗帜物品：底色是物品的数据值；附加数据里 Patterns 是一层层图案（每层 Pattern 是编号的写法、Color 是颜色），Type 为 1 的是
灾厄旗帜（织布机不收）。一面旗帜最多 MAX_PATTERNS 层（照原版织布机：满了不能再织）。
"""
from ..Common import Items

try:
    _TEXT = (str, unicode)  # noqa: F821
    _INTS = (int, long)  # noqa: F821
except NameError:
    _TEXT = (str,)
    _INTS = (int,)

BANNER = "minecraft:banner"
MAX_PATTERNS = 6
GRAY, WHITE = 8, 15   # 织布机图案按钮上的样子：灰底、白色的图案


class Pattern(object):
    """
    一种旗帜图案（见模块说明）。index 是它在 PATTERNS 里的下标（引擎的编号）；item 是原版的图案物品（没有为 None），items 是
    全部图案物品（原版的在前，登记的接着）。
    """

    __slots__ = ("index", "code", "name", "item", "items", "hidden")

    def __init__(self, index, code, name, item=None, hidden=False):
        self.index, self.code, self.name, self.item, self.hidden = index, code, name, item, hidden
        self.items = (item,) if item else ()


def _patterns(rows):
    return tuple(Pattern(index, *row) for index, row in enumerate(rows))


PATTERNS = _patterns((
    ("", "base", None, True),
    ("bo", "border"),
    ("bri", "bricks", "minecraft:field_masoned_banner_pattern"),
    ("mc", "circle"),
    ("cre", "creeper", "minecraft:creeper_banner_pattern"),
    ("sku", "skull", "minecraft:skull_banner_pattern"),
    ("cr", "cross"),
    ("cbo", "curly_border", "minecraft:bordure_indented_banner_pattern"),
    ("ld", "diagonal_up_left"),
    ("rud", "diagonal_up_right"),
    ("lud", "diagonal_left"),
    ("rd", "diagonal_right"),
    ("flo", "flower", "minecraft:flower_banner_pattern"),
    ("gra", "gradient"),
    ("gru", "gradient_up"),
    ("hh", "half_horizontal"),
    ("hhb", "half_horizontal_bottom"),
    ("vh", "half_vertical"),
    ("vhr", "half_vertical_right"),
    ("ill", "illager", None, True),
    ("moj", "mojang", "minecraft:mojang_banner_pattern"),
    ("mr", "rhombus"),
    ("ss", "small_stripes"),
    ("bl", "square_bottom_left"),
    ("br", "square_bottom_right"),
    ("tl", "square_top_left"),
    ("tr", "square_top_right"),
    ("sc", "straight_cross"),
    ("bs", "stripe_bottom"),
    ("cs", "stripe_center"),
    ("dls", "stripe_downleft"),
    ("drs", "stripe_downright"),
    ("ls", "stripe_left"),
    ("ms", "stripe_middle"),
    ("rs", "stripe_right"),
    ("ts", "stripe_top"),
    ("bt", "triangle_bottom"),
    ("tt", "triangle_top"),
    ("bts", "triangles_bottom"),
    ("tts", "triangles_top"),
    ("pig", "piglin", "minecraft:piglin_banner_pattern"),
    ("glb", "globe", "minecraft:globe_banner_pattern"),
    ("flw", "flow", "minecraft:flow_banner_pattern"),
    ("gus", "guster", "minecraft:guster_banner_pattern"),
))
BY_CODE = dict((pattern.code, pattern) for pattern in PATTERNS)
BY_ITEM = dict((pattern.item, pattern) for pattern in PATTERNS if pattern.item)
PATTERN_ITEMS = tuple(pattern.item for pattern in PATTERNS if pattern.item)   # 图案物品，按图案的顺序

DYES = dict((name, color) for color, name in enumerate((
    "minecraft:black_dye", "minecraft:red_dye", "minecraft:green_dye", "minecraft:brown_dye", "minecraft:blue_dye",
    "minecraft:purple_dye", "minecraft:cyan_dye", "minecraft:light_gray_dye", "minecraft:gray_dye", "minecraft:pink_dye",
    "minecraft:lime_dye", "minecraft:yellow_dye", "minecraft:light_blue_dye", "minecraft:magenta_dye",
    "minecraft:orange_dye", "minecraft:white_dye")))
_revision = [0]   # 登记表改过几次（织布机按它重算派生的表）


def registerDye(name, color):
    """登记染料：name（物品名）在织布机里算 color（引擎的颜色编号 0–15）的染料。两端都要登记。"""
    if not 0 <= int(color) <= 15:
        raise ValueError("dye color must be 0-15: %r" % (color,))
    DYES[name] = int(color)
    _revision[0] += 1


def registerPatternItem(name, code):
    """
    登记图案物品：name（物品名）放进织布机的图案格时能织 code（引擎图案表里已有的图案的编号写法）那种图案；那种图案原来不要
    图案物品的，从此也要。两端都要登记。
    """
    pattern = BY_CODE.get(code)
    if pattern is None or pattern.hidden:
        raise ValueError("unknown loom pattern: %r" % (code,))
    if name not in pattern.items:
        pattern.items += (name,)
    if pattern.item is None:
        pattern.item = name
    BY_ITEM[name] = pattern
    _revision[0] += 1


def revision():
    """登记表改过几次。"""
    return _revision[0]


def _plain(value):
    return value.get("__value__") if isinstance(value, dict) and "__value__" in value else value


def _user(stack):
    user = stack.get("userData") if not Items.isEmpty(stack) else None
    return user if isinstance(user, dict) else {}


def isDefaultBanner(stack):
    """普通的旗帜（不是灾厄旗帜）：织布机的旗帜格只收它。"""
    if Items.isEmpty(stack) or stack.get("newItemName") != BANNER:
        return False
    kind = _plain(_user(stack).get("Type"))
    return kind is None or kind == 0


def layers(stack):
    """旗帜附加数据里的那一列图案（原样，可能有写坏的项）；没有为空列表。"""
    found = _user(stack).get("Patterns")
    found = _plain(found)
    return list(found) if isinstance(found, (list, tuple)) else []


def _layer(entry):
    """一层图案的 (编号的写法, 颜色)；不是写着 Pattern 与 Color 的一项时为 None（照原版跳过）。"""
    if not isinstance(entry, dict) or "Pattern" not in entry or "Color" not in entry:
        return None
    code, color = _plain(entry["Pattern"]), _plain(entry["Color"])
    if not isinstance(code, _TEXT) or isinstance(color, bool) or not isinstance(color, _INTS):
        return None
    return code, int(color)


def patternOf(item):
    """要用图案物品 item（物品堆）的那种图案；不是图案物品为 None。"""
    return BY_ITEM.get(item.get("newItemName")) if not Items.isEmpty(item) else None


def matches(pattern, item):
    """图案物品 item 是不是 pattern 要的（它的图案物品之一）。"""
    return bool(pattern.items) and not Items.isEmpty(item) and item.get("newItemName") in pattern.items


def weave(banner, dye, material, pattern):
    """
    织布机织出来的旗帜（照原版织布机），织不了为 None：旗帜格是普通的旗帜、图案没满 MAX_PATTERNS 层、染料格是染料；pattern
    要图案物品时图案格是那种图案物品，不要时图案格要空着。产物是一面旗帜（一个）：照抄原来的旗帜，附加数据里的图案重写一遍
    （只留每层的 Pattern 与 Color，写坏的项丢掉），最后加上这一层（颜色是染料的颜色）。
    """
    if pattern is None or not isDefaultBanner(banner) or len(layers(banner)) >= MAX_PATTERNS:
        return None
    if Items.isEmpty(dye) or dye.get("newItemName") not in DYES:
        return None
    if (pattern.item is not None and not matches(pattern, material)) or (pattern.item is None and not Items.isEmpty(material)):
        return None
    rows = [row for row in (_layer(entry) for entry in layers(banner)) if row is not None]
    rows.append((pattern.code, DYES[dye["newItemName"]]))
    user = dict(_user(banner))
    user["Patterns"] = [{"Pattern": {"__type__": 8, "__value__": code}, "Color": {"__type__": 3, "__value__": color}}
                        for code, color in rows]
    return Items.normalize(dict(Items.withCount(banner, 1), userData=user))


def rendererBag(stack):
    """
    原版旗帜图案渲染器的属性包（照原版织布机右边的预览）：底是一层 base（颜色是物品的数据值），往上是附加数据里的一层层图案
    （不认得的图案画成 base，照原版）；不是旗帜时两项都是空串（什么都不画）。
    """
    if Items.isEmpty(stack) or stack.get("newItemName") != BANNER:
        return {"#banner_patterns": "", "#banner_colors": ""}
    patterns, colors = ["0_"], ["%d_" % int(stack.get("newAuxValue") or 0)]
    for row in (_layer(entry) for entry in layers(stack)):
        if row is not None:
            found = BY_CODE.get(row[0])
            patterns.append("%d_" % (found.index if found is not None else 0))
            colors.append("%d_" % row[1])
    return {"#banner_patterns": "".join(patterns), "#banner_colors": "".join(colors)}


def buttonBag(pattern):
    """织布机图案按钮上的旗帜（照原版）：灰底上一层白色的这种图案。"""
    return {"#banner_patterns": "0_%d_" % pattern.index, "#banner_colors": "%d_%d_" % (GRAY, WHITE)}
