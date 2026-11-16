# -*- coding: utf-8 -*-
# runner: py3
"""服务端事件的接线：玩法模块 registerHandler 的每个引擎事件，ModServer.py 里都要有对应的 @Listen（否则处理函数永远不会被叫到）；
需要方块组件才触发的事件（站在方块上、实体在方块里、落到方块上），方块 JSON 里要带那个组件。
"""
from __future__ import print_function

import glob
import io
import json
import os
import re

import fdtest

SCRIPTS = os.path.join(fdtest.BP, fdtest.SCRIPTS)
BLOCKS = os.path.join(fdtest.BP, "netease_blocks")


def _read(*path):
    with io.open(os.path.join(*path), encoding="utf-8-sig") as f:
        return f.read()


def _components(identifier):
    name = "arris_" + identifier.split(":")[1] + ".json"
    return json.loads(_read(BLOCKS, name))["minecraft:block"]["components"]


def testEveryRegisteredEventHasAListenInModServer():
    listened = set(re.findall(r'@Listen\("(\w+)"\)', _read(SCRIPTS, "Server", "ModServer.py")))
    registered = {}
    for path in glob.glob(os.path.join(SCRIPTS, "Server", "*.py")) + glob.glob(os.path.join(SCRIPTS, "Compat", "*", "*.py")):
        for event in re.findall(r'registerHandler\(\s*"(\w+)"', _read(path)):
            registered.setdefault(event, []).append(os.path.basename(path))
    missing = dict((event, files) for event, files in registered.items() if event not in listened)
    assert not missing, "这些事件有处理函数却没人 @Listen：%s" % missing


def testTriggerComponentsAreOnTheBlocksThatNeedThem():
    # 站在点燃的炉灶上被烫：OnStandOnBlockServerEvent <- netease:on_stand_on；熄灭的炉灶是另一个方块，不带
    assert _components("arris:stove")["netease:on_stand_on"] == {"send_python_event": True}
    assert "netease:on_stand_on" not in _components("arris:stove_extinguish")
    # 篮子吸掉落物：OnEntityInsideBlockServerEvent <- netease:on_entity_inside（竹篮、木篮都要）
    for basket in ("arris:basket", "arris:wooden_basket"):
        assert _components(basket)["netease:on_entity_inside"] == {"send_python_event": True}, basket
    # 安全网：OnBeforeFallOnBlockServerEvent <- netease:on_before_fall_on
    assert _components("arris:safety_net")["netease:on_before_fall_on"] == {"send_python_event": True}


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
