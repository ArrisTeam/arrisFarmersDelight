# -*- coding: utf-8 -*-
"""gen_tatami - 榻榻米方块两两配对的样子：照 JE 的方块状态 + 模型算出每个状态六个面各贴哪张图、转几个直角，写进方块 JSON 的
states / permutations，转好要用的贴图、登记进 terrain_texture.json（开发工具，py -3 运行，要 Pillow）

JE（FarmersDelight 1.20 blockstates/tatami.json）按 facing × paired 选模型：没配对是 tatami_half（六面单块），配对是
tatami_odd / tatami_even（侧面是半张、开口朝另一半），再按 x / y 转；模型的面还带 rotation。基岩版的 material_instances
每个面只能给一张图、不能转，所以把 JE 每个面上贴图实际的摆向换算到基岩 full_block 那一面的贴图坐标里（顺时针转几个直角），
用事先转好的图。JE 的算法照抄：顶点的 UV（CuboidFace.getU / getV：rotation 让顶点下标挪 rotation / 90 位）、方块状态的转动
（ModelRotation：先绕 X 轴转 -x°，再绕 Y 轴转 -y°），贴图跟着面转（uvlock 没开）。
基岩 full_block 每个面的贴图坐标（从外面正对着看，贴图的右、上）：前五面和 JE 一样；底面右 = 西、上 = 北，和 JE（东、南）差 180°
（arrisCreate 机壳连接纹理真机标定；Strata 引擎资料：旧管线底面 (x, 1−z)，full_block 底面 (1−x, z)）。
JE 的三张图本包都有：tatami.png（和 tatami_mat_half.png 是同一张图）= arris:tatami_mat_half，tatami_odd、tatami_even 同名。

方块 JSON 只改 description.states 和 permutations，components 是手写的、原样保留。方块态的名字、取值的意思在
Shared/Rules/TatamiPair.py。12 个状态各一条 permutation（条件两两互斥），用到 3 张图 × 4 个转角。
用法：py -3 tools/gen_tatami.py [--check]
"""
from __future__ import print_function

import io
import json
import os
import re
import sys
from collections import OrderedDict

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RP = os.path.join(ROOT, "rp")
BLOCK_JSON = os.path.join(ROOT, "bp", "netease_blocks", "arris_tatami.json")
TERRAIN_JSON = os.path.join(RP, "textures", "terrain_texture.json")

FACING_STATE = "arris:tatami_facing"
PAIRED_STATE = "arris:paired"
FACINGS = ("down", "up", "north", "south", "west", "east")      # 方块态取值的顺序 = 网易 Facing 枚举
FACES = ("up", "down", "north", "south", "west", "east")

# JE 的贴图键 -> (本包 terrain_texture 里的名字, 文件)
SOURCES = OrderedDict([
    ("single", ("arris:tatami_mat_half", "textures/blocks/tatami_mat_half")),
    ("odd", ("arris:tatami_odd", "textures/blocks/tatami_odd")),
    ("even", ("arris:tatami_even", "textures/blocks/tatami_even")),
])
TURN_SUFFIX = ("", "_cw90", "_cw180", "_cw270")                 # 顺时针转 0 / 1 / 2 / 3 个直角的图
_ROTATED = re.compile(r"^arris:tatami_(mat_half|odd|even)_cw(90|180|270)$")
_TRANSPOSE = (None, Image.Transpose.ROTATE_270, Image.Transpose.ROTATE_180, Image.Transpose.ROTATE_90)   # PIL 的角度是逆时针

# JE blockstates/tatami.json：(facing, paired) -> (模型, x, y)
JE_VARIANTS = {
    ("down", False): ("tatami_half", 180, 0), ("down", True): ("tatami_even", 180, 0),
    ("up", False): ("tatami_half", 0, 0), ("up", True): ("tatami_odd", 0, 0),
    ("north", False): ("tatami_half", 90, 0), ("north", True): ("tatami_even", 90, 0),
    ("south", False): ("tatami_half", 90, 180), ("south", True): ("tatami_odd", 90, 180),
    ("west", False): ("tatami_half", 90, 270), ("west", True): ("tatami_even", 90, 270),
    ("east", False): ("tatami_half", 90, 90), ("east", True): ("tatami_odd", 90, 90),
}
# JE 模型：面 -> (贴图键, rotation)。tatami_half 是 cube_all（六面同一张、不转）；tatami_odd / tatami_even 照 models/block 下的文件
JE_MODELS = {
    "tatami_half": dict((face, ("single", 0)) for face in FACES),
    "tatami_odd": {"north": ("odd", 180), "east": ("even", 0), "south": ("odd", 180), "west": ("even", 0),
                   "up": ("single", 0), "down": ("single", 90)},
    "tatami_even": {"north": ("even", 0), "east": ("odd", 180), "south": ("even", 0), "west": ("odd", 180),
                    "up": ("single", 0), "down": ("single", 90)},
}

_DIRS = {"down": (0, -1, 0), "up": (0, 1, 0), "north": (0, 0, -1), "south": (0, 0, 1), "west": (-1, 0, 0), "east": (1, 0, 0)}
_FACE_OF = dict((vector, face) for face, vector in _DIRS.items())
# JE FaceInfo：每个面四个顶点（以方块中心为原点，±1 = 那一轴的大 / 小端）；顶点 0..3 不转时是贴图的左上、左下、右下、右上
_JE_VERTICES = {
    "down": ((-1, -1, 1), (-1, -1, -1), (1, -1, -1), (1, -1, 1)),
    "up": ((-1, 1, -1), (-1, 1, 1), (1, 1, 1), (1, 1, -1)),
    "north": ((1, 1, -1), (1, -1, -1), (-1, -1, -1), (-1, 1, -1)),
    "south": ((-1, 1, 1), (-1, -1, 1), (1, -1, 1), (1, 1, 1)),
    "west": ((-1, 1, -1), (-1, -1, -1), (-1, -1, 1), (-1, 1, 1)),
    "east": ((1, 1, 1), (1, -1, 1), (1, -1, -1), (1, 1, -1)),
}
# 基岩 full_block 每个面贴图的 (右, 上)
_BEDROCK_FRAME = {
    "up": ("east", "north"), "down": ("west", "north"),
    "north": ("west", "up"), "south": ("east", "up"), "west": ("south", "up"), "east": ("north", "up"),
}
_CLOCKWISE = ((0, 0), (16, 0), (16, 16), (0, 16))              # 贴图的四个角：左上、右上、右下、左下（顺时针）


def _turn(point, xDegrees, yDegrees):
    x, y, z = point
    for _ in range(xDegrees // 90 % 4):                         # 绕 X 转 -90°：上 -> 北 -> 下 -> 南
        x, y, z = x, z, -y
    for _ in range(yDegrees // 90 % 4):                         # 绕 Y 转 -90°：北 -> 东 -> 南 -> 西
        x, y, z = -z, y, x
    return (x, y, z)


def _jeCorner(vertex, rotation):
    index = (vertex + rotation // 90) % 4
    return (0 if index in (0, 1) else 16, 0 if index in (0, 3) else 16)


def _bedrockCorner(face, point):
    right, up = (_DIRS[name] for name in _BEDROCK_FRAME[face])
    return (16 if sum(a * b for a, b in zip(point, right)) > 0 else 0, 0 if sum(a * b for a, b in zip(point, up)) > 0 else 16)


def appearance(facing, paired):
    """JE 的 (facing, paired) 在世界里六个面的样子：{世界面: (贴图键, 顺时针转几个直角)}，按基岩 full_block 的贴图坐标。"""
    model, xDegrees, yDegrees = JE_VARIANTS[(facing, bool(paired))]
    look = {}
    for face, (key, rotation) in JE_MODELS[model].items():
        world = _FACE_OF[_turn(_DIRS[face], xDegrees, yDegrees)]
        lands = dict((_jeCorner(vertex, rotation), _bedrockCorner(world, _turn(point, xDegrees, yDegrees)))
                     for vertex, point in enumerate(_JE_VERTICES[face]))
        turns = [k for k in range(4) if all(lands[_CLOCKWISE[i]] == _CLOCKWISE[(i + k) % 4] for i in range(4))]
        assert len(turns) == 1, (facing, paired, face, lands)  # 只会是转动，不会是镜像
        look[world] = (key, turns[0])
    assert sorted(look) == sorted(FACES), (facing, paired)
    return look


def textureName(key, turns):
    return SOURCES[key][0] + TURN_SUFFIX[turns]


def texturePath(key, turns):
    return SOURCES[key][1] + TURN_SUFFIX[turns]


def states():
    return OrderedDict([(FACING_STATE, list(range(len(FACINGS)))), (PAIRED_STATE, [0, 1])])


def permutations():
    out = []
    for value, facing in enumerate(FACINGS):
        for paired in (0, 1):
            look = appearance(facing, paired)
            instances = OrderedDict([("*", {"texture": SOURCES["single"][0]})])
            for face in FACES:
                instances[face] = {"texture": textureName(*look[face])}
            out.append(OrderedDict([
                ("components", {"minecraft:material_instances": instances}),
                ("condition", "q.block_state('%s') == %d && q.block_state('%s') == %d" % (FACING_STATE, value, PAIRED_STATE, paired)),
            ]))
    return out


def usedTextures():
    """permutations 用到的 (贴图键, 转角)，按 SOURCES、转角排好。"""
    used = set()
    for facing in FACINGS:
        for paired in (0, 1):
            used.update(appearance(facing, paired).values())
    return sorted(used, key=lambda item: (list(SOURCES).index(item[0]), item[1]))


def _readText(path):
    with io.open(path, encoding="utf-8") as f:
        return f.read()


def _readJson(path):
    return json.loads(_readText(path), object_pairs_hook=OrderedDict)


def _render(document, sortKeys):
    """和这两份文件现有的写法一样：缩进 4、中文不转义、末尾不换行；方块 JSON 的键排好序，terrain_texture.json 保持原来的顺序。"""
    return json.dumps(document, indent=4, sort_keys=sortKeys, ensure_ascii=False)


def _writeText(path, text):
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def blockDocument():
    document = _readJson(BLOCK_JSON)
    block = document["minecraft:block"]
    block["description"]["states"] = states()
    block["permutations"] = permutations()
    return document


def terrainDocument():
    """terrain_texture.json：转好的图登记在原图后面；不再用到的转角图删掉。"""
    document = _readJson(TERRAIN_JSON)
    wanted = OrderedDict((textureName(key, turns), texturePath(key, turns)) for key, turns in usedTextures() if turns)
    data = OrderedDict()
    for name, entry in document["texture_data"].items():
        if _ROTATED.match(name):
            continue
        data[name] = entry
        for key, (source, _path) in SOURCES.items():
            if name == source:
                for turns in (1, 2, 3):
                    rotated = textureName(key, turns)
                    if rotated in wanted:
                        data[rotated] = {"textures": wanted[rotated]}
    document["texture_data"] = data
    return document


def images():
    """{文件（相对 rp，带 .png）: 转好的图}，只含转过的。"""
    out = OrderedDict()
    for key, turns in usedTextures():
        if turns:
            source = Image.open(os.path.join(RP, SOURCES[key][1] + ".png")).convert("RGBA")
            out[texturePath(key, turns) + ".png"] = source.transpose(_TRANSPOSE[turns])
    return out


def _staleImages(wanted):
    folder = os.path.join(RP, "textures", "blocks")
    return sorted("textures/blocks/" + name for name in os.listdir(folder)
                  if _ROTATED.match("arris:" + name[:-4]) and "textures/blocks/" + name not in wanted)


def check():
    problems = []
    if _readText(BLOCK_JSON) != _render(blockDocument(), sortKeys=True):
        problems.append("arris_tatami.json 的 states / permutations 不是最新的")
    if _readText(TERRAIN_JSON) != _render(terrainDocument(), sortKeys=False):
        problems.append("terrain_texture.json 里榻榻米转角图的登记不是最新的")
    wanted = images()
    for path, image in wanted.items():
        full = os.path.join(RP, path)
        if not os.path.isfile(full):
            problems.append("缺图 " + path)
        elif Image.open(full).convert("RGBA").tobytes() != image.tobytes():
            problems.append("图不对 " + path)
    problems += ["多余的图 " + path for path in _staleImages(wanted)]
    return problems


def write():
    _writeText(BLOCK_JSON, _render(blockDocument(), sortKeys=True))
    _writeText(TERRAIN_JSON, _render(terrainDocument(), sortKeys=False))
    wanted = images()
    for path, image in wanted.items():
        image.save(os.path.join(RP, path))
    for path in _staleImages(wanted):
        os.remove(os.path.join(RP, path))
    print("permutations %d 条，转角图 %d 张" % (len(permutations()), len(wanted)))


def main(argv):
    if "--check" in argv:
        problems = check()
        for problem in problems:
            print(problem)
        return 1 if problems else 0
    write()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
