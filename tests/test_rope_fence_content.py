# -*- coding: utf-8 -*-
# runner: py3
"""绳栅栏、绳栅栏门的数据文件对照 JE（FarmersDelight 1.20：RopeFenceBlock、RopeFenceGateBlock、RopeFenceConnectionMixin、
rope_fence* 的模型 / 方块状态 / 战利品表 / 标签）。

栅栏的连接靠引擎的 netease:connection（按标识符列名单）+ 模型和碰撞盒的 query.is_connect，没有脚本：
JE 的 connectsTo = "邻居朝向这边的面是实心的（树叶、屏障、南瓜、西瓜、潜影盒除外）或是绳栅栏或是方向对得上的绳栅栏门"，
原版栅栏、墙、玻璃板都不连它（它们的面不是实心的；原版栅栏另被 mixin 明着拒绝）。
"""
from __future__ import print_function

import io
import os

import blockkit
import fdtest

Rule = fdtest.load("Shared.Rules.RopeFence")
FENCE, GATE, OPEN = "arris:rope_fence", Rule.GATE, Rule.GATE_OPEN
IN_WALL = "query.is_connect(4) && query.is_connect(5)"
NOT_IN_WALL = "!(query.is_connect(4) && query.is_connect(5))"
EPS = 0.0625
# is_connect 的面号：2 北、3 南、4 西、5 东
ARMS = {2: "north", 3: "south", 4: "west", 5: "east"}


def _cubes(geometry):
    """{骨骼名: (enable, [立方体包围盒的 (最小角, 最大角)])}。"""
    found = {}
    for bone in geometry["bones"]:
        found[bone["name"]] = (bone.get("enable"), [blockkit.cubeBounds(cube) for cube in bone["cubes"]])
    return found


# ---- 栅栏 ----

def testFenceBlockMatchesJavaProperties():
    parts, desc = blockkit.components(FENCE), blockkit.description(FENCE)
    assert parts["minecraft:destroy_time"] == {"value": 1.0} and parts["minecraft:explosion_resistance"] == {"value": 1.0}   # strength(1.0F)
    assert parts["netease:solid"] == {"value": False} and parts["netease:render_layer"] == {"value": "alpha"}
    assert parts["netease:tier"] == {"destroy_special": False, "digger": "hatchet", "level": 0}                    # 斧头挖得快，空手也掉
    assert parts["netease:fuel"] == {"duration": 10}                                                               # FuelBlockItem 200 刻
    assert "netease:pathable" not in parts                                                                         # 当障碍物
    assert desc["register_to_creative_menu"] is True and desc["category"] == "arris_farmers_delight"
    assert "netease:face_directional" not in parts and "minecraft:loot" not in parts                               # 朝向无关、掉自己


def testFenceBoxesAreAPostAndFourSwitchableArmsLikeCrossCollisionBlock():
    # JE CrossCollisionBlock(1, 1, 16, 16, 24)：柱 7..9、臂 7..9 宽伸到方块边；选取框高 16、碰撞高 24（1.5 格）
    aabb = blockkit.components(FENCE)["netease:aabb"]
    for kind, top in (("clip", 1.0), ("collision", 1.5)):
        boxes = aabb[kind]
        assert boxes[0] == {"min": [0.4375, 0, 0.4375], "max": [0.5625, top, 0.5625]} and "enable" not in boxes[0], kind
        expected = {2: ([0.4375, 0, 0], [0.5625, top, 0.5625]), 3: ([0.4375, 0, 0.4375], [0.5625, top, 1.0]),
                    4: ([0, 0, 0.4375], [0.5625, top, 0.5625]), 5: ([0.4375, 0, 0.4375], [1.0, top, 0.5625])}
        arms = dict((int(box["enable"][len("query.is_connect("):-1]), (box["min"], box["max"])) for box in boxes[1:])
        assert arms == expected, kind
    # 选取框不能比碰撞盒大（官方文档：否则弹射物命中异常）
    assert [box["max"][1] for box in aabb["clip"]] == [1.0] * 5 and [box["max"][1] for box in aabb["collision"]] == [1.5] * 5


def testFenceModelIsAPostWithArmsThatAppearWhereTheBoxesAre():
    geometry = blockkit.model(FENCE)
    assert geometry["description"]["textures"] == ["arris:rope_fence"] and geometry["description"]["use_ao"] is True
    cubes = _cubes(geometry)
    assert cubes["post"] == (None, [((7, 0, 7), (9, 16, 9))])                         # JE rope_fence_post
    # JE rope_fence_side（北）/ side_alt（南）：x=8 的竖片，y 4..14、长 7；东 / 西是同一批转 90°
    expected = {2: ((8, 4, 0), (8, 14, 7)), 3: ((8, 4, 9), (8, 14, 16)), 4: ((0, 4, 8), (7, 14, 8)), 5: ((9, 4, 8), (16, 14, 8))}
    for face, bounds in expected.items():
        enable, boxes = cubes[ARMS[face]]
        assert enable == "query.is_connect(%d)" % face and boxes == [bounds], face
    assert sorted(cubes) == ["east", "north", "post", "south", "west"]


def testFenceArmFacesCarryTheJavaUvRegions():
    # 臂是零厚度的片，每片一个面（双面渲染）：JE 北 / 东臂的 uv 是 [9,2,16,12]，南 / 西臂 [0,2,7,12]；贴图左右镜像对称，背面等于 JE 的另一个面
    geometry = blockkit.model(FENCE)
    uv = dict((bone["name"], bone["cubes"][0]["uv"]) for bone in geometry["bones"])
    assert uv["north"] == {"east": {"texture": 0, "uv": [9, 2], "uv_size": [7, 10]}}
    assert uv["south"] == {"east": {"texture": 0, "uv": [0, 2], "uv_size": [7, 10]}}
    assert uv["east"] == {"south": {"texture": 0, "uv": [9, 2], "uv_size": [7, 10]}}
    assert uv["west"] == {"south": {"texture": 0, "uv": [0, 2], "uv_size": [7, 10]}}
    post = uv["post"]
    assert all(post[side] == {"texture": 0, "uv": [7, 0], "uv_size": [2, 16]} for side in ("north", "east", "south", "west"))
    assert post["down"] == {"texture": 0, "uv": [5, 14], "uv_size": [2, 2]}
    assert post["up"] == {"texture": 0, "uv": [7, 16], "uv_size": [-2, -2]}


def testFenceConnectsToSolidBlocksItsOwnKindAndNotToTheExceptions():
    names = blockkit.components(FENCE)["netease:connection"]["blocks"]
    assert names == sorted(set(names)) and all(":" in name for name in names)
    for name in (FENCE, GATE, OPEN):
        assert name in names, name                                                    # 自己、自己的门（关着 / 开着）
    for name in ("minecraft:stone", "minecraft:dirt", "minecraft:grass_block", "minecraft:oak_planks", "minecraft:oak_log",
                 "minecraft:cobblestone", "minecraft:glass", "minecraft:white_wool", "minecraft:white_concrete",
                 "minecraft:bookshelf", "minecraft:oak_double_slab", "minecraft:iron_ore", "minecraft:hay_block",
                 "minecraft:barrel", "minecraft:crafting_table", "minecraft:white_glazed_terracotta", "minecraft:ice",
                 "arris:oak_cabinet", "arris:straw_bale", "arris:tomato_crate", "arris:tatami"):
        assert name in names, name                                                    # 实心整格方块
    # JE isExceptionForConnection：树叶、屏障、南瓜（含雕刻 / 南瓜灯）、西瓜、潜影盒不连
    for name in names:
        assert not name.endswith("_leaves") and "shulker_box" not in name, name
    for name in ("minecraft:barrier", "minecraft:pumpkin", "minecraft:carved_pumpkin", "minecraft:lit_pumpkin", "minecraft:melon_block"):
        assert name not in names, name
    # 面不是实心的方块不连：原版栅栏 / 门 / 墙 / 玻璃板 / 半砖 / 楼梯 / 地毯 / 活板门
    for name in [name for name in names if name.startswith("minecraft:")]:
        assert not name.endswith(("_fence", "_fence_gate", "_wall", "_pane", "_stairs", "_carpet", "_trapdoor", "_door")), name
        assert not (name.endswith("_slab") and "double" not in name), name
    for name in ("minecraft:oak_fence", "minecraft:cobblestone_wall", "minecraft:glass_pane", "minecraft:oak_stairs",
                 "minecraft:stone_slab", "minecraft:farmland", "minecraft:honey_block", "minecraft:powder_snow"):
        assert name not in names, name


def testEveryOwnBlockInTheConnectionListsExists():
    defined = set(blockkit.blockDefinitions())
    for block in (FENCE, GATE, OPEN):
        for name in blockkit.components(block)["netease:connection"]["blocks"]:
            if name.startswith("arris:"):
                assert name in defined, (block, name)


# ---- 门 ----

def testGateBlocksMatchJavaProperties():
    for name in (GATE, OPEN):
        parts = blockkit.components(name)
        assert parts["minecraft:destroy_time"] == {"value": 1.0} and parts["minecraft:explosion_resistance"] == {"value": 1.0}, name
        assert parts["netease:face_directional"] == {"type": "direction"}, name
        assert parts["netease:tier"] == {"destroy_special": False, "digger": "hatchet", "level": 0}, name
        assert parts["netease:solid"] == {"value": False} and parts["netease:render_layer"] == {"value": "alpha"}, name
        # 靠墙的门画成"在墙里"的样子：两边都是墙时（JE updateShape 的 isBorderedByWalls），名单就是原版的墙
        walls = parts["netease:connection"]["blocks"]
        assert walls == sorted(set(walls)) and len(walls) >= 20 and all(name.endswith("_wall") for name in walls), name
    assert blockkit.description(GATE)["register_to_creative_menu"] is True
    assert blockkit.description(OPEN)["register_to_creative_menu"] is False
    assert blockkit.components(GATE)["netease:fuel"] == {"duration": 10}
    # JE RopeFenceGateBlock.isPathfindable（继承 FenceGateBlock）：开着的门走得过去
    assert blockkit.components(OPEN)["netease:pathable"] == {"value": True} and "netease:pathable" not in blockkit.components(GATE)


def testGateBoxesFollowJava():
    # JE：选取框 box(0,0,7,16,14,9)（开关都一样）；碰撞 box(0,0,7,16,24,9)，开着没有碰撞
    closed = blockkit.components(GATE)["netease:aabb"]
    opened = blockkit.components(OPEN)["netease:aabb"]
    clip = {"min": [0.0, 0.0, 0.4375], "max": [1.0, 0.875, 0.5625]}
    assert closed["clip"] == clip and opened["clip"] == clip
    assert closed["collision"] == {"min": [0.0, 0.0, 0.4375], "max": [1.0, 1.5, 0.5625]}
    assert opened["collision"] == {"min": [0.0, 0.0, 0.0], "max": [0.0, 0.0, 0.0]}


def testBothGatesDropTheClosedGateItem():
    assert "minecraft:loot" not in blockkit.components(GATE)
    table = blockkit.readJson(os.path.join(fdtest.BP, blockkit.components(OPEN)["minecraft:loot"]["table"]))
    entries = [entry for pool in table["pools"] for entry in pool["entries"]]
    assert [(entry["name"], entry["type"]) for entry in entries] == [(GATE, "item")]


def _gateBones(identifier):
    geometry = blockkit.model(identifier)
    assert geometry["description"]["textures"] == ["arris:rope_fence_gate", "arris:rope_fence_gate_wall", "arris:rope_fence_gate_open"]
    return geometry, _cubes(geometry)


def testClosedGateModelFollowsJavaGateAndWallGateModels():
    geometry, cubes = _gateBones(GATE)
    assert sorted(cubes) == ["cloth", "posts", "wall_cloth"]
    # JE rope_fence_gate：west_post、east_post（2×14×2）和 x 2..14、y 4..12 的布（z=8，北南各一面，这里错开 1/16 像素）
    enable, posts = cubes["posts"]
    assert enable == NOT_IN_WALL and sorted(posts) == [((0, 0, 7), (2, 14, 9)), ((14, 0, 7), (16, 14, 9))]
    enable, cloth = cubes["cloth"]
    assert enable == NOT_IN_WALL
    assert sorted(cloth) == sorted([((2, 4, 8 - EPS), (14, 12, 8 - EPS)), ((2, 4, 8 + EPS), (14, 12, 8 + EPS))])
    # JE rope_fence_gate_wall：x 0..16、y 4..13 一整片布，没有柱
    enable, wall = cubes["wall_cloth"]
    assert enable == IN_WALL
    assert sorted(wall) == sorted([((0, 4, 8 - EPS), (16, 13, 8 - EPS)), ((0, 4, 8 + EPS), (16, 13, 8 + EPS))])


def testOpenGateModelFollowsJavaOpenModels():
    geometry, cubes = _gateBones(OPEN)
    assert sorted(cubes) == ["coil", "posts", "wall_coil"]
    assert cubes["posts"][0] == NOT_IN_WALL and len(cubes["posts"][1]) == 2
    # JE rope_fence_gate_open：卷起来的布 x 1..3、y 4..12、z 6..10（西边那根柱旁）；_wall_open：x 0..2、y 5..13
    assert cubes["coil"] == (NOT_IN_WALL, [((1, 4, 6), (3, 12, 10))])
    assert cubes["wall_coil"] == (IN_WALL, [((0, 5, 6), (2, 13, 10))])
    coil = geometry["bones"][1]["cubes"][0]["uv"]
    # JE：north [4,0,6,8]、east [2,0,6,8]、south [0,0,2,8]、west [6,0,2,8]（翻转）、up [2,3,4,7]、down [2,2,4,6]，都贴 open 那张
    assert coil["north"] == {"texture": 2, "uv": [4, 0], "uv_size": [2, 8]}
    assert coil["east"] == {"texture": 2, "uv": [2, 0], "uv_size": [4, 8]}
    assert coil["south"] == {"texture": 2, "uv": [0, 0], "uv_size": [2, 8]}
    assert coil["west"] == {"texture": 2, "uv": [6, 0], "uv_size": [-4, 8]}
    assert coil["up"] == {"texture": 2, "uv": [4, 7], "uv_size": [-2, -4]}
    assert coil["down"] == {"texture": 2, "uv": [2, 2], "uv_size": [2, 4]}


def testGateClothFacesCarryTheJavaUv():
    geometry = blockkit.model(GATE)
    cloth = [cube["uv"] for bone in geometry["bones"] if bone["name"] == "cloth" for cube in bone["cubes"]]
    assert {"north": {"texture": 0, "uv": [2, 4], "uv_size": [12, 8]}} in cloth
    assert {"south": {"texture": 0, "uv": [2, 4], "uv_size": [12, 8]}} in cloth
    wall = [cube["uv"] for bone in geometry["bones"] if bone["name"] == "wall_cloth" for cube in bone["cubes"]]
    assert {"north": {"texture": 1, "uv": [0, 3], "uv_size": [16, 9]}} in wall
    posts = [cube["uv"] for bone in geometry["bones"] if bone["name"] == "posts" for cube in bone["cubes"]]
    for uv in posts:                                        # JE：侧面 [0,2,2,16]，上 / 下 [2,14,4,16]
        assert all(uv[side] == {"texture": 0, "uv": [0, 2], "uv_size": [2, 14]} for side in ("north", "east", "south", "west"))
        assert uv["down"] == {"texture": 0, "uv": [2, 14], "uv_size": [2, 2]} and uv["up"] == {"texture": 0, "uv": [4, 16], "uv_size": [-2, -2]}


# ---- 登记 ----

def testTexturesNamesSoundsAndModelsAreRegistered():
    registered = blockkit.terrainTextures()
    resource = blockkit.resourceBlocks()
    names = blockkit.langNames()
    for identifier, label in ((FENCE, "绳栅栏"), (GATE, "绳栅栏门"), (OPEN, "绳栅栏门")):
        geometry = blockkit.model(identifier)
        for texture in geometry["description"]["textures"] + [geometry["description"]["item_texture"]]:
            assert texture in registered and blockkit.textureFileExists(registered[texture]), (identifier, texture)
        assert resource[identifier] == {"netease_model": identifier, "sound": "wood"}, identifier       # copy(OAK_FENCE)：木头声
        assert names["tile.%s.name" % identifier] == label, identifier                                  # JE zh_cn
    # 栅栏的物品图标是照 JE rope_fence_inventory 的正面拼的，门直接用正面贴图
    assert blockkit.model(FENCE)["description"]["item_texture"] == "arris:rope_fence_icon"
    assert blockkit.model(GATE)["description"]["item_texture"] == "arris:rope_fence_gate"


def testRopeAlsoBurnsLikeJava():
    # JE RopeItem extends FuelBlockItem(…, 200)
    assert blockkit.components("arris:rope")["netease:fuel"] == {"duration": 10}


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
