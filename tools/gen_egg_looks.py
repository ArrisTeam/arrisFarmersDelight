# -*- coding: utf-8 -*-
"""gen_egg_looks - 生成煎蛋从生到熟的几张专用图标 rp/textures/items/egg_look_*.png（开发工具，py -3 运行，要 Pillow）

JE 画煎锅 / 炉灶里的蛋：煎蛋的图标按 RAW_EGG（0xC8E6E2D8，半透明发灰）往白渐变着色（HoD 的 KitchenLooks.fryingTint 对蛋的那一支）。
基岩版的客户端掉落物没法着色，所以把几档的颜色烤进图标：第 k 档（Shared/Rules/EggLook.py 的 STAGES 档）是朝上那面煎到 k / STAGES 的颜色，
从 rp/textures/items/fried_egg.png 逐像素相乘（红绿蓝各乘着色的红绿蓝 / 255，透明度也乘）。着色的颜色就是 EggLook.tintOf 算的，
这里不另写一份。图标物品的定义在 bp/netease_items_beh、rp/netease_items_res，贴图名在 rp/textures/item_texture.json（静态文件，测试核对）。

用法：py -3 tools/gen_egg_looks.py [--check]
  不带参数：写文件；--check：只比较，不一致就非 0 退出（测试会跑）。
"""
import importlib
import os
import sys

sys.dont_write_bytecode = True      # 别在行为包里留 .pyc

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ITEMS = os.path.join(ROOT, "rp", "textures", "items")
SOURCE = os.path.join(ITEMS, "fried_egg.png")
sys.path.insert(0, os.path.join(ROOT, "bp"))
EggLook = importlib.import_module("arrisFarmersDelightScripts.Shared.Rules.EggLook")


def shade(source, tint):
    """source（RGBA）逐像素乘上 tint（ARGB 整数）。"""
    alpha, red, green, blue = (tint >> 24) & 0xFF, (tint >> 16) & 0xFF, (tint >> 8) & 0xFF, tint & 0xFF
    image = Image.new("RGBA", source.size, (0, 0, 0, 0))
    for y in range(source.size[1]):
        for x in range(source.size[0]):
            r, g, b, a = source.getpixel((x, y))
            image.putpixel((x, y), (int(r * red / 255.0 + 0.5), int(g * green / 255.0 + 0.5), int(b * blue / 255.0 + 0.5),
                                    int(a * alpha / 255.0 + 0.5)))
    return image


def path(name):
    return os.path.join(ITEMS, name.split(":", 1)[1] + ".png")


def same(file, image):
    if not os.path.isfile(file):
        return False
    old = Image.open(file).convert("RGBA")
    return old.size == image.size and old.tobytes() == image.tobytes()


def main(argv):
    check = "--check" in argv
    source = Image.open(SOURCE).convert("RGBA")
    bad = []
    for stage, name in enumerate(EggLook.ITEMS):
        image = shade(source, EggLook.tintOf(stage))
        if not same(path(name), image):
            bad.append(path(name))
            if not check:
                image.save(path(name))
    wanted = set(os.path.basename(path(name)) for name in EggLook.ITEMS)
    extra = [name for name in sorted(os.listdir(ITEMS)) if name.startswith("egg_look_") and name not in wanted]
    for file in bad:
        print(("不是最新：" if check else "已写：") + os.path.relpath(file, ROOT))
    for name in extra:
        print("多出来的贴图：" + name)
    return 1 if check and (bad or extra) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
