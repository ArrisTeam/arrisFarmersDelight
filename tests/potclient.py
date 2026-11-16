# -*- coding: utf-8 -*-
"""potclient - 厨锅客户端模块（Compat/Diegesis 的 PotScene / PotScenes / PotHands / PotModel / PotFx / PotSceneFx）离线测试的假引擎
（不是测试本身，跑器只收 test_*.py）

假引擎沿用煎锅那份（panclient：掉落物、方块实体 molang、粒子、声音只记录调用，没预设的接口报 AttributeError），再补厨锅模型多用的
SetBlockEntityExtraUniforms（着色器的几组数）。测试塞广播、跑渲染帧，然后看：摆了哪些客户端掉落物、molang 变量和 uniform 被推成了什么、
放了哪些粒子和声音。
"""
from __future__ import print_function

import panclient as C

world = C.install()
POS = C.POS


def _extraUniforms(self, pos, index, values):
    world.uniforms[(tuple(pos), index)] = tuple(values)
    return True


C.Comp.SetBlockEntityExtraUniforms = _extraUniforms


def reset():
    """每个用例开头：世界清空，方块是一口厨锅。"""
    world.reset()
    world.uniforms = {}
    world.blocks[POS] = ("arris:cooking_pot", 0)


def load(dotted):
    return C.load(dotted)


def item(name, count=1, aux=0):
    return {"newItemName": name, "newAuxValue": aux, "count": count}


def look(items=(), **changes):
    """服务端广播的载荷（Server/PotLook.build 的样子）：items 是至多 6 件料（空位给 None）。"""
    cells = [item(*entry) if isinstance(entry, tuple) else (entry or {}) for entry in list(items)[:6]]
    cells += [{}] * (6 - len(cells))
    payload = {"dimensionId": 0, "pos": list(POS), "items": cells, "served": {}, "meal": {}, "dish": {}, "sunk": [], "heated": False,
               "stirring": False, "spoon": [0.0, 0.0], "progress": 0.0, "rate": 0.0, "cooking": False}
    payload.update(changes)
    return payload
