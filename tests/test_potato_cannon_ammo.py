# -*- coding: utf-8 -*-
# runner: both
"""机械动力的土豆加农炮认农夫乐事的七种弹药（Compat/Create/PotatoCannonAmmo.py）对照 JE 农夫乐事的
data/farmersdelight/create/potato_projectile/type/*.json；登记走机械动力门面的 potatoCannon.registerAmmoType（它的 EXTENSION-API §15.52）。
"""
from __future__ import print_function

import io
import json
import os

import fdtest

Ammo = fdtest.load("Compat.Create.PotatoCannonAmmo")

JE_DIR = os.path.join(fdtest.ROOT, ".refs", "FarmersDelight", "src", "main", "resources", "data", "farmersdelight", "create",
                      "potato_projectile", "type")
# JE 的物品 / 方块名 -> 本包的（派的整块物品叫 *_item，洋葱作物是 onions_stage0）
JE_NAMES = {"farmersdelight:cabbage": "arris:cabbage", "farmersdelight:apple_pie": "arris:apple_pie_item",
            "farmersdelight:sweet_berry_cheesecake": "arris:sweet_berry_cheesecake_item",
            "farmersdelight:chocolate_pie": "arris:chocolate_pie_item", "farmersdelight:cake_slice": "arris:cake_slice",
            "farmersdelight:apple_pie_slice": "arris:apple_pie_slice",
            "farmersdelight:sweet_berry_cheesecake_slice": "arris:sweet_berry_cheesecake_slice",
            "farmersdelight:chocolate_pie_slice": "arris:chocolate_pie_slice", "farmersdelight:onion": "arris:onion",
            "farmersdelight:onions": "arris:onions_stage0", "farmersdelight:pumpkin_slice": "arris:pumpkin_slice",
            "farmersdelight:rotten_tomato": "arris:rotten_tomato", "farmersdelight:tomato": "arris:tomato"}


def _ours(fields):
    out = dict(fields)
    out["items"] = [JE_NAMES[name] for name in fields["items"]]
    if "on_block_hit" in fields:
        out["on_block_hit"] = dict(fields["on_block_hit"], block=JE_NAMES[fields["on_block_hit"]["block"]])
    return out


def testTheSevenTypesAreJavasOwn():
    types = dict(Ammo.ammoTypes())
    assert len(types) == 7
    if not os.path.isdir(JE_DIR):
        print("跳过和 JE 的比对：没有 .refs/FarmersDelight")
        return
    for name in sorted(os.listdir(JE_DIR)):
        with io.open(os.path.join(JE_DIR, name), encoding="utf-8") as handle:
            je = json.load(handle)
        assert types.pop("arris:" + name[:-len(".json")]) == _ours(je), name
    assert types == {}


def testEveryItemAndBlockExists():
    known = set()
    for sub, key in (("netease_items_beh", "minecraft:item"), ("netease_blocks", "minecraft:block")):
        for root, _dirs, files in os.walk(os.path.join(fdtest.BP, sub)):
            for name in files:
                if name.endswith(".json"):
                    with io.open(os.path.join(root, name), encoding="utf-8") as handle:
                        known.add(json.load(handle)[key]["description"]["identifier"])
    for typeId, fields in Ammo.ammoTypes():
        for item in fields["items"]:
            assert item in known, (typeId, item)
        if "on_block_hit" in fields:
            assert fields["on_block_hit"]["block"] in known, typeId


class _Cannon(object):
    def __init__(self):
        self.calls = []

    def registerAmmoType(self, typeId, fields):
        self.calls.append((typeId, fields))
        fields["damage"] = -1                                  # 门面改了它拿到的字典也碰不到本包的表
        return {"ok": True, "error": None}


class _Facade(object):
    def __init__(self, capable=True):
        self.capable = capable
        self.potatoCannon = _Cannon()

    def hasCapability(self, name):
        return self.capable and name == "potato_cannon_ammo"


def testRegistersOnlyWhenTheFacadeHasTheCapability():
    facade = _Facade()
    assert Ammo.register(facade) == 7 and [typeId for typeId, _ in facade.potatoCannon.calls][0] == "arris:cabbage"
    assert dict(Ammo.ammoTypes())["arris:cabbage"]["damage"] == 7
    old = _Facade(capable=False)
    assert Ammo.register(old) is None and old.potatoCannon.calls == []
    assert Ammo.register(None) is None


class _System(object):
    def __init__(self):
        self.listened = []

    def ListenForEvent(self, namespace, system, event, target, method):
        self.listened.append((namespace, system, event, method))


class _Api(object):
    def __init__(self, facade=None):
        self.facade = facade

    def GetSystem(self, namespace, name):
        return object() if self.facade is not None else None

    def ImportModule(self, path):
        facade = self.facade

        class Module(object):
            @staticmethod
            def getExtensionApi(side):
                return facade
        return Module if path == Ammo.FACADE_MODULE else None


def testHookListensOnceAndAttachesWhenCreateIsReadyOrAlreadyFrozen():
    Ammo._attached.clear()
    system = _System()
    assert Ammo.hook("server", system, _Api()) is False                # 没装机械动力：只挂监听
    assert Ammo.hook("server", system, _Api()) is False
    assert [(ns, name, event) for ns, name, event, _m in system.listened] == [("arrisCreate", "ExtensionApi", "ServerExtensionApiReady")]
    facade = _Facade()
    system.listened[0][3]({"extension": facade, "side": "server", "apiVersion": 3})   # ready 事件
    assert len(facade.potatoCannon.calls) == 7
    system.listened[0][3]({"extension": facade})                                         # 接过了不再接
    assert len(facade.potatoCannon.calls) == 7
    late = _Facade()                                                                     # 客户端：机械动力已经广播过
    assert Ammo.hook("client", _System(), _Api(late)) is True and len(late.potatoCannon.calls) == 7


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
