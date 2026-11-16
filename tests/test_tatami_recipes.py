# -*- coding: utf-8 -*-
# runner: py3
"""榻榻米配方对照 JE（FarmersDelight 1.20：full_tatami_mat、full_tatami_mat_from_halves、half_tatami_mat、tatami_block_from_full）。

四条都是无序配方：榻榻米方块 -> 2 长垫、2 短垫 -> 1 长垫、1 长垫 -> 2 短垫、2 长垫 -> 1 榻榻米方块；
JE 没有"榻榻米方块直接拆短垫"的配方（原来基岩版自己加的"1 个方块 -> 4 个短垫"已去掉）。成品的做法总账在 test_recipe_parity.py。
"""
from __future__ import print_function

import fdtest
import recipekit


def testRecipesAreTheFourJavaShapelessConversions():
    recipes = recipekit.byIdentifier()
    expected = {"arris:tatami_full_mat": ([("arris:tatami", 1)], ("arris:tatami_full_mat", 2)),
                "arris:tatami_full_mat_from_halves": ([("arris:tatami_half_mat", 2)], ("arris:tatami_full_mat", 1)),
                "arris:tatami_half_mat": ([("arris:tatami_full_mat", 1)], ("arris:tatami_half_mat", 2)),
                "arris:tatami_block_from_full": ([("arris:tatami_full_mat", 2)], ("arris:tatami", 1))}
    for identifier, (ingredients, result) in sorted(expected.items()):
        kind, body = recipes[identifier]
        assert kind == "shapeless", identifier
        assert sorted(recipekit.ingredientsOf(kind, body).items()) == sorted(ingredients), identifier
        assert recipekit.resultsOf(body) == [result], identifier
    # 原来的"榻榻米方块拆成 4 个短垫"是基岩版自己加的，JE 没有
    for kind, body in recipekit.loadRecipes().values():
        if kind == "shapeless" and recipekit.resultsOf(body)[0][0] == "arris:tatami_half_mat":
            assert "arris:tatami" not in recipekit.ingredientsOf(kind, body)


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
