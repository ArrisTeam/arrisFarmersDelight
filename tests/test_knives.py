# -*- coding: utf-8 -*-
# runner: both
"""是不是刀（Shared/Rules/Knives.isKnife）：knifeList（联动契约）∪ arris:knife ∪ common:knife 标签，服务端 IsKnife、客户端 isKnife、炉灶站点开不开都问它。

锁的事：
  1. 没有引擎口：knifeList 里的（含下游追加的）是刀；农夫乐事自己的五把刀按静态词表也是刀；剑、空手不是
  2. 只挂了 arris:knife 或 common:knife 标签的（别的模组的刀）是刀——口还没准备好也认（按单件问的照样问引擎）
  3. 炉灶站点：拿着只挂了标签的刀也开（原来只看 knifeList，R1 F.6）
  4. 服务端 Items.IsKnife 就是这条规则；knifeList 还是契约交出去的那个列表对象
"""
from __future__ import print_function

import fdtest

Tags = fdtest.load("Shared.Data.Tags")
Cutting = fdtest.load("Shared.Data.Cutting")
ItemTags = fdtest.load("Shared.Rules.ItemTags")
Knives = fdtest.load("Shared.Rules.Knives")
Grill = fdtest.load("Shared.Rules.GrillStation")


class TagPort(object):
    """只答按物品问的标签：tags = {物品名: [标签]}。"""

    def __init__(self, tags, ready=True):
        self.tags = tags
        self.isReady = ready

    def ready(self):
        return self.isReady

    def tagsOf(self, itemName, aux=0):
        return self.tags.get(itemName)

    def itemsOf(self, tag):
        return None


def _reset():
    for side in ItemTags.SIDES:
        ItemTags.setPort(side, None)


def testKnivesWithoutAnEnginePort():
    _reset()
    for name in Tags.ITEM_TAGS[Tags.KNIFE] + ("ends_delight:dragon_tooth_knife",):
        assert Knives.isKnife(name), name
    for name in ("minecraft:iron_sword", "minecraft:iron_axe", "arris:skillet_item", "", None):
        assert not Knives.isKnife(name), name
    Cutting.knifeList.append("mymod:cleaver")
    try:
        assert Knives.isKnife("mymod:cleaver"), "下游往 knifeList 里追加的"
    finally:
        Cutting.knifeList.remove("mymod:cleaver")
    assert not Knives.isKnife("mymod:cleaver")


def testKnivesByTagEvenBeforeThePortIsReady():
    _reset()
    port = TagPort({"kaleidoscope_cookery:iron_kitchen_knife": ["arris:knife", "kaleidoscope_cookery:kitchen_knife"],
                    "mymod:santoku": [Tags.KNIFE], "minecraft:iron_sword": ["minecraft:is_sword"]}, ready=False)
    ItemTags.setPort("client", port)
    assert Knives.isKnife("kaleidoscope_cookery:iron_kitchen_knife"), "物品 JSON 里挂了 arris:knife（linkage.md 的写法）"
    assert Knives.isKnife("mymod:santoku"), "netease_tags 登记进 common:knife"
    assert not Knives.isKnife("minecraft:iron_sword")
    port.isReady = True
    assert Knives.isKnife("mymod:santoku") and not Knives.isKnife("minecraft:iron_sword")
    _reset()


def testTheStoveStationOpensForATaggedKnife():
    _reset()
    assert not Grill.opens("mymod:santoku", "sword", False), "没人说它是刀：剑类的东西不开"
    ItemTags.setPort("server", TagPort({"mymod:santoku": [Tags.KNIFE]}))
    assert Grill.opens("mymod:santoku", "sword", False), "只挂了 common:knife 的刀也开炉灶站点（原来只看 knifeList）"
    assert Grill.opens("arris:iron_knife", "sword", False) and not Grill.opens("mymod:santoku", "sword", True), "盖着锅照旧不开"
    _reset()


def testTheServerHelperIsThisRule():
    _reset()
    import fakeengine
    fakeengine.install()
    Items = fdtest.load("Server.Helpers.Items")
    ItemTags.setPort("server", TagPort({"mymod:santoku": [Tags.KNIFE]}))
    assert Items.IsKnife("mymod:santoku") and Items.IsKnife("arris:flint_knife") and not Items.IsKnife("minecraft:iron_sword")
    assert fdtest.load("Api.LegacyModAttr").ArrisFarmersDelightObtain("knifeList") is Cutting.knifeList, "契约交出去的还是那个列表"
    _reset()


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
