# -*- coding: utf-8 -*-
"""
标准库：原版的物品操作（docs/ARCHITECTURE.md 第 3.5 节；行为契约见 docs/DESIGN.md 第 4 节），照原版容器界面的行为写。
纯逻辑，两端共用：服务端按它改真实状态，客户端用它预测。只用公开接口（Common/Rules 的工作副本与工具、Common/Ops、
Common/Schema）写成。

键鼠与手柄用"手持物"模型（拿到指针上再放下）；触屏用"选中格"模型（选中的东西留在原格，点目标时才搬），
触屏的操作是 move / distribute / gatherToSlot / drop，不经过手持物。
收纳袋的装入、取出、两袋之间转移是单独的操作（bundleInsert / bundleExtract / bundleTransfer），
从算出的格子拿走产物是 craft；什么手势对应哪个操作由客户端照原版判断；收纳袋内容的写法与重量见 Bundles。

后半部分把它们登记成操作（线上格式、涉及的格子、客户端表现），由 Std/Defaults.py 在两端启动时导入：
    click   {"ref": 格, "btn": 0|1}                左键 / 右键（手柄 A / X）
    take    {"ref": 格, "n": 数量}                 按住后的渐进拿取
    quick   {"ref": 格}                            快速转移
    quickN  {"ref": 格, "n": 数量}                 快速转移几个（触屏点按熔炉的产物格：转一个）
    gatherK {"ref": 格}                            双击收集到手持物
    gatherS {"ref": 格}                            触屏双击收集到选中格
    spread  {"src": 格, "n": 数量|None, "to": [格...], "mode": 0|1}   拖动分配
    drop    {"ref": 格, "n": 数量}                 丢出（格子或手持物）
    move    {"src": 格, "dst": 格, "n": 数量|None}  触屏：选中格搬到目标格
    hotbar  {"ref": 格, "key": 0-8}                悬停时按快捷栏键位
    bundleIn   {"src": 格, "bag": 格, "n": 数量|None}   把 src 的东西放进 bag 处的收纳袋
    bundleOut  {"bag": 格, "i": 项|None, "dst": 格}     从收纳袋取出一项（None 为最上面一项）放到 dst
    bundleMove {"bag": 格, "i": 项, "dst": 格}          触屏：收纳袋里选中的一项放进 dst 处的另一个收纳袋
    craft   {"ref": 算出的格, "mode": 0-3, "key": 0-8}  从产物格合成（方式见 craft；key 只在放进快捷栏时用）
"""
from ..Common import Bundles, Items, Ops, Rules, Schema
from ..Common.Collections import COMBINED, CURSOR_ITEMS, CURSOR_REF, HOTBAR, HOTBAR_SIZE
from ..Common.Rules import EVEN, ONE, PRIMARY
from ..Common.Slots import MOUSE, TOUCH

MAX_SPREAD_TARGETS = 512
MAX_BUNDLE_INDEX = 255

CRAFT_CURSOR = 0   # 左键、右键、手柄 X：合成一次到手上
CRAFT_ONE = 1      # 触屏点按、手柄 A：合成一次，放进背包
CRAFT_ALL = 2      # Shift 点击、手柄 Y：合成尽量多，放进背包
CRAFT_HOTBAR = 3   # 悬停时按快捷栏键位（手上空着）：合成一次，放进快捷栏的那一格
CRAFT_MODES = (CRAFT_CURSOR, CRAFT_ONE, CRAFT_ALL, CRAFT_HOTBAR)
MAX_CRAFTS = 256   # 一次"合成尽量多"最多合成几次（网格里每格最多一组，到不了这么多）

NO_REMOVE = "notification.lock.noRemove"
NO_DROP = "notification.lock.noDrop"


# ---------------------------------------------------------------- 键鼠与手柄（手持物模型）


def _taking(ws, stack, button):
    """
    从一格拿到手上的个数：左键整堆、右键一半（向上取整）。超堆叠的格子先截成手上放得下的一组（原版的堆叠数），
    再按这一组算一半。
    """
    whole = min(Items.count(stack), ws.limit(CURSOR_REF, stack))
    return whole if button == PRIMARY else (whole + 1) // 2


def oneStack(ws, stack):
    """stack 里一次拿得动的一组：原版的堆叠数（超堆叠的格子里拿到手上、Shift 点击、丢出整堆都先截成这么多）。"""
    return min(Items.count(stack), ws.rules.maxStack(stack))


def click(ws, ref, button):
    """
    单击格子：左键拿起整堆 / 放下整堆，右键拿起一半 / 放下一个（超堆叠的格子拿起时先截成一组）。
    放不进手上那种东西的格子（熔炉的产物格这类），照原版：格子里是同种时把它加到手上（左键整堆、右键一半，
    以手上放得下的为限），别的情形什么都不做（不交换）。
    """
    cursor, target = ws.get(CURSOR_REF), ws.get(ref)
    if Items.isEmpty(cursor):
        if Items.isEmpty(target):
            return False
        return Rules.transfer(ws, ref, CURSOR_REF, _taking(ws, target, button)) > 0
    if not ws.canPlace(ref, cursor):
        if Items.isEmpty(target) or not ws.rules.canStack(cursor, target):
            return False
        return Rules.transfer(ws, ref, CURSOR_REF, _taking(ws, target, button)) > 0
    if button == PRIMARY:
        return Rules.placeAll(ws, CURSOR_REF, ref)
    if Items.isEmpty(target) or (ws.rules.canStack(target, cursor) and ws.room(ref, cursor) > 0):
        return Rules.transfer(ws, CURSOR_REF, ref, 1) > 0
    return Rules.swap(ws, CURSOR_REF, ref)


def takeAmount(ws, ref, amount):
    """按住后的渐进拿取：从 ref 拿 amount 个到空的手持物上。"""
    stack = ws.get(ref)
    if not Items.isEmpty(ws.get(CURSOR_REF)) or Items.isEmpty(stack):
        return False
    if not 1 <= amount <= Items.count(stack):
        raise Rules.RuleError("bad_amount")
    return Rules.transfer(ws, ref, CURSOR_REF, amount) > 0


def gatherToCursor(ws, ref, profile):
    """
    双击：第一下拿空了 ref，第二下把同种的东西收到手持物上。
    什么都没收到（包括手持物已经满了）就把手持物放回 ref 再快速转移。
    """
    _checkCoalesce(ws, ref)
    cursor = ws.get(CURSOR_REF)
    if Items.isEmpty(cursor) or not Items.isEmpty(ws.get(ref)):
        return False
    if _gather(ws, CURSOR_REF, ws.structure.gatherOrder(ref[0], profile)):
        return True
    if not Rules.placeAll(ws, CURSOR_REF, ref):
        return False
    quickMove(ws, ref, profile)
    return True


def hotbarKey(ws, hovered, key):
    """悬停时按快捷栏键位（key 为 0–8）：与快捷栏第 key 格按"放下整堆"的规矩互换。"""
    if not 0 <= key < HOTBAR_SIZE:
        raise Rules.RuleError("bad_hotbar_key")
    hotbar = (HOTBAR, key)
    if ws.same(hovered, hotbar):
        return False
    carried, item = ws.get(CURSOR_REF), ws.get(hovered)
    if Items.isEmpty(carried):
        if not Items.isEmpty(item):
            return Rules.placeAll(ws, hovered, hotbar)
        return Rules.placeAll(ws, hotbar, hovered)
    return Rules.placeAll(ws, CURSOR_REF, hotbar if not Items.isEmpty(item) else hovered)


# ---------------------------------------------------------------- 各种输入共用


def quickMove(ws, ref, profile, amount=None):
    """
    Shift 点击 / 手柄 Y / 双击兜底 / 种类存储的转出：先问界面模型（Menu.quickMove 与部件的，改写了的才问），给了结果就照它；
    没给时照去向表（routeQuickMove）。
    """
    menu = ws.menu
    if menu is not None and menu.hooksFor("quickMove"):
        if ref[0] == CURSOR_ITEMS:
            raise Rules.RuleError("bad_ref")
        result = menu.quickMoveAll(ws, ref, profile, amount)
        if result is not None:
            return bool(result)
    return routeQuickMove(ws, ref, profile, amount)


def routeQuickMove(ws, ref, profile, amount=None):
    """
    照去向表的快速转移（缺省的 Shift 点击）：整堆（超堆叠的格子先截成一组；amount 给出时只转这么多个）按界面模型的去向表
    转到另一侧，放不下的留在原格。
    每个目标集合先补同种堆、再填空格；带"进了就停"的目标在补完同种堆后、填完空格后各看一次，
    到这时已经放进去了东西就不再往后试（熔炉：燃料能进燃料格就不进原料格）。
    触屏点按熔炉的产物格是转一个（原版的"自动放置一个"）。目标的格子类型可以自己定怎么收（SlotType.quickInto：种类存储
    按种类并进去，幽灵格放一份副本、原格不动，能删东西的来源格——原版创造布局的快捷栏——把这一堆删掉）。
    """
    if ref[0] == CURSOR_ITEMS:
        raise Rules.RuleError("bad_ref")
    stack = ws.get(ref)
    if Items.isEmpty(stack) or not ws.canLeave(ref, stack):
        return False
    if amount is not None and amount < 1:
        raise Rules.RuleError("bad_amount")
    total = remaining = oneStack(ws, stack) if amount is None else min(amount, Items.count(stack))
    for name, stop in ws.structure.quickTargets(ref[0], profile):
        left = ws.structure.get(name).slot.quickInto(ws, name, ref, remaining)
        if left is not None:
            remaining = left
            if remaining <= 0 or (stop and remaining < total):
                break
            continue
        remaining = Rules.topUp(ws, name, ref, remaining, exclude=ref)
        if remaining <= 0 or (stop and remaining < total):
            break
        remaining = Rules.fillEmpty(ws, name, ref, remaining, exclude=ref)
        if remaining <= 0 or (stop and remaining < total):
            break
    return remaining < total


def distribute(ws, source, amount, targets, mode):
    """
    拖动分配。source 是手持物（键鼠、手柄）或选中格（触屏），amount 是拿来分的个数（None 为全部，超堆叠的格子先截成一组）。
    targets 是拖过的格子，按经过的先后排列。

    平均分配：逐格判断能否加入（空格或同种未满、放得进去、东西还够每格至少一个），
    最后每格加 max(总数 // 格数, 1) 个（以空间为限），余下的回到 source。
    每格一个：按顺序给能放的格子各一个，直到分完。
    """
    stack = ws.get(source)
    if Items.isEmpty(stack):
        return False
    total = Items.count(stack)
    pool = oneStack(ws, stack) if amount is None else amount
    if not 1 <= pool <= total:
        raise Rules.RuleError("bad_amount")
    if not ws.canLeave(source, stack):
        return False
    template = Items.withCount(stack, 1)
    ws.set(source, Items.withCount(stack, total - pool))
    visited, keys = [], set()

    def eligible(ref):
        if ws.collection(ref) is None:
            return False
        # 经过的格子最后都会分到东西，所以集合可显示的格数按"它们都已放了东西"来算：格数随内容长的集合拖进末尾空格后
        # 新长出的格子也能继续拖进去，与边拖边放的原版一致（有格数的集合不受影响）
        top = max([-1] + [index for name, index in visited if name == ref[0]])
        if ref[1] >= ws.size(ref[0], top) or not ws.canPlace(ref, template, checkExists=False):
            return False
        return ws.space(ref, template) > 0

    for ref in targets:
        key = ws.key(ref)
        if key is None or key in keys or ref == CURSOR_REF or not eligible(ref):
            continue
        if mode == ONE:
            if pool <= 0:
                break
            visited.append(ref)
            keys.add(key)
            pool -= _put(ws, ref, template, 1)
            continue
        size = len(visited) + 1
        share = max(pool // size, 1)
        if pool <= (size - 1) * share:
            continue
        visited.append(ref)
        keys.add(key)
    if mode == EVEN and visited:
        share = max(pool // len(visited), 1)
        for ref in visited:
            pool -= _put(ws, ref, template, min(share, pool))
    if pool > 0:
        _put(ws, source, template, pool, force=True)
    return bool(visited)


def _put(ws, ref, template, amount, force=False):
    """往 ref 里加 amount 个 template 那种东西（ref 为空或同种）。force 用于退回 source，不看空间。"""
    if amount <= 0:
        return 0
    target = ws.get(ref)
    room = amount if force else ws.room(ref, template)
    put = min(amount, room)
    if put <= 0:
        return 0
    base = 0 if Items.isEmpty(target) else Items.count(target)
    ws.set(ref, Items.withCount(template if Items.isEmpty(target) else target, base + put))
    return put


def drop(ws, ref, amount):
    """丢出 ref（格子或手持物）里的 amount 个。"""
    stack = ws.get(ref)
    if Items.isEmpty(stack):
        return False
    if not 1 <= amount <= Items.count(stack):
        raise Rules.RuleError("bad_amount")
    if not ws.state.canDrop(stack) or not ws.canLeave(ref, stack):
        return False
    ws.set(ref, Items.withCount(stack, Items.count(stack) - amount))
    ws.drops.append(Items.withCount(stack, amount))
    return True


# ---------------------------------------------------------------- 触屏（选中格模型）


def move(ws, src, dst, amount):
    """
    选中 src 后点 dst：dst 空则搬 amount 个（None 为整堆）；同种则合并能放下的部分，满了就整堆交换；
    不同种整堆交换（这时 amount 不起作用）。
    """
    if CURSOR_ITEMS in (src[0], dst[0]) or ws.same(src, dst):
        raise Rules.RuleError("bad_ref")
    stack, target = ws.get(src), ws.get(dst)
    if Items.isEmpty(stack):
        return False
    total = Items.count(stack)
    amount = total if amount is None else amount
    if not 1 <= amount <= total:
        raise Rules.RuleError("bad_amount")
    if Items.isEmpty(target) or (ws.rules.canStack(target, stack) and ws.room(dst, stack) > 0):
        return Rules.transfer(ws, src, dst, amount) > 0
    return Rules.swap(ws, src, dst)


def gatherToSlot(ws, ref, profile):
    """触屏双击选中格：把同种的东西收进这一格；什么都没收到就快速转移这一格。"""
    if ref[0] == CURSOR_ITEMS:
        raise Rules.RuleError("bad_ref")
    _checkCoalesce(ws, ref)
    if Items.isEmpty(ws.get(ref)):
        return False
    if _gather(ws, ref, ws.structure.gatherOrder(ref[0], profile)):
        return True
    return quickMove(ws, ref, profile)


def _checkCoalesce(ws, ref):
    """双击收集只对收集同类的格子（格子类型的 coalesce；原版物品栏的盔甲格、副手格不收，客户端不会发）。"""
    collection = ws.structure.get(ref[0])
    if collection is not None and not collection.slot.coalesce:
        raise Rules.RuleError("no_coalesce")


def _gather(ws, dst, order):
    """把 order 各集合里与 dst 同种的东西收进 dst：先收零散的、再收满堆的，各集合都从下标大的往小收。"""
    template = ws.get(dst)
    if Items.isEmpty(template):
        return False
    gathered = False
    target = ws.key(dst)
    for wantFull in (False, True):
        for name in order:
            for index in reversed(range(ws.size(name))):
                available = ws.room(dst, template)
                if available <= 0:
                    return gathered
                ref = (name, index)
                if ws.key(ref) == target:
                    continue
                item = ws.get(ref)
                if Items.isEmpty(item) or not ws.rules.canStack(template, item):
                    continue
                if (Items.count(item) >= ws.rules.maxStack(item)) != wantFull:
                    continue
                if Rules.transfer(ws, ref, dst, available) > 0:
                    gathered = True
    return gathered


# ---------------------------------------------------------------- 收纳袋


def _entryStackable(a, b, rules):
    return rules.canStack(Bundles.entryItem(a), Bundles.entryItem(b)) and Bundles.entryExtras(a) == Bundles.entryExtras(b)


def _consolidate(items, rules):
    """
    原版往收纳袋里放东西前先整理一遍：能叠放的几堆从下往上并到最早的那一堆（满了换下一堆接着并），再把空位排紧。
    """
    items = list(items)
    groups = []
    for index, entry in enumerate(items):
        for group in groups:
            if _entryStackable(group[0], entry, rules):
                group[1].append(index)
                break
        else:
            groups.append((entry, [index]))
    for _, indexes in groups:
        target = indexes[0]
        for index in indexes[1:]:
            destination, source = items[target], items[index]
            largest = rules.maxStack(Bundles.entryItem(destination))
            have, give = Bundles.entryItem(destination)["count"], Bundles.entryItem(source)["count"]
            if have >= largest:
                target = index
                continue
            moved = min(largest - have, give)
            items[target] = Bundles.entryWithCount(destination, have + moved)
            items[index] = Bundles.entryWithCount(source, give - moved)
            if largest - have - give < 0:
                target = index
    return [entry for entry in items if entry is not None]


def _insertInto(ws, bundleRef, stack, amount, whole=False):
    """
    把 stack 里的东西（amount 个，None 为整堆）放进 bundleRef 处的收纳袋，改好收纳袋，返回放进去了几个（放不进为 0）。照原版：
    锁定的物品、规格不收的（原版：潜影盒）、收纳袋所在的格子不收的都放不进；收纳袋只能整个放进别的收纳袋
    （还要对方允许套袋、重量放得下）；普通物品按剩余重量能放几个放几个，先并进第一堆没满的同种（并完挪到最上面），
    没有就放在最上面一项。whole 为真时只放整堆：放不完就一个都不放（产物做进收纳袋用）。
    """
    bundle = ws.get(bundleRef)
    spec = Bundles.specOf(bundle)
    if spec is None or Items.isEmpty(stack) or Items.lockMode(stack) != Items.LOCK_NONE or not spec.admits(stack):
        return 0
    if not ws.canPlace(bundleRef, stack, checkExists=False):
        return 0
    rules = ws.rules
    items = _consolidate(Bundles.entries(bundle), rules)
    remaining = spec.weightLimit - sum(Bundles.weightOf(Bundles.entryItem(entry), rules) for entry in items)
    if remaining <= 0:
        return 0
    inner = Bundles.specOf(stack)
    if inner is not None:
        if not spec.allowNested or inner.ownWeight <= 0 or Bundles.weightOf(stack, rules) > remaining \
                or len(items) >= spec.maxSlots:
            return 0
        items.append(Bundles.makeEntry(stack))
        ws.set(bundleRef, Bundles.withEntries(bundle, items))
        return Items.count(stack)
    each = Bundles.perItemWeight(stack, rules)
    if each <= 0:
        return 0
    wanted = Items.count(stack) if amount is None else amount
    moved = min(wanted, remaining // each)
    if moved <= 0 or (whole and moved < wanted):
        return 0
    incoming = Bundles.makeEntry(stack)
    for index, entry in enumerate(items):
        if not _entryStackable(entry, incoming, rules):
            continue
        have = Bundles.entryItem(entry)["count"]
        room = rules.maxStack(stack) - have
        if room <= 0:
            continue
        moved = min(moved, room)
        if whole and moved < wanted:
            return 0
        del items[index]
        items.append(Bundles.entryWithCount(entry, have + moved))
        break
    else:
        if len(items) >= spec.maxSlots:
            return 0
        items.append(Bundles.entryWithCount(incoming, moved))
    ws.set(bundleRef, Bundles.withEntries(bundle, items))
    return moved


def bundleInsert(ws, src, bundleRef, amount=None):
    """
    把 src 的东西放进 bundleRef 处的收纳袋（键鼠：手上拿着收纳袋左键点一格，或手上拿着东西左键点收纳袋；
    触屏：选中一格后点收纳袋，或收纳袋展开时点一格）。amount 为触屏选好的数量，None 为整堆。放不下的留在原处。
    """
    if ws.same(src, bundleRef):
        raise Rules.RuleError("bad_ref")
    stack = ws.get(src)
    if amount is not None and not 1 <= amount <= Items.count(stack):
        raise Rules.RuleError("bad_amount")
    if Items.isEmpty(stack) or not ws.canLeave(src, stack):
        return False
    moved = _insertInto(ws, bundleRef, stack, amount)
    if moved <= 0:
        return False
    ws.set(src, Items.withCount(stack, Items.count(stack) - moved))
    return True


def bundleExtract(ws, bundleRef, index, dst):
    """
    从 bundleRef 处的收纳袋取出一项放到 dst。index 为 None 时取最上面一项（只能放进空格）；
    指定 index（在提示里选中的那一项）时，dst 空就整项放过去，dst 是同种还没满就并上去（放不下的留在袋里），
    并完的空位由上面的项依次补上。
    """
    if ws.same(dst, bundleRef):
        raise Rules.RuleError("bad_ref")
    bundle = ws.get(bundleRef)
    items = Bundles.entries(bundle)
    if Bundles.specOf(bundle) is None or not items:
        return False
    top = index is None
    index = len(items) - 1 if top else index
    if not 0 <= index < len(items):
        raise Rules.RuleError("bad_index")
    item = Bundles.entryItem(items[index])
    target = ws.get(dst)
    if not ws.canPlace(dst, item):
        return False
    rules = ws.rules
    if Items.isEmpty(target):
        moved = min(ws.limit(dst, item), Items.count(item))
        ws.set(dst, Items.withCount(item, moved))
        left = Items.count(item) - moved
    else:
        if top or target.get("newItemName") != item.get("newItemName") or Bundles.entryExtras(items[index]) \
                or not rules.canStack(target, item):
            return False
        moved = min(ws.space(dst, item), Items.count(item))
        if moved <= 0:
            return False
        ws.set(dst, Items.withCount(target, Items.count(target) + moved))
        left = Items.count(item) - moved
    items = list(items)
    if left > 0:
        items[index] = Bundles.entryWithCount(items[index], left)
    else:
        del items[index]
    ws.set(bundleRef, Bundles.withEntries(bundle, items))
    return True


def bundleTransfer(ws, srcBundle, index, dstBundle):
    """触屏：展开的收纳袋里选中一项后点另一个收纳袋，把这一项按放进收纳袋的规矩放过去，放不下的留在原袋。"""
    if ws.same(srcBundle, dstBundle):
        raise Rules.RuleError("bad_ref")
    source = ws.get(srcBundle)
    items = Bundles.entries(source)
    if Bundles.specOf(source) is None or not items:
        return False
    if not 0 <= index < len(items):
        raise Rules.RuleError("bad_index")
    item = Bundles.entryItem(items[index])
    moved = _insertInto(ws, dstBundle, item, None)
    if moved <= 0:
        return False
    items = list(items)
    if moved < Items.count(item):
        items[index] = Bundles.entryWithCount(items[index], Items.count(item) - moved)
    else:
        del items[index]
    ws.set(srcBundle, Bundles.withEntries(source, items))
    return True


# ---------------------------------------------------------------- 合成（算出的格子）


def craft(ws, ref, mode, key=0, profile=None):
    """
    从算出的格子（工作台的产物格）拿走产物，照原版工作台：
    - CRAFT_CURSOR：手上空着就拿到手上；手上是同种、放得下整份产物就叠上；产物格的格子类型 intoBundle 为真（原版工作台、
      切石机）时，手上是收纳袋、整份产物放得进去就合成一次放进收纳袋；手上是别的东西什么都不做（不交换）；
    - CRAFT_ONE：整份产物放得进背包（先补同种、再填空格，快捷栏 0 号起）才合成；
    - CRAFT_ALL：一份一份地合成，直到配方变了（材料用完）或背包放不下；
    - CRAFT_HOTBAR：手上空着、快捷栏第 key 格空着或是同种且放得下整份产物时合成一次放进去。
    "放进背包"的去处：产物格的集合在去向表里（这个界面档）有去处时按它依次放（每个去处先补同种、再填空格，放不下的接着往后放：
    原版物品栏先试盔甲、副手），没有时是合并背包。
    算出这一格的部件提供 match(读格子, 查看者) -> 匹配结果（result()、recipe）与 consume(工作副本, 匹配结果)：
    每合成一次由部件扣材料、放附带产物。返回合成了没有。
    """
    if mode not in CRAFT_MODES or ref[0] not in ws.structure.derivers:
        raise Rules.RuleError("bad_ref")
    if not ws.active(ref[0]):
        return False   # 在关着的面板里
    part = ws.structure.derivers[ref[0]]
    first = part.match(ws.get, ws.viewer)
    if first is None:
        return False
    targets = [name for name, _ in ws.structure.quickTargets(ref[0], profile)] or [COMBINED]
    if mode == CRAFT_ALL:
        crafted = 0
        while crafted < MAX_CRAFTS:
            found = part.match(ws.get, ws.viewer)
            if found is None or found.recipe is not first.recipe:
                break
            result = found.result()
            if not _fitsAll(ws, targets, result):
                break
            _insertAll(ws, targets, result)
            part.consume(ws, found)
            crafted += 1
        return crafted > 0
    result = first.result()
    if mode == CRAFT_CURSOR:
        if not addWhole(ws, CURSOR_REF, result) and not (
                getattr(ws.collection(ref).slot, "intoBundle", False)
                and _insertInto(ws, CURSOR_REF, result, None, whole=True)):
            return False
    elif mode == CRAFT_ONE:
        if not _fitsAll(ws, targets, result):
            return False
        _insertAll(ws, targets, result)
    else:
        if not 0 <= key < HOTBAR_SIZE:
            raise Rules.RuleError("bad_hotbar_key")
        if not Items.isEmpty(ws.get(CURSOR_REF)) or not addWhole(ws, (HOTBAR, key), result):
            return False
    part.consume(ws, first)
    return True


def _fitsAll(ws, names, stack):
    """整份 stack 能不能放进这几个集合（按顺序，每个先补同种、再填空格，放不下的接着往后放）。"""
    amount = Items.count(stack)
    for name in names:
        for index in range(ws.size(name)):
            ref = (name, index)
            if ws.canPlace(ref, stack):
                amount -= ws.space(ref, stack)
                if amount <= 0:
                    return True
    return False


def _insertAll(ws, names, stack):
    """把整份 stack 凭空依次放进这几个集合（先确认放得下）。"""
    left = Items.count(stack)
    for name in names:
        if left <= 0:
            break
        left = Rules.insertInto(ws, name, stack, left)


# ---------------------------------------------------------------- 幽灵格（放副本）


def _ghostSlot(ws, ref):
    collection = ws.collection(ref)
    if collection is None or not collection.slot.copies:
        raise Rules.RuleError("bad_ref")
    return collection.slot


def _setGhost(ws, ref, stack):
    """幽灵格 ref 设成 stack 的一份副本（一个）。格子类型不收、底层状态不收时不改；设成一样的也不算改。"""
    slot = _ghostSlot(ws, ref)
    if not ws.placeable(ref) or not slot.allows(stack, ws.rules):
        return False
    copy = Items.withCount(Items.normalize(stack), 1)
    if not ws.state.accepts(ref, copy):
        return False
    current = ws.get(ref)
    if Items.count(current) == 1 and Items.sameKind(current, copy):
        return False
    ws.set(ref, copy)
    return True


def ghostSet(ws, ref, src):
    """
    幽灵格 ref 设成 src（手持物、触屏选中的格子、快捷栏的一格）那一格东西的一份副本（一个），src 不动；
    src 为 None 或空着时清空 ref。返回改了没有。
    """
    _ghostSlot(ws, ref)
    if src is not None and ws.same(ref, src):
        raise Rules.RuleError("bad_ref")
    stack = ws.get(src) if src is not None else None
    if Items.isEmpty(stack):
        if Items.isEmpty(ws.get(ref)) or not ws.placeable(ref):
            return False
        ws.set(ref, None)
        return True
    return _setGhost(ws, ref, stack)


def ghostQuick(ws, name, stack):
    """
    快速转移到幽灵格的集合 name：放一份副本到第一个能放的空格（原格不动）。格子类型不收重复的（repeats 为假）时，
    集合里已经有同种的就不放。返回放了没有。
    """
    slot = ws.structure.get(name).slot
    free = None
    for index in range(ws.size(name)):
        ref = (name, index)
        current = ws.get(ref)
        if Items.isEmpty(current):
            if free is None and ws.placeable(ref):
                free = ref
        elif not slot.repeats and Items.sameKind(current, stack):
            return False
    return free is not None and _setGhost(ws, free, stack)


# ---------------------------------------------------------------- 来源格（拿走得到新的一份）


def _sourceStack(ws, ref, amount):
    """来源格 ref 里那种东西的 amount 个（一次最多一组；格子空着、停用着为 None）。"""
    collection = ws.collection(ref)
    if collection is None or not getattr(collection.slot, "source", False):
        raise Rules.RuleError("bad_ref")
    stack = ws.get(ref)
    if Items.isEmpty(stack) or not ws.exists(ref) or not ws.active(ref[0]) or not collection.slot.copyable(ws, ref):
        return None, collection.slot
    largest = ws.rules.maxStack(stack)
    if not 1 <= amount <= largest:
        raise Rules.RuleError("bad_amount")
    return Items.withCount(Items.normalize(stack), amount), collection.slot


def copyTo(ws, ref, dst, amount):
    """
    从来源格 ref 凭空拿 amount 个（不超过一组）放进 dst（手持物或格子）：dst 空着就放，同种就加到放满为止；
    dst 是别的东西时，来源格能删东西（trash，创造物品栏）就换掉（原来的删掉），否则不做。返回放了没有。
    """
    if ws.same(ref, dst):
        raise Rules.RuleError("bad_ref")
    stack, slot = _sourceStack(ws, ref, amount)
    if stack is None or not ws.canPlace(dst, stack):
        return False
    target = ws.get(dst)
    if not Items.isEmpty(target) and not ws.rules.canStack(target, stack):
        if not slot.trash or not ws.canLeave(dst, target) or Items.lockMode(target) != Items.LOCK_NONE:
            return False
        target = None
    put = min(amount, ws.limit(dst, stack) if Items.isEmpty(target) else ws.space(dst, stack))
    if put <= 0:
        return False
    ws.set(dst, Items.withCount(stack if Items.isEmpty(target) else target, Items.count(target) + put))
    return True


def copyQuick(ws, ref, amount, profile):
    """从来源格 ref 凭空拿 amount 个按去向表放进另一侧（每个目标先补同种堆、再填空格，进了就停的照常），放不下的不要。"""
    stack, slot = _sourceStack(ws, ref, amount)
    if stack is None:
        return False
    left = amount
    for name, stop in ws.structure.quickTargets(ref[0], profile):
        put = ws.structure.get(name).slot.copyInto(ws, name, stack, left)
        left = Rules.insertInto(ws, name, stack, left) if put is None else put
        if left <= 0 or (stop and left < amount):
            break
    return left < amount


def copyDrop(ws, ref, amount):
    """从来源格 ref 凭空拿 amount 个丢出。"""
    stack, slot = _sourceStack(ws, ref, amount)
    if stack is None or not ws.state.canDrop(stack):
        return False
    ws.drops.append(stack)
    return True


def trash(ws, ref, src, amount):
    """把 src（手持物或触屏选中的格子）里的 amount 个点进能删东西的来源格 ref：删掉。锁定的物品删不掉。"""
    collection = ws.collection(ref)
    if collection is None or not getattr(collection.slot, "trash", False) or ws.same(ref, src):
        raise Rules.RuleError("bad_ref")
    stack = ws.get(src)
    if Items.isEmpty(stack) or not ws.placeable(ref):
        return False
    if not 1 <= amount <= Items.count(stack):
        raise Rules.RuleError("bad_amount")
    if Items.lockMode(stack) != Items.LOCK_NONE or not ws.canLeave(src, stack):
        return False
    ws.set(src, Items.withCount(stack, Items.count(stack) - amount))
    return True


def addWhole(ws, ref, stack):
    """整份 stack 放进 ref（空着，或同种且放得下整份）。放不下时什么都不改，返回 False。"""
    target = ws.get(ref)
    if Items.isEmpty(target):
        if Items.count(stack) > ws.limit(ref, stack):
            return False
        ws.set(ref, stack)
        return True
    if not ws.rules.canStack(target, stack) or ws.space(ref, stack) < Items.count(stack):
        return False
    ws.set(ref, Items.withCount(target, Items.count(target) + Items.count(stack)))
    return True


# ---------------------------------------------------------------- 登记（线上格式、涉及的格子、客户端表现）


def _touch(device):
    return device == TOUCH


@Ops.register("click")
class Click(Ops.Op):
    params = (("ref", Schema.Ref()), ("btn", Schema.Int(0, 1, "bad_button")))

    def involved(self, op):
        return [op[1], CURSOR_REF]

    def apply(self, ws, op, profile):
        return click(ws, op[1], op[2])

    def lockNotice(self, op):
        return NO_REMOVE


@Ops.register("take")
class Take(Ops.Op):
    params = (("ref", Schema.Ref()), ("n", Schema.Amount()))

    def involved(self, op):
        return [op[1], CURSOR_REF]

    def apply(self, ws, op, profile):
        return takeAmount(ws, op[1], op[2])


@Ops.register("quick")
class Quick(Ops.Op):
    params = (("ref", Schema.Ref()),)

    def involved(self, op):
        return [op[1]]

    def apply(self, ws, op, profile):
        return quickMove(ws, op[1], profile)

    def flies(self, op, device, cursorBefore):
        return True


@Ops.register("quickN")
class QuickN(Quick):
    params = (("ref", Schema.Ref()), ("n", Schema.Amount()))

    def apply(self, ws, op, profile):
        return quickMove(ws, op[1], profile, op[2])


@Ops.register("gatherK")
class GatherToCursor(Ops.Op):
    params = (("ref", Schema.Ref()),)

    def involved(self, op):
        return [op[1], CURSOR_REF]

    def apply(self, ws, op, profile):
        return gatherToCursor(ws, op[1], profile)


@Ops.register("gatherS")
class GatherToSlot(Ops.Op):
    params = (("ref", Schema.Ref()),)

    def involved(self, op):
        return [op[1]]

    def apply(self, ws, op, profile):
        return gatherToSlot(ws, op[1], profile)

    def flies(self, op, device, cursorBefore):
        return _touch(device)


@Ops.register("spread")
class Spread(Ops.Op):
    params = (("src", Schema.Ref(cursor=True)), ("n", Schema.Amount(optional=True)),
              ("to", Schema.Refs(MAX_SPREAD_TARGETS, "bad_targets")), ("mode", Schema.Int(0, 1, "bad_mode")))

    def involved(self, op):
        return [op[1]]

    def apply(self, ws, op, profile):
        return distribute(ws, op[1], op[2], op[3], op[4])

    def flies(self, op, device, cursorBefore):
        return _touch(device)

    def lockNotice(self, op):
        return NO_REMOVE if op[1] == CURSOR_REF else None


@Ops.register("drop")
class Drop(Ops.Op):
    params = (("ref", Schema.Ref(cursor=True)), ("n", Schema.Amount()))
    drops = True

    def involved(self, op):
        return [op[1]]

    def apply(self, ws, op, profile):
        return drop(ws, op[1], op[2])

    def lockNotice(self, op):
        return NO_DROP if op[1] == CURSOR_REF else None


@Ops.register("move")
class Move(Ops.Op):
    params = (("src", Schema.Ref()), ("dst", Schema.Ref()), ("n", Schema.Amount(optional=True)))

    def involved(self, op):
        return [op[1], op[2]]

    def apply(self, ws, op, profile):
        return move(ws, op[1], op[2], op[3])

    def flies(self, op, device, cursorBefore):
        return _touch(device)


@Ops.register("hotbar")
class Hotbar(Ops.Op):
    params = (("ref", Schema.Ref()), ("key", Schema.Int(0, HOTBAR_SIZE - 1, "bad_hotbar_key")))

    def involved(self, op):
        return [op[1], (HOTBAR, op[2]), CURSOR_REF]

    def apply(self, ws, op, profile):
        return hotbarKey(ws, op[1], op[2])

    def flies(self, op, device, cursorBefore):
        return device == MOUSE and Items.isEmpty(cursorBefore)

    def lockNotice(self, op):
        return NO_REMOVE


@Ops.register("bundleIn")
class BundleIn(Ops.Op):
    params = (("src", Schema.Ref(cursor=True)), ("bag", Schema.Ref(cursor=True)), ("n", Schema.Amount(optional=True)))

    def involved(self, op):
        return [op[1], op[2]]

    def apply(self, ws, op, profile):
        return bundleInsert(ws, op[1], op[2], op[3])

    def flights(self, op, changes, key, device):
        """原版：触屏装进收纳袋时，东西从原来那一格飞到收纳袋上（键鼠与手柄不飞）。"""
        if device != TOUCH:
            return None
        source, bag = key(op[1]), key(op[2])
        moving = changes.get(source, (None, None))[0]
        before = changes.get(bag, (None, None))[0]
        return [(moving, source, bag, Items.isEmpty(before))] if not Items.isEmpty(moving) else []


@Ops.register("bundleOut")
class BundleOut(Ops.Op):
    params = (("bag", Schema.Ref(cursor=True)), ("i", Schema.Int(0, MAX_BUNDLE_INDEX, "bad_index", optional=True)),
              ("dst", Schema.Ref(cursor=True)))

    def involved(self, op):
        return [op[1], op[3]]

    def apply(self, ws, op, profile):
        return bundleExtract(ws, op[1], op[2], op[3])

    def flights(self, op, changes, key, device):
        """原版：触屏从收纳袋里取出时，取出的那一项从收纳袋飞到目标格（键鼠与手柄不飞）。"""
        if device != TOUCH:
            return None
        bag, target = key(op[1]), key(op[3])
        entries = Bundles.entries(changes.get(bag, (None, None))[0])
        index = op[2] if op[2] is not None else len(entries) - 1
        moving = Bundles.entryItem(entries[index]) if 0 <= index < len(entries) else None
        before = changes.get(target, (None, None))[0]
        return [(moving, bag, target, Items.isEmpty(before))] if not Items.isEmpty(moving) else []


@Ops.register("bundleMove")
class BundleMove(BundleOut):
    params = (("bag", Schema.Ref(cursor=True)), ("i", Schema.Int(0, MAX_BUNDLE_INDEX, "bad_index")),
              ("dst", Schema.Ref(cursor=True)))

    def apply(self, ws, op, profile):
        return bundleTransfer(ws, op[1], op[2], op[3])


@Ops.register("ghost")
class Ghost(Ops.Op):
    params = (("ref", Schema.Ref()), ("src", Schema.Ref(cursor=True, optional=True)))

    def check(self, op, structure):
        if not structure.get(op[1][0]).slot.copies:
            raise Schema.BadRequest("bad_ref")

    def involved(self, op):
        return [op[1]] + ([op[2]] if op[2] is not None else [])

    def apply(self, ws, op, profile):
        return ghostSet(ws, op[1], op[2])


@Ops.register("copy")
class Copy(Ops.Op):
    params = (("ref", Schema.Ref()), ("dst", Schema.Ref(cursor=True)), ("n", Schema.Amount()))

    def check(self, op, structure):
        if not getattr(structure.get(op[1][0]).slot, "source", False):
            raise Schema.BadRequest("bad_ref")

    def involved(self, op):
        return [op[1], op[2]]

    def apply(self, ws, op, profile):
        return copyTo(ws, op[1], op[2], op[3])


@Ops.register("copyQ")
class CopyQuick(Copy):
    params = (("ref", Schema.Ref()), ("n", Schema.Amount()))

    def involved(self, op):
        return [op[1]]

    def apply(self, ws, op, profile):
        return copyQuick(ws, op[1], op[2], profile)


@Ops.register("copyD")
class CopyDrop(CopyQuick):
    drops = True

    def apply(self, ws, op, profile):
        return copyDrop(ws, op[1], op[2])


@Ops.register("trash")
class Trash(Ops.Op):
    params = (("ref", Schema.Ref()), ("src", Schema.Ref(cursor=True)), ("n", Schema.Amount()))

    def check(self, op, structure):
        if not getattr(structure.get(op[1][0]).slot, "trash", False):
            raise Schema.BadRequest("bad_ref")

    def involved(self, op):
        return [op[1], op[2]]

    def apply(self, ws, op, profile):
        return trash(ws, op[1], op[2], op[3])

    def lockNotice(self, op):
        return NO_REMOVE


@Ops.register("craft")
class Craft(Ops.Op):
    params = (("ref", Schema.Ref()), ("mode", Schema.Int(0, len(CRAFT_MODES) - 1, "bad_mode")),
              ("key", Schema.Int(0, HOTBAR_SIZE - 1, "bad_hotbar_key", default=0)))

    def check(self, op, structure):
        if op[1][0] not in structure.derivers:
            raise Schema.BadRequest("bad_ref")

    def involved(self, op):
        refs = [op[1], CURSOR_REF]
        if op[2] == CRAFT_HOTBAR:
            refs.append((HOTBAR, op[3]))
        return refs

    def apply(self, ws, op, profile):
        return craft(ws, op[1], op[2], op[3], profile)
