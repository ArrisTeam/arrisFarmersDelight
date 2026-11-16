# -*- coding: utf-8 -*-
"""blockkit - 方块定义、网易方块模型、贴图登记、名字的读取工具（不是测试本身，跑器只收 test_*.py）

给 test_tatami_mats_content.py、test_rope_fence_content.py 共用：把一个方块的行为包定义、blocks.json 登记、
模型文件、贴图文件、语言文件名字这几处按标识符对起来读。
"""
from __future__ import print_function

import io
import json
import os

import fdtest

RP = os.path.join(fdtest.ROOT, "rp")
BLOCKS_DIR = os.path.join(fdtest.BP, "netease_blocks")
MODELS_DIR = os.path.join(RP, "models", "netease_block")


def readJson(path):
    with io.open(path, encoding="utf-8-sig") as f:
        return json.load(f)


def blockDefinitions():
    """{标识符: (components, description)}：bp/netease_blocks 下（含子目录）的全部方块定义。"""
    found = {}
    for root, _dirs, files in os.walk(BLOCKS_DIR):
        for name in files:
            if name.endswith(".json"):
                block = readJson(os.path.join(root, name))["minecraft:block"]
                found[block["description"]["identifier"]] = (block["components"], block["description"])
    return found


def components(identifier):
    return blockDefinitions()[identifier][0]


def description(identifier):
    return blockDefinitions()[identifier][1]


def resourceBlocks():
    """rp/blocks.json：{标识符: 登记项}。"""
    return readJson(os.path.join(RP, "blocks.json"))


def terrainTextures():
    """rp/textures/terrain_texture.json：{贴图名: 文件路径（不带扩展名）}。"""
    data = readJson(os.path.join(RP, "textures", "terrain_texture.json"))["texture_data"]
    return dict((key, value["textures"]) for key, value in data.items())


def textureFileExists(path):
    return os.path.isfile(os.path.join(RP, path + ".png"))


def model(identifier):
    """网易方块模型（models/netease_block 下 netease:block_geometry.description.identifier 对得上的那份）。"""
    for name in os.listdir(MODELS_DIR):
        if name.endswith(".json"):
            geometry = readJson(os.path.join(MODELS_DIR, name)).get("netease:block_geometry")
            if geometry and geometry["description"]["identifier"] == identifier:
                return geometry
    raise KeyError(identifier)


def langNames():
    """texts/zh_CN.lang：{键: 名字}。"""
    names = {}
    with io.open(os.path.join(RP, "texts", "zh_CN.lang"), encoding="utf-8-sig") as f:
        for line in f.read().splitlines():
            if "=" in line and not line.startswith("#"):
                key, value = line.split("=", 1)
                names[key.strip()] = value.strip()
    return names


def modelFaces(geometry):
    """模型里每根骨骼的每个立方体的面：[(骨骼名, enable 表达式或 None, 立方体, {面名: 面})]。"""
    found = []
    for bone in geometry["bones"]:
        for cube in bone["cubes"]:
            found.append((bone["name"], bone.get("enable"), cube, cube["uv"]))
    return found


def cubeBounds(cube):
    """立方体在方块像素坐标（x 向东、z 向南，和 JE 模型的 from / to 同一套，不转的立方体）里的包围盒 ((x0, y0, z0), (x1, y1, z1))。

    网易模型文件里的 x 是取了反的：整格的 origin.x 是 -16，所以 x0 = -(origin.x + size.x)、x1 = -origin.x。
    """
    ox, oy, oz = cube["origin"]
    sx, sy, sz = cube["size"]
    return (-(ox + sx), oy, oz), (-ox, oy + sy, oz + sz)

