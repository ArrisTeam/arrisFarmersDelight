# -*- coding: utf-8 -*-
# runner: both
"""经典玩法的右键盛菜（Server/PotServe.serveByHand，FD 的 CookingPotBlock.use -> CookingPotBlockEntity.useHeldItemOnMeal）里创造模式的一处：
JE 的 useHeldItemOnMeal 对手里的容器 container.shrink(1) 不看创造模式，创造模式照样扣一个碗（java:474-481）；盛出的一份照样进背包。
"""
from __future__ import print_function

import potkit as K

fake = K.fake
SAUCE, BOWL, POT = K.SAUCE, K.BOWL, K.POT


def _serve(creative):
    manager, data = K.setup(creative=creative)
    K.setMeal(SAUCE, 3, data)
    K.PotContainer.addUsed(data, SAUCE, 3)
    fake.give("a", 0, BOWL, 5)
    return K.PotServe.serveByHand("a", 0, POT)


def testASurvivalServeUsesUpOneBowl():
    assert _serve(False) is True
    assert fake.count("a", BOWL) == 4 and fake.count("a", SAUCE) == 1 and K.preview()["count"] == 2


def testACreativeServeUsesUpOneBowlToo():
    assert _serve(True) is True
    assert fake.count("a", BOWL) == 4, "JE 的 container.shrink(1) 不看创造模式"
    assert fake.count("a", SAUCE) == 1 and K.preview()["count"] == 2, "盛出的一份照样进背包，锅里少一份"


def testTheLastBowlIsUsedUpInCreativeToo():
    manager, data = K.setup(creative=True)
    K.setMeal(SAUCE, 3, data)
    K.PotContainer.addUsed(data, SAUCE, 3)
    fake.give("a", 0, BOWL, 1)
    assert K.PotServe.serveByHand("a", 0, POT) is True
    assert fake.world.players["a"]["inv"][0] is None or fake.world.players["a"]["inv"][0]["newItemName"] != BOWL
    assert fake.count("a", BOWL) == 0 and fake.count("a", SAUCE) == 1


if __name__ == "__main__":
    raise SystemExit(K.dgtest.run(globals()))
