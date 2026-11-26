# -*- coding: utf-8 -*-
# runner: both
"""Builder 认机械动力的写法（Api/ExtensionApi/RecipeBuilder.py）。

- 关键字照机械动力：ingredient("ns:name", data=aux)、ingredient(..., count=2)（厨锅一格一件：两格同样的）、ingredientTag(标签, count)，
  写出来的 JSON 和我们原来的写法一模一样；output(物品, count, data, chance) 的位置次序和机械动力一样；container(物品, data)。
- 写错了不抛：不认识的关键字、把数量当成位置参数、data 用在标签或几个选项上、count 不是正整数，都在 register() 时答 invalid_recipe，
  message 说哪里不对；客户端照旧先答 server_only。这里只看 toJson 和失败的回答，不往表里登记。
"""
from __future__ import print_function

import fdtest

Facade = fdtest.load("Api.ExtensionApi.Facade")
RecipeJson = fdtest.load("Shared.Rules.RecipeJson")
SERVER, CLIENT = Facade.getExtensionApi("server").recipes, Facade.getExtensionApi("client").recipes


def _cooking(recipes=SERVER):
    return recipes.createBuilder("mymod:cooking/potion_soup", "cooking")


def testCreateStyleKeywordsWriteTheSameJson():
    ours = _cooking().ingredient(("minecraft:potion", 4)).ingredient("#common:tomato").ingredient("#common:tomato") \
        .ingredient("minecraft:carrot").ingredient("minecraft:carrot").output("mymod:potion_soup", 2).container("minecraft:bowl")
    create = _cooking().ingredient("minecraft:potion", data=4).ingredientTag("common:tomato", count=2) \
        .ingredient("minecraft:carrot", count=2).output("mymod:potion_soup", 2, 0).container("minecraft:bowl", data=0)
    assert create.toJson() == ours.toJson(), (create.toJson(), ours.toJson())
    assert _cooking().ingredientTag("#common:tomato").toJson()["ingredients"] == [{"tag": "common:tomato"}], "标签名带不带 # 都行"
    spec, problem = RecipeJson.parse(create.toJson())
    assert problem is None and spec["slots"] == [[("minecraft:potion", 4)], ["#common:tomato"], ["#common:tomato"],
                                                 [("minecraft:carrot", 0)], [("minecraft:carrot", 0)]], spec
    assert _cooking().ingredient("a:b", "a:c").toJson()["ingredients"] == [[{"item": "a:b"}, {"item": "a:c"}]], "一次调用一格：几个参数是几个选项"


def testOutputAndContainerTakeCreatesPositionalOrder():
    cut = SERVER.createBuilder("mymod:cutting/tofu", "cutting").ingredient("mymod:tofu").output("mymod:tofu_cube", 4) \
        .output("minecraft:bone_meal", 1, 0, 0.5).output("minecraft:dye", 1, 4).tool("knife")
    assert cut.toJson()["result"] == [{"item": "mymod:tofu_cube", "count": 4}, {"item": "minecraft:bone_meal", "chance": 0.5},
                                      {"item": "minecraft:dye", "data": 4}], "(物品, count, data, chance)"
    assert _cooking().container("minecraft:potion", data=4).toJson()["container"] == {"item": "minecraft:potion", "data": 4}
    assert _cooking().output(("mymod:soup", 3)).toJson()["result"] == {"item": "mymod:soup", "data": 3}, "元组照旧认"


def testWrongSpellingsAreAnsweredNotRaised():
    cases = ((lambda builder: builder.ingredient("minecraft:carrot", 2), "count="),
             (lambda builder: builder.ingredient("minecraft:carrot", amount=2), "amount"),
             (lambda builder: builder.ingredient("#common:tomato", data=1), "data="),
             (lambda builder: builder.ingredient("a:b", "a:c", data=1), "data="),
             (lambda builder: builder.ingredient("a:b", count=0), "count"),
             (lambda builder: builder.ingredient("a:b", count=True), "count"),
             (lambda builder: builder.ingredientTag(3), "标签名"),
             (lambda builder: builder.output(("mymod:x", 1), data=2), "data="),
             (lambda builder: builder.container(("minecraft:bowl", 0), data=2), "data="))
    for write, word in cases:
        builder = _cooking().ingredient("minecraft:apple").output("mymod:potion_soup")
        assert write(builder) is builder, "写错了也照样接着链"
        answer = builder.register()
        assert answer["ok"] is False and answer["error"] == "invalid_recipe" and word in answer["message"], (word, answer)
    two = SERVER.createBuilder("mymod:cutting/two", "cutting").ingredient("a:b", count=2).output("a:c").tool("knife").register()
    assert two["error"] == "invalid_recipe" and "正好一个" in two["message"], "砧板只有一格一件"
    client = _cooking(CLIENT).ingredient("a:b", count=0).output("mymod:x").register()
    assert client == {"ok": False, "error": "server_only", "id": "mymod:cooking/potion_soup"}, "客户端照旧先答 server_only"
    assert _cooking().ingredient("a:b", count=0).output("mymod:x").register()["id"] == "mymod:cooking/potion_soup"
    bad = SERVER.createBuilder("bad id", "cooking").ingredient("a:b", count=0).output("mymod:x").register()
    assert bad["error"] == "invalid_id", "ID 写法不对先说 ID"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
