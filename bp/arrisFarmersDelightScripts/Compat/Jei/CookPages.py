# -*- coding: utf-8 -*-
"""CookPages - JEI 的煎锅、炉灶两个分类共用的：营火配方怎么分页、配方页怎么画（客户端）

一页一组原料（Shared/Rules/StationBooks.cookGroups）：成品相同、原料都在原版 minecraft:egg 标签里的并成一页（基岩版的三种蛋，
原料那一格每秒换一种），别的一件一页。按成品查得到那一页，按组里任何一件原料查用途也查得到。
秒数和站点食谱书页脚的同一句（HoD 的键），先经 shownSeconds 换成整数再填（直接填 6.0 英文会写成 6.0 s）。
"""
from .Registry import SetHoverText
from ...Client import Texts
from ...Shared.Rules.StationBooks import cookGroups, shownSeconds

SECONDS = ("handson_delight.book.seconds", "%d 秒")
INPUT = "/bg/jeiInputItemRender"
OUTPUT = "/bg/jeiOutputItemRender"
RENDERER = "/item_cell/item/item_renderer"


def records():
    """[{"input": 第一件原料, "inputs": 这一页的全部原料, "output": 成品}]，每页一条。"""
    return [{"input": raws[0], "inputs": list(raws), "output": result} for raws, result in cookGroups()]


def register(registry, recipeTag):
    """按成品、按原料登记全部配方页（物品的 aux 不看，和原来一样）。"""
    found = records()
    for itemData in registry.getAllRegisteredItems():
        byResult = [record for record in found if record["output"] == itemData[0]]
        if byResult:
            registry.setRecipeByResult(recipeTag, itemData, byResult)
        byInput = [record for record in found if itemData[0] in record["inputs"]]
        if byInput:
            registry.setRecipeByInput(recipeTag, itemData, byInput)


class CookRecipe(object):
    """一页：原料、成品、多少秒（seconds() 由子类给：煎锅 6 秒、炉灶 30 秒）。"""

    def __init__(self, screenNode, recipeControl, recipeData, recipeIndex, itemData):
        self.screenNode = screenNode
        self.recipeControl = recipeControl
        self.recipeData = recipeData
        self.recipeIndex = recipeIndex
        self.itemData = itemData
        self.indexTurns = 0  # 原料轮播索引

    def seconds(self):
        return 0

    def _show(self, path, name):
        self.recipeControl.GetChildByPath(path + RENDERER).asItemRenderer().SetUiItem(name, 0)
        SetHoverText(self.recipeControl, path, name)

    def OnCreate(self):
        """创建配方UI时调用"""
        self.recipeControl.GetChildByPath("/bg/timer").asLabel().SetText(Texts.fill(SECONDS[0], SECONDS[1], shownSeconds(self.seconds())))
        self._show(INPUT, self.recipeData["input"])
        self._show(OUTPUT, self.recipeData["output"])

    def OnInterval(self):
        """原料不止一种（三种蛋并成的那一页）时每秒换一种。"""
        inputs = self.recipeData.get("inputs") or ()
        if len(inputs) > 1:
            self.indexTurns = (self.indexTurns + 1) % len(inputs)
            self._show(INPUT, inputs[self.indexTurns])
