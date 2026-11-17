# -*- coding: utf-8 -*-
# runner: both
"""厨锅的吊把手在模型和客户端上：rp 的几何 / 实体 / 渲染控制器里 FD 的 cooking_pot_handle 那一组，Compat/Diegesis 的 PotModel / PotScene 把支架（吊把手 / 托盘）
跟着服务端的世界外观推给方块实体模型、方块实体在本端重建之后整份重推，Client/BlockEntityRestore 在方块实体加载时按存档补变量。引擎是 potclient.py 里的假的。

FD 的 cooking_pot_handle.json：handle 组 = hoop（[1,8,8] 到 [15,16,8]，南北两面）、两片侧面（x = 1 和 15，[8,7] 到 [16,9]，东西两面）、
top_handle（y = 15.999，[1,7] 到 [15,9]，上下两面）；贴图 cooking_pot_handle.png 16 x 16。基岩版几何的 x 和 JE 反着（-x），贴图贴在 64 x 64 的图集里 (0, 40) 起的一块。
"""
from __future__ import print_function

import io
import json
import os
import struct
import sys

import fdtest
import potclient as C

world = C.world
Scenes = C.load("Compat.Diegesis.PotScenes")
BrothColors = C.load("Shared.Data.BrothColors")
Rules = C.load("Shared.Rules.PotSupport")
POS = C.POS
DT = 1.0 / 60.0
RP = os.path.join(fdtest.ROOT, "rp")
ATLAS = (0, 40)                       # 手柄贴图在图集里的左上角


def _json(*path):
    with io.open(os.path.join(RP, *path), encoding="utf-8-sig") as handle:
        return json.load(handle)


def _bones():
    return _json("models", "entity", "cooking_pot.geo.json")["minecraft:geometry"][0]["bones"]


def setup():
    C.reset()
    Scenes._scenes.clear()
    Scenes.enable(BrothColors.BrothColors.get)
    return Scenes.ensure(0, POS)


def run(scene, seconds):
    for _ in range(int(round(seconds / DT))):
        scene.frame(DT, True)


def mod(name):
    return world.molang.get((POS, "variable.mod_" + name))


# ---------------------------------------------------------------- 资源

def testTheModelHasAHandleBoneAfterItsParentAndNothingShowsItByDefault():
    bones = _bones()
    names = [bone["name"] for bone in bones]
    handle = bones[names.index("handle")]
    assert handle["parent"] == "cooking_pot" and names.index("handle") > names.index("cooking_pot"), "骨骼要排在父骨骼后面"
    entity = _json("entity", "cooking_pot.json")["minecraft:client_entity"]["description"]
    assert "variable.mod_handle = 0.0;" in entity["scripts"]["initialize"], "缺省没有吊把手（方块实体重建之后也回到这里）"
    controllers = _json("render_controllers", "cooking_pot.render_controllers.json")["render_controllers"]
    assert {"handle": "variable.mod_handle > 0.5"} in controllers["controller.render.arris_cooking_pot"]["part_visibility"]
    for name in ("controller.render.arris_cooking_pot_glow", "controller.render.arris_cooking_pot_broth"):
        assert controllers[name]["part_visibility"][0] == {"*": False}, "描边和汤面那两层不画它（它们先全隐藏、再点名开）：" + name


def testTheHandleCubesAreFarmersDelightsMirroredAcrossX():
    """FD 的吊把手是四张没有厚度的面片，JE 里每张两面都贴图（JE 剔除背面，各画各的那一面）。这里的材质 entity_alphatest 不剔除背面：
    两面都贴的话两张叠在同一个深度上、来回闪（用户在游戏里看到的），所以每张只贴一面，从两边都看得到它。"""
    cubes = [bone for bone in _bones() if bone["name"] == "handle"][0]["cubes"]
    got = [(cube["origin"], cube["size"], sorted(cube["uv"])) for cube in cubes]
    assert got == [
        ([-15, 8, 8], [14, 8, 0], ["north"]),                             # hoop：from [1,8,8] to [15,16,8]
        ([-15, 8, 7], [0, 8, 2], ["west"]),                               # 第二个 east_handle：from [15,8,7] to [15,16,9]
        ([-1, 8, 7], [0, 8, 2], ["west"]),                                # 第二个 west_handle：from [1,8,7] to [1,16,9]
        ([-15, 15.999, 7], [14, 0, 2], ["up"]),                           # top_handle：from [1,15.999,7] to [15,15.999,9]
    ], got
    assert cubes[0]["uv"]["north"] == {"uv": [1, 8 + ATLAS[1]], "uv_size": [14, 8]}, "hoop 的 uv [1,8,15,16]"
    assert cubes[1]["uv"]["west"] == {"uv": [0, ATLAS[1]], "uv_size": [2, 8]}
    assert cubes[3]["uv"]["up"] == {"uv": [2, ATLAS[1]], "uv_size": [14, 2]}, "top_handle 的 uv [2,0,16,2]"


def testEveryHandleFaceReadsInsideTheHandleTextureBlockOfTheAtlas():
    for bone in _bones():
        if bone["name"] != "handle":
            continue
        for cube in bone["cubes"]:
            for name, face in cube["uv"].items():
                (u, v), (width, height) = face["uv"], face["uv_size"]
                us, vs = sorted([u, u + width]), sorted([v, v + height])
                assert ATLAS[0] <= us[0] and us[1] <= ATLAS[0] + 16 and ATLAS[1] <= vs[0] and vs[1] <= ATLAS[1] + 16, (name, face)


def testTheAtlasIsStillSixtyFourSquare():
    with open(os.path.join(RP, "textures", "entity", "cooking_pot.png"), "rb") as handle:
        head = handle.read(24)
    assert head[:8] == b"\x89PNG\r\n\x1a\n" and struct.unpack(">II", head[16:24]) == (64, 64), "几何里写的 texture_width / height 是 64"
    description = _json("models", "entity", "cooking_pot.geo.json")["minecraft:geometry"][0]["description"]
    assert (description["texture_width"], description["texture_height"]) == (64, 64)


# ---------------------------------------------------------------- 场景把支架推给模型

def testTheSceneShowsTheHandleOrTheTrayAsTheLookSays():
    scene = setup()
    scene.apply(C.look([], support=Rules.HANDLE))
    run(scene, 0.3)
    assert mod("handle") == 1.0 and mod("shelf") == 0.0
    scene.apply(C.look([], support=Rules.TRAY))
    run(scene, 0.3)
    assert mod("handle") == 0.0 and mod("shelf") == 1.0, "吊把手收了、托盘出来"
    scene.apply(C.look([], support=Rules.NONE))
    run(scene, 0.3)
    assert mod("handle") == 0.0 and mod("shelf") == 0.0


def testWhenTheEngineRebuiltTheBlockEntityTheSupportIsPushedAgain():
    """实机：进世界十来秒后引擎重建过一次方块实体，没有事件，模型上的变量全回到初始值（PotModel.check 隔 0.5 秒读回 mod_open 发现）。"""
    scene = setup()
    scene.apply(C.look([], support=Rules.HANDLE))
    run(scene, 0.7)
    assert mod("handle") == 1.0
    world.molang.clear()                                 # 重建：引擎那边的值全丢了
    run(scene, 0.7)
    assert mod("handle") == 1.0 and mod("shelf") == 0.0 and mod("open") == 1.0, "吊把手跟着别的值一起整份重推"
    scene.apply(C.look([], support=Rules.TRAY))
    run(scene, 0.3)
    world.molang.clear()
    run(scene, 0.7)
    assert mod("handle") == 0.0 and mod("shelf") == 1.0, "托盘也一样"


def testALookWithoutASupportOrWithAnUnknownOneIsNoSupport():
    scene = setup()
    scene.apply(C.look([], support=Rules.HANDLE))
    scene.apply(C.look([], support=9))
    run(scene, 0.3)
    assert mod("handle") == 0.0 and mod("shelf") == 0.0, "不是三个数之一：当没有"
    payload = C.look([])
    payload.pop("support", None)
    other = setup()
    other.apply(payload)
    run(other, 0.3)
    assert other.look.support == Rules.NONE and mod("handle") == 0.0


def testTheSupportOfTheSavedLookIsRestoredWhenTheChunkLoads():
    """方块实体数据里的 potLook 镜像带着 support：区块晚加载的客户端不用等广播就看得到吊把手。"""
    setup()
    world.exData[POS] = {Scenes.LOOK_KEY: {"__type__": "compound", "__value__": {
        "items": [{}] * 6, "heated": False, "support": {"__type__": "int", "__value__": Rules.HANDLE}}}}
    Scenes.OnBlockEntityLoaded({"blockName": "arris:cooking_pot", "dimensionId": 0, "posX": POS[0], "posY": POS[1], "posZ": POS[2]})
    scene = Scenes.sceneAt(0, POS)
    run(scene, 0.3)
    assert scene.look.support == Rules.HANDLE and mod("handle") == 1.0


# ---------------------------------------------------------------- 方块实体加载时按存档补变量

def _restore():
    engine = sys.modules[fdtest.SCRIPTS + ".Client.Engine"]
    engine.unwrap = lambda value, default=None: value["__value__"] if isinstance(value, dict) and "__value__" in value else (value or default)
    return C.load("Client.BlockEntityRestore")


def _flag(value):
    return {"__type__": "float", "__value__": value}


def testTheClientRestoresTheHandleVariableOfAPotWhenItsBlockEntityLoads():
    Restore = _restore()
    for flag in (1.0, 0.0):
        C.reset()
        world.exData[POS] = {"handleEnable": _flag(flag), "shelfEnable": _flag(0.0), "heatParticleEnable": _flag(1.0)}
        Restore.OnBlockEntityLoaded({"blockName": "arris:cooking_pot", "posX": POS[0], "posY": POS[1], "posZ": POS[2]})
        assert mod("handle") == flag and mod("shelf") == 0.0 and mod("heat") == 1.0, flag


def testAPotWithoutTheSavedFlagAndASkilletGetNoHandleVariable():
    Restore = _restore()
    C.reset()
    world.exData[POS] = {"shelfEnable": _flag(1.0), "heatParticleEnable": _flag(0.0)}
    Restore.OnBlockEntityLoaded({"blockName": "arris:cooking_pot", "posX": POS[0], "posY": POS[1], "posZ": POS[2]})
    assert mod("handle") is None and mod("shelf") == 1.0, "/setblock 放的锅没有这个键：不推"
    C.reset()
    world.exData[POS] = {"handleEnable": _flag(1.0), "shelfEnable": _flag(1.0)}
    Restore.OnBlockEntityLoaded({"blockName": "arris:skillet", "posX": POS[0], "posY": POS[1], "posZ": POS[2]})
    assert mod("handle") is None and mod("shelf") == 1.0, "煎锅没有吊把手"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
