# -*- coding: utf-8 -*-
"""modConfig - 过渡期转发壳（双端）

数据表已按领域拆进 Shared/Data，厨锅配方索引在 Shared/Rules/CookingPot，
联动契约函数在 Api/LegacyModAttr。这里只为还没迁走的旧模块保留同名导出，迁移完成后删除。
"""
from ..Shared.Data.Blocks import *  # noqa: F401,F403
from ..Shared.Data.Cooking import *  # noqa: F401,F403
from ..Shared.Data.CookingPotRecipes import *  # noqa: F401,F403
from ..Shared.Data.Cutting import *  # noqa: F401,F403
from ..Shared.Data.Effects import *  # noqa: F401,F403
from ..Shared.Data.Farming import *  # noqa: F401,F403
from ..Shared.Data.Food import *  # noqa: F401,F403
from ..Shared.Data.Mobs import *  # noqa: F401,F403
from ..Shared.Data.GuideBook import uiGuideBookPath, uiGuideBookScreen  # noqa: F401
from ..Shared.Rules.CookingPot import rebuildIndex as BuildCookingPotRecipeIndex  # noqa: F401
from ..Shared.Rules.CookingPot import lookupRecipe as LookupCookingPotRecipe  # noqa: F401
from ..Api.LegacyModAttr import ArrisFarmersDelightInterface, ArrisFarmersDelightObtain, AddCookingPotRecipe  # noqa: F401
