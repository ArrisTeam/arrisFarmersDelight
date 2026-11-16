# -*- coding: utf-8 -*-
"""gen_item_masks - 按物品贴图生成"图标的实心像素"表 Shared/Data/ItemMasks.py（开发工具，py -3 运行，要 Pillow）

Hands-On Delight 的砧板把板上的物品按它的图标画（ItemVoxels.read：alpha >= 128 的像素是实心），刀口线穿过实心像素的中心、
顺着它们最长的方向（ItemVoxels.Icon.axis），虚线只画在实心像素上（solidSpan）。基岩版的客户端读不到物品贴图的像素，
所以这里把砧板上要切的东西的图标离线读出来，每行一个整数（第 0 列是最低位，实心为 1），客户端照 JE 的算法在这个掩码上算
（Shared/Rules/HandsOn/BoardMarks.py）。没有贴图的东西（方块、别的包的物品）不进表，客户端按整格实心算。
农夫乐事的物品读本包 rp/ 的贴图，原版的读游戏自带的资源包（路径用 --vanilla 指定，缺省是本机 MCDK 用的 3.10）。
用法：py -3 tools/gen_item_masks.py [--vanilla <resource_packs/vanilla 目录>] [--check] [--show 物品名]
"""
import importlib.util
import io
import json
import os
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "bp", "arrisFarmersDelightScripts")
OUT = os.path.join(SCRIPTS, "Shared", "Data", "ItemMasks.py")
VANILLA_DEFAULT = "D:/MCStudioDownload/game/MinecraftPE_Netease/3.10.0.448891/data/resource_packs/vanilla"
SOLID = 128                      # ItemVoxels.read：alpha >= 128 算实心

# 原版物品名 -> 贴图（相对原版资源包）：图标名和物品名不一样的列在这里，其余按"去掉 minecraft: 当图标名"去 item_texture.json 里找
VANILLA = {
    "minecraft:beef": "textures/items/beef_raw", "minecraft:porkchop": "textures/items/porkchop_raw",
    "minecraft:chicken": "textures/items/chicken_raw", "minecraft:mutton": "textures/items/mutton_raw",
    "minecraft:muttonraw": "textures/items/mutton_raw", "minecraft:cooked_chicken": "textures/items/chicken_cooked",
    "minecraft:cooked_mutton": "textures/items/mutton_cooked", "minecraft:cod": "textures/items/fish_raw",
    "minecraft:cooked_cod": "textures/items/fish_cooked", "minecraft:salmon": "textures/items/fish_salmon_raw",
    "minecraft:cooked_salmon": "textures/items/fish_salmon_cooked", "minecraft:cake": "textures/items/cake",
    "minecraft:pumpkin_pie": "textures/items/pumpkin_pie", "minecraft:ink_sac": "textures/items/dye_powder_black",
    "minecraft:wooden_door": "textures/items/door_wood", "minecraft:clay": "textures/items/clay_ball",
}


def _data(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(SCRIPTS, "Shared", "Data", name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _json(path):
    return json.load(io.open(path, encoding="utf-8-sig"))["texture_data"]


def _texture(entry):
    textures = entry.get("textures") if isinstance(entry, dict) else entry
    return textures[0] if isinstance(textures, list) else textures


def paths(vanilla):
    """要切的东西的物品名 -> 贴图文件（不带扩展名）；找不到的不列。"""
    ours = _json(os.path.join(ROOT, "rp", "textures", "item_texture.json"))
    theirs = _json(os.path.join(vanilla, "textures", "item_texture.json")) if os.path.isdir(vanilla) else {}
    found = {}
    for name, _aux in sorted(_data("Cutting").CuttingBoardDict):
        if name.startswith("arris:") and name in ours:
            found[name] = os.path.join(ROOT, "rp", _texture(ours[name]))
        elif name in VANILLA:
            found[name] = os.path.join(vanilla, VANILLA[name])
        elif name.startswith("minecraft:") and name[len("minecraft:"):] in theirs:
            found[name] = os.path.join(vanilla, _texture(theirs[name[len("minecraft:"):]]))
    return found


def rows(path):
    """一张贴图 -> (宽, 高, [每行一个整数])；读不到返回 None。"""
    for ext in (".png", ".tga"):
        if os.path.exists(path + ext):
            image = Image.open(path + ext).convert("RGBA")
            break
    else:
        return None
    width, height = image.size
    out = []
    for y in range(height):
        out.append(sum(1 << x for x in range(width) if image.getpixel((x, y))[3] >= SOLID))
    return width, height, out


def table(vanilla):
    result = {}
    for name, path in sorted(paths(vanilla).items()):
        read = rows(path)
        if read is not None and any(read[2]):
            result[name] = read
    return result


def preview(read):
    width, height, lines = read
    return "\n".join("".join("#" if lines[y] >> x & 1 else "." for x in range(width)) for y in range(height))


def render(masks):
    lines = [
        "# -*- coding: utf-8 -*-",
        '"""ItemMasks - 砧板上要切的东西的图标哪些像素是实心（双端，纯数据，由 tools/gen_item_masks.py 按贴图生成，别手改）',
        "",
        "物品名 -> (宽, 高, 每行一个整数)：第 0 列是最低位，实心（alpha >= 128，同 HoD 的 ItemVoxels.read）为 1，第 0 行在图标最上面。",
        "刀口线怎么穿过它见 Shared/Rules/HandsOn/BoardMarks.py；表里没有的东西（方块、别的包的物品）客户端按整格实心算。",
        '"""',
        "ItemMasks = {",
    ]
    for name in sorted(masks):
        width, height, data = masks[name]
        lines.append("    %r: (%d, %d, (%s))," % (str(name), width, height, ", ".join("0x%04X" % row for row in data)))
    lines.append("}")
    return "\n".join(lines) + "\n"


def main(argv):
    vanilla = argv[argv.index("--vanilla") + 1] if "--vanilla" in argv else VANILLA_DEFAULT
    masks = table(vanilla)
    if "--show" in argv:
        print(preview(masks[argv[argv.index("--show") + 1]]))
        return 0
    text = render(masks)
    current = io.open(OUT, encoding="utf-8").read() if os.path.exists(OUT) else ""
    if "--check" in argv:
        return 0 if current == text else 1
    if current != text:
        io.open(OUT, "w", encoding="utf-8", newline="\n").write(text)
    print("%d 件" % len(masks))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
