# -*- coding: utf-8 -*-
"""BoardSounds - 砧板站点各种事件放什么声音、多大声、什么音调（双端，纯规则）

对应 Hands-On Delight：client/BoardBehavior.java 的 chopped / onEffect / pop（1350-1490、1650-1651），加上 FD 自己的切声
（CuttingBoardBlockEntity.playProcessingSound：配方的 sound -> 剪刀 -> 刀 0.8 -> 方块的破坏声 1.0 / 0.8 -> 木头破坏声 1.0 / 0.8，最后一刀响一次）。
每条声音是 (声音名, 音量, 音调)。JE 的声音事件换成基岩版的名字（都在原版 sound_definitions.json 里，刀声是本包自己的）：
    KNIFE_CUT                  ambient.cutting_board.knife
    AXE_STRIP / SHOVEL_FLATTEN use.wood / use.grass
    SHEEP_SHEAR                mob.sheep.shear
    BOARD_PLACE / BOARD_CARVE  dig.wood（FD 的 place_item / carve_tool 就是原版木头的放置声）
    BOARD_REMOVE / WOOD_HIT    hit.wood（FD 的 remove_item 是原版木头的击打声）
    ITEM_PICKUP                random.pop
    被切东西的材质击打 / 破坏    hit.* / dig.*（按物品名里的词分类，认不出是木头，和 JE 的 material() 一样）
随机的那一点音调由调用方传进来的 rng 给（测试里换成定值）。站点里的人（客户端 BoardView）和旁观的人（客户端 BoardWatch）用同一份，所以两边听到的一样。
"""
import random

from .HandsOn import Cutting

KNIFE_CUT = "ambient.cutting_board.knife"
AXE_STRIP = "use.wood"
SHOVEL_FLATTEN = "use.grass"
SHEEP_SHEAR = "mob.sheep.shear"
BOARD_PLACE = "dig.wood"
BOARD_CARVE = "dig.wood"
BOARD_REMOVE = "hit.wood"
WOOD_HIT = "hit.wood"
ITEM_PICKUP = "random.pop"

KNOCK = (WOOD_HIT, 0.25, 1.6)                   # 刀敲在食物上、没落在刀口线上（本人）
BOUNCE = (WOOD_HIT, 0.4, 1.4)                   # 板不收：弹回的那一声（本人）
SETTLE = (BOARD_PLACE, 0.5, 0.8)                # 层凑成一道等点的菜：各层落定
PICKUP_TAKEN = (ITEM_PICKUP, 0.3, 1.5)          # 取走一样
PICKUP_STROKE = (ITEM_PICKUP, 0.35, 1.3)        # 最后一刀：切好的东西飞给厨师
CARVE = (BOARD_CARVE, 1.0, 0.8)                 # 插一把工具
REMOVE = (BOARD_REMOVE, 0.6, 0.9)               # 拔出插着的工具
ASSEMBLED = ((BOARD_PLACE, 0.8, 0.75), (ITEM_PICKUP, 0.35, 1.4))      # 做成一道菜

# 被切的东西是什么做的（JE 取它的方块的 SoundType）：(材质, 名字里的词)，先到先得；黏土按砂砾算（JE 的 clay 就是砂砾的声音）
_MATERIALS = (
    ("gravel", ("gravel", "clay")),
    ("sand", ("sand",)),
    ("snow", ("snow",)),
    ("cloth", ("wool", "carpet", "leather", "saddle", "canvas", "bed")),
    ("grass", ("grass", "dirt", "moss", "leaves", "wild", "flower", "tulip", "orchid", "melon", "pumpkin", "mushroom")),
    ("stone", ("stone", "cobble", "deepslate", "brick", "quartz", "amethyst", "ore", "andesite", "diorite", "granite", "blackstone", "tuff",
               "obsidian", "basalt", "concrete", "terracotta", "furnace")),
)
HIT = {"wood": "hit.wood", "stone": "hit.stone", "gravel": "hit.gravel", "sand": "hit.sand", "grass": "hit.grass", "cloth": "hit.cloth",
       "snow": "hit.snow"}
BREAK = {"wood": "dig.wood", "stone": "dig.stone", "gravel": "dig.gravel", "sand": "dig.sand", "grass": "dig.grass", "cloth": "dig.cloth",
         "snow": "dig.snow"}


def materialOf(itemName, yields=()):
    """被切的东西是什么材质：先看它自己的名字，认不出再看切出来的东西（JE：它的方块，否则切出的第一个方块物品），都不认是木头。"""
    for name in [itemName] + list(yields or ()):
        words = set(str(name).split(":")[-1].split("_"))
        for material, keys in _MATERIALS:
            if any(key in words or (len(key) > 4 and any(key in word for word in words)) for key in keys):
                return material
    return "wood"


def snipBite(rng=random.random):
    """剪刀头两口各响一声（只有本人，944）：音调 1.25 + 0.15 * 随机。"""
    return (SHEEP_SHEAR, 0.3, 1.25 + 0.15 * rng())


def _text(value):
    """事件里的名字：不是字符串（坏数据）就当没有。"""
    return value if isinstance(value, (str, type(u""))) else ""


def _names(value):
    return [name for name in (value if isinstance(value, (list, tuple)) else ()) if _text(name)]


def placed(layer=None):
    """放下一样（所有人）：层号给了每层高一点（Each layer a little higher: the dish grows，1356-1357）。"""
    return (BOARD_PLACE, 0.7, 1.15 + 0.05 * layer if isinstance(layer, int) and not isinstance(layer, bool) else 1.0)


def _stroke(kind, tool, hits):
    """一刀（不是最后一刀）放什么：刀口上的刀声按工具分（chopSound：斧 = 削皮、锹 = 铲平，其余是刀）；削皮、剪刀各自的；
    别的是被切的东西的材质被敲的声音。返回 (声音名, 音量)。"""
    if kind == Cutting.TOOL_CUT:
        toolKind = Cutting.toolKindOf(tool or "")
        return (AXE_STRIP if toolKind == "axe" else SHOVEL_FLATTEN if toolKind == "shovel" else KNIFE_CUT), 0.8
    if kind == Cutting.TOOL_STRIP:
        return AXE_STRIP, 0.8
    if kind == Cutting.TOOL_SNIP:
        return SHEEP_SHEAR, 0.6
    return hits, 0.6


def _processing(kind, tool, block, material):
    """FD 的切声（BlockEntity.playProcessingSound，最后一刀响一次）：剪刀 -> 刀 -> 方块破坏声 -> 木头破坏声。"""
    toolKind = Cutting.toolKindOf(tool or "")
    if toolKind == "shears" or kind == Cutting.TOOL_SNIP:
        return (SHEEP_SHEAR, 1.0, 1.0)
    if toolKind == "knife" or (kind == Cutting.TOOL_CUT and toolKind is None):
        return (KNIFE_CUT, 0.8, 1.0)
    return (BREAK[material] if block else BREAK["wood"], 1.0, 0.8)


def chopped(data, rng=random.random):
    """一刀的声音（所有看得见板的人）。data 是 chopped 效果：tool、item、done、stroke、block（被切的是不是方块）、yields（切出来的东西的名字）。
    不是最后一刀：刀口上的那一声（刀、削皮 0.8，别的 0.6，音调 0.95 + 0.15 * 随机）；
    最后一刀：FD 的切声，再（被切的不是方块、而且不是刀 / 剪 / 削皮）一声材质的破坏声，最后切好的东西飞给厨师的那一声。"""
    tool, item, yields = _text(data.get("tool")), _text(data.get("item")), _names(data.get("yields"))
    kind = data.get("stroke") if data.get("stroke") in Cutting.STROKES else Cutting.strokeKind([tool], yields)
    block = bool(data.get("block"))
    material = materialOf(item, yields)
    if not data.get("done"):
        name, volume = _stroke(kind, tool, HIT[material])
        return [(name, volume, 0.95 + 0.15 * rng())]
    sounds = [_processing(kind, tool, block, material)]
    if not block and kind not in (Cutting.TOOL_CUT, Cutting.TOOL_SNIP, Cutting.TOOL_STRIP):
        sounds.append((BREAK[material], 0.8, 0.95 + 0.1 * rng()))
    sounds.append(PICKUP_STROKE)
    return sounds


def taken(data):
    """取走一样（所有人）：拔出插着的工具是拔出声加拿起声，别的只有拿起声。"""
    return ([REMOVE] if data.get("carved") else []) + [PICKUP_TAKEN]


def soundsOf(name, data=None, rng=random.random):
    """一个站点效果该放哪些声音：[(声音名, 音量, 音调)]。不出声的效果（refused 由本人自己放，book 之类）是空表。"""
    data = data or {}
    if name == "chopped":
        return chopped(data, rng)
    if name == "placed":
        return [placed(data.get("at"))]
    if name == "taken":
        return taken(data)
    if name == "carved":
        return [CARVE]
    if name == "assembled":
        return list(ASSEMBLED)
    return []
