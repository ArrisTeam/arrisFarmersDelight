# -*- coding: utf-8 -*-
"""
标准库：标准交互（Common/Slots.Interaction 的原版实现，docs/ARCHITECTURE.md 第 3.3 节；各手势的结果见 docs/DESIGN.md 第 4 节）。
缺省登记（Std/Defaults）把它接成标准交互（Slots.setStandard）：格子类型的交互不接的手势都交给它。两端都导入（不碰引擎），
只在客户端调用。

键鼠与手柄用"手持物"模型：按下时先在本地预览，手势确定后（松开、进入拖动分配、进入渐进拿取）才发一条请求。
    左键 / A：拿起整堆、放下整堆；右键 / X：拿起一半、放一个；按住 300 毫秒不动进入渐进拿取（1 秒内从 1 涨到整堆）；
    手上有东西时按住拖进别的格子：左键平均分配、右键每格一个；同一格 500 毫秒内第二下且刚拿空：收集同类；
    Shift 点击：快速转移；手柄 Y：手上空时快速转移，手上有东西时丢出整堆；
    悬停时 Q 丢一个、Ctrl+Q 丢整堆（手上有东西时 Q 丢手上的一个），快捷栏键位（缺省 1–9）与快捷栏互换；点面板外丢出手上的东西。
    收纳袋（按下即生效，不进入拖动分配）：手上拿着收纳袋左键点有东西的格子 = 那一格装进袋里，手上拿着东西左键点
    收纳袋 = 手上的装进袋里；手上拿着收纳袋右键点空格 = 取出最上面一项放过去，手上空着右键点收纳袋 = 取出选中的
    （没选中时取最上面的）一项拿到手上。悬停收纳袋时滚轮在里面选一项。音效按收纳袋的规格（Bundles.StorageSpec.sounds）。
触屏用"选中格"模型：点格子选中，点别的格子搬过去，再点一次取消；长按进入数量选择（左右滑动）；
    选中后拖过多格平均分配；没有选中时拖动是滚动（滚动本身由引擎的滚动视图做，这里只认出"这一下不是点按"）；
    双击收集同类；点面板外丢出选中的东西。
    收纳袋：点收纳袋展开（选中它，底部显示提示）；展开时点有东西的格子 = 装进袋里，点提示里的一项 = 选中它并收起提示，
    选中一项后点空格 / 同种的一堆 / 别的收纳袋 = 取出放过去；没选中时点空格 = 把收纳袋搬过去；再点收纳袋收起。
    选中别的东西时点收纳袋 = 选中的装进袋里。

Standard 的每一步都是方法：press（键鼠与手柄按下）、holdHover / holdTick / holdRelease（按住期间与松开，键鼠的拖动分配与
渐进拿取、触屏的分配、选数量、搬运）、touchPress、quick、drop、dropHeld、hotbar、outside（面板外）、moveSelected（触屏搬运）、
wheel、helpers（手柄提示条），收纳袋的 bundleClick / bundleDo / touchBundleDown / touchBundleUp，计时常量是类属性。
要在原版的基础上改几步就派生它、改写那几个方法；格子类型的交互派生它时，不改的照原版。手势识别器 g 的公开方法见
Client/Gestures"给格子类型的交互用的"一节。
"""
import math

from ..Common import Bundles, Items, Rules
from ..Common.Collections import CURSOR_REF
from ..Common.Slots import MOUSE, TOUCH, Interaction, setStandard

PRIMARY = Rules.PRIMARY
SECONDARY = Rules.SECONDARY
LOCKED_TARGET = "notification.lock.noReplace"   # 原版：触屏不能把东西放到锁定的物品上


def _movedAxis(a, b, limit):
    """横向或纵向超过 limit（原版判断按住期间指针动没动是逐轴比的，不是直线距离）。"""
    if a is None or b is None:
        return False
    return abs(a[0] - b[0]) > limit or abs(a[1] - b[1]) > limit


def _distance(a, b):
    if a is None or b is None:
        return 0.0
    return math.hypot(a[0] - b[0], a[1] - b[1])


def sliderAmount(dx, total, span=32.0):
    """触屏数量选择：按水平位移给出数量（±span 个界面单位，正弦曲线，起点一半）。"""
    ratio = max(-1.0, min(1.0, dx / span))
    p = (math.sin(ratio * math.pi / 2.0) + 1.0) / 2.0
    return int(math.floor(p * (total - 1))) + 1


def progressiveAmount(elapsed, total, seconds=1.0):
    """渐进拿取：进入后 elapsed 秒拿多少（seconds 秒内从 1 涨到整堆）。"""
    return int(math.floor(min(elapsed / seconds, 1.0) * (total - 1))) + 1


class Standard(Interaction):
    """原版容器界面的手势（见模块说明）。"""

    DOUBLE_CLICK_SECONDS = 0.5
    DOUBLE_CLICK_DISTANCE = 10.0
    HOLD_SECONDS = 0.3
    HOLD_MOVE_DISTANCE = 5.0   # 原版按住期间"动过"：横、纵各自比（任一方向超过 5 就算动过）
    HOLD_LAG_LIMIT = 0.1       # 键鼠按住计时的起点最多比按下早这么多
    PROGRESSIVE_SECONDS = 1.0
    SLIDER_RANGE = 32.0

    # ---------------------------------------------------------------- 键鼠与手柄

    def press(self, g, ref, button, now, position):
        cursor = g.mirror.get(CURSOR_REF)
        bundle = self.bundleClick(g, ref, button)
        if bundle is not None:
            # 原版收纳袋的这几种点法在按下时就生效，之后不进入拖动分配与渐进拿取
            g.lastPress = None
            self.bundleDo(g, *bundle)
            g.startPress(ref, button, now, position, self, cursor).mode = "bundle"
            return True
        # 键鼠按住计时从按下前最近一次 tick 算起；隔得太久（不到 10 帧每秒，或刚开界面还没 tick 过）按 HOLD_LAG_LIMIT 算
        last = g.lastTick
        holdFrom = max(last, now - self.HOLD_LAG_LIMIT) if last is not None and last <= now else now
        if self.isDouble(g, ref, button, now, position):
            g.lastPress = None
            if not Items.isEmpty(cursor):
                if Items.isEmpty(g.mirror.get(ref)) and g.lastActionRef == ref:
                    g.do(("gatherK", ref))
                    g.lastActionRef = ref
                    return True
                if not Items.isEmpty(g.mirror.get(ref)) and g.lastActionRef == ref:
                    return True   # 第一下是合并、格子没空：第二下什么都不做
        else:
            g.lastPress = (ref, now, position, button)
        g.startPress(ref, button, now, position, self, cursor, holdFrom)
        g.preview = g.mirror.preview(("click", ref, button), g.profile())
        return True

    def holdHover(self, g, press, ref, now):
        if press.mode == "held":
            return
        if g.device == TOUCH:
            self.touchHover(g, press, ref, now)
            return
        if press.mode == "progressive":
            g.finish(now)
            return
        if Items.isEmpty(press.cursor) or ref in press.targets or press.mode not in ("pending", "drag"):
            return
        if press.mode == "pending" and press.button == SECONDARY and not self.accepting(g, press.ref, press.cursor):
            return   # 右键按下时是交换，不进入每格一个
        press.mode = "drag"
        press.targets.append(ref)
        mode = Rules.EVEN if press.button == PRIMARY else Rules.ONE
        g.preview = g.mirror.preview(("spread", CURSOR_REF, None, list(press.targets), mode), g.profile())

    def holdTick(self, g, press, now, pointer):
        if press.mode == "held":
            return
        if g.device == TOUCH:
            self.touchTick(g, press, now, pointer)
            return
        moved = _movedAxis(pointer, press.position, self.HOLD_MOVE_DISTANCE)
        if press.mode == "pending":
            stack = g.mirror.get(press.ref)
            holdFrom = press.holdFrom if press.holdFrom is not None else press.start
            if Items.isEmpty(press.cursor) and not Items.isEmpty(stack) and Items.count(stack) > 1 \
                    and now - holdFrom > self.HOLD_SECONDS and not moved:
                press.mode = "progressive"
                press.progressStart = now
                g.preview = {}
        if press.mode == "progressive":
            if moved:
                g.finish(now)
                return
            total = g.oneStack(g.mirror.get(press.ref))
            press.amount = progressiveAmount(now - press.progressStart, total, self.PROGRESSIVE_SECONDS)
            g.progress = (press.ref, press.amount, total)

    def holdRelease(self, g, press, ref, now):
        if press.mode == "held":
            return
        if g.device == TOUCH:
            self.touchRelease(g, press, ref, now)
            return
        if press.mode == "bundle":
            return
        if press.mode == "drag":
            mode = Rules.EVEN if press.button == PRIMARY else Rules.ONE
            g.do(("spread", CURSOR_REF, None, list(press.targets), mode))
        elif press.mode == "progressive":
            if press.amount:
                g.do(("take", press.ref, press.amount))
        else:
            g.do(("click", press.ref, press.button))
        g.lastActionRef = press.ref

    def keysBlocked(self, g, press):
        return press.mode == "progressive"

    def quick(self, g, ref):
        g.do(("quick", ref))
        g.lastActionRef = ref
        return True

    def drop(self, g, ref, whole):
        stack = g.mirror.get(ref)
        if not Items.isEmpty(stack):
            g.do(("drop", ref, g.oneStack(stack) if whole else 1))
        return True

    def dropHeld(self, g, whole):
        """丢出拿在指针上的东西：whole 为真时整堆（手柄 Y），否则一个（Q）。"""
        cursor = g.mirror.get(CURSOR_REF)
        if not Items.isEmpty(cursor):
            g.do(("drop", CURSOR_REF, Items.count(cursor) if whole else 1))

    def hotbar(self, g, ref, index):
        g.do(("hotbar", ref, index))
        return True

    def outside(self, g, button, down, now):
        """面板外按下 / 抬起：键鼠与手柄按下时丢出手上的东西（左键整堆、右键一个）；触屏抬起时丢出选中的。"""
        if g.device == TOUCH:
            if down:
                g.outsidePress = now
            elif g.outsidePress is not None and g.selection is not None:
                g.outsidePress = None
                self.dropSelection(g)
            return
        if not down:
            return
        cursor = g.mirror.get(CURSOR_REF)
        if not Items.isEmpty(cursor):
            g.do(("drop", CURSOR_REF, Items.count(cursor) if button == PRIMARY else 1))

    def wheel(self, g, ref, up):
        """
        原版：键鼠悬停在装着东西的收纳袋上、手上空着时，滚轮在提示里选一项：没选中时向上选最后一格、向下选第一格，
        之后一格一格移，越过两头时绕回（向上绕到最后一格，向下绕到第一格）。
        """
        hover = g.bundleHover
        if g.device != MOUSE or hover is None or not Items.isEmpty(g.mirror.get(CURSOR_REF)):
            return False
        bundle = g.displayed(hover[0])
        if not Bundles.entries(bundle):
            return False
        first, last = Bundles.TooltipLayout(bundle).firstAndLast()
        cell = hover[1]
        if cell is None:
            cell = last if up else first
        else:
            cell += -1 if up else 1
            if cell > last or cell < first:
                cell = last if up else first
        hover[1] = cell
        return True

    def helpers(self, g, ref):
        """
        原版容器界面的手柄说明（x、a、y、b）：A 拿取 / 放置 / 添加到收纳袋；X 拿取一半 / 放置一个 / 交换 / 从收纳袋取出 /
        收纳袋里的放下；Y 快速转移 / 丢弃；B 退出。
        """
        cursor = g.displayed(CURSOR_REF)
        carrying = not Items.isEmpty(cursor)
        hovering = ref is not None and not Items.isEmpty(g.displayed(ref))
        bundleHovered = g.bundleHover is not None
        if (Bundles.isBundle(cursor) and hovering) or (bundleHovered and carrying):
            a = "controller.buttonTip.add.to.bundle"
        else:
            a = "controller.buttonTip.place" if carrying else "controller.buttonTip.take"
        if bundleHovered and not carrying:
            x = "controller.buttonTip.take.from.bundle"
        elif Bundles.isBundle(cursor) and not hovering:
            x = "controller.buttonTip.place.from.bundle"
        elif carrying:
            x = "controller.buttonTip.swap" if hovering else "controller.buttonTip.place.one"
        else:
            x = "controller.buttonTip.take.half"
        return (x, a, "controller.buttonTip.drop" if carrying else "controller.buttonTip.quick.move",
                "controller.buttonTip.exit")

    def isDouble(self, g, ref, button, now, position):
        """这一下与上一下接成双击（同一格、左键、隔得不久、没挪远，格子收集同类）。"""
        last = g.lastPress
        return last is not None and button == PRIMARY and last[3] == PRIMARY and last[0] == ref \
            and now - last[1] < self.DOUBLE_CLICK_SECONDS and _distance(position, last[2]) < self.DOUBLE_CLICK_DISTANCE \
            and self.coalesces(g, ref)

    def coalesces(self, g, ref):
        """双击这一格收不收集同类（格子类型的 coalesce；原版物品栏的盔甲格、副手格不收，两下照普通点击算）。"""
        slotType = g.slotType(ref)
        return slotType is None or slotType.coalesce

    def accepting(self, g, ref, stack):
        """ref 能接手上这堆的一个（空格，或同种未满）。"""
        target = g.mirror.get(ref)
        return Items.isEmpty(target) or (g.mirror.rules.canStack(target, stack) and g.mirror.rules.room(target, stack) > 0)

    # ---------------------------------------------------------------- 收纳袋（键鼠与手柄）

    def bundleClick(self, g, ref, button):
        """键鼠与手柄点格子时原版收纳袋的几种情形，给出 (操作, 是不是装进袋里, 收纳袋所在的格)；不是这些情形时为 None。"""
        cursor, target = g.mirror.get(CURSOR_REF), g.mirror.get(ref)
        if button == PRIMARY:
            if Bundles.isBundle(cursor) and not Items.isEmpty(target):
                return ("bundleIn", ref, CURSOR_REF, None), True, CURSOR_REF
            if Bundles.isBundle(target) and not Items.isEmpty(cursor):
                return ("bundleIn", CURSOR_REF, ref, None), True, ref
            return None
        if Bundles.isBundle(cursor) and Items.isEmpty(target):
            return ("bundleOut", CURSOR_REF, None, ref), False, CURSOR_REF
        if Items.isEmpty(cursor) and Bundles.isBundle(target):
            selection = g.bundleSelection()
            index = selection[2] if selection is not None and selection[0] == ref else None
            return ("bundleOut", ref, index, CURSOR_REF), False, ref
        return None

    def bundleDo(self, g, op, inserting, bag):
        """
        执行收纳袋操作（inserting：装进袋里，否则是取出；bag 是收纳袋所在的格）并放音效（收纳袋规格的 sounds，原版：装进去
        bundle.insert、装不进 bundle.insert_fail、取出 bundle.remove_one）。
        """
        spec = Bundles.specOf(g.mirror.get(bag))
        sounds = spec.sounds if spec is not None else Bundles.VANILLA_SOUNDS
        done = g.do(op)
        if inserting:
            g.sound(sounds[0] if done else sounds[1])
        elif done:
            g.sound(sounds[2])
        if not inserting and g.bundleHover is not None:
            g.bundleHover[1] = None    # 原版：取出后清掉提示里的选中
        return done

    # ---------------------------------------------------------------- 触屏

    def touchPress(self, g, ref, now, position):
        stack = g.mirror.get(ref)
        if not Items.isEmpty(stack):
            g.decidingSince = now
        if self.touchBundleDown(g, ref):
            g.lastPress = None
            g.startPress(ref, PRIMARY, now, position, self).mode = "bundle"
            return True
        if not Items.isEmpty(stack):
            # 原版：触屏按下有物品的格子就在底部显示它的完整悬停文本（选好数量、正要放下时不显示；
            # 收纳袋不显示，收纳袋展开着时也不显示）
            if not (g.selection and g.selection["amount"]) and not Bundles.isBundle(stack) and g.bundleActive is None:
                g.details(ref)
        last = g.lastPress
        if last is not None and last[0] == ref and now - last[1] < self.DOUBLE_CLICK_SECONDS \
                and _distance(position, last[2]) < self.DOUBLE_CLICK_DISTANCE \
                and g.selection is not None and g.selection["ref"] == ref and self.coalesces(g, ref):
            g.lastPress = None
            g.selection = None
            g.do(("gatherS", ref))
            return True
        g.lastPress = (ref, now, position, PRIMARY)
        g.startPress(ref, PRIMARY, now, position, self)
        return True

    def touchHover(self, g, press, ref, now):
        """触屏按住时手指移进了 ref：选中了东西时拖过两格以上是平均分配。"""
        if press.mode in ("scroll", "slider") or g.selection is None:
            return
        source = g.selection["ref"]
        if Items.isEmpty(g.mirror.get(source)):
            return
        if ref not in press.targets:
            press.targets.append(ref)
        if len(press.targets) >= 2:
            press.mode = "split"
            op = ("spread", source, g.selection["amount"], list(press.targets), Rules.EVEN)
            g.preview = g.mirror.preview(op, g.profile())

    def touchTick(self, g, press, now, pointer):
        """触屏按住的每帧：拖动了是滚动，长按进入选数量，选数量时按滑动（或按住回车的时间）定数量。"""
        if press.mode == "pending":
            moved = g.scrolled(press, pointer)
            stack = g.mirror.get(press.ref)
            if moved and g.selection is None:
                press.mode = "scroll"   # 拖动交给引擎的滚动视图，松开时不当点按
            elif not moved and now - press.holdFrom > g.longPress and not Items.isEmpty(stack) \
                    and Items.count(stack) > 1 and not press.noSlider:
                self.startSlider(g, press, pointer, now)
        if press.mode == "slider":
            total = g.oneStack(g.mirror.get(press.ref))
            if press.keyboard:
                amount = progressiveAmount(now - press.sliderStart, total, self.PROGRESSIVE_SECONDS)   # 原版：按住回车时 1 秒涨到整堆
            else:
                dx = (pointer[0] - press.sliderOrigin) if pointer is not None else 0.0
                amount = sliderAmount(dx, total, self.SLIDER_RANGE)
            g.slider = (press.ref, amount, total)
            g.selection["amount"] = amount

    def startSlider(self, g, press, pointer, now):
        """
        触屏长按进入选数量，照原版：
        - 别的格子选中着、还没选数量：先把选中的整堆放到长按的格子（空格搬过去、同种合并、放不下或不同种交换），
          再选中这一格、在这一格上选数量；
        - 别的格子选中着、已经选好数量：不进入选数量，松开时照点按把选好的数量搬过去；
        - 长按的就是选好过数量的选中格：数量接着按上次的起点算（原版不重新起算）。
        """
        selection = g.selection
        origin = pointer[0] if pointer is not None else 0.0
        if selection is not None and selection["ref"] != press.ref:
            if selection["amount"]:
                press.noSlider = True
                return
            g.do(("move", selection["ref"], press.ref, None))
            selection = None
        if selection is not None and selection.get("origin") is not None:
            origin = selection["origin"]
        press.mode = "slider"
        press.sliderOrigin = origin
        press.sliderStart = now
        g.selection = {"ref": press.ref, "amount": selection["amount"] if selection else None, "origin": origin}
        g.effects.append(("hideDetails", None))   # 原版：进入选数量时撤掉物品详情

    def touchRelease(self, g, press, ref, now):
        """触屏松开（ref 是松开处的格子）：点按选中、搬运、平均分配，收纳袋展开时的点按。"""
        if press.mode in ("slider", "bundle"):
            return
        if g.bundleActive is not None and press.mode == "pending" and ref == press.ref and self.touchBundleUp(g, ref):
            return
        if press.mode == "split":
            source = g.selection["ref"]
            g.do(("spread", source, g.selection["amount"], list(press.targets), Rules.EVEN))
            g.selection = None
            return
        if press.mode == "scroll" or ref != press.ref:
            return
        selection = g.selection
        if selection is None:
            if not Items.isEmpty(g.mirror.get(ref)):
                g.select(ref)
            return
        g.selection = None
        if selection["ref"] == ref:
            return
        if not g.interactionAt(selection["ref"]).moveSelected(g, selection, ref):
            g.standard.moveSelected(g, selection, ref)

    def moveSelected(self, g, selection, ref):
        """触屏：把选中的（选好的数量，没选数量时整堆）搬到 ref；ref 里是锁定的物品时提示、不搬。"""
        if Items.lockMode(g.mirror.get(ref)) != Items.LOCK_NONE:
            g.lockNotice(LOCKED_TARGET)
            return True
        g.do(("move", selection["ref"], ref, selection["amount"]))
        return True

    def dropSelection(self, g):
        """触屏：丢出选中的（选好的数量，没选数量时一组）。"""
        if not g.mirror.dropAllowed:
            return
        selection, g.selection = g.selection, None
        g.bundleActive = None
        stack = g.mirror.get(selection["ref"])
        if not Items.isEmpty(stack):
            amount = selection["amount"] or g.oneStack(stack)
            g.do(("drop", selection["ref"], min(amount, Items.count(stack))))

    # ---------------------------------------------------------------- 收纳袋（触屏）

    def touchBundleDown(self, g, ref):
        """触屏按下时原版收纳袋的几种情形（原版在按下时生效）；处理了返回 True。"""
        stack, selection, active = g.mirror.get(ref), g.selection, g.bundleActive
        if active is None:
            if not Bundles.isBundle(stack):
                return False
            if selection is None:
                g.bundleActive = {"ref": ref, "cell": None, "minimized": False}
                g.select(ref)
                g.effects.append(("hideDetails", None))
                return True
            source = selection["ref"]
            if source == ref or Bundles.isBundle(g.mirror.get(source)):
                return False
            g.selection = None
            self.bundleDo(g, ("bundleIn", source, ref, selection["amount"]), True, ref)
            return True
        bag = active["ref"]
        if ref == bag:
            if active["minimized"] and active["cell"] is not None:
                active["cell"], active["minimized"] = None, False   # 原版：收起后再点收纳袋重新展开
                return True
            return False
        index = g.activeBundleEntry()
        if index is None:
            return False
        if Bundles.isBundle(stack):
            op = ("bundleMove", bag, index, ref)
        elif Items.isEmpty(stack):
            op = ("bundleOut", bag, index, ref)
        else:
            chosen = Bundles.entryItem(Bundles.entries(g.mirror.get(bag))[index])
            if stack["newItemName"] != chosen["newItemName"] or g.mirror.rules.maxStack(stack) <= 1:
                return False
            op = ("bundleOut", bag, index, ref)
        self.bundleDo(g, op, False, bag)
        if active["minimized"]:
            g.closeBundle()
        else:
            active["cell"] = None
        return True

    def touchBundleUp(self, g, ref):
        """收纳袋展开时的点按（原版在抬起时生效）：点收纳袋本身收起；点有东西的格子装进袋里；点空格把收纳袋搬过去。"""
        bag = g.bundleActive["ref"]
        if ref == bag:
            g.closeBundle()
            return True
        if not Items.isEmpty(g.mirror.get(ref)):
            self.bundleDo(g, ("bundleIn", ref, bag, None), True, bag)
            return True
        g.bundleActive = None     # 收纳袋搬到空格：照普通的搬运做，收纳袋随之收起
        return False


STANDARD = Standard()
setStandard(STANDARD)
