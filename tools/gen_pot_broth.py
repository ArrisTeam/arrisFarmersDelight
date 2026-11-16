# -*- coding: utf-8 -*-
"""gen_pot_broth - 拼出厨锅汤面用的贴图 rp/textures/entity/cooking_pot_broth.png（开发工具，py -3 运行，要 Pillow）

32x512：左边 16 列是 Diegesis 的 block/liquid.png（汤面的纹理，32 帧、每帧 16x16，着色器每 0.1 秒换一帧）；
右边第 16..23 列从上到下是 Diegesis 的 block/bits 六张 8x8 的碎料图案（灰度，着色器按配料的颜色染）：
coin / chunk / nugget / shred / leaf / drop——次序就是着色器里的图案号（Shared/Rules/PotPiecesLook.py 的 KINDS）。
两样都来自 .refs/diegesis（MIT，见 THIRD_PARTY_NOTICES.md）。.refs 不进仓库：没有它时不写文件，--check 算通过。
用法：py -3 tools/gen_pot_broth.py [--check]
"""
import os
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE = os.path.join(ROOT, ".refs", "diegesis", "common", "src", "main", "resources", "assets", "diegesis", "textures", "block")
OUT = os.path.join(ROOT, "rp", "textures", "entity", "cooking_pot_broth.png")
SIZE = (32, 512)
BITS = ("coin", "chunk", "nugget", "shred", "leaf", "drop")
BITS_X, BIT = 16, 8


def build():
    sheet = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    sheet.paste(Image.open(os.path.join(SOURCE, "liquid.png")).convert("RGBA"), (0, 0))
    for index, name in enumerate(BITS):
        sheet.paste(Image.open(os.path.join(SOURCE, "bits", name + ".png")).convert("RGBA"), (BITS_X, index * BIT))
    return sheet


def main(argv):
    check = "--check" in argv
    if not os.path.isdir(SOURCE):
        print("没有 .refs/diegesis：跳过")
        return 0
    sheet = build()
    current = Image.open(OUT).convert("RGBA") if os.path.isfile(OUT) else None
    if current is not None and current.size == sheet.size and current.tobytes() == sheet.tobytes():
        print("已是最新：%s" % os.path.relpath(OUT, ROOT))
        return 0
    if check:
        print("不是最新：%s" % os.path.relpath(OUT, ROOT))
        return 1
    sheet.save(OUT)
    print("已写：%s" % os.path.relpath(OUT, ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
