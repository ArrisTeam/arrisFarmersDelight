# -*- coding: utf-8 -*-
"""gen_broth_colors - 按物品贴图算汤色、碎料色、倒进锅里的液体色，生成 Shared/Data/BrothColors.py（开发工具，py -3 运行，要 Pillow）

照 Hands-On Delight 的 client/FoodColors.java，取色规则在 bp/.../Shared/Rules/HandsOn/PotColors.py（纯函数，和 JDK 逐位对过）：
  BrothColors   每道厨锅菜（我们厨锅配方的每个成品）的汤色：FoodColors.broth——色相分 12 份取最大的一族，容器（配方的 Vessel，没有就是
                物品自带的合成剩余物）自己的颜色去掉，或者容器的颜色没画在菜上就只看图标上面 60% 的行；
  MainColors    每件配料（配方里出现的物品，加上它进炉子烧出来的熟食）切成碎料时的颜色：FoodColors.main；
  PouredColors  倒进锅里的液体（HoD 的 poured 标签里本包有的）：和空容器的图标不一样的像素里最多的那种颜色（ItemVoxels.contents），
                加上生蛋搅进去的 0xF2DC9A；
  CookedForms   配料 -> 它进炉子烧出来的熟食（CookedPieces.cooked：熟的还是食物才换），碎料按熟的颜色。
农夫乐事的物品读本包 rp/ 的贴图，原版的读游戏自带的资源包（路径用 --vanilla 指定，缺省是本机 MCDK 用的 3.10；那个目录不在时，原版物品沿用
现有 BrothColors.py 里的值、只重算本包的物品，--check 也只比本包的物品）。
用法：py -3 tools/gen_broth_colors.py [--vanilla <游戏的 resource_packs/vanilla 目录>] [--check]
"""
import glob
import importlib
import importlib.util
import io
import json
import os
import sys

sys.dont_write_bytecode = True      # 别在 tools/ 和行为包里留 .pyc（下面导入的模块也算）

from PIL import Image

import gen_food_colors

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BP = os.path.join(ROOT, "bp")
OUT = os.path.join(BP, "arrisFarmersDelightScripts", "Shared", "Data", "BrothColors.py")
sys.path.insert(0, BP)
SCRIPTS = "arrisFarmersDelightScripts.Shared."
Colors = importlib.import_module(SCRIPTS + "Rules.HandsOn.PotColors")
Recipes = importlib.import_module(SCRIPTS + "Data.CookingPotRecipes")
Remainders = importlib.import_module(SCRIPTS + "Data.Remainders")

# gen_food_colors.VANILLA 里没有的原版物品：贴图相对原版资源包
VANILLA_MORE = {
    "minecraft:mushroom_stew": "textures/items/mushroom_stew", "minecraft:beetroot_soup": "textures/items/beetroot_soup",
    "minecraft:rabbit_stew": "textures/items/rabbit_stew", "minecraft:cooked_rabbit": "textures/items/rabbit_cooked",
    "minecraft:rotten_flesh": "textures/items/rotten_flesh", "minecraft:bone": "textures/items/bone",
    "minecraft:bone_meal": "textures/items/dye_powder_white", "minecraft:cocoa_beans": "textures/items/dye_powder_brown",
    "minecraft:hanging_roots": "textures/items/hanging_roots", "minecraft:glow_lichen": "textures/blocks/glow_lichen",
    "minecraft:bowl": "textures/items/bowl", "minecraft:glass_bottle": "textures/items/potion_bottle_empty",
    "minecraft:bucket": "textures/items/bucket_empty", "minecraft:milk_bucket": "textures/items/bucket_milk",
    "minecraft:water_bucket": "textures/items/bucket_water", "minecraft:lava_bucket": "textures/items/bucket_lava",
    "minecraft:honey_bottle": "textures/items/honey_bottle", "minecraft:dragon_breath": "textures/items/dragons_breath",
}
# 方块物品的图标（terrain_texture.json 里的名字）：JE 里这个物品是平面图标
BLOCK_ICONS = {"arris:stuffed_pumpkin_block_stage0": "arris:stuffed_pumpkin_block_icon"}
# HoD 的 poured 标签里本包有的物品：倒出来的是容器里的液体，容器是物品自带的合成剩余物
POURED = ("minecraft:milk_bucket", "minecraft:water_bucket", "minecraft:lava_bucket", "minecraft:honey_bottle", "minecraft:dragon_breath",
          "arris:milk_bottle", "arris:tomato_sauce")
CRACKED = ("minecraft:egg",)    # HoD 的 cracked 标签：生蛋搅进汤里是蛋黄加蛋白的颜色 FoodColors.EGG
# 原版的熔炉配方里烧出食物的（本包自己的熔炉配方读 bp/recipes）
VANILLA_SMELTING = {
    "minecraft:beef": "minecraft:cooked_beef", "minecraft:porkchop": "minecraft:cooked_porkchop", "minecraft:chicken": "minecraft:cooked_chicken",
    "minecraft:mutton": "minecraft:cooked_mutton", "minecraft:rabbit": "minecraft:cooked_rabbit", "minecraft:cod": "minecraft:cooked_cod",
    "minecraft:salmon": "minecraft:cooked_salmon", "minecraft:potato": "minecraft:baked_potato", "minecraft:kelp": "minecraft:dried_kelp",
}


def _json(*path):
    return json.load(io.open(os.path.join(ROOT, *path), encoding="utf-8-sig"))


def _first(entry):
    textures = entry.get("textures") if isinstance(entry, dict) else entry
    return textures[0] if isinstance(textures, list) else textures


def readIcon(path):
    """贴图文件（不带扩展名，找 .png 再找 .tga）-> (pixels, width, height)；没有返回 None。动画条（高是宽的整数倍）只取第一帧。"""
    for ext in (".png", ".tga"):
        if os.path.exists(path + ext):
            image = Image.open(path + ext).convert("RGBA")
            break
    else:
        return None
    width, height = image.size
    if height > width and height % width == 0:
        height = width
    pixels = [image.getpixel((x, y)) for y in range(height) for x in range(width)]
    return pixels, width, height


class Icons(object):
    """物品名 -> 图标。本包的物品读 rp/ 的贴图，原版的读 vanilla 目录（None = 这台机器上没有）。"""

    def __init__(self, vanilla):
        self.vanilla = vanilla if vanilla and os.path.isdir(vanilla) else None
        self.items = _json("rp", "textures", "item_texture.json")["texture_data"]
        self.terrain = _json("rp", "textures", "terrain_texture.json")["texture_data"]
        self.vanillaPaths = dict(gen_food_colors.VANILLA, **VANILLA_MORE)

    def ours(self, name):
        if name in BLOCK_ICONS:
            return readIcon(os.path.join(ROOT, "rp", _first(self.terrain[BLOCK_ICONS[name]])))
        if name in self.items:
            return readIcon(os.path.join(ROOT, "rp", _first(self.items[name])))
        return None

    def get(self, name):
        if name.startswith("minecraft:"):
            return readIcon(os.path.join(self.vanilla, self.vanillaPaths[name])) if self.vanilla and name in self.vanillaPaths else None
        return self.ours(name)


def furnaceRecipes():
    """本包 bp/recipes 里的熔炉配方：{输入: 输出}（只收进 furnace 的）。"""
    found = {}
    for path in sorted(glob.glob(os.path.join(ROOT, "bp", "recipes", "*.json"))):
        recipe = json.load(io.open(path, encoding="utf-8-sig")).get("minecraft:recipe_furnace")
        if recipe and "furnace" in recipe.get("tags", []):
            found[recipe["input"]["item"]] = recipe["output"]["item"]
    return found


def ingredientNames():
    """厨锅配方里出现的所有配料名，按出现的先后。"""
    names = []
    for recipe in Recipes.CookingPotRecipeList:
        for variant in recipe["Recipe"]:
            for name, _aux in variant:
                if name not in names:
                    names.append(name)
    return names


def dishes():
    """[(成品名, 盛它的容器名或 None)]：配方表里每个成品第一次出现的那条，容器是配方的 Vessel，没有就是物品自带的合成剩余物。"""
    found = []
    for recipe in Recipes.CookingPotRecipeList:
        result = recipe["CookResult"][0]
        if result not in [dish for dish, _c in found]:
            vessel = recipe.get("Vessel")
            found.append((result, vessel[0] if vessel else Remainders.craftRemainderOf(result)))
    return found


def compute(icons, previous):
    """-> 四张表。算一个值要的图标没读到（这台机器没有原版资源包）就沿用 previous（现有的表）；本包自己的物品读不到贴图就报错。"""
    missing, tables = [], {"BrothColors": {}, "MainColors": {}, "PouredColors": {}, "CookedForms": {}}

    def icon(name):
        found = icons.get(name)
        if found is None and not (name.startswith("minecraft:") and not icons.vanilla):
            missing.append(name)
        return found

    def keep(table, name, value):
        if value is not None:
            tables[table][name] = value
        elif name in previous.get(table, {}):
            tables[table][name] = previous[table][name]

    def withContainer(name, container, rule):
        """图标和容器的图标都读到了才算；容器没有（None）算读到了。"""
        full, box = icon(name), (icon(container) if container else None)
        return rule(full, box) if full is not None and (not container or box is not None) else None

    for dish, container in dishes():
        keep("BrothColors", dish, withContainer(dish, container, lambda full, box: Colors.brothOf(full[0], full[1], full[2], box)))
    smelting = dict(VANILLA_SMELTING, **furnaceRecipes())
    names = ingredientNames()
    for name in names:
        if name in smelting:
            tables["CookedForms"][name] = smelting[name]
    for name in names + sorted(set(tables["CookedForms"].values())):
        found = icon(name)
        keep("MainColors", name, Colors.sampleMain(found[0], found[1], found[2]) if found else None)
    for name in POURED:
        keep("PouredColors", name, withContainer(name, Remainders.craftRemainderOf(name), Colors.liquidColor))
    for name in CRACKED:
        tables["PouredColors"][name] = Colors.EGG
    if missing:
        raise SystemExit("读不到这些物品的贴图: " + ", ".join(sorted(set(missing))))
    return tables


def render(tables):
    lines = [
        "# -*- coding: utf-8 -*-",
        '"""BrothColors - 汤色、碎料色、倒进锅里的液体色（双端，纯数据，由 tools/gen_broth_colors.py 按贴图生成，别手改）',
        "",
        "照 Hands-On Delight 的 FoodColors（取色规则在 Shared/Rules/HandsOn/PotColors.py）。颜色都是 0xRRGGBB。",
        "BrothColors   每道厨锅菜的汤色（FoodColors.broth：去掉容器自己的颜色，色相分 12 份取最大一族）；没有的菜用 FALLBACK。",
        "MainColors    每件配料和它烧熟之后的样子切成碎料时的颜色（FoodColors.main）。",
        "PouredColors  倒进锅里的液体的颜色（和空容器不一样的像素里最多的那种），和生蛋搅进去的 RAW_EGG。",
        "CookedForms   配料 -> 它进炉子烧出来的熟食（CookedPieces.cooked），碎料按熟的颜色。",
        '"""',
        "FALLBACK = 0x%06X" % Colors.FALLBACK,
        "RAW_EGG = 0x%06X" % Colors.EGG,
        "",
    ]
    for table, numeric in (("BrothColors", True), ("MainColors", True), ("PouredColors", True), ("CookedForms", False)):
        lines.append("%s = {" % table)
        for name in sorted(tables[table]):
            value = tables[table][name]
            shown = repr(str(value)) if not numeric else ("RAW_EGG" if table == "PouredColors" and name in CRACKED else "0x%06X" % value)
            lines.append("    %r: %s," % (str(name), shown))
        lines.append("}")
        lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n"


def loadPrevious():
    if not os.path.exists(OUT):
        return {}
    spec = importlib.util.spec_from_file_location("BrothColorsPrevious", OUT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return dict((table, getattr(module, table)) for table in ("BrothColors", "MainColors", "PouredColors", "CookedForms"))


def ownOnly(tables):
    """--check 在没有原版资源包的机器上只比本包的物品。"""
    return dict((table, dict((k, v) for k, v in rows.items() if not k.startswith("minecraft:"))) for table, rows in tables.items())


def main(argv):
    vanilla = argv[argv.index("--vanilla") + 1] if "--vanilla" in argv else gen_food_colors.VANILLA_DEFAULT
    icons = Icons(vanilla)
    if icons.vanilla is None:
        print("原版资源包不在 %s：原版物品沿用现有的值，只重算本包的物品" % vanilla)
    previous = loadPrevious()
    tables = compute(icons, previous)
    text = render(tables)
    current = io.open(OUT, encoding="utf-8").read() if os.path.exists(OUT) else ""
    if "--check" in argv:
        if icons.vanilla is None:
            return 0 if ownOnly(tables) == ownOnly(previous) else 1
        return 0 if current == text else 1
    if current != text:
        io.open(OUT, "w", encoding="utf-8", newline="\n").write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
