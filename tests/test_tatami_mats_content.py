# -*- coding: utf-8 -*-
# runner: py3
"""长榻榻米垫的数据文件对照 JE（FarmersDelight 1.20：TatamiMatBlock、full_tatami_mat 的方块状态 / 模型 / 战利品表 / 配方）。

静态检查：两个方块（脚、头）的定义、模型的每个面贴哪张图、掉落、名字和贴图登记。配方见 test_tatami_recipes.py，放置与拆除见 test_tatami_mats_server.py。
"""
from __future__ import print_function

import os

import blockkit
import fdtest

Mat = fdtest.load("Shared.Rules.TatamiMat")

SIDE, INNER, ODD, EVEN = "arris:tatami_mat_side", "arris:tatami_mat_half", "arris:tatami_odd", "arris:tatami_even"
TEXTURES = [SIDE, INNER, ODD, EVEN]
SIDE_UV = ([0, 14], [16, 2])           # JE：side 贴图的 [0, 14, 16, 16]
INNER_UV = ([0, 7], [16, 2])           # JE：inner 的 [0, 7, 16, 9]（两半接头那一面）
TOP_UV = ([16, 16], [-16, -16])        # 网易 up 面的写法：整张贴图顺着摆，等于 JE 的 [0, 0, 16, 16]
BOTTOM_UV = ([0, 0], [16, 16])
# JE tatami_mat_foot / tatami_mat_head（facing=south 不转）每个面贴什么：贴图下标
FOOT_FACES = {"north": SIDE, "east": SIDE, "south": INNER, "west": SIDE, "up": ODD, "down": EVEN}
HEAD_FACES = {"north": INNER, "east": SIDE, "south": SIDE, "west": SIDE, "up": EVEN, "down": ODD}


def testBothHalvesAreDirectionalTwoPixelSlabsLikeJava():
    for name in Mat.PAIR:
        parts, desc = blockkit.components(name), blockkit.description(name)
        assert parts["netease:face_directional"] == {"type": "direction"}, name
        assert parts["netease:neighborchanged_sendto_script"] == {"value": True}, name         # 另一半 / 脚下变了要通知脚本
        assert parts["netease:redstone_property"] == {"value": "break_on_push"}, name
        box = {"min": [0.0, 0.0, 0.0], "max": [1.0, 0.125, 1.0]}                                # JE：box(0, 0, 0, 16, 2, 16)
        assert parts["netease:aabb"] == {"collision": box, "clip": box}, name
        assert parts["minecraft:destroy_time"] == {"value": 0.3}, name                         # JE：strength(0.3F)
        assert parts["minecraft:explosion_resistance"] == {"value": 0.3}, name
        assert parts["netease:solid"] == {"value": False} and parts["netease:render_layer"] == {"value": "alpha"}, name
        assert desc["category"] == "arris_farmers_delight", name
    # 创造栏和物品栏里只有一种长垫子：头方块是技术方块
    assert blockkit.description(Mat.FOOT)["register_to_creative_menu"] is True
    assert blockkit.description(Mat.HEAD)["register_to_creative_menu"] is False
    # JE：FuelBlockItem(FULL_TATAMI_MAT, 200)，200 刻 = 10 秒
    assert blockkit.components(Mat.FOOT)["netease:fuel"] == {"duration": 10}


def testEitherHalfDropsTheFootItem():
    # 脚没写战利品表，掉自己（= 长垫子）；头的战利品表指向同一个物品：拆哪一半都掉一个（另一半静默消失）
    assert "minecraft:loot" not in blockkit.components(Mat.FOOT)
    table = blockkit.readJson(os.path.join(fdtest.BP, blockkit.components(Mat.HEAD)["minecraft:loot"]["table"]))
    entries = [entry for pool in table["pools"] for entry in pool["entries"]]
    assert [(entry["name"], entry["type"]) for entry in entries] == [(Mat.FOOT, "item")]
    assert all(pool["rolls"] == 1 for pool in table["pools"])
    counts = [function["count"] for function in entries[0]["functions"] if function["function"] == "set_count"]
    assert counts == [{"min": 1, "max": 1}]


def testHalfMatAndTatamiFollowJavaSupportPushAndFuel():
    half = blockkit.components(Mat.HALF)
    # JE TatamiHalfMatBlock：canSurvive 要脚下有方块（updateShape 里没了就变空气）、pushReaction(DESTROY)、FuelBlockItem 100 刻
    assert half["netease:neighborchanged_sendto_script"] == {"value": True}
    assert half["netease:redstone_property"] == {"value": "break_on_push"}
    assert half["netease:fuel"] == {"duration": 5}
    assert half["netease:aabb"]["collision"] == {"min": [0.0, 0.0, 0.0], "max": [1.0, 0.125, 1.0]}
    # JE TATAMI 的物品是 FuelBlockItem(…, 400)
    assert blockkit.components("arris:tatami")["netease:fuel"] == {"duration": 20}


def _faceTextures(identifier):
    geometry = blockkit.model(identifier)
    cubes = blockkit.modelFaces(geometry)
    assert len(cubes) == 1, identifier
    boneName, enable, cube, faces = cubes[0]
    assert enable is None, identifier                                  # 垫子不随邻居变样子
    assert cube["origin"] == [-16, 0, 0] and cube["size"] == [16, 2, 16], identifier      # 网易模型坐标里的整格 16×2×16
    return geometry, dict((name, geometry["description"]["textures"][face["texture"]]) for name, face in faces.items()), faces


def testFootModelFollowsTheJavaFootModel():
    geometry, textures, faces = _faceTextures(Mat.FOOT)
    assert geometry["description"]["textures"] == TEXTURES
    assert textures == FOOT_FACES
    _checkUv(faces, {"north": SIDE_UV, "east": SIDE_UV, "south": INNER_UV, "west": SIDE_UV, "up": TOP_UV, "down": BOTTOM_UV})


def testHeadModelFollowsTheJavaHeadModel():
    geometry, textures, faces = _faceTextures(Mat.HEAD)
    assert geometry["description"]["textures"] == TEXTURES
    assert textures == HEAD_FACES
    _checkUv(faces, {"north": INNER_UV, "east": SIDE_UV, "south": SIDE_UV, "west": SIDE_UV, "up": TOP_UV, "down": BOTTOM_UV})


def _checkUv(faces, expected):
    for name, (uv, size) in expected.items():
        assert faces[name]["uv"] == uv and faces[name]["uv_size"] == size, (name, faces[name])


def testJoinSideOfTheFootIsOppositeToTheJoinSideOfTheHead():
    # 脚的接头面（inner）在南、头的在北：不转时头在脚的南边，放下去两个 inner 面正好贴在一起
    assert [name for name, tex in FOOT_FACES.items() if tex == INNER] == ["south"]
    assert [name for name, tex in HEAD_FACES.items() if tex == INNER] == ["north"]


def testModelsTexturesNamesAndSoundsAreRegistered():
    registered = blockkit.terrainTextures()
    resource = blockkit.resourceBlocks()
    names = blockkit.langNames()
    for name in Mat.PAIR:
        geometry = blockkit.model(name)
        for texture in geometry["description"]["textures"] + [geometry["description"]["item_texture"]]:
            assert texture in registered and blockkit.textureFileExists(registered[texture]), (name, texture)
        assert resource[name] == {"netease_model": name, "sound": "cloth"}, name
        assert names["tile.%s.name" % name] == "长榻榻米垫", name       # JE zh_cn：长榻榻米垫


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
