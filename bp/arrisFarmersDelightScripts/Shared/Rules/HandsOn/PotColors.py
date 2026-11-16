# -*- coding: utf-8 -*-
"""PotColors - 汤、碎料、倒进去的液体是什么颜色：从物品图标的像素算（双端，纯函数）

移植自 Hands-On Delight 的 client/FoodColors.java（main / broth / sampleMain / isGreen / lighter / mix）、client/KitchenLooks.java 的 liquidColor、
client/ItemVoxels.java 的 contents，以及 PotBehavior.blend（1105-1111 行）。Java 的浮点是 float（32 位），取色边界（色相分成 12 份、
饱和度 / 亮度的下限）很敏感，所以这里的每一步浮点运算都舍入到 float32，java.awt.Color 的 RGBtoHSB / HSBtoRGB 也照 JDK 的写法逐步移植；
结果和 Java 逐位一致（tests/test_pot_colors.py 里有拿 JDK 跑出来的对照值）。

图标用像素表示：pixels 是行优先的 (r, g, b, a) 列表（各 0..255），width / height 是图标的宽高；颜色一律 0xRRGGBB（blend 例外：0xAARRGGBB）。
本模块不读文件；tools/gen_broth_colors.py 拿它按贴图生成 Shared/Data/BrothColors.py，游戏里不需要重算。
"""
import math
import struct

from .Mth import roundInt


def f32(value):
    """舍入到 32 位浮点（Java 的 float）。"""
    return struct.unpack("f", struct.pack("f", value))[0]


FALLBACK = 0xB0A070              # 什么都读不出来时的颜色（FoodColors.FALLBACK）
EGG = 0xF2DC9A                   # 生蛋搅进去：蛋黄加蛋白（FoodColors.EGG）
HUES = 12                        # 色相分 12 份数直方图
BOWL_TOP = f32(0.6)              # 容器颜色不在图标里时只看上面这一部分行（碗里的东西露在图标上半）
GREY = f32(0.14)                 # 饱和度低于它算灰的：给熟食的暖色调
WARM_HUE = f32(0.1)
MIN_SATURATION = f32(0.38)
MIN_BRIGHTNESS = f32(0.72)
OUTLINE = f32(0.3)               # 亮度低于它的像素是描边，不算
GREEN_FROM = f32(0.2)            # isGreen 的色相范围
GREEN_TO = f32(0.47)
FAT_LIGHT = f32(0.55)            # 浮油比汤亮多少（CookedPieces.FAT_LIGHT）
SOLID = 128                      # alpha 不小于它的像素才算


def rgbToHsb(r, g, b):
    """java.awt.Color.RGBtoHSB：(色相, 饱和度, 亮度)，都是 float32 的值，0..1。"""
    cmax = max(r, g, b)
    cmin = min(r, g, b)
    brightness = f32(cmax / 255.0)
    saturation = f32((cmax - cmin) / float(cmax)) if cmax != 0 else 0.0
    if saturation == 0.0:
        return 0.0, saturation, brightness
    span = float(cmax - cmin)
    redc, greenc, bluec = f32((cmax - r) / span), f32((cmax - g) / span), f32((cmax - b) / span)
    if r == cmax:
        hue = f32(bluec - greenc)
    elif g == cmax:
        hue = f32(f32(2.0 + redc) - bluec)
    else:
        hue = f32(f32(4.0 + greenc) - redc)
    hue = f32(hue / 6.0)
    if hue < 0:
        hue = f32(hue + 1.0)
    return hue, saturation, brightness


def hsbToRgb(hue, saturation, brightness):
    """java.awt.Color.HSBtoRGB（去掉 alpha，即 & 0xFFFFFF）：0xRRGGBB。参数按 float32 用；超出 0..1 的参数和 Java 一样把字节溢出进相邻通道。"""
    hue, saturation, brightness = f32(hue), f32(saturation), f32(brightness)

    def byte(value):
        return int(f32(f32(value * 255.0) + 0.5))

    if saturation == 0.0:
        v = byte(brightness)
        return (v << 16 | v << 8 | v) & 0xFFFFFF
    h = f32(f32(hue - math.floor(hue)) * 6.0)
    f = f32(h - math.floor(h))
    p = f32(brightness * f32(1.0 - saturation))
    q = f32(brightness * f32(1.0 - f32(saturation * f)))
    t = f32(brightness * f32(1.0 - f32(saturation * f32(1.0 - f))))
    r, g, b = ((brightness, t, p), (q, brightness, p), (p, brightness, t),
               (p, q, brightness), (t, p, brightness), (brightness, p, q))[int(h)] if 0 <= int(h) <= 5 else (0, 0, 0)
    return (byte(r) << 16 | byte(g) << 8 | byte(b)) & 0xFFFFFF


def isGreen(rgb):
    """FoodColors.isGreen：色相在 0.2 到 0.47 之间（不含）。菜叶 + 碎条，而不是币 + 小块。"""
    hue = rgbToHsb(rgb >> 16 & 0xFF, rgb >> 8 & 0xFF, rgb & 0xFF)[0]
    return GREEN_FROM < hue < GREEN_TO


def lighter(rgb, amount):
    """FoodColors.lighter：rgb 朝白色走 amount（0..1），逐通道四舍五入；浮油用 FAT_LIGHT。"""
    amount, result = f32(amount), 0
    for shift in (0, 8, 16):
        value = rgb >> shift & 0xFF
        result |= roundInt(f32(value + f32((255 - value) * amount))) << shift
    return result


def blend(start, end, amount):
    """PotBehavior.blend：ARGB 的 start 朝 end 走 amount，逐通道（含 alpha）四舍五入；返回 0xAARRGGBB（无符号）。"""
    amount, result = f32(amount), 0
    for shift in (0, 8, 16, 24):
        a, b = start >> shift & 0xFF, end >> shift & 0xFF
        result |= roundInt(f32(a + f32(amount * f32(b - a)))) << shift
    return result


def mix(colors):
    """FoodColors.mix：几个 0xRRGGBB 取平均（逐通道整数除），没有就是 FALLBACK。"""
    if not colors:
        return FALLBACK
    red = sum(c >> 16 & 0xFF for c in colors) // len(colors)
    green = sum(c >> 8 & 0xFF for c in colors) // len(colors)
    blue = sum(c & 0xFF for c in colors) // len(colors)
    return red << 16 | green << 8 | blue


def coloursOf(pixels):
    """图标上看得见的像素的颜色集合（FoodColors.colours）：{(r, g, b)}。"""
    return set((p[0], p[1], p[2]) for p in pixels if p[3] >= SOLID)


def sampleMain(pixels, width, height, rows=1.0, leftOut=()):
    """FoodColors.sampleMain：图标主要是什么色（色相直方图里最大的一族，提亮一点），0xRRGGBB。

    只看上面 rows（0..1）那部分行；颜色在 leftOut（{(r, g, b)}）里的像素不算（容器自己的颜色）；亮度低于 0.3 的描边不算；
    像素按 1 + round(饱和度 * 4) 加权，红色跨着色相环两头，最后一份并进第一份；最大的一族（并列取靠前的）取平均，
    再把饱和度乘 1.3（至少 0.38）、亮度乘 1.2（至少 0.72），灰的（饱和度 < 0.14）换成暖色相 0.1；读不出来是 FALLBACK。
    """
    families = [[0, 0, 0, 0] for _ in range(HUES)]
    limit = f32(height * f32(rows))
    for y in range(height):
        if not y < limit:
            break
        for x in range(width):
            r, g, b, a = pixels[y * width + x][:4]
            if a < SOLID or (r, g, b) in leftOut:
                continue
            hue, saturation, brightness = rgbToHsb(r, g, b)
            if brightness < OUTLINE:
                continue
            weight = 1 + roundInt(f32(saturation * 4.0))
            slot = min(HUES - 1, int(f32(hue * HUES)))
            family = families[0 if slot == HUES - 1 else slot]
            family[0] += r * weight
            family[1] += g * weight
            family[2] += b * weight
            family[3] += weight
    best = families[0]
    for family in families:
        best = family if family[3] > best[3] else best
    if best[3] == 0:
        return FALLBACK
    hue, saturation, brightness = rgbToHsb(best[0] // best[3], best[1] // best[3], best[2] // best[3])
    hue = WARM_HUE if saturation < GREY else hue
    saturation = max(MIN_SATURATION, min(1.0, f32(saturation * f32(1.3))))
    brightness = max(MIN_BRIGHTNESS, min(1.0, f32(brightness * f32(1.2))))
    return hsbToRgb(hue, saturation, brightness)


def brothOf(pixels, width, height, container=None):
    """FoodColors.broth：一道汤 / 菜的汤色。container 是它盛在里面的容器的图标 (pixels, width, height)，没有就是 None。

    容器自己的颜色要去掉（碗的木色会把每碗汤染棕，瓶子的玻璃把每杯饮料染蓝）：没有容器 -> 整个图标；容器的颜色一个都没画在菜上
    -> 只看上面 60% 的行（碗里的东西露在图标上半）；画了 -> 整个图标但去掉容器的颜色。
    """
    colours = coloursOf(container[0]) if container else set()
    if not colours or not any((p[0], p[1], p[2]) in colours for p in pixels if p[3] >= SOLID):
        return sampleMain(pixels, width, height, 1.0 if not colours else BOWL_TOP)
    return sampleMain(pixels, width, height, 1.0, colours)


def _hashOrder(calls):
    """java.util.HashMap<Integer, ?> 遍历的先后（calls：每次 merge 调用的键，按调用先后，重复的也算）：复现 Stream.max 在票数并列时取谁。

    照 HashMap.merge 的写法：新结点放在桶的最前面（不是 put 的接在最后）；扩容在每次调用一开头——已有数超过 0.75 的装载就先扩一倍
    （所以键数刚到 13 之后只要还有一次 merge 就已经是 32 个桶了）；桶里已有 7 个再放第 8 个时表还不到 64 就再扩一倍（treeifyBin）；
    扩容时桶里的先后不变。
    """
    capacity, size, present = 16, 0, set()
    table = [[] for _ in range(capacity)]

    def grow(table, capacity):
        capacity *= 2
        moved = [[] for _ in range(capacity)]
        for bucket in table:
            for key in bucket:
                m = key & 0xFFFFFFFF
                moved[(m ^ (m >> 16)) & (capacity - 1)].append(key)
        return moved, capacity

    for key in calls:
        if size > capacity * 3 // 4:
            table, capacity = grow(table, capacity)
        if key in present:
            continue
        h = key & 0xFFFFFFFF
        bucket = table[(h ^ (h >> 16)) & (capacity - 1)]
        crowded = len(bucket) >= 7
        bucket.insert(0, key)
        present.add(key)
        size += 1
        if crowded and capacity < 64:
            table, capacity = grow(table, capacity)
    return [key for bucket in table for key in bucket]


def liquidAt(full, empty=None):
    """ItemVoxels.contents：满的容器图标上"装的是什么"那一个像素的 (列, 行)。

    full / empty 是 (pixels, width, height)，empty 是空容器的图标或 None。数看得见的像素里和空容器不一样的（大小不同、空容器那里是透明的、
    或颜色不同，颜色连 alpha 一起比），按颜色（0xAARRGGBB）计票，票最多的那种取它第一次出现的位置；票数并列时取 Java 的 HashMap（merge 的放法）
    遍历里靠前的；一个不一样的都没有就取图标正中（宽 // 2, 高 // 2）。
    """
    pixels, width, height = full
    counts, where, calls = {}, {}, []
    for row in range(height):
        for column in range(width):
            r, g, b, a = pixels[row * width + column][:4]
            if a < SOLID:
                continue
            same = (empty is not None and empty[1] == width and empty[2] == height
                    and tuple(empty[0][row * width + column][:4]) == (r, g, b, a) and a >= SOLID)
            if same:
                continue
            key = a << 24 | r << 16 | g << 8 | b
            calls.append(key)
            counts[key] = counts.get(key, 0) + 1
            where.setdefault(key, (column, row))
    best = None
    for key in _hashOrder(calls):
        if best is None or counts[key] > counts[best]:
            best = key
    return where[best] if best is not None else (width // 2, height // 2)


def liquidColor(full, empty=None):
    """倒进锅里的液体是什么颜色（KitchenLooks.liquidColor，去掉 alpha）：liquidAt 找到的那个像素的 0xRRGGBB。"""
    column, row = liquidAt(full, empty)
    pixel = full[0][row * full[1] + column]
    return pixel[0] << 16 | pixel[1] << 8 | pixel[2]
