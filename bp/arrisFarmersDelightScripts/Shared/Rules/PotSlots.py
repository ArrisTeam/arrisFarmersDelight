# -*- coding: utf-8 -*-
"""PotSlots - 厨锅配方的"格子"：每格收什么、锅里的料能不能一件对一格配上、一种料占几格、按格子展开成写法（双端，纯规则）

配方表一行的 "Slots"（Shared/Data/CookingPotRecipes.py）是每格能放的选项列表，一格可以并列几个选项：
    "ns:name"          这个物品（aux 0）
    ("ns:name", aux)   这个物品、这个 aux
    "#ns:tag"          带这个物品标签的任何物品（标签没有 aux：哪个 aux 都算）
JE 的厨锅就是这么认的（CookingPotRecipe.matches：RecipeMatcher.findMatches，锅里每个非空格算一件，和配料一一配对）。
这里的函数都不碰标签本身：hasTag(物品名, 标签) / membersOf(标签) 由调用的人给（Shared/Rules/CookingPot.py 交 ItemTags 的），离线可测。
"""
import itertools

from .TableWire import isInt as _isInt      # py2 的 long 也算整数（引擎给的 aux 可能是 long），bool 不算

TAG_MARK = "#"
MOST_SLOTS = 6          # 厨锅只有 6 个食材格

try:
    _TEXT = (str, unicode)  # noqa: F821 - py2
except NameError:
    _TEXT = (str,)


def parseOption(option):
    """一个选项 -> ("item", (物品名, aux)) / ("tag", 标签名)；写法不对是 None。"""
    if isinstance(option, _TEXT):
        if option.startswith(TAG_MARK):
            tag = option[len(TAG_MARK):]
            return ("tag", tag) if ":" in tag and " " not in tag else None
        return ("item", (option, 0)) if ":" in option and " " not in option else None
    if isinstance(option, (tuple, list)) and len(option) == 2 and isinstance(option[0], _TEXT) and _isInt(option[1]):
        name = option[0]
        if ":" in name and not name.startswith(TAG_MARK) and " " not in name and option[1] >= 0:
            return "item", (name, option[1])
    return None


def slotsProblem(slots):
    """格子的写法哪里不对（给登记接口报错用）；对的是 None。"""
    if not isinstance(slots, (list, tuple)) or not slots:
        return "slots 要是 1 到 %d 格的列表" % MOST_SLOTS
    if len(slots) > MOST_SLOTS:
        return "最多 %d 格，给了 %d 格" % (MOST_SLOTS, len(slots))
    for index, slot in enumerate(slots):
        if not isinstance(slot, (list, tuple)) or not slot:
            return "第 %d 格要是至少一个选项的列表" % (index + 1)
        for option in slot:
            if parseOption(option) is None:
                return "第 %d 格的选项 %r 写法不对（物品名 ns:name、(物品名, aux) 或 #标签名）" % (index + 1, option)
    return None


def isValid(slots):
    return slotsProblem(slots) is None


def tagsIn(slots):
    """格子里用到的全部标签名。"""
    found = set()
    for slot in slots:
        for option in slot:
            parsed = parseOption(option)
            if parsed is not None and parsed[0] == "tag":
                found.add(parsed[1])
    return found


def itemsIn(slots):
    """格子里直接写着的全部物品 (物品名, aux)。"""
    found = set()
    for slot in slots:
        for option in slot:
            parsed = parseOption(option)
            if parsed is not None and parsed[0] == "item":
                found.add(parsed[1])
    return found


def accepts(slot, kind, hasTag):
    """这一格收不收 kind（(物品名, aux)）。"""
    for option in slot:
        parsed = parseOption(option)
        if parsed is None:
            continue
        if parsed[0] == "item":
            if parsed[1] == (kind[0], kind[1]):
                return True
        elif hasTag(kind[0], parsed[1]):
            return True
    return False


def _match(slots, items, hasTag):
    """items（一件一个 (物品名, aux)）和格子一一配上了没有：二分图完美匹配（增广路，最多 6 x 6）。"""
    if len(items) != len(slots):
        return False
    takes = [[accepts(slot, item, hasTag) for slot in slots] for item in items]
    holder = [-1] * len(slots)

    def give(item, seen):
        for slot in range(len(slots)):
            if takes[item][slot] and not seen[slot]:
                seen[slot] = True
                if holder[slot] < 0 or give(holder[slot], seen):
                    holder[slot] = item
                    return True
        return False

    return all(give(item, [False] * len(slots)) for item in range(len(items)))


def fits(slots, items, hasTag):
    """锅里的料（一个非空格算一件，items 是 (物品名, aux) 的序列）配不配得上这些格子。"""
    return _match(slots, list(items), hasTag)


def _splits(total, parts):
    """total 拆成 parts 个正整数的全部拆法，按字典序（第一个数从小到大）。"""
    if parts == 1:
        yield (total,)
        return
    for first in range(1, total - parts + 2):
        for rest in _splits(total - first, parts - 1):
            yield (first,) + rest


def partsOf(slots, kinds, hasTag):
    """kinds（几种互不相同的 (物品名, aux)，顺序就是结果里种类的先后）摆进这些格子、每种至少占一格、格子正好用完的全部摆法：
    [{种类: 占几格}, ...]，按拆法的字典序。HoD 的 StationRecipes.parts / assign 只留出份最多的一种，这里全给，由 PotLayout.choose 照 HoD 的次序挑。"""
    kinds = list(kinds)
    if not kinds or len(kinds) > len(slots):
        return []
    if not all(any(accepts(slot, kind, hasTag) for slot in slots) for kind in kinds):
        return []
    found = []
    for split in _splits(len(slots), len(kinds)):
        items = [kind for kind, count in zip(kinds, split) for _ in range(count)]
        if _match(slots, items, hasTag):
            found.append(dict(zip(kinds, split)))
    return found


def optionsOf(slot, membersOf):
    """这一格能放的具体物品 [(物品名, aux)]：标签换成 membersOf(标签) 的成员（aux 0），按写的先后，去重。"""
    found, seen = [], set()
    for option in slot:
        parsed = parseOption(option)
        if parsed is None:
            continue
        kinds = [parsed[1]] if parsed[0] == "item" else [(name, 0) for name in membersOf(parsed[1]) or ()]
        for kind in kinds:
            if kind not in seen:
                seen.add(kind)
                found.append(kind)
    return found


def _unique(choices, cap):
    """格子一格一格的候选 -> 写法 [[(物品名, aux), ...], ...]：最后一格变得最快（和配方表的 _ways 同一个次序），排好序后一样的只留第一种，最多 cap 种。"""
    ways, seen = [], set()
    for way in itertools.product(*choices):
        key = tuple(sorted(way))
        if key in seen:
            continue
        seen.add(key)
        ways.append(list(way))
        if len(ways) >= cap:
            break
    return ways


def expand(slots, membersOf, cap):
    """按格子展开成写法（新接口登记的配方的 Recipe 快照、只认物品的旧读者看它）：某格一个成员都没有时是 []。"""
    return _unique([optionsOf(slot, membersOf) for slot in slots], cap)


def concretize(slots, available, hasTag, cap):
    """手头有的种类（available：(物品名, aux) 的序列，按先后）能凑出的写法：每格从 available 里挑它收的，最多 cap 种。"""
    kinds = []
    for kind in available:
        if kind is not None and (kind[0], kind[1]) not in kinds:
            kinds.append((kind[0], kind[1]))
    return _unique([[kind for kind in kinds if accepts(slot, kind, hasTag)] for slot in slots], cap)
