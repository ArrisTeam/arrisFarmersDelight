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

配料照 JE 的 FD 1.3.4（recipes/cooking/）一格一格写：JE 写标签的格子写标签（JE 的 forge: 标签名换成词表的 common: 名，Shared/Data/Tags.py
的 JE_NAMES；鸡蛋用原版的 minecraft:egg，蓝色、棕色鸡蛋也收），JE 写物品的写物品（farmersdelight: 换成 arris:）。tests/test_cooking_pot_data.py
对着 .refs 里 JE 的配方文件逐格核对。Recipe 是把同一份格子展开成的写法（_ways）：标签按词表里农夫乐事登记的成员展开（和原来那几张 JE 标签的
展开列表一个顺序），鸡蛋只展开普通鸡蛋——旧读者看到的还是原来的 170 种写法；别的模组进了标签的料、蓝色棕色鸡蛋只有 Slots 认。
下游模组运行时会往表里追加配方（Api/LegacyModAttr.py），查配方见 Shared/Rules/CookingPot.py；表被修改后要调用它的 rebuildIndex()。
"""
from . import Tags

_ID = "farmersdelight:cooking/"
_LEGACY = {Tags.EGG: ("minecraft:egg",)}       # 旧写法里鸡蛋只有普通鸡蛋（原来就是这样）；别的标签按词表里农夫乐事登记的成员展开


def _tag(name):
    return "#" + name


def _options(slot):
    """一格的写法（一个选项，或几个选项的列表）-> 展开旧写法用的物品名（标签换成农夫乐事登记的成员）。"""
    found = []
    for option in ([slot] if isinstance(slot, str) else slot):
        found += list(_LEGACY.get(option[1:], Tags.ITEM_TAGS.get(option[1:], ()))) if option.startswith("#") else [option]
    return found


def _ways(*slots):
    """每格能放的料（一个物品名，或一组可替换的物品名；"#标签" 按词表的成员）-> 全部写法 [[(物品名, 0), ...], ...]；排好序后相同的写法只留一种。"""
    ways, seen = [[]], set()
    for slot in slots:
        ways = [way + [(name, 0)] for way in ways for name in _options(slot)]
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


_BEEF, _PORK, _CHICKEN, _MUTTON, _MEAT = _tag(Tags.RAW_BEEF), _tag(Tags.RAW_PORK), _tag(Tags.RAW_CHICKEN), _tag(Tags.RAW_MUTTON), _tag(Tags.RAW_MEAT)
_FISH, _COD = _tag(Tags.RAW_FISH), _tag(Tags.RAW_COD)
_CABBAGE, _VEGETABLE, _MUSHROOM, _MILK, _BERRY = (_tag(Tags.CABBAGE), _tag(Tags.VEGETABLE), _tag(Tags.MUSHROOMS), _tag(Tags.MILK),
                                                  _tag(Tags.BERRY))
_TOMATO, _ONION, _CARROT, _POTATO, _BEETROOT = (_tag(Tags.TOMATO), _tag(Tags.ONION), _tag(Tags.CARROT), _tag(Tags.POTATO),
                                                _tag(Tags.BEETROOT))
_RICE, _PASTA, _DOUGH, _BREAD, _BONE, _EGG = (_tag(Tags.RICE), _tag(Tags.PASTA), _tag(Tags.DOUGH), _tag(Tags.BREAD), _tag(Tags.BONES),
                                              _tag(Tags.EGG))
_MUSHROOMS = ["minecraft:brown_mushroom", "minecraft:red_mushroom"]      # JE 在这两格写的是物品，不是 #forge:mushrooms

_BOWL = ("minecraft:bowl", 0)
_BOTTLE = ("minecraft:glass_bottle", 0)

# 厨锅配方
CookingPotRecipeList = [
    _dish("mushroom_stew", _MUSHROOMS,
          CookResult=("minecraft:mushroom_stew", 0), Vessel=_BOWL, PushItem=[], text="蘑菇煲"),
    _dish("beetroot_soup", [_BEETROOT, _BEETROOT, _BEETROOT],
          CookResult=("minecraft:beetroot_soup", 0), Vessel=_BOWL, PushItem=[], text="甜菜汤"),
    _dish("rabbit_stew", [_POTATO, "minecraft:rabbit", _CARROT, _MUSHROOMS],
          CookResult=("minecraft:rabbit_stew", 0), Vessel=_BOWL, PushItem=[], text="兔肉煲"),
    _dish("tomato_sauce", [_TOMATO, _TOMATO],
          CookResult=("arris:tomato_sauce", 0), Vessel=_BOWL, PushItem=[], text="番茄酱", CookTime=5.0, Experience=0.35),
    _dish("cooked_rice", [_RICE],
          CookResult=("arris:cooked_rice", 0), Vessel=_BOWL, PushItem=[], text="米饭", CookTime=5.0, Experience=0.35),
    _dish("fried_rice", [_RICE, _EGG, _CARROT, _ONION],
          CookResult=("arris:fried_rice", 0), Vessel=_BOWL, PushItem=[], text="炒饭"),
    _dish("dumplings", [_DOUGH, _CABBAGE, _ONION, [_CHICKEN, _PORK, _BEEF, "minecraft:brown_mushroom"]],
          CookResult=("arris:dumplings", 0), CookCount=2, PushItem=[], text="饺子"),
    _dish("pasta_with_meatballs", ["arris:minced_beef", _PASTA, "arris:tomato_sauce"],
          CookResult=("arris:pasta_with_meatballs", 0), Vessel=_BOWL, PushItem=[], text="肉丸意面"),
    _dish("pasta_with_mutton_chop", [_MUTTON, _PASTA, "arris:tomato_sauce"],
          CookResult=("arris:pasta_with_mutton_chop", 0), Vessel=_BOWL, PushItem=[], text="羊排意面"),
    _dish("mushroom_rice", ["minecraft:brown_mushroom", "minecraft:red_mushroom", _RICE, ["minecraft:carrot", "minecraft:potato"]],
          CookResult=("arris:mushroom_rice", 0), Vessel=_BOWL, PushItem=[], text="蘑菇饭"),
    _dish("vegetable_noodles", [_CARROT, _MUSHROOM, _PASTA, _CABBAGE, _VEGETABLE],
          CookResult=("arris:vegetable_noodles", 0), Vessel=_BOWL, PushItem=[], text="蔬菜面"),
    _dish("ratatouille", [_TOMATO, _ONION, _BEETROOT, _VEGETABLE],
          CookResult=("arris:ratatouille", 0), Vessel=_BOWL, PushItem=[], text="蔬菜杂烩"),
    _dish("squid_ink_pasta", [_FISH, _PASTA, _TOMATO, "minecraft:ink_sac"],
          CookResult=("arris:squid_ink_pasta", 0), Vessel=_BOWL, PushItem=[], text="鱿鱼墨面"),
    _dish("stuffed_pumpkin_block", [_RICE, _ONION, "minecraft:brown_mushroom", _POTATO, _BERRY, _VEGETABLE],
          CookResult=("arris:stuffed_pumpkin_block_stage0", 0), Vessel=("minecraft:pumpkin", 0), PushItem=[],
          text="填馅南瓜", CookTime=20.0, Experience=2.0),
    _dish("cabbage_rolls", [_CABBAGE, [_MEAT, _FISH, _VEGETABLE, _MUSHROOM]],
          CookResult=("arris:cabbage_rolls", 0), PushItem=[], text="卷心菜卷", CookTime=5.0, Experience=0.35),
    _dish("bone_broth", [_BONE, ["minecraft:glow_berries", _MUSHROOM, "minecraft:hanging_roots", "minecraft:glow_lichen"]],
          CookResult=("arris:bone_broth", 0), Vessel=_BOWL, PushItem=[], text="大骨汤", Experience=0.35),
    _dish("beef_stew", [_BEEF, _CARROT, _POTATO],
          CookResult=("arris:cookbeef_stew", 0), Vessel=_BOWL, PushItem=[], text="牛肉炖"),
    _dish("chicken_soup", [_CHICKEN, _CARROT, _CABBAGE, _VEGETABLE],
          CookResult=("arris:chicken_soup", 0), Vessel=_BOWL, PushItem=[], text="鸡肉汤"),
    _dish("vegetable_soup", [_CARROT, _POTATO, _BEETROOT, _CABBAGE],
          CookResult=("arris:vegetable_soup", 0), Vessel=_BOWL, PushItem=[], text="蔬菜汤"),
    _dish("fish_stew", [_FISH, "arris:tomato_sauce", _ONION],
          CookResult=("arris:fish_stew", 0), Vessel=_BOWL, PushItem=[], text="鱼肉炖"),
    _dish("pumpkin_soup", ["arris:pumpkin_slice", _CABBAGE, _PORK, _MILK],
          CookResult=("arris:pumpkin_soup", 0), Vessel=_BOWL, PushItem=[], text="南瓜汤"),
    _dish("onion_soup", [_ONION, _ONION, _BREAD, _MILK],
          CookResult=("arris:onion_soup", 0), Vessel=_BOWL, PushItem=[], text="洋葱汤"),
    _dish("baked_cod_stew", [_COD, _POTATO, _EGG, _TOMATO],
          CookResult=("arris:baked_cod_stew", 0), Vessel=_BOWL, PushItem=[], text="烘焙鳕鱼炖"),
    _dish("noodle_soup", [_PASTA, _EGG, "minecraft:dried_kelp", _PORK],
          CookResult=("arris:noodle_soup", 0), Vessel=_BOWL, PushItem=[], text="面条汤"),
    _dish("hot_cocoa", [_MILK, "minecraft:sugar", "minecraft:cocoa_beans", "minecraft:cocoa_beans"],
          CookResult=("arris:hot_cocoa", 0), Vessel=_BOTTLE, PushItem=[], text="热可可"),
    _dish("apple_cider", ["minecraft:apple", "minecraft:apple", "minecraft:sugar"],
          CookResult=("arris:apple_cider", 0), Vessel=_BOTTLE, PushItem=[], text="苹果酒"),
    _dish("glow_berry_custard", ["minecraft:glow_berries", _MILK, _EGG, "minecraft:sugar"],
          CookResult=("arris:glow_berry_custard", 0), Vessel=_BOTTLE, PushItem=[], text="发光浆果蛋奶沙司"),
    _dish("dog_food", ["minecraft:rotten_flesh", "minecraft:bone_meal", _MEAT, _RICE],
          CookResult=("arris:dog_food", 0), Vessel=_BOWL, PushItem=[], text="狗粮"),
]
