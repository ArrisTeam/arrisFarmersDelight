# -*- coding: utf-8 -*-
"""PotStation - 厨锅站点的纯规则：站点声明（schema）、放料规则、份数、下锅就沉的料、徽章与提示文字（双端）

对应 Hands-On Delight：station/CookingPotStation.java（schema、isDish）与 station/PotLogic.java 的 mayPlace / servingsLeft /
sinks / containerSlot。选菜与把料摆回格子在 PotLayout.py（StationRecipes 的移植），下锅就沉的料表在 Shared/Data/PotSunk.py。
本移植的配方是"每个非空食材格算一件、(物品名, aux) 精确匹配"（Shared/Rules/CookingPot.py），所以一份每格用 1 件，
份数就是非空格里最少的那格。两个番茄的番茄酱要占两格：站点放进来的料按配方摆开（layout），玩家不用自己分格；
凑不出任何配方的料原样放着（HoD："Food that makes nothing stays as it lies"）。
食材格是 6 项的列表，每项是物品字典（newItemName / newAuxValue / count）或空（None / {}）。
"""
from .CookingPot import isIngredient, isVessel, vesselOf  # noqa: F401 - 站点的放料判定、盛菜容器
from .HandsOn.PotCooking import FD_WAY, WAITING
from .PotLayout import INPUT_SLOTS, choose, countOf, keyOf, kindsOf, lay, layout, planFill  # noqa: F401 - 站点和测试从这里取
from ..Data.PotSunk import SUNK

STATION_ID = "arris:cooking_pot"
POT_BLOCKS = ("arris:cooking_pot",)
COOK_SECONDS = 10.0          # 一份的配方时长（秒）：FD 原样一份一份煮、搅拌整批煮都按它算
HOTBAR = 9                   # 背包的前 9 格是快捷栏（0-8）
DISHES = frozenset(["minecraft:bowl", "minecraft:glass_bottle"])    # 盛菜用的，不下锅（CookingPotStation.isDish）

GROUP_INGREDIENTS = "ingredients"      # 站点的槽组：6 格食材 = 方块容器格 0..5
GROUP_SERVED = "served"                # 1 格只能取的产出 = 方块容器格 7（FD 的产出格）
CONTROLS = ("progress", "heated", "stirring", "spoon_x", "spoon_z", "stars")    # 都是只有服务端能改的


def acceptsIngredient(item):
    """schema 里 ingredients 槽组的 accepts：碗和玻璃瓶是盛菜的，不下锅。"""
    return item.get("newItemName") not in DISHES


def acceptsNothing(item):
    """schema 里 served 槽组的 accepts：只能取，不能放。"""
    return False


def buildSchema(kit):
    """站点的声明，两端各建一份一模一样的（服务端登记站点、客户端登记表现时用）。
    kit 是带 StationSchema / ControlSpec / SlotRules 的东西：前置包的服务端 Api 模块，或它的 Shared/Schema 模块（客户端经
    ImportModule 拿）；这里不导入前置包，Shared 保持纯。控件都 locked：只有服务端按锅的状态写。
    progress 0..1 分 100 步；spoon_x / spoon_z 是勺尖在世界朝向里的位置（方块中心为原点，-1..1 是勺子够得着的范围）分 64 步；
    stars 0..3 分 60 步（HoD 的 CookingPotStation.schema）。"""
    kept = kit.SlotRules.DEFAULT.kept()
    control = kit.ControlSpec
    return (kit.StationSchema.builder()
            .slots(GROUP_INGREDIENTS, INPUT_SLOTS, kept.withAccepts(acceptsIngredient))
            .slots(GROUP_SERVED, 1, kept.withAccepts(acceptsNothing))
            .control("progress", control.stepped(0.0, 1.0, 100, 0.0).locked())
            .control("heated", control.toggle(False).locked())
            .control("stirring", control.toggle(False).locked())
            .control("spoon_x", control.stepped(-1.0, 1.0, 64, 0.0).locked())
            .control("spoon_z", control.stepped(-1.0, 1.0, 64, 0.0).locked())
            .control("stars", control.stepped(0.0, 3.0, 60, 0.0).locked())
            .build())


def mayPlace(item):
    """PotLogic.mayPlace：配方里的料都收；不是料的东西，除了某道菜盛菜用的容器，也都收（凑不成菜的料原样放着，不拦）。"""
    key = keyOf(item)
    return key is not None and (isIngredient(key) or not isVessel(key[0]))


def usable(key):
    """背包托盘里这种物品亮不亮：是某个配方的食材，或是某道菜盛菜用的容器（HoD 的 usable）。key 是 (物品名, aux)。"""
    return key is not None and (isIngredient(key) or isVessel(key[0]))


def isSunk(key):
    """这种料下锅就沉（倒进去的液体、打进去的蛋、化掉的粉），浮不起来、点不到，只能取回（PotLogic.sinks）。"""
    return key in SUNK


def sunkSlots(slots):
    """食材格里装着下锅就沉的料的格号（升序）。"""
    return [index for index, slot in enumerate(slots) if isSunk(keyOf(slot))]


def containerSlot(window, selected, name):
    """空手盛菜时从背包里挑装菜的容器格：选中的快捷栏格优先，然后 0.. 按序；没有返回 -1（PotLogic.containerSlot）。
    window 是背包的格子（物品字典或 None），name 是容器的物品名。"""
    def holds(index):
        item = window[index]
        return bool(item) and item.get("newItemName") == name and (item.get("count") or 0) > 0

    if 0 <= selected < min(HOTBAR, len(window)) and holds(selected):
        return selected
    for index in range(len(window)):
        if holds(index):
            return index
    return -1


def servingsLeft(slots):
    """料够做几份：非空格里最少的那格（一份每格用 1 件）。"""
    counts = [countOf(slot) for slot in slots if countOf(slot) > 0]
    return min(counts) if counts else 0


def foodCount(slots):
    return sum(countOf(slot) for slot in slots)


def badgeOf(data):
    """站点同步来的数据 -> 焦点界面顶部的徽章（星星、菜、进度）；锅里没菜可做也没菜可盛时 None。"""
    if data.get("meals"):
        grade = data.get("grade") or 0
        return {"item": data.get("meal"), "stars": grade, "open": max(grade, data.get("open") or 1), "progress": None}
    if data.get("dish"):
        return {"item": data.get("dish"), "stars": data.get("stars") or 0.0, "open": data.get("open") or 1,
                "progress": data.get("progress") or 0.0}
    return None


def statusText(data):
    """站点同步来的数据 -> 焦点界面底部的一行提示（星星和进度在徽章上）。mode 是锅上一步的煮法（WAITING / FD_WAY / STIRRED）。"""
    if data.get("meals"):
        need = "（要%s）" % data.get("vesselName") if data.get("vesselName") else ""
        return "点锅边浮着的菜盛出 %d 份%s   拖动勺子接着搅" % (data["meals"], need)
    if not any(keyOf(slot) for slot in data.get("inputs") or []):
        return "点下方物品栏把食材放进锅里   潜行右键 = 原来的界面"
    if not data.get("dish"):
        return "这些料凑不出菜：点锅里的料取回"
    if not data.get("heated"):
        return "锅下面没有热源：放在炉灶、营火或岩浆块上"
    if data.get("mode") == FD_WAY:
        return "锅在自己一份一份地煮   拖动勺子搅拌：整批一起煮"
    batch = data.get("batch") or 0
    if data.get("mode") == WAITING:
        return "拖动勺子搅拌才会煮   这批 %d 份" % batch
    return "搅拌中   这批 %d 份，还要 %d 秒" % (batch, data.get("left") or 0)
