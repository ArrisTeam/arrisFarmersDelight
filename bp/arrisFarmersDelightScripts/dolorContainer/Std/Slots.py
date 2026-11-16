# -*- coding: utf-8 -*-
"""
标准库：原版的几种格子类型（docs/ARCHITECTURE.md 第 3.3 节；各手势的结果见 docs/DESIGN.md 第 4 节）。

- Output（只出，熔炉的产物格）：放不进东西，拿取照常；被拿走时通知界面模型（Menu.onTaken，熔炉据此给经验）。
  键鼠与手柄手上是同种时点它把东西加到手上——这是点击的通用规矩（放不进的格子里是同种就加到手上，见 Operations.click）。
  触屏照原版：点按转一个进背包、0.25 秒内再点转余下的整堆，长按进入选数量，不选中、不进入拖动分配与双击收集。
- Result（算出，工作台的产物格）：内容由部件按别的格子算出（结构里配 derive），只经合成操作拿走。照原版工作台：
  按下即合成，左右键（手柄 X）合成一次到手上，手柄 A 与触屏点按合成一次放进背包，触屏按住 0.7 秒后每 0.25 秒合成一次；
  Shift 点击、手柄 Y 合成尽量多；悬停时快捷栏键位（手上空着）合成一次放进那一格；不进入拖动分配、渐进拿取与收集同类，
  Q 不起作用。
- Display（只看）：不能拿放；内容可以来自界面数据（items，配方、奖励的预览）。只读（宿主物品所在的那一格）不是格子类型，
  是锁住的格子（Server/Hosts.lockedSlot）。
- Ghost（幽灵 / 过滤）：格子里放的是副本。左键（手柄 A）手上有东西时设成它的一份（一个，手上的不动），空手左键、右键
  （手柄 X）、Shift 点击清空；悬停时快捷栏键位设成快捷栏那一格的一份（那一格空着就清空）；触屏选中了东西时点它设成选中的
  一份，没选中时点它清空。按下即生效，不进入拖动分配、渐进拿取与收集同类，Q 不起作用。别的集合 Shift 点击（快速转移）到
  幽灵格的集合时放一份到第一个空着的幽灵格，原格不动（repeats 为假时集合里已经有同种的就不放）。关界面不退回。
- Source（来源，创造物品栏）：拿走得到新的一份，格子里的不变；内容可以来自界面数据（items）。照原版创造物品栏：手上空着时
  左键（手柄 A）拿一组、右键（手柄 X）拿一个；Shift 点击（手柄 Y）放一组进另一侧（先补同种、再填空格）；Q / Ctrl + Q 丢一个 /
  一组；悬停时快捷栏键位放一组进那一格。trash 为真（创造物品栏）时手上的东西点进来就删掉（左键整堆、右键一个，同种也删）；
  为假时手上是同种就加到手上（左键加到一组、右键加一个），别的东西不动。触屏点它选中、再点取消，选中后点别的格子放一组
  过去（那一格是同种就加满，别的东西 trash 时换掉）；trash 时选中别的格子再点它，把选中的（选好的数量）删掉。
- Equipment（装备）：只收 fits 认的东西（盔甲部位见 wearable，副手见 offhandable），每格缺省一个（maxStack）；带绑定诅咒的
  拿不走（binding，创造模式除外）；服务端在内容变了之后调用 onEquip(会话, 格子, 原来的, 现在的)，作用到宿主。手势照普通格子。
- Disableable（可停用，合成器）：flags 是界面数据里每格停没停用（Data.SlotValues(Data.Bool(), 集合)），toggle 是切换的动作
  （格号, 停用）。照原版合成器：手上空着按下（键鼠两个键、手柄 A / X）空着的格子把它停用（sound 是停用时的音效），悬停空着的
  格子时提示"点击以禁用槽位"；左键（手柄 A）按停用的格子把它启用，手上拿着东西时启用后把手上的整堆放进去，右键（手柄 X）
  不起作用；触屏没选中东西时点按空着的格子停用，点按停用的格子启用，选中了东西时随之放进去。停用的格子不收东西（快速转移、
  拖动分配、合成都跳过它），盖一层停用的样子。要停用的格子空着才行。现成的一套见 Parts/Toggles（每格开关存在实例状态里，
  带动作）。
- Virtual（虚拟，列表视图的一项）：不是真的格子，内容来自界面数据（entries），手势变成界面模型的动作 action(格号, 方式,
  手上那一格, 数量)，由动作在背后的存储里取放：手上空着左键拿一组（LIST_TAKE）、右键拿半组（LIST_HALF）；手上有东西左键全部
  放进去（LIST_PUT）、右键放一个（LIST_PUT_ONE）；Shift 点击拿一组进背包（LIST_QUICK）；Q / Ctrl + Q 丢一个 / 一组
  （LIST_DROP / LIST_DROP_ALL）。触屏选中了东西时点它把选中的（选好的数量，0 为整堆）放进去，没选中时点它拿一组进背包。
- Choice（可选的一项，原版切石机的配方按钮）：算出的格子（结构里配 derive，部件可以给 shown 定显示几格），拿不走也放不进；
  键鼠左键、右键、Shift 点击、Q（Ctrl + Q）、手柄 A / X / Y、触屏点按都选中这一项：发动作 select(格号)（照原版的按钮放
  sound），快捷栏键位不起作用。选中的那一格（每位查看者状态或界面数据 selected，Data.Int）的底格是 cells 的第二张，别的是
  第一张（原版切石机：反色的与普通的格子底图）。悬停照常写物品的悬停文本。
"""
from ..Common import Bundles, Data, Items, Rules
from ..Common.Collections import CURSOR_REF, HOTBAR
from ..Common.Slots import GAMEPAD, TOUCH, Decoration, Interaction, SlotType
from . import Operations

TOGGLE_HINT = "gui.togglable_slot"   # 原版合成器空格的悬停提示（"点击以禁用槽位"）
OUTPUT_DOUBLE_TAP = 0.25     # 原版触屏：上一次在产物格上抬起后这么久之内再点，转余下的整堆
CRAFT_REPEAT_START = 0.7     # 原版触屏按住产物格：0.7 秒后开始连续合成
CRAFT_REPEAT_SECONDS = 0.25  # 之后每 0.25 秒合成一次


class OutputInteraction(Interaction):
    """只出格子的触屏手势（键鼠与手柄照普通格子）。"""

    def touchPress(self, g, ref, now, position):
        # 原版触屏按下熔炉的产物格：不选中、不显示详情，等抬起（点按）或长按（选数量）
        g.forgetDoubleClick()
        g.hold(ref, Rules.PRIMARY, now, position, self)
        return True

    def holdTick(self, g, press, now, pointer):
        if g.device != TOUCH:
            return
        if now - press.holdFrom > g.longPress and Items.count(g.mirror.get(press.ref)) > 1:
            # 原版：按住产物格超过拆分触发时间、东西多于一个时进入选数量，选中的就是产物格
            g.beginSlider(press, pointer[0] if pointer is not None else 0.0, now)

    def holdRelease(self, g, press, ref, now):
        """
        触屏点按熔炉的产物格，照原版：转一个进背包（"自动放置一个"）并取消选中；上一次在产物格上抬起后 0.25 秒内
        再点，转余下的整堆。按住超过拆分触发时间才松开（只有一个、没进入选数量）什么都不做。
        """
        memory = g.memory(self)
        last, memory["released"] = memory.get("released"), now
        held = now - (press.holdFrom if press.holdFrom is not None else press.start)
        if ref != press.ref or held >= g.longPress:
            return
        g.takeSelection()
        if last is not None and now - last < OUTPUT_DOUBLE_TAP:
            g.do(("quick", ref))
        else:
            g.do(("quickN", ref, 1))
        g.lastActionRef = ref


class ResultInteraction(Interaction):
    """算出格子的手势：按下即合成，这一下之后不进入拖动、渐进拿取与收集同类。"""

    def _craft(self, g, ref, mode, key=0):
        g.forgetDoubleClick()
        g.lastActionRef = ref
        return g.do(("craft", ref, mode, key))

    def _press(self, g, ref, button, now, position, mode):
        self._craft(g, ref, mode)
        press = g.hold(ref, button, now, position, self)
        press.data["next"] = now + CRAFT_REPEAT_START
        return True

    def press(self, g, ref, button, now, position):
        mode = Operations.CRAFT_ONE if g.device == GAMEPAD and button == Rules.PRIMARY else Operations.CRAFT_CURSOR
        return self._press(g, ref, button, now, position, mode)

    def touchPress(self, g, ref, now, position):
        return self._press(g, ref, Rules.PRIMARY, now, position, Operations.CRAFT_ONE)

    def quick(self, g, ref):
        self._craft(g, ref, Operations.CRAFT_ALL)
        return True

    def drop(self, g, ref, whole):
        return True   # 原版：产物格上 Q 不起作用

    def hotbar(self, g, ref, index):
        if Items.isEmpty(g.mirror.get(CURSOR_REF)):
            self._craft(g, ref, Operations.CRAFT_HOTBAR, index)
        return True

    def holdTick(self, g, press, now, pointer):
        if g.device == TOUCH and now >= press.data["next"]:   # 原版：触屏按住产物格连续合成
            self._craft(g, press.ref, Operations.CRAFT_ONE)
            press.data["next"] = now + CRAFT_REPEAT_SECONDS


class Output(SlotType):
    """只出（见模块说明）。owner 是拿走时通知的部件（Menus.Part 的 onTaken），不给时通知界面模型。"""

    interaction = OutputInteraction()

    def __init__(self, owner=None, **options):
        SlotType.__init__(self, **options)
        self.owner = owner

    def mayPlace(self, ws, ref, stack):
        return False

    def onTake(self, session, ref, stack):
        (self.owner if self.owner is not None else session.menu).onTaken(session, ref, stack)


class Result(SlotType):
    """
    算出（见模块说明）。intoBundle 为真时，手上拿着收纳袋点产物（合成到手上的那几种手势）把产物合成进收纳袋（整份放得进去
    才合成）：原版工作台、切石机是这样；砂轮、锻造台不是（缺省为假）。
    """

    interaction = ResultInteraction()
    computed = True
    returnsOnClose = False
    intoBundle = False

    def mayPlace(self, ws, ref, stack):
        return False

    def mayTake(self, ws, ref, stack):
        return False


class Display(SlotType):
    """只看（见模块说明）。items 是界面数据里每格物品（Data.SlotValues(Data.Item(), 集合)）的名字时，内容就是它。"""

    returnsOnClose = False

    def __init__(self, items=None, **options):
        SlotType.__init__(self, **options)
        self.itemsFrom = items

    def mayPlace(self, ws, ref, stack):
        return False

    def mayTake(self, ws, ref, stack):
        return False


# ---------------------------------------------------------------- 幽灵格


class GhostInteraction(Interaction):
    """幽灵格的手势（见模块说明）。"""

    def _set(self, g, ref, src):
        g.forgetDoubleClick()
        g.lastActionRef = ref
        g.do(("ghost", ref, src))

    def press(self, g, ref, button, now, position):
        filled = button == Rules.PRIMARY and not Items.isEmpty(g.mirror.get(CURSOR_REF))
        self._set(g, ref, CURSOR_REF if filled else None)
        return True

    def touchPress(self, g, ref, now, position):
        g.forgetDoubleClick()
        g.hold(ref, Rules.PRIMARY, now, position, self)
        return True

    def holdTick(self, g, press, now, pointer):
        g.trackMove(press, pointer)

    def holdRelease(self, g, press, ref, now):
        if not g.tapped(press, ref, now):
            return
        selection = g.takeSelection()
        source = selection["ref"] if selection is not None else None
        self._set(g, ref, source if source is not None and not Items.isEmpty(g.mirror.get(source)) else None)

    def quick(self, g, ref):
        self._set(g, ref, None)
        return True

    def drop(self, g, ref, whole):
        return True

    def hotbar(self, g, ref, index):
        self._set(g, ref, (HOTBAR, index))
        return True


class Ghost(SlotType):
    """幽灵 / 过滤（见模块说明）。repeats 为真时 Shift 点击可以放进同种的第二份。"""

    interaction = GhostInteraction()
    returnsOnClose = False
    copies = True

    def __init__(self, repeats=False, **options):
        SlotType.__init__(self, **options)
        self.repeats = repeats

    def mayPlace(self, ws, ref, stack):
        return False

    def mayTake(self, ws, ref, stack):
        return False

    def quickInto(self, ws, name, src, amount):
        """快速转移进来：放一份副本到第一个能放的空格，原格不动（算全转完了）；放不了时一个都没转。"""
        return 0 if Operations.ghostQuick(ws, name, ws.get(src)) else amount

    def copyInto(self, ws, name, stack, amount):
        """来源格的快速转移不往幽灵格里放。"""
        return amount


# ---------------------------------------------------------------- 来源格


class SourceInteraction(Interaction):
    """来源格的手势（见模块说明）。"""

    def _largest(self, g, stack):
        return g.mirror.rules.maxStack(stack)

    def press(self, g, ref, button, now, position):
        g.forgetDoubleClick()
        g.lastActionRef = ref
        stack, cursor = g.mirror.get(ref), g.mirror.get(CURSOR_REF)
        if not Items.isEmpty(cursor) and g.slotType(ref).trash:
            g.do(("trash", ref, CURSOR_REF, Items.count(cursor) if button == Rules.PRIMARY else 1))
        elif not Items.isEmpty(stack):
            g.do(("copy", ref, CURSOR_REF, self._largest(g, stack) if button == Rules.PRIMARY else 1))
        return True

    def quick(self, g, ref):
        stack = g.mirror.get(ref)
        if not Items.isEmpty(stack):
            g.do(("copyQ", ref, self._largest(g, stack)))
        return True

    def drop(self, g, ref, whole):
        stack = g.mirror.get(ref)
        if not Items.isEmpty(stack):
            g.do(("copyD", ref, self._largest(g, stack) if whole else 1))
        return True

    def hotbar(self, g, ref, index):
        stack = g.mirror.get(ref)
        if not Items.isEmpty(stack):
            g.do(("copy", ref, (HOTBAR, index), self._largest(g, stack)))
        return True

    def touchPress(self, g, ref, now, position):
        g.forgetDoubleClick()
        if not Items.isEmpty(g.mirror.get(ref)):
            g.details(ref)   # 原版：触屏按下有物品的格子就在底部显示它的完整悬停文本
        g.hold(ref, Rules.PRIMARY, now, position, self)
        return True

    def holdTick(self, g, press, now, pointer):
        g.trackMove(press, pointer)

    def holdRelease(self, g, press, ref, now):
        if not g.tapped(press, ref, now):
            return
        selection = g.selection
        if selection is not None and selection["ref"] == ref:
            g.selection = None
            return
        if selection is not None and g.slotType(ref).trash and not isinstance(g.slotType(selection["ref"]), Source):
            g.selection = None
            held = g.mirror.get(selection["ref"])
            if not Items.isEmpty(held):
                g.do(("trash", ref, selection["ref"], min(selection["amount"] or Items.count(held), Items.count(held))))
            return
        g.selection = {"ref": ref, "amount": None} if not Items.isEmpty(g.mirror.get(ref)) else None

    def moveSelected(self, g, selection, ref):
        stack = g.mirror.get(selection["ref"])
        if not Items.isEmpty(stack):
            g.do(("copy", selection["ref"], ref, self._largest(g, stack)))
        return True

    def blank(self, g, name, button):
        """能删东西的（原版创造栏）：左键、确认键点空白处整堆删掉手上的（点进格子区的第一格）；右键照面板空白处。"""
        cursor = g.mirror.get(CURSOR_REF)
        if button != Rules.PRIMARY or Items.isEmpty(cursor) or not g.slotType((name, 0)).trash:
            return False
        g.do(("trash", (name, 0), CURSOR_REF, Items.count(cursor)))
        return True


class Source(SlotType):
    """来源（见模块说明）。items 是界面数据里每格物品的名字时，内容就是它；trash 为真时点进来的东西删掉。"""

    interaction = SourceInteraction()
    returnsOnClose = False
    source = True

    def __init__(self, items=None, trash=False, **options):
        SlotType.__init__(self, **options)
        self.itemsFrom = items
        self.trash = trash

    def mayPlace(self, ws, ref, stack):
        return False

    def mayTake(self, ws, ref, stack):
        return False

    def quickInto(self, ws, name, src, amount):
        """快速转移进来：能删东西的（trash）把这些删掉（锁定的物品删不掉），别的不收。"""
        stack = ws.get(src)
        if not self.trash or Items.lockMode(stack) != Items.LOCK_NONE:
            return amount
        ws.set(src, Items.withCount(stack, Items.count(stack) - amount))
        return 0

    def copyable(self, ws, ref):
        """ref 这一格拿得出东西（改写它的：原版创造栏的组头点它是展开、收起，拿不出东西）。"""
        return True


# ---------------------------------------------------------------- 装备格

HEAD, CHEST, LEGS, FEET = 0, 1, 2, 3   # 原版盔甲的部位（引擎物品信息里的 armorSlot）
# 引擎物品信息里不是防具、原版却能穿戴的东西：物品名 -> 部位（方块类的雕刻南瓜、头颅戴在头上；鞘翅、海龟壳的信息里有部位）。
# 模组的这类东西经 addWearable 登记（两端都要执行到）
WEARABLES = {
    "minecraft:carved_pumpkin": HEAD, "minecraft:skull": HEAD, "minecraft:skeleton_skull": HEAD,
    "minecraft:wither_skeleton_skull": HEAD, "minecraft:zombie_head": HEAD, "minecraft:player_head": HEAD,
    "minecraft:creeper_head": HEAD, "minecraft:dragon_head": HEAD, "minecraft:piglin_head": HEAD,
}


def addWearable(names, part=HEAD):
    """登记能穿戴在部位 part 上的东西（引擎物品信息里不是防具的：模组的帽子方块这类；两端都要执行到）。"""
    for name in names:
        WEARABLES[name] = part


def wearable(part):
    """装备格的 fits：能穿戴在部位 part（HEAD、CHEST、LEGS、FEET）上的东西，照原版的盔甲栏（另加登记过的 WEARABLES）。"""
    def fits(stack, rules):
        name = stack.get("newItemName")
        if name in WEARABLES:
            return WEARABLES[name] == part
        info = rules.info(name, stack.get("newAuxValue", 0)) if rules is not None else {}
        return info.get("itemType") == "armor" and info.get("armorSlot") == part
    return fits


# 原版允许放副手的东西（物品带"可放副手"的：盾、箭（含药箭，数据值不同）、烟花火箭、地图、不死图腾、鹦鹉螺壳）。引擎没有给脚本
# 查这一项的接口：自定义物品允许放副手的（minecraft:allow_off_hand、netease:allow_offhand、穿戴部位是副手的）经 addOffhand 登记
# （两端都要执行到）；引擎不收的写不进去（服务端核对后撤回）
OFFHAND_ITEMS = set(["minecraft:shield", "minecraft:arrow", "minecraft:firework_rocket", "minecraft:filled_map",
                     "minecraft:totem_of_undying", "minecraft:nautilus_shell"])


def addOffhand(names):
    """登记允许放副手的东西（模组物品写了允许放副手的；两端都要执行到）。"""
    OFFHAND_ITEMS.update(names)


def offhandable(stack, rules=None):
    """副手格的 fits：原版允许放副手的东西（OFFHAND_ITEMS）。"""
    return stack.get("newItemName") in OFFHAND_ITEMS


# 绑定诅咒：判断一件东西穿上了就拿不下来（装备格的 binding）的规则；缺省认原版的绑定诅咒，模组自己的附魔经 addBinding 登记
_binders = [lambda stack: Items.hasEnchantment(stack, Items.CURSE_OF_BINDING)]


def addBinding(predicate):
    """登记一条"穿上就拿不下来"的规则 predicate(物品堆) -> 真假（模组的诅咒附魔这类；两端都要执行到）。"""
    _binders.append(predicate)
    return predicate


def isBound(stack):
    """stack 穿上了就拿不下来（原版的绑定诅咒，或登记过的规则认它）。"""
    return not Items.isEmpty(stack) and any(binder(stack) for binder in _binders)


# 不能互相装的盒子：照原版潜影盒——这种盒子里不收这种盒子（收纳袋里装着的也算）。缺省认各种颜色的潜影盒，模组的背包、
# 存储箱子经 addUnnestable 登记（两端都要执行到）：它们进不了潜影盒，也进不了彼此
_unnestable = [lambda name: bool(name) and name.endswith("shulker_box")]


def addUnnestable(names=(), predicate=None):
    """登记不能互相装的盒子：物品名（方块名同名）或谓词 predicate(名字) -> 真假。"""
    names = frozenset(names)
    if names:
        _unnestable.append(names.__contains__)
    if predicate is not None:
        _unnestable.append(predicate)


def unnestable(name):
    """名字（物品名、方块名）是不是不能互相装的盒子（原版潜影盒与登记过的）。"""
    return any(rule(name) for rule in _unnestable)


def holdsUnnestable(stack):
    """stack（连同收纳袋里装着的）里有没有不能互相装的盒子。"""
    return any(unnestable(item.get("newItemName")) for item in Bundles.walk(stack))


def notUnnestable(stack, rules=None):
    """格子类型的 accept：不收不能互相装的盒子（潜影盒这类盒子的格子）。"""
    return not holdsUnnestable(stack)


class Equipment(SlotType):
    """
    装备（见模块说明）：fits(物品堆, 物品规则) -> 收不收；binding 为真时带绑定诅咒的拿不走（创造模式除外）；
    onEquip(会话, 格子, 原来的, 现在的) 在服务端内容变了之后调用。每格上限缺省 1。
    """

    def __init__(self, fits=None, binding=True, onEquip=None, maxStack=1, **options):
        SlotType.__init__(self, maxStack=maxStack, accept=fits, **options)
        self.binding = binding
        self.onEquip = onEquip

    def mayTake(self, ws, ref, stack):
        if self.binding and not ws.state.creative and isBound(stack):
            return False
        return SlotType.mayTake(self, ws, ref, stack)

    def onChanged(self, session, ref, old, new):
        if self.onEquip is not None:
            self.onEquip(session, ref, old, new)


# ---------------------------------------------------------------- 可停用的格子


class DisableInteraction(Interaction):
    """可停用格子的手势（见模块说明）。"""

    def _toggle(self, g, ref, off):
        slot = g.slotType(ref)
        g.forgetDoubleClick()
        g.call(slot.toggle, [ref[1], off])
        if off and slot.sound:
            g.sound(slot.sound)

    def _state(self, g, ref):
        """(停用着, 空着)。"""
        return not g.slotType(ref).isActive(g.workspace(), ref), Items.isEmpty(g.mirror.get(ref))

    def press(self, g, ref, button, now, position):
        disabled, empty = self._state(g, ref)
        cursor = g.mirror.get(CURSOR_REF)
        if disabled:
            if button != Rules.PRIMARY:
                return True   # 原版：停用的格子上盖着一个只认交互键的按钮，右键（手柄 X）不起作用
            self._toggle(g, ref, False)
            if not Items.isEmpty(cursor):
                g.do(("click", ref, Rules.PRIMARY))   # 原版的意图：拿着东西点停用的格子，启用后把手上的整堆放进去
            return True
        if empty and Items.isEmpty(cursor):
            self._toggle(g, ref, True)
            return True
        return False

    def touchPress(self, g, ref, now, position):
        disabled, empty = self._state(g, ref)
        if not disabled and not (empty and g.selection is None):
            return False
        g.forgetDoubleClick()
        g.hold(ref, Rules.PRIMARY, now, position, self)
        return True

    def holdTick(self, g, press, now, pointer):
        g.trackMove(press, pointer)

    def holdRelease(self, g, press, ref, now):
        if not g.tapped(press, ref, now):
            return
        disabled, empty = self._state(g, ref)
        if disabled:
            self._toggle(g, ref, False)
            selection = g.takeSelection()
            if selection is not None and not Items.isEmpty(g.mirror.get(selection["ref"])):
                g.standard.moveSelected(g, selection, ref)   # 启用后照普通的触屏搬运放进去
        elif empty and g.selection is None:
            self._toggle(g, ref, True)


class Disableable(SlotType):
    """可停用（见模块说明）。flags：每格停没停用的界面数据名；toggle：切换的动作名；sound：停用时的音效（None 不放）。"""

    interaction = DisableInteraction()

    def __init__(self, flags, toggle, sound=None, **options):
        SlotType.__init__(self, **options)
        self.flags = flags
        self.toggle = toggle
        self.sound = sound

    def isActive(self, ws, ref):
        return not (ws.data(self.flags) or {}).get(ref[1]) and SlotType.isActive(self, ws, ref)

    def hint(self, ws, ref):
        hint = SlotType.hint(self, ws, ref)
        if hint is not None:
            return hint
        return TOGGLE_HINT if self.isActive(ws, ref) else None

    def check(self, menu, name):
        SlotType.check(self, menu, name)
        menu.checkSlotData(name, self.flags, "Bool")
        menu.checkSlotAction(name, self.toggle, ("Int", "Bool"))


# ---------------------------------------------------------------- 虚拟格（列表视图的一项）

LIST_TAKE = 0       # 手上空着左键（手柄 A）：拿一组到手上
LIST_HALF = 1       # 手上空着右键（手柄 X）：拿半组（向上取整）到手上
LIST_QUICK = 2      # Shift 点击、手柄 Y、触屏没选中东西时点按：拿一组放进背包
LIST_PUT = 3        # 手上有东西左键、触屏选中了东西时点按：手上（选中格里选好）的放进去
LIST_PUT_ONE = 4    # 手上有东西右键（手柄 X）：放一个进去
LIST_DROP = 5       # 悬停时 Q：丢一个
LIST_DROP_ALL = 6   # 悬停时 Ctrl + Q：丢一组
LIST_MODES = (LIST_TAKE, LIST_HALF, LIST_QUICK, LIST_PUT, LIST_PUT_ONE, LIST_DROP, LIST_DROP_ALL)


class VirtualInteraction(Interaction):
    """虚拟格的手势（见模块说明）：都变成界面模型的动作，结果随应答回来（不预测）。"""

    def _send(self, g, ref, mode, held=CURSOR_REF, amount=0):
        g.forgetDoubleClick()
        g.lastActionRef = ref
        g.call(g.slotType(ref).action, [ref[1], mode, g.wire(held), amount])

    def press(self, g, ref, button, now, position):
        if not Items.isEmpty(g.mirror.get(CURSOR_REF)):
            self._send(g, ref, LIST_PUT if button == Rules.PRIMARY else LIST_PUT_ONE)
        elif not Items.isEmpty(g.mirror.get(ref)):
            self._send(g, ref, LIST_TAKE if button == Rules.PRIMARY else LIST_HALF)
        return True

    def quick(self, g, ref):
        if not Items.isEmpty(g.mirror.get(ref)):
            self._send(g, ref, LIST_QUICK)
        return True

    def drop(self, g, ref, whole):
        if not Items.isEmpty(g.mirror.get(ref)):
            self._send(g, ref, LIST_DROP_ALL if whole else LIST_DROP)
        return True

    def hotbar(self, g, ref, index):
        return True

    def touchPress(self, g, ref, now, position):
        g.forgetDoubleClick()
        g.hold(ref, Rules.PRIMARY, now, position, self)
        return True

    def holdTick(self, g, press, now, pointer):
        g.trackMove(press, pointer)

    def holdRelease(self, g, press, ref, now):
        if not g.tapped(press, ref, now):
            return
        selection = g.takeSelection()
        if selection is not None:
            if not Items.isEmpty(g.mirror.get(selection["ref"])):
                self._send(g, ref, LIST_PUT, selection["ref"], selection["amount"] or 0)
        elif not Items.isEmpty(g.mirror.get(ref)):
            self._send(g, ref, LIST_QUICK)


class Virtual(SlotType):
    """
    虚拟（见模块说明）。entries：界面数据里每格物品（Data.SlotValues(Data.Item(), 集合)）的名字；action：取放的动作名，
    参数依次是格号（Schema.Int）、方式（Schema.Int，LIST_*）、手上那一格（Schema.Ref(cursor=True)）、数量（Schema.Int，
    0 为整堆）。集合要落在不放东西的容器上。
    """

    interaction = VirtualInteraction()
    returnsOnClose = False

    def __init__(self, entries, action, **options):
        SlotType.__init__(self, **options)
        self.itemsFrom = entries
        self.action = action

    def mayPlace(self, ws, ref, stack):
        return False

    def mayTake(self, ws, ref, stack):
        return False

    def check(self, menu, name):
        SlotType.check(self, menu, name)
        menu.checkSlotAction(name, self.action, ("Int", "Int", "Ref", "Int"))


# ---------------------------------------------------------------- 可选的一项（切石机的配方按钮）

CHOICE_CELLS = ("textures/ui/cell_image_normal", "textures/ui/cell_image_invert")   # 原版切石机：没选中、选中的底格
CHOICE_SOUND = "random.click"   # 原版按钮的声音


class ChoiceInteraction(Interaction):
    """可选的一项的手势（见模块说明）：按下就选中，不进入拖动分配、渐进拿取与收集同类。"""

    def _select(self, g, ref):
        g.forgetDoubleClick()
        g.lastActionRef = ref
        slot = g.slotType(ref)
        if g.call(slot.select, [ref[1]]) and slot.sound:
            g.sound(slot.sound)
        return True

    def press(self, g, ref, button, now, position):
        return self._select(g, ref)

    def touchPress(self, g, ref, now, position):
        return self._select(g, ref)

    def quick(self, g, ref):
        return self._select(g, ref)

    def drop(self, g, ref, whole):
        return self._select(g, ref)

    def hotbar(self, g, ref, index):
        return True


class Choice(SlotType):
    """可选的一项（见模块说明）。select：选中的动作名（参数是格号）；selected：选中的格号的名字；cells：(没选中, 选中) 的底格。"""

    interaction = ChoiceInteraction()
    computed = True
    returnsOnClose = False

    def __init__(self, select, selected, cells=CHOICE_CELLS, sound=CHOICE_SOUND, **options):
        SlotType.__init__(self, **options)
        self.select = select
        self.selected = selected
        self.cells = tuple(cells)
        self.sound = sound

    def mayPlace(self, ws, ref, stack):
        return False

    def mayTake(self, ws, ref, stack):
        return False

    def decorate(self, ws, ref, stack):
        out = Decoration()
        viewer = ws.viewer or {}
        chosen = viewer.get(self.selected) if self.selected in viewer else ws.data(self.selected)
        out.cell = self.cells[1] if chosen == ref[1] else self.cells[0]
        return out

    def check(self, menu, name):
        SlotType.check(self, menu, name)
        field = menu.viewerState.get(self.selected) or menu.data.get(self.selected)
        if not isinstance(field, Data.Int):
            raise ValueError("menu %s: collection %s chooses by %r, which must be a Data.Int viewer state or data"
                             % (menu.menuName, name, self.selected))
        menu.checkSlotAction(name, self.select, ("Int",))
