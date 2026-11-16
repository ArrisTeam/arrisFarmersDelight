# -*- coding: utf-8 -*-
# runner: both
"""烧着的厨锅的沸腾声归谁放（rp/entity/cooking_pot.json 的 boil / boil_water、rp/sounds 的定义、PotModel.food、场景的 boil）：
JE 的 CookingPotBlockMixin 只在场景显示着、锅里有东西时才取消农夫乐事自己的声音，空锅烧着照响；场景自己的沸腾声只放"汤"那几条，不混水沸声。"""
from __future__ import print_function

import io
import json
import os
import re

import fdtest
import potclient as C

world = C.world
Scenes = C.load("Compat.Diegesis.PotScenes")
SceneFx = C.load("Compat.Diegesis.PotSceneFx")
BrothColors = C.load("Shared.Data.BrothColors")
POS = C.POS
DT = 1.0 / 60.0
RP = os.path.join(fdtest.ROOT, "rp")


def _json(*path):
    with io.open(os.path.join(RP, *path), encoding="utf-8-sig") as handle:
        return json.load(handle)


ENTITY = _json("entity", "cooking_pot.json")["minecraft:client_entity"]["description"]
DEFINITIONS = _json("sounds", "sound_definitions.json")["sound_definitions"]
ANIMATIONS = _json("animations", "cooking_pot.animation.json")["animations"]


def _files(name):
    return sorted(sound["name"] for sound in DEFINITIONS[name]["sounds"])


def _gate(animation):
    for entry in ENTITY["scripts"]["animate"]:
        if isinstance(entry, dict) and animation in entry:
            return entry[animation]
    return None


def testTheSoupAndTheWaterBoilHaveTheirOwnDefinitionsAndTheOldOneIsBoth():
    soup = ["sounds/cooking_pot/boil_soup%d" % index for index in (1, 2, 3)]
    water = ["sounds/cooking_pot/boil_water%d" % index for index in (1, 2)]
    assert _files("ambient.cooking_pot.boil_soup") == soup
    assert _files("ambient.cooking_pot.boil_water") == water
    assert _files("ambient.cooking_pot.boil") == sorted(soup + water), "模型自带的那条（不知道锅里有没有菜）还是两种混着"
    for name in soup + water:
        assert os.path.isfile(os.path.join(RP, name + ".ogg")), name
    volumes = set(sound["volume"] for key in ("boil", "boil_soup", "boil_water") for sound in DEFINITIONS["ambient.cooking_pot." + key]["sounds"])
    assert volumes == set([20]), "和原有的一样自带 20 倍，场景那边除回去"


def testTheModelKeepsItsWaterBoilWhenTheSceneShowsAnEmptyHeatedPot():
    assert "variable.mod_food = 0.0;" in ENTITY["scripts"]["initialize"]
    assert _gate("boil") == "variable.mod_heat == 1.0 && variable.mod_open < 0.5", "没有场景（离得远）：和原来一样"
    water = _gate("boil_water")
    assert "variable.mod_heat == 1.0" in water and "variable.mod_open >= 0.5" in water and "variable.mod_food < 0.5" in water, water
    assert ENTITY["animations"]["boil_water"] == "animation.cooking_pot.boil_water"
    assert ENTITY["sound_effects"]["boil_water"] == "ambient.cooking_pot.boil_water"
    effects = ANIMATIONS["animation.cooking_pot.boil_water"]["sound_effects"]
    assert [entry["effect"] for entry in effects.values()] == ["boil_water"]
    assert ANIMATIONS["animation.cooking_pot.boil_water"]["animation_length"] == ANIMATIONS["animation.cooking_pot.boil"]["animation_length"]


def testTheScenesOwnBoilIsTheSoupOnlyDefinition():
    assert SceneFx.SOUNDS["boil"][0] == "ambient.cooking_pot.boil_soup"
    assert SceneFx.SOUNDS["boil"][0] in DEFINITIONS


def setup():
    C.reset()
    Scenes._scenes.clear()
    Scenes.enable(BrothColors.BrothColors.get)
    return Scenes.ensure(0, POS)


def run(scene, seconds):
    for _ in range(int(round(seconds / DT))):
        scene.frame(DT, True)


def food():
    return world.molang[(POS, "variable.mod_food")]


def testTheSceneTellsTheModelWhetherThereIsAnythingInThePot():
    scene = setup()
    scene.apply(C.look([], heated=True))
    run(scene, 0.3)
    assert food() == 0.0 and world.molang[(POS, "variable.mod_open")] == 1.0, "场景接管了盖子，空锅：模型自带的水沸声接着响"
    scene.apply(C.look([("minecraft:carrot", 1)], heated=True))
    run(scene, 0.3)
    assert food() == 1.0
    scene.apply(C.look([], heated=True, meal={"newItemName": "arris:tomato_sauce", "count": 2}))
    run(scene, 0.3)
    assert food() == 1.0, "煮好还没装的菜也算有东西"
    scene.apply(C.look([], heated=True, served={"newItemName": "arris:tomato_sauce", "count": 2}))
    run(scene, 0.3)
    assert food() == 0.0, "产出格里装好的不算（PotLogic.hasFood 只数食材格和煮好的那一格）"


def testTheScenePlaysTheSoupBoilOnlyWhenThereIsFoodAndNeverTheMixedOne():
    scene = setup()
    scene.apply(C.look([], heated=True))
    run(scene, 12.0)
    assert not [sound for sound in world.sounds if sound["name"].startswith("ambient.cooking_pot")], "空锅：场景不放，留给模型自带的"
    scene.apply(C.look([("minecraft:carrot", 1)], heated=True))
    run(scene, 12.0)
    names = set(sound["name"] for sound in world.sounds if sound["name"].startswith("ambient.cooking_pot"))
    assert names == set(["ambient.cooking_pot.boil_soup"]), names


def testEveryVariableTheSceneSetsOnTheModelIsInitialisedInTheEntity():
    # 方块实体重建之后变量回到初始值：场景推过的每个 mod_ 变量都要在 initialize 里有，不然读到的是未定义
    scene = setup()
    scene.apply(C.look([("minecraft:carrot", 1)], heated=True))
    run(scene, 0.5)
    pushed = set(name for (_pos, name) in world.molang)
    initialised = set(re.findall(r"variable\.\w+", " ".join(ENTITY["scripts"]["initialize"])))
    assert pushed and "variable.mod_food" in pushed
    assert not (pushed - initialised), sorted(pushed - initialised)


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
