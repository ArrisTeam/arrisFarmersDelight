# -*- coding: utf-8 -*-
"""PotRecipeMemory - 厨锅记着上一道配方：锅里的料换成了另一道菜，进度从头来（双端，纯规则）

移植自 Farmer's Delight 1.20 的 CookingPotBlockEntity.getMatchingRecipe（281-307 行）：锅记着上次做的配方（lastRecipeID，不存档，
区块重载后是空的）；每个加热着、有料的步按下面的次序决定这一步按哪条配方煮：
1. 上次的配方现在还凑得成：就是它，进度不动；
2. 凑不成了，而盛出格里摆着的正是它的成品：这一步没有配方（盛出格不空，不另找新的）；
3. 找到了新配方：和上次不是同一条（有上次的话）就把进度清零（cookTime = 0），记下新的；
4. 什么也找不到：没有配方，记着的还是上次那条——做到一半拿掉一样料、过一会儿再放回去，进度只是掉了一点（不煮时每刻掉 2 刻），
   不会清零；中间换成别的菜才清零。
配方用配方表里的序号认（Shared/Rules/CookingPot.matchIndex），没有上一条就是 None。FD 的 checkNewRecipe 只是"料没变就不再找"
的缓存，找的结果不变，这里不需要。
"""


class RecipeMemory(object):
    """一口锅记着的上一条配方（FD 的 lastRecipeID）。"""

    def __init__(self):
        self.last = None

    def look(self, found, lastIsMeal):
        """这一步的配方：返回 (配方序号或 None, 进度要不要清零)。
        found 是现在的料凑成的配方序号（凑不成是 None）；lastIsMeal 是盛出格里摆着的正是上一条配方的成品。"""
        last = self.last
        if last is not None:
            if found == last:
                return last, False
            if lastIsMeal:
                return None, False
        if found is None:
            return None, False
        self.last = found
        return found, last is not None and found != last
