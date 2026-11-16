# -*- coding: utf-8 -*-
"""je_model_to_netease - 把 JE 的方块模型（models/block/*.json 的 elements）转成网易方块模型（开发工具，py -3 运行）

输出是 rp/models/netease_block/ 下的 netease:block_geometry（blocks.json 的 netease_model 指向它）。换算依据 Strata 知识库
kb/engine/rp/16_netease_block_model（引擎反汇编核实）与 JE 的 FaceBakery / FaceInfo：
- 文件空间 x 取反：一个方块占 x ∈ [-16, 0]；元素 from/to 换成 origin = (-to.x, from.y, from.z)、size = to - from；
- 旋转：JE 绕一根轴转 angle（右手），pivot 是 origin；网易读成 (-rx, -ry, +rz)、pivot.x 取反，所以 x、y 轴取 -angle、z 轴取 +angle，
  pivot = (-ox, oy, oz)；
- UV：JE 的 [u0, v0, u1, v1] 除了顶面都是 uv = [u0, v0]、uv_size = [u1 - u0, v1 - v0]（负的就是翻转）；网易的顶面四个角另排，
  写 uv = [u1, v1]、uv_size = [u0 - u1, v0 - v1]；面的旋转 rotation 对应 rot（只认 0 / 90 / 180，别的值一律按 270）；
- 贴图：JE 的 "#名字" 换成 description.textures 里的下标，名字由 --map 给（terrain_texture.json 的短名）。
JE 里没有对应物、网易模型也不支持的（shade、forge_data 的自发光、cullface、tintindex、groups）直接丢掉；rescale 和省略 uv 的面不支持，报错。
tests/test_je_model_convert.py 用 JE 的烘焙规则逐顶点逐 UV 对照这里的输出。

用法：py -3 tools/je_model_to_netease.py --je <JE 模型 json> --id arris:xxx --icon arris:xxx_icon --map salad=arris:gleaming_salad [...] --out <输出 json>
"""
import argparse
import io
import json
import sys

# 引擎面键的顺序（down, up, north, south, west, east）
FACES = ("down", "up", "north", "south", "west", "east")
TEXTURE_SIZE = 16


def num(value):
    """整数值写成整数，别的保持小数；-0.0 写成 0。"""
    return int(value) if value == int(value) else value


def rotationOf(rotation):
    """JE 元素旋转 {angle, axis, origin} -> (网易 rotation, 网易 pivot)。"""
    if rotation.get("rescale"):
        raise ValueError("不支持 rescale 的旋转")
    angle, axis = rotation["angle"], rotation["axis"]
    if axis not in ("x", "y", "z"):
        raise ValueError("旋转轴 %r" % axis)
    result = [0, 0, 0]
    result["xyz".index(axis)] = num(angle if axis == "z" else -angle)
    ox, oy, oz = rotation["origin"]
    return result, [num(-ox), num(oy), num(oz)]


def faceOf(direction, face, textureIndex):
    """JE 一个面 -> 网易 uv 里的一项（texture、uv、uv_size，旋转了再加 rot）。"""
    if "uv" not in face:
        raise ValueError("%s 面没写 uv（JE 会按元素大小自动算，这里不支持）" % direction)
    u0, v0, u1, v1 = face["uv"]
    if direction == "up":
        entry = {"texture": textureIndex, "uv": [num(u1), num(v1)], "uv_size": [num(u0 - u1), num(v0 - v1)]}
    else:
        entry = {"texture": textureIndex, "uv": [num(u0), num(v0)], "uv_size": [num(u1 - u0), num(v1 - v0)]}
    rot = int(face.get("rotation", 0)) % 360
    if rot % 90:
        raise ValueError("面旋转 %r 不是 90 的倍数" % rot)
    if rot:
        entry["rot"] = rot
    return entry


def textureNames(model, mapping):
    """description.textures 的顺序：按各元素、各面第一次用到的先后，面按引擎面键的顺序（不看 JSON 里键的先后，py2 的字典没有顺序）。"""
    names = []
    for element in model["elements"]:
        for direction in FACES:
            if direction not in element["faces"]:
                continue
            ref = element["faces"][direction]["texture"]
            if not ref.startswith("#"):
                raise ValueError("面的贴图 %r 不是 #引用" % ref)
            if ref[1:] not in mapping:
                raise ValueError("--map 里没有 %s" % ref[1:])
            if mapping[ref[1:]] not in names:
                names.append(mapping[ref[1:]])
    return names


def convert(model, identifier, icon, mapping):
    """JE 模型（已读成 dict）-> 网易方块模型 dict。mapping：JE 贴图名 -> terrain_texture.json 短名。"""
    names = textureNames(model, mapping)
    cubes = []
    for element in model["elements"]:
        fx, fy, fz = element["from"]
        tx, ty, tz = element["to"]
        cube = {"origin": [num(-tx), num(fy), num(fz)], "size": [num(tx - fx), num(ty - fy), num(tz - fz)]}
        if element.get("rotation"):
            cube["rotation"], cube["pivot"] = rotationOf(element["rotation"])
        uv = {}
        for direction in FACES:
            if direction in element["faces"]:
                face = element["faces"][direction]
                uv[direction] = faceOf(direction, face, names.index(mapping[face["texture"][1:]]))
        unknown = set(element["faces"]) - set(FACES)
        if unknown:
            raise ValueError("不认识的面 %r" % sorted(unknown))
        cube["uv"] = uv
        cubes.append(cube)
    description = {
        "identifier": identifier,
        "textures": names,
        "textures_descriptions": [{"width": TEXTURE_SIZE, "length": TEXTURE_SIZE} for _name in names],
        "use_ao": True,
    }
    if icon:
        description["item_texture"] = icon
    return {
        "format_version": "1.13.0",
        "netease:block_geometry": {
            "bones": [{"name": "bone", "pivot": [0, 0, 0], "rotation": [0, 0, 0], "cubes": cubes}],
            "description": description,
        },
    }


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--je", required=True, help="JE 方块模型 json")
    parser.add_argument("--id", required=True, help="description.identifier（blocks.json 的 netease_model 写它）")
    parser.add_argument("--icon", default="", help="description.item_texture（物品栏里的平面图标，terrain_texture.json 短名）")
    parser.add_argument("--map", action="append", default=[], metavar="JE贴图名=短名")
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    mapping = dict(item.split("=", 1) for item in args.map)
    with io.open(args.je, encoding="utf-8") as handle:
        model = json.load(handle)
    text = json.dumps(convert(model, args.id, args.icon, mapping), indent=4, ensure_ascii=False, sort_keys=True)
    with io.open(args.out, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
