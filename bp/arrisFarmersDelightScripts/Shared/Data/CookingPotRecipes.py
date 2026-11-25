# -*- coding: utf-8 -*-
"""CookingPotRecipes - 厨锅配方表（双端，纯数据）

每条配方（一个字典）：
- Id：配方 ID。农夫乐事自己的 28 道照 JE：farmersdelight:cooking/<JE 的配方文件名>；旧接口追加进来的没有这个键（查的时候派生一个只读的）；
- Slots：每格能放什么，一格可以并列几个选项：物品名 "ns:name"（aux 0）、(物品名, aux)、"#标签名"（写法和怎么配见 Shared/Rules/PotSlots.py）；
- Recipe：旧格式的写法列表 [[(物品名, aux), ...], ...]（每种写法最多 6 件）：只认物品的旧读者在读、联动契约的 AddCookingPotRecipe 往里追加，照旧保留；
- CookResult、CookCount（一份出几个，缺省 1）、Vessel（盛出成品要的容器，可缺省）、PushItem（出锅时额外吐出的东西）、text（界面显示名）、
  CookTime（一份煮多久，秒；缺省 10 秒 = JE 的 200 刻）、Experience（盛出一份给的经验，缺省 1.0）；
- Disabled：被移除的配方留的墓碑：行不摘掉（很多地方拿下标当身份），读的地方都跳过它。
用掉的料自带的空容器（奶桶的桶、奶瓶的玻璃瓶）由 Shared/Rules/CookingPot.py 按料算出来一起吐出，不用写进 PushItem。

配料照 JE 的 FD 1.3.4（recipes/cooking/）：Slots 一格一格对着 JE 的 ingredients 写，Recipe 是把 Slots 展开成的写法（_ways）；JE 用标签的格子，
标签的内容照 JE 的 forge 标签换成基岩版的物品名（生肉含 FD 切好的肉丁 / 肉排 / 培根，生鱼含鱼片，卷心菜含卷心菜叶，奶含奶桶和奶瓶）。
下游模组运行时会往表里追加配方（Api/LegacyModAttr.py），查配方见 Shared/Rules/CookingPot.py；表被修改后要调用它的 rebuildIndex()。
"""

_ID = "farmersdelight:cooking/"


def _ways(*slots):
    """每格能放的料（一个物品名，或一组可替换的物品名）-> 全部写法 [[(物品名, 0), ...], ...]；排好序后相同的写法只留一种。"""
    ways, seen = [[]], set()
    for slot in slots:
        options = [slot] if isinstance(slot, str) else slot
        ways = [way + [(name, 0)] for way in ways for name in options]
    unique = []
    for way in ways:
        key = tuple(sorted(way))
        if key not in seen:
            seen.add(key)
            unique.append(way)
    return unique


def _dish(path, slots, **fields):
    """农夫乐事的一道菜：配方 ID（JE 的配方文件名）、每格的选项（Slots）、展开出来的写法（Recipe），再加上别的字段。"""
    row = {"Id": _ID + path, "Slots": [[slot] if isinstance(slot, str) else list(slot) for slot in slots], "Recipe": _ways(*slots)}
    row.update(fields)
    return row


# JE 的 forge 标签（基岩版物品名）
_RAW_BEEF = ["minecraft:beef", "arris:minced_beef"]
_RAW_CHICKEN = ["minecraft:chicken", "arris:chicken_cuts"]
_RAW_PORK = ["minecraft:porkchop", "arris:bacon"]
_RAW_MUTTON = ["minecraft:mutton", "arris:mutton_chops"]
_RAW_MEAT = ["minecraft:rabbit"] + _RAW_BEEF + _RAW_CHICKEN + _RAW_PORK + _RAW_MUTTON
_RAW_COD = ["minecraft:cod", "arris:cod_slice"]
_RAW_FISHES = _RAW_COD + ["minecraft:salmon", "arris:salmon_slice", "minecraft:tropical_fish"]
_CABBAGE = ["arris:cabbage", "arris:cabbage_leaf"]
_VEGETABLES = ["minecraft:beetroot", "minecraft:carrot", "arris:onion", "minecraft:potato", "arris:tomato"]
_MUSHROOMS = ["minecraft:brown_mushroom", "minecraft:red_mushroom"]
_MILK = ["minecraft:milk_bucket", "arris:milk_bottle"]
_BERRIES = ["minecraft:sweet_berries", "minecraft:glow_berries"]

_BOWL = ("minecraft:bowl", 0)
_BOTTLE = ("minecraft:glass_bottle", 0)

# 厨锅配方
CookingPotRecipeList = [
    _dish("mushroom_stew", ["minecraft:brown_mushroom", "minecraft:red_mushroom"],
          CookResult=("minecraft:mushroom_stew", 0), Vessel=_BOWL, PushItem=[], text="蘑菇煲"),
    _dish("beetroot_soup", ["minecraft:beetroot", "minecraft:beetroot", "minecraft:beetroot"],
          CookResult=("minecraft:beetroot_soup", 0), Vessel=_BOWL, PushItem=[], text="甜菜汤"),
    _dish("rabbit_stew", ["minecraft:potato", "minecraft:rabbit", "minecraft:carrot", _MUSHROOMS],
          CookResult=("minecraft:rabbit_stew", 0), Vessel=_BOWL, PushItem=[], text="兔肉煲"),
    _dish("tomato_sauce", ["arris:tomato", "arris:tomato"],
          CookResult=("arris:tomato_sauce", 0), Vessel=_BOWL, PushItem=[], text="番茄酱", CookTime=5.0, Experience=0.35),
    _dish("cooked_rice", ["arris:rice"],
          CookResult=("arris:cooked_rice", 0), Vessel=_BOWL, PushItem=[], text="米饭", CookTime=5.0, Experience=0.35),
    _dish("fried_rice", ["arris:rice", "minecraft:egg", "minecraft:carrot", "arris:onion"],
          CookResult=("arris:fried_rice", 0), Vessel=_BOWL, PushItem=[], text="炒饭"),
    _dish("dumplings", ["arris:wheat_dough", _CABBAGE, "arris:onion", _RAW_CHICKEN + _RAW_PORK + _RAW_BEEF + ["minecraft:brown_mushroom"]],
          CookResult=("arris:dumplings", 0), CookCount=2, PushItem=[], text="饺子"),
    _dish("pasta_with_meatballs", ["arris:minced_beef", "arris:raw_pasta", "arris:tomato_sauce"],
          CookResult=("arris:pasta_with_meatballs", 0), Vessel=_BOWL, PushItem=[], text="肉丸意面"),
    _dish("pasta_with_mutton_chop", [_RAW_MUTTON, "arris:raw_pasta", "arris:tomato_sauce"],
          CookResult=("arris:pasta_with_mutton_chop", 0), Vessel=_BOWL, PushItem=[], text="羊排意面"),
    _dish("mushroom_rice", ["minecraft:brown_mushroom", "minecraft:red_mushroom", "arris:rice", ["minecraft:carrot", "minecraft:potato"]],
          CookResult=("arris:mushroom_rice", 0), Vessel=_BOWL, PushItem=[], text="蘑菇饭"),
    _dish("vegetable_noodles", ["minecraft:carrot", _MUSHROOMS, "arris:raw_pasta", _CABBAGE, _VEGETABLES],
          CookResult=("arris:vegetable_noodles", 0), Vessel=_BOWL, PushItem=[], text="蔬菜面"),
    _dish("ratatouille", ["arris:tomato", "arris:onion", "minecraft:beetroot", _VEGETABLES],
          CookResult=("arris:ratatouille", 0), Vessel=_BOWL, PushItem=[], text="蔬菜杂烩"),
    _dish("squid_ink_pasta", [_RAW_FISHES, "arris:raw_pasta", "arris:tomato", "minecraft:ink_sac"],
          CookResult=("arris:squid_ink_pasta", 0), Vessel=_BOWL, PushItem=[], text="鱿鱼墨面"),
    _dish("stuffed_pumpkin_block", ["arris:rice", "arris:onion", "minecraft:brown_mushroom", "minecraft:potato", _BERRIES, _VEGETABLES],
          CookResult=("arris:stuffed_pumpkin_block_stage0", 0), Vessel=("minecraft:pumpkin", 0), PushItem=[],
          text="填馅南瓜", CookTime=20.0, Experience=2.0),
    _dish("cabbage_rolls", [_CABBAGE, _RAW_MEAT + _RAW_FISHES + _VEGETABLES + _MUSHROOMS],
          CookResult=("arris:cabbage_rolls", 0), PushItem=[], text="卷心菜卷", CookTime=5.0, Experience=0.35),
    _dish("bone_broth", ["minecraft:bone", ["minecraft:glow_berries"] + _MUSHROOMS + ["minecraft:hanging_roots", "minecraft:glow_lichen"]],
          CookResult=("arris:bone_broth", 0), Vessel=_BOWL, PushItem=[], text="大骨汤", Experience=0.35),
    _dish("beef_stew", [_RAW_BEEF, "minecraft:carrot", "minecraft:potato"],
          CookResult=("arris:cookbeef_stew", 0), Vessel=_BOWL, PushItem=[], text="牛肉炖"),
    _dish("chicken_soup", [_RAW_CHICKEN, "minecraft:carrot", _CABBAGE, _VEGETABLES],
          CookResult=("arris:chicken_soup", 0), Vessel=_BOWL, PushItem=[], text="鸡肉汤"),
    _dish("vegetable_soup", ["minecraft:carrot", "minecraft:potato", "minecraft:beetroot", _CABBAGE],
          CookResult=("arris:vegetable_soup", 0), Vessel=_BOWL, PushItem=[], text="蔬菜汤"),
    _dish("fish_stew", [_RAW_FISHES, "arris:tomato_sauce", "arris:onion"],
          CookResult=("arris:fish_stew", 0), Vessel=_BOWL, PushItem=[], text="鱼肉炖"),
    _dish("pumpkin_soup", ["arris:pumpkin_slice", _CABBAGE, _RAW_PORK, _MILK],
          CookResult=("arris:pumpkin_soup", 0), Vessel=_BOWL, PushItem=[], text="南瓜汤"),
    _dish("onion_soup", ["arris:onion", "arris:onion", "minecraft:bread", _MILK],
          CookResult=("arris:onion_soup", 0), Vessel=_BOWL, PushItem=[], text="洋葱汤"),
    _dish("baked_cod_stew", [_RAW_COD, "minecraft:potato", "minecraft:egg", "arris:tomato"],
          CookResult=("arris:baked_cod_stew", 0), Vessel=_BOWL, PushItem=[], text="烘焙鳕鱼炖"),
    _dish("noodle_soup", ["arris:raw_pasta", "minecraft:egg", "minecraft:dried_kelp", _RAW_PORK],
          CookResult=("arris:noodle_soup", 0), Vessel=_BOWL, PushItem=[], text="面条汤"),
    _dish("hot_cocoa", [_MILK, "minecraft:sugar", "minecraft:cocoa_beans", "minecraft:cocoa_beans"],
          CookResult=("arris:hot_cocoa", 0), Vessel=_BOTTLE, PushItem=[], text="热可可"),
    _dish("apple_cider", ["minecraft:apple", "minecraft:apple", "minecraft:sugar"],
          CookResult=("arris:apple_cider", 0), Vessel=_BOTTLE, PushItem=[], text="苹果酒"),
    _dish("glow_berry_custard", ["minecraft:glow_berries", _MILK, "minecraft:egg", "minecraft:sugar"],
          CookResult=("arris:glow_berry_custard", 0), Vessel=_BOTTLE, PushItem=[], text="发光浆果蛋奶沙司"),
    _dish("dog_food", ["minecraft:rotten_flesh", "minecraft:bone_meal", _RAW_MEAT, "arris:rice"],
          CookResult=("arris:dog_food", 0), Vessel=_BOWL, PushItem=[], text="狗粮"),
]
