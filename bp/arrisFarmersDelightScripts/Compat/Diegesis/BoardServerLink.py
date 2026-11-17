# -*- coding: utf-8 -*-
"""BoardServerLink - 联动步骤 board（服务端）：登记切菜板站点，登记上了就打开它连带的旁观声音和工作台拦截

BoardLogic.register 在配置里关了砧板站点（cutting_board）时返回 None（前置包 API 不够新时也是，Presence 已经挡掉了）：这一步记成 skipped，
砧板和它连带的东西一起没有，砧板照农夫乐事原样用。工作台拦截（DishCrafts）还要看 remove_crafting_recipes
（没有砧板站点时 Options.removeCraftingRecipes 本来就是假）。
"""
from . import BoardLogic, DishCrafts
from ...Server import BoardLook
from ...Shared.Rules import HandsOnOptions as Options


def link(ctx):
    if BoardLogic.register(ctx.api) is None:
        return False
    if Options.removeCraftingRecipes():
        DishCrafts.register()    # 改在砧板上摆的菜：工作台不再出（照 HoD 在 JE 上的缺省）；配置里关了 remove_crafting_recipes 就照旧
    BoardLook.enable()           # 附近没开站点的人也听得到切菜声（站点里的人收站点自己的 effect）
    return True
