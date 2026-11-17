# -*- coding: utf-8 -*-
# runner: both
"""锅里的料换成另一道菜，进度从头来（Shared/Rules/PotRecipeMemory.py + Server/HandCooking.py，引擎是 potfake.py 里的假的）。

FD 的 CookingPotBlockEntity.getMatchingRecipe（281-307 行）：锅记着上次做的配方（lastRecipeID，不存档）；
上次的配方还凑得成就是它；凑不成了而盛出格里摆着的正是它的成品，这一步没有配方；找到的新配方和上次不是同一条，进度清零；
什么也找不到，记着的还是上次那条（做到一半拿掉一样料再放回去，进度只是掉了一点，没有清零）。加热着、有料的步才问这一遍。
"""
from __future__ import print_function

import dgtest
import fdtest
import potkit as K
from potkit import POT, SAUCE, fake

Memory = fdtest.load("Shared.Rules.PotRecipeMemory")
HandCooking = K.HandCooking
SAUCE_AT, RICE_AT = 3, 4                    # 配方表里番茄酱（两格番茄，5 秒）和熟米饭（一格米，5 秒）的序号
RICE = K.Recipes.CookingPotRecipeList[RICE_AT]["Recipe"][0][0][0]
COOKED_RICE = K.Recipes.CookingPotRecipeList[RICE_AT]["CookResult"][0]


def _lay(recipeAt, each=8):
    """锅里的料换成第 recipeAt 条配方第一种写法的料（每格 each 个，一种料一格），别的格清空；不经站点，像漏斗放的。"""
    slots = fake.containers[(0, POT)]
    for index in range(6):
        slots[index] = None
    for index, kind in enumerate(K.Recipes.CookingPotRecipeList[recipeAt]["Recipe"][0]):
        fake.setContainer(POT, index, kind[0], each, aux=kind[1])


def _cookTime():
    return HandCooking.handOf(0, POT).clock.cookTime


def _cooking(recipeAt, seconds):
    """放着 recipeAt 的料煮 seconds 秒。"""
    manager, data = K.setup()
    _lay(recipeAt)
    K.alone(seconds)
    return data


# ---------------------------------------------------------------- 规则：记着的上一条配方

def testTheFirstRecipeIsJustRemembered():
    memory = Memory.RecipeMemory()
    assert memory.look(None, False) == (None, False) and memory.last is None
    assert memory.look(3, False) == (3, False) and memory.last == 3, "没有上一条：不算换了"


def testTheSameRecipeAgainKeepsTheProgress():
    memory = Memory.RecipeMemory()
    memory.look(3, False)
    assert memory.look(3, False) == (3, False)


def testAnotherRecipeThanTheLastRestartsTheProgress():
    memory = Memory.RecipeMemory()
    memory.look(3, False)
    assert memory.look(4, False) == (4, True) and memory.last == 4
    assert memory.look(4, False) == (4, False), "只在换的那一步清零一次"


def testNothingMatchingKeepsTheLastRecipeSoBackToItIsNotAChange():
    memory = Memory.RecipeMemory()
    memory.look(3, False)
    assert memory.look(None, False) == (None, False) and memory.last == 3
    assert memory.look(3, False) == (3, False), "A、没有、A：进度只掉了一点，不清零"


def testNothingThenAnotherRecipeRestarts():
    memory = Memory.RecipeMemory()
    memory.look(3, False)
    memory.look(None, False)
    assert memory.look(4, False) == (4, True), "A、没有、B：清零"


def testWhileTheLastRecipesMealWaitsNoNewRecipeIsLookedFor():
    memory = Memory.RecipeMemory()
    memory.look(3, False)
    assert memory.look(4, True) == (None, False) and memory.last == 3, "盛出格里摆着上一道菜：这一步没有配方，记着的不变"
    assert memory.look(3, True) == (3, False), "料又凑得成上一条：照常煮"
    assert memory.look(None, True) == (None, False)


def testTheMealOfAnotherRecipeDoesNotBlockTheSearch():
    memory = Memory.RecipeMemory()
    memory.look(3, False)
    assert memory.look(4, False) == (4, True), "盛出格里是别的菜（lastIsMeal 假）：照常找新配方"


# ---------------------------------------------------------------- 锅：换了菜进度从头来

def testSwappingTheIngredientsForAnotherDishStartsTheProgressOver():
    data = _cooking(SAUCE_AT, 3.0)
    assert 2.9 < _cookTime() < 3.1, "番茄酱煮了 3 秒"
    _lay(RICE_AT)
    K.alone(0.2)
    assert abs(_cookTime() - 0.2) < 1e-6, "换成米：从头算，这一步煮了 0.2 秒（不是 3.2）"
    assert abs(data["timer"] - (5.0 - _cookTime())) < 1e-6, "界面读的 timer 也跟着回到头"
    K.alone(4.4)
    assert K.preview() == {}, "米煮了 4.6 秒：还没好（接着番茄酱的 3 秒的话 2 秒就好了）"
    K.alone(0.4)
    assert K.preview()["newItemName"] == COOKED_RICE and _cookTime() < 0.5, "5 秒到了才出锅"


def testTakingOneIngredientOutAndPuttingItBackOnlyLosesALittle():
    _cooking(SAUCE_AT, 3.0)
    fake.containers[(0, POT)][1] = None                      # 拿掉一个番茄：凑不成任何菜
    K.alone(0.4)
    assert 2.1 < _cookTime() < 2.3, "不煮时每秒掉 2 秒：3.0 - 0.8"
    fake.setContainer(POT, 1, "arris:tomato", 8)
    K.alone(0.2)
    assert 2.3 < _cookTime() < 2.5, "放回去还是番茄酱：接着煮，没有清零"


def testTakingOneIngredientOutAndPuttingInSomethingThatMakesAnotherDishStartsOver():
    _cooking(SAUCE_AT, 3.0)
    fake.setContainer(POT, 0, "minecraft:dirt", 3)            # 凑不成菜
    fake.containers[(0, POT)][1] = None
    K.alone(0.2)
    assert 2.5 < _cookTime() < 2.7
    _lay(RICE_AT)
    K.alone(0.2)
    assert abs(_cookTime() - 0.2) < 1e-6, "A、没有、B：清零"


def testTheFirstRecipeAfterTheChunkReloadsIsNotAChange():
    # FD 的 lastRecipeID 不存档：读回来之后第一条配方没有"上一条"可比，进度（cookTime 是存了的）照旧
    data = _cooking(SAUCE_AT, 3.0)
    HandCooking._hands.clear()
    _lay(RICE_AT)
    K.alone(0.2)
    assert 3.1 < _cookTime() < 3.3, _cookTime()


def testNothingIsAskedWhileThePotIsNotHeatedSoTheChangeCountsWhenItHeatsUpAgain():
    # cookingTick：isHeated && hasInput 才调 getMatchingRecipe；没热的时候进度只往回掉
    data = _cooking(SAUCE_AT, 3.0)
    data["heatEnable"] = False
    _lay(RICE_AT)
    K.alone(0.2)
    assert 2.5 < _cookTime() < 2.7, "没热源：只掉 0.4 秒，没有清零"
    data["heatEnable"] = True
    K.alone(0.2)
    assert abs(_cookTime() - 0.2) < 1e-6, "再热起来的这一步才认出换了菜"


def testWhileTheMealOfTheLastDishStillWaitsTheNewDishIsNotLookedFor():
    # getMatchingRecipe：上一条凑不成了，盛出格里摆着的又是它的成品：不另找新的，所以进度只是往回掉，换回来还接着煮
    manager, data = K.setup()
    K.setMeal(SAUCE, 1, data)                                # 上一批番茄酱没装碗，还在盛出格里
    _lay(SAUCE_AT)
    K.alone(3.0)
    _lay(RICE_AT)
    K.alone(0.2)
    assert 2.5 < _cookTime() < 2.7 and K.preview()["newItemName"] == SAUCE, "米不煮（盛出格被占着），进度掉 0.4"
    _lay(SAUCE_AT)
    K.alone(0.2)
    assert 2.7 < _cookTime() < 2.9, "料换回番茄酱：接着煮，没有清零"


def testTheStirredBatchStartsOverToo():
    manager, data = K.setup()
    K.feed(manager, "arris:tomato", 8)
    K.feed(manager, "arris:tomato", 8, slotIndex=1)
    K.run(manager, 2.0, stir=True)
    before = _cookTime()
    assert before > 0.8, before                              # 整批 8 份、搅了 2 秒：每秒走 1.5 / sqrt(8) 约 0.53 个配方秒
    fake.setContainer(POT, 0, RICE, 2)
    fake.containers[(0, POT)][1] = None
    K.run(manager, 0.2, stir=True)
    assert _cookTime() < 0.4, "搅着煮的整批也一样：换了菜从头来（%r -> %r）" % (before, _cookTime())


if __name__ == "__main__":
    raise SystemExit(dgtest.run(globals()))
