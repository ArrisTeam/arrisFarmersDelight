# -*- coding: utf-8 -*-
# runner: both
"""闪亮沙拉（JE 1.3 的 GleamingSaladBlock 盛宴）：五个阶段的方块对 JE 的核对、盛菜流程、模型和贴图。

JE 的事实（FeastBlock、GleamingSaladBlock、ModBlocks、FDBlockLoot、BlockStates，抄在下面，离线可跑）：
- 4 份（stage0 = 4 份 … stage3 = 1 份，leftover = 0 份），每份要一个碗，盛出一碗 arris:gleaming_salad；盛完最后一份
  留下空盘（hasLeftovers），空盘再点一下拆掉；
- 发光 = 剩余份数 × 3（12 / 9 / 6 / 3 / 0）；碰撞和轮廓是固定的两个盒子（和份数无关）：
  Block.box(3, 0, 3, 13, 2, 13) 与 Block.box(2, 2, 2, 14, 6, 14)；
- 硬度和抗爆都是 0.5、被活塞推时破坏（PushReaction.DESTROY）、方块物品堆叠 1（stacksTo(1)）、声音是木头；
- 战利品：整份（servings = 4）掉自己，其余掉一个碗；
- 方块模型是 JE 的 gleaming_salad_block_stage0..3 与 gleaming_salad_block_leftovers，元素 14 / 15 / 13 / 10 / 5 个。
模型是 tools/je_model_to_netease.py 从 JE 模型转出来的：找得到 JE 的资源时（FD_JE_ASSETS 环境变量，缺省 .refs/FarmersDelight 下的
src/main/resources/assets/farmersdelight）重新转一遍和提交的文件逐项比对，找不到就跳过这一条。
"""
from __future__ import print_function

import io
import json
import os
import struct
import sys

import fakeengine
import fdtest

world = fakeengine.install()
Registry = fdtest.load("Server.EventRegistry")
FoodBlocks = fdtest.load("Server.FoodBlocks")
Food = fdtest.load("Shared.Data.Food")

sys.path.insert(0, os.path.join(fdtest.ROOT, "tools"))
import je_model_to_netease as Converter  # noqa: E402

RP = os.path.join(fdtest.ROOT, "rp")
BLOCKS_DIR = os.path.join(fdtest.BP, "netease_blocks", "gleaming_salad_block")
# 阶段 -> (剩余份数, 模型元素个数, JE 的模型文件名)
STAGES = {
    "stage0": (4, 14, "gleaming_salad_block_stage0"),
    "stage1": (3, 15, "gleaming_salad_block_stage1"),
    "stage2": (2, 13, "gleaming_salad_block_stage2"),
    "stage3": (1, 10, "gleaming_salad_block_stage3"),
    "leftover": (0, 5, "gleaming_salad_block_leftovers"),
}
# JE 贴图名 -> 本包 terrain_texture.json 的短名（tray_bottom 用本包已有的）
TEXTURES = {"bowl": "arris:gleaming_salad_bowl", "tray_bottom": "arris:tray_bottom", "salad": "arris:gleaming_salad",
            "details": "arris:gleaming_salad_details", "leftovers": "arris:gleaming_salad_leftovers"}
ICON = "arris:gleaming_salad_block_icon"
BOWL = {"newItemName": "minecraft:bowl", "newAuxValue": 0, "count": 4}
POS = (1, 64, 1)


def _name(stage):
    return "arris:gleaming_salad_block_" + stage


def _read(path):
    with io.open(path, encoding="utf-8") as handle:
        return json.load(handle)


def _block(stage):
    return _read(os.path.join(BLOCKS_DIR, "arris_gleaming_salad_block_%s.json" % stage))["minecraft:block"]


def _box(low, high):
    return {"min": [value / 16.0 for value in low], "max": [value / 16.0 for value in high]}


def _pngSize(path):
    with io.open(path, "rb") as handle:
        header = handle.read(24)
    assert header[:8] == b"\x89PNG\r\n\x1a\n", path
    return struct.unpack(">II", header[16:24])


# ---- 方块 ----

def testEveryStageFollowsTheJavaBlock():
    shape = [_box((3, 0, 3), (13, 2, 13)), _box((2, 2, 2), (14, 6, 14))]
    for stage, (servings, _elements, _model) in sorted(STAGES.items()):
        block = _block(stage)
        components = block["components"]
        assert block["description"]["identifier"] == _name(stage)
        # 旧写法的发光是 0~1 的小数，引擎 ×15 取整；JE 是份数 × 3 级
        assert round(components["minecraft:block_light_emission"]["emission"] * 15) == servings * 3, stage
        assert abs(components["minecraft:block_light_emission"]["emission"] * 15 - servings * 3) < 1e-9, "要正好落在整数上，免得取整差一级"
        assert components["minecraft:destroy_time"]["value"] == 0.5 and components["minecraft:explosion_resistance"]["value"] == 0.5
        assert components["netease:aabb"] == {"clip": shape, "collision": shape}, stage
        assert components["netease:redstone_property"] == {"value": "break_on_push"}, "JE：PushReaction.DESTROY"
        assert components["netease:face_directional"] == {"type": "direction"}
        assert components["netease:render_layer"] == {"value": "alpha"} and components["netease:solid"] == {"value": False}
        assert components["minecraft:block_light_absorption"] == {"value": 0}, "网易模型方块要写，否则模型会变黑"


def testOnlyTheFullFeastIsAnItemInTheCreativeMenuAndItStacksToOne():
    for stage in sorted(STAGES):
        block = _block(stage)
        full = stage == "stage0"
        assert bool(block["description"].get("register_to_creative_menu")) == full, stage
        assert ("minecraft:max_stack_size" in block["components"]) == full, stage
        if full:
            assert block["components"]["minecraft:max_stack_size"] == {"value": 1}, "JE：PlaceableItem 的 stacksTo(1)"
            assert block["description"]["category"] == "arris_farmers_delight"
    group = [entry for entry in _read(os.path.join(fdtest.BP, "netease_group", "arris_farmers_delight_group.json"))["groups"]
             if entry["group_name"] == "itemGroup.name.farmer_plate_packaged_food"][0]["list"]
    assert group.index(_name("stage0")) + 1 == group.index("arris:gleaming_salad"), "方块后面紧跟碗装的"
    assert group.index("arris:shepherds_pie") < group.index(_name("stage0")) < group.index("arris:rice_roll_medley_block_stage0"), "JE 的顺序"


def testLootDropsItselfWhenFullAndABowlOtherwise():
    for stage in sorted(STAGES):
        table = _block(stage)["components"]["minecraft:loot"]["table"]
        drops = [(entry["name"], function["count"]["min"], function["count"]["max"])
                 for pool in _read(os.path.join(fdtest.BP, table))["pools"] for entry in pool["entries"]
                 for function in entry["functions"] if function["function"] == "set_count"]
        assert drops == ([(_name("stage0"), 1, 1)] if stage == "stage0" else [("minecraft:bowl", 1, 1)]), (stage, drops)


def testBlocksJsonPointsEveryStageAtItsModelWithWoodSound():
    blocks = _read(os.path.join(RP, "blocks.json"))
    for stage in sorted(STAGES):
        assert blocks[_name(stage)] == {"netease_model": _name(stage), "sound": "wood"}, stage


def testNamesAreTheJavaTranslations():
    lang = dict(line.split("=", 1) for line in io.open(os.path.join(RP, "texts", "zh_CN.lang"), encoding="utf-8").read().splitlines()
                if "=" in line)
    for stage in sorted(STAGES):
        assert lang["tile.%s.name" % _name(stage)] == u"闪亮沙拉", stage
    assert lang["item.arris:gleaming_salad.name"] == u"碗装闪亮沙拉"


# ---- 模型和贴图 ----

def testModelsUseTheJavaElementsAndRealTextures():
    terrain = _read(os.path.join(RP, "textures", "terrain_texture.json"))["texture_data"]
    for stage, (_servings, elements, _model) in sorted(STAGES.items()):
        model = _read(os.path.join(RP, "models", "netease_block", "gleaming_salad_block_%s.json" % stage))["netease:block_geometry"]
        description = model["description"]
        assert description["identifier"] == _name(stage) and description["use_ao"] is True
        assert sum(len(bone["cubes"]) for bone in model["bones"]) == elements, "%s 的元素个数和 JE 的模型不一样" % stage
        assert description.get("item_texture") == (ICON if stage == "stage0" else None), stage
        assert len(description["textures"]) == len(set(description["textures"])) == len(description["textures_descriptions"])
        for texture, size in zip(description["textures"], description["textures_descriptions"]):
            path = os.path.join(RP, terrain[texture]["textures"] + ".png")
            assert os.path.isfile(path), "%s 的贴图文件 %s 不存在" % (texture, path)
            assert _pngSize(path) == (size["width"], size["length"]), "%s 的 textures_descriptions 要照贴图的实际大小写" % texture
    icon = os.path.join(RP, terrain[ICON]["textures"] + ".png")
    assert os.path.isfile(icon) and _pngSize(icon) == (16, 16)


def _jeAssets():
    base = os.environ.get("FD_JE_ASSETS") or os.path.join(fdtest.ROOT, ".refs", "FarmersDelight", "src", "main", "resources",
                                                         "assets", "farmersdelight")
    return base if os.path.isdir(os.path.join(base, "models", "block")) else None


def testModelsAreTheConvertedJavaModels():
    base = _jeAssets()
    if base is None:
        print("跳过：没有 JE 的资源（FD_JE_ASSETS 或 .refs/FarmersDelight）")
        return
    for stage, (_servings, _elements, javaModel) in sorted(STAGES.items()):
        expected = Converter.convert(_read(os.path.join(base, "models", "block", javaModel + ".json")), _name(stage),
                                     ICON if stage == "stage0" else "", TEXTURES)
        actual = _read(os.path.join(RP, "models", "netease_block", "gleaming_salad_block_%s.json" % stage))
        assert actual == expected, "%s 的模型和 JE 模型的转换结果不一样：py -3 tools/je_model_to_netease.py 重新转" % stage


# ---- 砧板摆盘（前置包在场时工作台不再出它，改在砧板上做；HoD 的规则：配料不止一种的盛宴改在砧板上摆） ----

def testTheBoardMakesItOnABowlOutOfTheNineJavaIngredients():
    Dishes = fdtest.load("Shared.Data.Dishes")
    Rules = fdtest.load("Shared.Rules.DishStation")
    ingredients = [("minecraft:glow_berries", 0)] * 2 + [("minecraft:honey_bottle", 0), ("arris:tomato", 0), ("minecraft:golden_carrot", 0),
                                                         ("minecraft:beetroot", 0), ("arris:cabbage", 0), ("arris:cabbage", 0)]
    dishes = [dish for dish in Dishes.DishList if dish["result"][0] == _name("stage0")]
    assert len(dishes) == 1 and dishes[0]["count"] == 1, "无序配方只有一条做法"
    assert sorted(dishes[0]["ingredients"]) == sorted(ingredients + [("minecraft:bowl", 0)])
    assert Rules.isDishResult(_name("stage0")) and Rules.blocksAtTable(_name("stage0")), "它是砧板菜，工作台要拦"
    assert Rules.isBase(("minecraft:bowl", 0))
    layers = [("minecraft:bowl", 0)]
    for kind in ingredients:
        assert Rules.completed(layers) is None
        assert Rules.fitsNext(layers, kind), kind
        layers.append(kind)
    assert Rules.completed(layers)["result"] == (_name("stage0"), 0)
    # 蜂蜜瓶的玻璃瓶和工作台一样还给厨师
    assert Rules.containerOf(_name("stage0")) == {"itemName": "minecraft:glass_bottle", "count": 1, "auxValue": 0}


# ---- 盛菜 ----

def _setUp(hand=BOWL, blockName="arris:gleaming_salad_block_stage0"):
    Registry.clearAll()
    Registry.registerHandler("ServerBlockUseEvent", match=FoodBlocks.platePackagedFoodDict)(FoodBlocks.OnServePlatedFood)
    del world.calls[:]
    world.spawned[:] = []
    world.sounds[:] = []
    world.players.clear()
    world.entities.clear()
    world.timers = []
    world.addPlayer("p1", hand=dict(hand) if hand else None)
    world.setBlock(POS[0], POS[1], POS[2], blockName)


def _click():
    blockName = world.blockName(*POS)
    args = {"x": POS[0], "y": POS[1], "z": POS[2], "dimensionId": 0, "playerId": "p1", "blockName": blockName, "aux": 0}
    Registry.dispatch("ServerBlockUseEvent", args, blockName)
    world.runTimers()          # 过了交互冷却，下一次点击才算新的一次


def _given():
    return [(item["itemName"], item["count"]) for item in world.players["p1"]["given"]]


def testFourServingsThenAnEmptyBowlThatClearsOnTheNextClick():
    _setUp()
    seen = []
    for _ in range(4):
        _click()
        seen.append(world.blockName(*POS))
    assert seen == ["arris:gleaming_salad_block_stage1", "arris:gleaming_salad_block_stage2", "arris:gleaming_salad_block_stage3",
                    "arris:gleaming_salad_block_leftover"], seen
    assert _given() == [("arris:gleaming_salad", 1)] * 4
    assert world.players["p1"]["hand"] is None, "4 个碗用了 4 个"
    _click()
    assert world.blockName(*POS) == "minecraft:air" and len(_given()) == 4, "空盘收走不再盛菜（掉落物按战利品表：一个碗）"


def testEachServingNeedsABowlAndLeavesTheBlockAloneWithoutOne():
    _setUp(hand={"newItemName": "minecraft:bread", "newAuxValue": 0, "count": 1})
    _click()
    assert world.blockName(*POS) == "arris:gleaming_salad_block_stage0" and _given() == []
    assert ("p1", "ShowTip", "你需要一个碗以食用它。") in world.calls


def testCreativeKeepsTheBowl():
    _setUp(blockName="arris:gleaming_salad_block_stage3")
    world.players["p1"]["creative"] = True
    _click()
    assert world.blockName(*POS) == "arris:gleaming_salad_block_leftover" and _given() == [("arris:gleaming_salad", 1)]
    assert world.players["p1"]["hand"]["count"] == 4


def testEveryStageIsInTheServingTableAndEndsInTheLeftover():
    chain = ["arris:gleaming_salad_block_" + stage for stage in ("stage0", "stage1", "stage2", "stage3", "leftover")]
    for here, after in zip(chain, chain[1:] + [None]):
        entry = Food.platePackagedFoodDict[here]
        assert entry["target"] == (after if here != chain[-1] else None), here
        assert entry["item"] == (None if here == chain[-1] else "arris:gleaming_salad"), here


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
