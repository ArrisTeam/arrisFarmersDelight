# -*- coding: utf-8 -*-
"""gen_pot_badge - 生成厨锅徽章用的小贴图 rp/textures/ui/pot_badge/*.png（开发工具，py -3 运行，要 Pillow）

徽章（厨锅右边那块牌：底板、星、进度条、火苗、"+N"）在 JE 里是一个个像素方块拼的；基岩版每样东西用一张小贴图，
没亮满的星、没走完的进度条靠界面图片的裁切。贴图就是 Shared/Rules/HandsOn/PotBadgeGlyphs.py 的 PATTERNS 里那些字符画：
# 画成白色不透明、别的透明，颜色在界面上染（底板 0x8C1E140C、没亮的 0x50FFF2DC、亮的 0xFFFFCB6B）。

用法：py -3 tools/gen_pot_badge.py [--check]
  不带参数：写文件；--check：只比较，不一致就非 0 退出（测试会跑）。
"""
import importlib
import os
import sys

sys.dont_write_bytecode = True      # 别在行为包里留 .pyc

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "rp", "textures", "ui", "pot_badge")
sys.path.insert(0, os.path.join(ROOT, "bp"))
Glyphs = importlib.import_module("arrisFarmersDelightScripts.Shared.Rules.HandsOn.PotBadgeGlyphs")
INK = (255, 255, 255, 255)


def draw(rows):
    image = Image.new("RGBA", (len(rows[0]), len(rows)), (0, 0, 0, 0))
    for y, line in enumerate(rows):
        for x, char in enumerate(line):
            if char == "#":
                image.putpixel((x, y), INK)
    return image


def same(path, image):
    if not os.path.isfile(path):
        return False
    old = Image.open(path).convert("RGBA")
    return old.size == image.size and old.tobytes() == image.tobytes()


def main(argv):
    check = "--check" in argv
    bad = []
    if not check and not os.path.isdir(OUT):
        os.makedirs(OUT)
    for name, rows in sorted(Glyphs.PATTERNS.items()):
        path = os.path.join(OUT, name + ".png")
        image = draw(rows)
        if not same(path, image):
            bad.append(path)
            if not check:
                image.save(path)
    extra = [name for name in (os.listdir(OUT) if os.path.isdir(OUT) else []) if name.endswith(".png") and name[:-4] not in Glyphs.PATTERNS]
    for path in bad:
        print(("不是最新：" if check else "已写：") + os.path.relpath(path, ROOT))
    for name in extra:
        print("多出来的贴图：" + name)
    return 1 if check and (bad or extra) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
