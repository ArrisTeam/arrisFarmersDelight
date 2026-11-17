# -*- coding: utf-8 -*-
"""PotScenes - 本客户端全部厨锅场景的登记与调度：方块实体加载 / 卸载、服务端广播、每帧推进（客户端）

装了场景交互前置才启用（PotClientLink 这一步导入本模块、调 enable）；没装时本模块不会被导入，厨锅照旧是合着盖的农夫乐事原样。
- 方块实体在本端加载：建场景（顺带问一次所在位置的群系水色，PotBiome），按方块实体数据里存的静态部分（potLook）先摆出来；重复加载（区块重载）当作重建；
- 服务端 Server/PotLook.py 广播给 32 格内的人：OnPotLook(payload)，带 event 的是一次性的表现（盛出、出锅）；
- 每个渲染帧：近的每帧算，远的隔几帧算一次、不放粒子和声音，太远的不算。
"""
import time

from . import PotBiome, PotFx
from .PotScene import PotScene
from ...Client.Engine import compFactory, levelId, playerId, unwrapDeep, blockEntityExData
from ...QuModLibs.Client import AllowCall, Listen
from ...Shared.Rules import CookingPot as CookingPotRules
from ...Shared.Rules import PotModelMath

POT_BLOCK = "arris:cooking_pot"
LOOK_KEY = "potLook"
NEAR, FAR = 32.0, 40.0          # 格：NEAR 以内每帧、带粒子声音（Diegesis 的 WATCH_RANGE：服务端的状态和效果只发到这么远）；到 FAR 为止隔帧算、只画（SceneRenderer.RENDER_RANGE）；再远不算
FAR_EVERY = 4
MAX_FRAME = 0.1
_state = {"on": False, "last": None, "tick": 0, "brothOf": None, "listeners": []}
_scenes = {}                    # (维度, 坐标) -> PotScene


def enable(brothOf=None):
    """前置包在场：从现在起厨锅按 HoD 的样子画。brothOf(菜名) -> 汤色，没有表就不给。"""
    _state["on"] = True
    _state["brothOf"] = brothOf


def enabled():
    return _state["on"]


def sceneAt(dimensionId, pos):
    return _scenes.get((dimensionId, (int(pos[0]), int(pos[1]), int(pos[2]))))


def onEvent(listener):
    """登记一次性表现的听众：listener(scene, name, payload)（开着站点的 PotView 用）。返回取消登记的函数。"""
    _state["listeners"].append(listener)
    return lambda: listener in _state["listeners"] and _state["listeners"].remove(listener)


def opensStation(pos, dimensionId):
    """这一下右键开不开站点。JE：手里拿着盛这锅菜的容器、锅里有煮好的菜时不开，照农夫乐事原样直接盛一份。"""
    scene = sceneAt(dimensionId, pos)
    meal = scene.look.meal if scene is not None and scene.look is not None else None
    if not meal:
        return True
    recipe = CookingPotRules.findRecipeByResult(meal["newItemName"])
    vessel = recipe.get("Vessel") if recipe else None
    held = compFactory.CreateItem(playerId).GetCarriedItem()
    return not (vessel and held and held.get("newItemName") == vessel[0])


def _currentDimension():
    return compFactory.CreateGame(levelId).GetCurrentDimension()


def ensure(dimensionId, pos):
    """这个位置的厨锅场景，没有就建（那里不是厨锅返回 None）。"""
    key = (dimensionId, (int(pos[0]), int(pos[1]), int(pos[2])))
    scene = _scenes.get(key)
    if scene is None:
        block = compFactory.CreateBlockInfo(levelId).GetBlock(key[1])
        if not block or block[0] != POT_BLOCK:
            return None
        scene = _scenes[key] = PotScene(dimensionId, key[1], PotModelMath.facingOf(block[1]))
        scene.brothOf = _state["brothOf"]
        PotBiome.bind(scene)                  # 清水取所在群系的水色（JE 的 getAverageWaterColor）：建场景时问一次，谁看都对
    return scene


def _drop(key, blockGone):
    scene = _scenes.pop(key, None)
    if scene is not None:
        scene.destroy(blockGone)


@Listen("ModBlockEntityLoadedClientEvent")
def OnBlockEntityLoaded(args):
    if not _state["on"] or args["blockName"] != POT_BLOCK:
        return
    pos = (args["posX"], args["posY"], args["posZ"])
    known = sceneAt(args["dimensionId"], pos)
    scene = known or ensure(args["dimensionId"], pos)
    if scene is None:
        return
    if known is not None:
        scene.rebuilt()
    saved = unwrapDeep(blockEntityExData(pos).get(LOOK_KEY))
    scene.apply(saved if isinstance(saved, dict) else {})


@Listen("ModBlockEntityRemoveClientEvent")
def OnBlockEntityRemoved(args):
    _drop((args["dimensionId"], (args["posX"], args["posY"], args["posZ"])), True)


@Listen("DimensionChangeClientEvent")
def OnDimensionChange(args=None):
    for key in list(_scenes):
        _drop(key, True)


@AllowCall
def OnPotLook(payload):
    # 服务端发给 32 格内的人；别的维度的、不是厨锅的直接丢
    if not _state["on"] or not isinstance(payload, dict) or payload.get("dimensionId") != _currentDimension():
        return
    pos = payload.get("pos")
    if not isinstance(pos, (list, tuple)) or len(pos) != 3:
        return
    scene = ensure(payload["dimensionId"], pos)
    if scene is None:
        return
    if payload.get("event"):
        for listener in list(_state["listeners"]):
            listener(scene, str(payload["event"]), payload)
        scene.event(str(payload["event"]), payload)
    else:
        scene.apply(payload)


@Listen("GameRenderTickEvent")
def OnRenderTick(args=None):
    if not _state["on"]:
        return
    now = time.time()
    dt = 0.0 if _state["last"] is None else min(MAX_FRAME, max(0.0, now - _state["last"]))
    _state["last"] = now
    PotFx.step(dt)
    if not _scenes:
        return
    _state["tick"] += 1
    eye = compFactory.CreatePos(playerId).GetFootPos()
    if not eye:
        return
    slow = _state["tick"] % FAR_EVERY == 0
    for (_, pos), scene in list(_scenes.items()):
        dx, dy, dz = pos[0] + 0.5 - eye[0], pos[1] + 0.5 - eye[1], pos[2] + 0.5 - eye[2]
        distance = dx * dx + dy * dy + dz * dz
        if scene.hand or distance <= NEAR * NEAR:
            scene.frame(dt, True)
        elif distance <= FAR * FAR and slow:
            scene.frame(dt * FAR_EVERY, False)
