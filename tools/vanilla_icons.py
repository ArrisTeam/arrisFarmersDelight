# -*- coding: utf-8 -*-
"""vanilla_icons - 原版物品在原版资源包里读哪张贴图（开发工具，gen_broth_colors 用）

JE 取一件东西的颜色看它模型的粒子贴图（HoD 的 FoodColors.main：ItemVoxels.model(stack).getParticleIcon()）：平面物品（食物、船、告示牌、门、皮甲、
花……）是它自己的图标，方块物品（原木、石头、栅栏、活板门……）是方块模型的粒子贴图（原木取侧面，栅栏、按钮、压力板取木板）。
基岩版的原版资源包里没有"物品 -> 图标"的表（那份在引擎里），这里按规则找，找不到的返回 None（调用的人要列出来，不能编颜色）：
  1. 名字不规则的平面图标（IRREGULAR_ITEMS：门 door_<木>、船 boat_<木>、告示牌 sign_<木>、矿车 minecart_<种>、生羊肉）；
  2. 名字对得上的平面图标 textures/items/<名字>（皮甲、鞍、蛋糕、悬挂式告示牌、樱木 / 红树 / 竹的门船和告示牌……）；
  3. 方块：blocks.json 里这个方块的贴图名（有 side 取侧面，再试 north、up）-> terrain_texture.json 里的路径。
返回的路径相对原版资源包、不带扩展名。
"""
import io
import json
import os

WOODS_WITH_OLD_DOORS = ("acacia", "birch", "dark_oak", "jungle", "spruce")
WOODS_WITH_OLD_BOATS = ("oak", "acacia", "birch", "dark_oak", "jungle", "spruce")
WOODS_WITH_OLD_SIGNS = ("acacia", "birch", "jungle", "spruce", "crimson", "warped")
IRREGULAR_ITEMS = {
    "minecraft:wooden_door": "door_wood", "minecraft:oak_sign": "sign", "minecraft:dark_oak_sign": "sign_darkoak",
    "minecraft:chest_minecart": "minecart_chest", "minecraft:hopper_minecart": "minecart_hopper", "minecraft:tnt_minecart": "minecart_tnt",
    "minecraft:muttonraw": "mutton_raw",
}
for _wood in WOODS_WITH_OLD_DOORS:
    IRREGULAR_ITEMS["minecraft:%s_door" % _wood] = "door_%s" % _wood
for _wood in WOODS_WITH_OLD_BOATS:
    IRREGULAR_ITEMS["minecraft:%s_boat" % _wood] = "boat_%s" % _wood
for _wood in WOODS_WITH_OLD_SIGNS:
    IRREGULAR_ITEMS["minecraft:%s_sign" % _wood] = "sign_%s" % _wood


def _json(path):
    return json.load(io.open(path, encoding="utf-8-sig"))


def _exists(base, path):
    return any(os.path.exists(os.path.join(base, path + ext)) for ext in (".png", ".tga"))


def _first(entry):
    """terrain_texture.json 一项的第一张贴图路径（字符串、列表、带 path 的字典都有）。"""
    textures = entry.get("textures") if isinstance(entry, dict) else entry
    if isinstance(textures, list):
        textures = textures[0] if textures else None
    if isinstance(textures, dict):
        textures = textures.get("path")
    return textures


class VanillaIcons(object):
    """原版资源包目录 base 里的物品贴图查找。"""

    def __init__(self, base):
        self.base = base
        self.terrain = _json(os.path.join(base, "textures", "terrain_texture.json"))["texture_data"]
        self.blocks = _json(os.path.join(base, "blocks.json"))

    def textureOf(self, name):
        flat = "textures/items/" + IRREGULAR_ITEMS.get(name, name.split(":")[-1])
        if _exists(self.base, flat):
            return flat
        return self._block(name.split(":")[-1])

    def _block(self, short):
        block = self.blocks.get(short)
        faces = block.get("textures") if isinstance(block, dict) else None
        if isinstance(faces, dict):
            faces = faces.get("side") or faces.get("north") or faces.get("up")
        path = _first(self.terrain[faces]) if isinstance(faces, str) and faces in self.terrain else None
        return path if path and _exists(self.base, path) else None
