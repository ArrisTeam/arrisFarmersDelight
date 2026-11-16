# -*- coding: utf-8 -*-
# runner: both
"""煎锅方块实体模型的资源（rp/models/entity/skillet.geo.json、rp/animations/skillet.animation.json、rp/entity/skillet.json、
rp/render_controllers/skillet.render_controllers.json、rp/particles/arris_pan_heat.json）：骨骼层级、动画和渲染控制器里用到的 molang 变量
都在实体里初始化、PanModel 推的变量名一个不少、控制器引用的材质 / 贴图 / 骨骼都在。游戏里怎么画只能实机看，这里守的是"引用对得上"。"""
from __future__ import print_function

import io
import json
import os
import re

import fdtest
import pngkit

RP = os.path.join(fdtest.ROOT, "rp")
DG = os.path.join(fdtest.ROOT, "diegesisRp")


def load(*parts):
    with io.open(os.path.join(*((RP,) + parts)), encoding="utf-8") as handle:
        return json.load(handle)


def bones():
    geometry = load("models", "entity", "skillet.geo.json")["minecraft:geometry"][0]
    return dict((bone["name"], bone) for bone in geometry["bones"])


def entity():
    return load("entity", "skillet.json")["minecraft:client_entity"]["description"]


def initialized():
    return set(re.findall(r"(variable\.[a-z_0-9]+)\s*=", " ".join(entity()["scripts"]["initialize"])))


def testTheBoneTreeIsPanOverEverythingThatMovesWithTheToss():
    named = bones()
    assert set(named) == {"pan", "skillet", "handle", "handle_glow", "pot", "pan_glow", "shelf", "oil_0", "oil_1", "oil_2", "oil_3"}
    assert named["pan_glow"]["parent"] == "pot" and named["pan_glow"]["cubes"][0]["size"] == [14.16, 4.05, 14.16], \
        "锅身的描边壳：外形（14x4x14）四周各大 0.08，底抬到台面上方一点（贴着台面的那条边才露得出来）"
    assert named["pan"].get("parent") is None and named["pan"]["pivot"] == [-8, 0, 8], "pan 骨骼的枢轴在锅心、锅底（锅被颠时绕它转）"
    assert named["skillet"]["parent"] == "pan" and named["skillet"]["rotation"] == [0, 180, 0], "原来的根骨骼挂在 pan 下，自己的转半圈不动"
    assert named["handle"]["parent"] == "skillet" and named["pot"]["parent"] == "skillet"
    assert named["handle_glow"]["parent"] == "handle"
    assert named["shelf"].get("parent") is None, "支架（站在营火上才显示）不跟着锅颠：它关于锅心对称，不挂在转了半圈的骨骼下看不出差别"
    for i in range(4):
        oil = named["oil_%d" % i]
        assert oil["parent"] == "pan" and oil["pivot"] == [-8, 1.03, 8] and oil["rotation"] == [0, 90 * i, 0], "油膜跟着锅，只转四分之一圈的整数倍"
        cube = oil["cubes"][0]
        assert cube["origin"] == [-9, 1.02, 7] and cube["size"] == [2, 0.02, 2], "2x2 像素的片，以枢轴为中心，贴在锅底上方 1.03"
        assert list(cube["uv"]) == ["up"] and cube["uv"]["up"]["uv_size"] == [64, 64], "只画朝上的一面，贴图整张铺满（几何声明 64x64）"


def testTheGlowShellIsTheHandleCubeALittleBigger():
    handle = bones()["handle"]["cubes"][0]
    shell = bones()["handle_glow"]["cubes"][0]
    assert shell["pivot"] == handle["pivot"] and shell["rotation"] == handle["rotation"]
    for axis in range(3):
        assert abs(shell["origin"][axis] - (handle["origin"][axis] - 0.08)) < 1e-9
        assert abs(shell["size"][axis] - (handle["size"][axis] + 0.16)) < 1e-9, "每边大 0.08 像素，和厨锅的 ladle_glow 一样"
    assert all(face == {"uv": [0, 0], "uv_size": [1, 1]} for face in shell["uv"].values()), "整只壳取贴图左上角那一个像素"


def testEveryBoneAParentNamesExists():
    named = bones()
    for name, bone in named.items():
        parent = bone.get("parent")
        assert parent is None or parent in named, (name, parent)
        seen, at = set(), name
        while at is not None:
            assert at not in seen, "骨骼层级里有环：%s" % name
            seen.add(at)
            at = named[at].get("parent")


def testTheSceneAnimationDrivesThePanAndTheOilFromInitializedVariables():
    scene = load("animations", "skillet.animation.json")["animations"]["animation.skillet.scene"]
    assert set(scene["bones"]) == {"pan", "oil_0", "oil_1", "oil_2", "oil_3"} and scene["loop"] is True
    assert scene["bones"]["pan"] == {"position": [0, "variable.mod_pan_y", "variable.mod_pan_z"], "rotation": ["variable.mod_pan_rx", 0, 0]}
    assert scene["bones"]["oil_2"] == {"position": ["variable.mod_oil_x2", 0, "variable.mod_oil_z2"], "scale": "variable.mod_oil_s2"}
    used = set(re.findall(r"variable\.[a-z_0-9]+", json.dumps(scene)))
    assert used <= initialized(), used - initialized()
    for old in ("animation.skillet.shelf", "animation.skillet.sizzle"):
        assert old in load("animations", "skillet.animation.json")["animations"], "原来的两条动画还在"


def testTheEntityKeepsItsOldBehaviourAndAddsTheScene():
    description = entity()
    assert description["identifier"] == "arris:skillet" and description["geometry"] == {"default": "geometry.skillet"}
    assert description["animations"]["scene"] == "animation.skillet.scene" and "shelf" in description["animations"] and "sizzle_sound" in description["animations"]
    animate = description["scripts"]["animate"]
    assert {"sizzle_sound": "variable.mod_heat == 1.0 && variable.mod_scene < 0.5"} in animate and {"shelf": "variable.mod_shelf == 0.0"} in animate and "scene" in animate
    assert {"variable.mod_heat", "variable.mod_shelf", "variable.mod_scene"} <= initialized(), "原来的两个变量照旧初始化"


def testTheRenderControllersPointAtWhatTheEntityDeclares():
    description = entity()
    controllers = load("render_controllers", "skillet.render_controllers.json")["render_controllers"]
    assert description["render_controllers"] == ["controller.render.arris_skillet", "controller.render.arris_skillet_glow", "controller.render.arris_skillet_oil"]
    for name in description["render_controllers"]:
        controller = controllers[name]
        material = controller["materials"][0]["*"].split(".", 1)[1]
        texture = controller["textures"][0].split(".", 1)[1]
        assert material in description["materials"] and texture in description["textures"], name
        for rule in controller["part_visibility"]:
            for bone in rule:
                assert bone == "*" or bone in bones(), (name, bone)
        used = set(re.findall(r"variable\.[a-z_0-9]+", json.dumps(controller)))
        assert used <= initialized(), (name, used - initialized())
    main = controllers["controller.render.arris_skillet"]["part_visibility"]
    assert {"handle_glow": False} in main and all({"oil_%d" % i: False} in main for i in range(4)), "主画面不画描边壳和油膜"
    assert controllers["controller.render.arris_skillet_glow"]["part_visibility"][0] == {"*": False}
    assert controllers["controller.render.arris_skillet_oil"]["color"]["a"] == "variable.mod_oil_a", "油膜的浓淡由 mod_oil_a 管"


def testTheMaterialsAndTexturesExist():
    description = entity()
    assert description["materials"]["glow"] == "arris_outline" and description["materials"]["oil"] == "entity_alphablend"
    with io.open(os.path.join(RP, "materials", "entity.material"), encoding="utf-8") as handle:
        assert '"arris_outline:entity_alphablend"' in handle.read(),             "描边的材质（只画反面）：厨锅那条发光的（entity_emissive + 透明度 0 的贴图）在煎锅的模型上实机和 Strata 都不出图，煎锅用混合材质加不透明的贴图"
    assert description["textures"]["glow"] == "textures/entity/outline_solid"
    for texture in ("textures/entity/skillet_item", "textures/entity/outline_solid"):
        assert os.path.isfile(os.path.join(RP, texture + ".png")), texture
    assert description["textures"]["oil"] == "textures/handson/block/oil_film"
    assert os.path.isfile(os.path.join(DG, "textures", "handson", "block", "oil_film.png")), "油膜的图在前置包的资源里（HoD 的 block/oil_film）"


def testTheOutlineShellIsTheColourDiegesisDrawsItsOutlinesIn():
    """JE 的悬停描边色是 Diegesis 的缺省（InterfaceOptions.DEFAULT.outlineColor = 0xFFE6E6E6，skillet.json 没写 outline_color）；
    煎锅的描边壳（锅柄 / 锅身）只用 outline_solid.png 这一张图，原来是偏暖的 (255, 232, 192)。"""
    width, height, rows = pngkit.read(os.path.join(RP, "textures", "entity", "outline_solid.png"))
    assert (width, height) == (4, 4)
    assert all(pixel == (0xE6, 0xE6, 0xE6, 0xFF) for row in rows for pixel in row), rows[0]


def testPanModelOnlyPushesVariablesTheEntityInitializes():
    with io.open(os.path.join(fdtest.BP, fdtest.SCRIPTS, "Compat", "Diegesis", "PanModel.py"), encoding="utf-8") as handle:
        source = handle.read()
    pushed = set()
    for name in re.findall(r'"(variable\.[a-z_0-9]+(?:%d)?)"', source):
        pushed |= set(name % i for i in range(4)) if "%d" in name else {name}
    assert {"variable.mod_scene", "variable.mod_pan_rx", "variable.mod_pan_y", "variable.mod_pan_z", "variable.mod_handle_lit", "variable.mod_oil_a",
            "variable.mod_oil_x3", "variable.mod_oil_z0", "variable.mod_oil_s2"} <= pushed
    assert pushed <= initialized(), pushed - initialized()


def testTheHeatParticleIsTheOneThePanFxSpawns():
    particle = load("particles", "arris_pan_heat.json")["particle_effect"]
    assert particle["description"]["identifier"] == "arris:pan_heat"
    assert particle["description"]["basic_render_parameters"]["texture"] == "textures/handson/particle/heat"
    assert os.path.isfile(os.path.join(DG, "textures", "handson", "particle", "heat.png"))
    flipbook = particle["components"]["minecraft:particle_appearance_billboard"]["uv"]["flipbook"]
    assert flipbook["max_frame"] == 4 and flipbook["size_UV"] == [8, 8] and flipbook["step_UV"] == [0, 8], "heat.png 是 8x32 的四帧竖条"
    with io.open(os.path.join(fdtest.BP, fdtest.SCRIPTS, "Compat", "Diegesis", "PanFx.py"), encoding="utf-8") as handle:
        assert 'HEAT = "arris:pan_heat"' in handle.read()
    creation = particle["components"]["minecraft:emitter_initialization"]["creation_expression"]
    for name in ("tint_set", "alpha", "scale", "count", "life", "speed_set", "vx", "vy", "vz"):
        assert "variable.%s" % name in creation, "PotFx.particle 会设的变量，粒子里要有初值：%s" % name


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
