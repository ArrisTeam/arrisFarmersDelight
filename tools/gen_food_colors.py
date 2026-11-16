# -*- coding: utf-8 -*-
"""gen_food_colors - 按物品贴图算"这件东西是什么颜色"，生成 Shared/Data/FoodColors.py（开发工具，py -3 运行，要 Pillow）

照 Hands-On Delight 的 client/FoodColors.sample：贴图里不透明的像素按鲜艳度（1 + 最大分量 - 最小分量）加权平均，
灰的描边说明不了食物是什么颜色。砧板切东西飞的碎屑按它染色（HoD 的 BoardBehavior）。
农夫乐事的物品读本包 rp/ 的贴图，原版的食材读游戏自带的资源包（路径用 --vanilla 指定，缺省是本机 MCDK 用的 3.10）。
用法：py -3 tools/gen_food_colors.py [--vanilla <游戏的 resource_packs/vanilla 目录>] [--check]
"""
import io
import json
import os
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "bp", "arrisFarmersDelightScripts", "Shared", "Data", "FoodColors.py")
VANILLA_DEFAULT = "D:/MCStudioDownload/game/MinecraftPE_Netease/3.10.0.448891/data/resource_packs/vanilla"

# 原版食材：物品名 -> 贴图（相对原版资源包）
VANILLA = {
    "minecraft:beef": "textures/items/beef_raw", "minecraft:cooked_beef": "textures/items/beef_cooked",
    "minecraft:porkchop": "textures/items/porkchop_raw", "minecraft:cooked_porkchop": "textures/items/porkchop_cooked",
    "minecraft:chicken": "textures/items/chicken_raw", "minecraft:cooked_chicken": "textures/items/chicken_cooked",
    "minecraft:mutton": "textures/items/mutton_raw", "minecraft:cooked_mutton": "textures/items/mutton_cooked",
    "minecraft:cod": "textures/items/fish_raw", "minecraft:cooked_cod": "textures/items/fish_cooked",
    "minecraft:salmon": "textures/items/fish_salmon_raw", "minecraft:cooked_salmon": "textures/items/fish_salmon_cooked",
    "minecraft:tropical_fish": "textures/items/fish_clownfish_raw", "minecraft:rabbit": "textures/items/rabbit_raw",
    "minecraft:potato": "textures/items/potato", "minecraft:baked_potato": "textures/items/potato_baked",
    "minecraft:carrot": "textures/items/carrot", "minecraft:beetroot": "textures/items/beetroot", "minecraft:apple": "textures/items/apple",
    "minecraft:bread": "textures/items/bread", "minecraft:egg": "textures/items/egg", "minecraft:cake": "textures/items/cake",
    "minecraft:melon_slice": "textures/items/melon", "minecraft:pumpkin_pie": "textures/items/pumpkin_pie",
    "minecraft:sweet_berries": "textures/items/sweet_berries", "minecraft:glow_berries": "textures/items/glow_berries",
    "minecraft:kelp": "textures/items/kelp", "minecraft:dried_kelp": "textures/items/dried_kelp", "minecraft:cookie": "textures/items/cookie",
    "minecraft:wheat": "textures/items/wheat", "minecraft:sugar": "textures/items/sugar", "minecraft:ink_sac": "textures/items/dye_powder_black",
    "minecraft:brown_mushroom": "textures/blocks/mushroom_brown", "minecraft:red_mushroom": "textures/blocks/mushroom_red",
    "minecraft:pumpkin": "textures/blocks/pumpkin_side", "minecraft:melon_block": "textures/blocks/melon_side",
}


def sample(path):
    """HoD 的 FoodColors.sample：不透明像素按鲜艳度加权平均，返回 0xRRGGBB；读不到返回 None。"""
    for ext in (".png", ".tga"):
        if os.path.exists(path + ext):
            image = Image.open(path + ext).convert("RGBA")
            break
    else:
        return None
    red = green = blue = weight = 0
    width, height = image.size
    for y in range(height):
        for x in range(width):
            r, g, b, a = image.getpixel((x, y))
            if a < 128:
                continue
            vivid = 1 + max(r, g, b) - min(r, g, b)
            red, green, blue, weight = red + r * vivid, green + g * vivid, blue + b * vivid, weight + vivid
    return None if weight == 0 else (red // weight) << 16 | (green // weight) << 8 | (blue // weight)


def _texture(entry):
    textures = entry.get("textures") if isinstance(entry, dict) else entry
    return textures[0] if isinstance(textures, list) else textures


def colors(vanilla):
    table = {}
    items = json.load(io.open(os.path.join(ROOT, "rp", "textures", "item_texture.json"), encoding="utf-8-sig"))["texture_data"]
    for name, entry in sorted(items.items()):
        if name.startswith("arris:"):
            color = sample(os.path.join(ROOT, "rp", _texture(entry)))
            if color is not None:
                table[name] = color
    terrain = json.load(io.open(os.path.join(ROOT, "rp", "textures", "terrain_texture.json"), encoding="utf-8-sig"))["texture_data"]
    for name in ("arris:wild_cabbages", "arris:wild_beetroots", "arris:wild_carrots", "arris:wild_onions", "arris:wild_potatoes",
                 "arris:wild_rice", "arris:wild_tomatoes", "arris:brown_mushroom_colony", "arris:red_mushroom_colony"):
        if name in terrain and name not in table:
            color = sample(os.path.join(ROOT, "rp", _texture(terrain[name])))
            if color is not None:
                table[name] = color
    for name, path in sorted(VANILLA.items()):
        color = sample(os.path.join(vanilla, path))
        if color is not None:
            table[name] = color
    return table


def render(table):
    lines = [
        "# -*- coding: utf-8 -*-",
        '"""FoodColors - 物品是什么颜色（双端，纯数据，由 tools/gen_food_colors.py 按贴图生成，别手改）',
        "",
        "照 Hands-On Delight 的 FoodColors.sample：不透明像素按鲜艳度加权平均。砧板切东西飞的碎屑按它染色。",
        '"""',
        "FoodColors = {",
    ]
    for name in sorted(table):
        lines.append("    %r: 0x%06X," % (str(name), table[name]))
    lines.append("}")
    return "\n".join(lines) + "\n"


def main(argv):
    vanilla = argv[argv.index("--vanilla") + 1] if "--vanilla" in argv else VANILLA_DEFAULT
    text = render(colors(vanilla))
    current = io.open(OUT, encoding="utf-8").read() if os.path.exists(OUT) else ""
    if "--check" in argv:
        return 0 if current == text else 1
    if current != text:
        io.open(OUT, "w", encoding="utf-8", newline="\n").write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
