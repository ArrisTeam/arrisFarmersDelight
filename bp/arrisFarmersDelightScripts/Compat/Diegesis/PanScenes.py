# -*- coding: utf-8 -*-
"""PanScenes - 本客户端全部煎锅场景的登记与调度：方块实体加载 / 卸载、服务端广播、每帧推进（客户端）

装了场景交互前置才启用（ClientBoot 调 enable）；没装时煎锅照旧是农夫乐事原样（食物由 Client/BlockItems 摆），这里的监听什么都不做。
- 方块实体在本端加载：建场景，按方块实体数据里存的（cookingDict、heatEnable、panFrying）先摆出来；重复加载（区块重载）当作重建；
- 服务端 Server/PanLook.py 广播给 32 格内的人：OnPanLook(payload)，带 event 的是一次性的表现（放进来、被拒、颠、取走、煎好）；
- 每个渲染帧：近的每帧算，远的隔几帧算一次、不放粒子声音，太远的不算。
场景接管锅里食物的画法：Client/BlockItems 那份对煎锅不再画（hide）；场景没了、方块还在时还原。
"""
import time

from .PanScene import PanScene
from ...Client import BlockItems
from ...Client.Engine import compFactory, levelId, playerId, unwrapDeep, blockEntityExData
from ...QuModLibs.Client import AllowCall, Listen
from ...Shared.Rules import PanLookState, PanModelMath

SKILLET_BLOCK = "arris:skillet"
NEAR, FAR = 24.0, 48.0          # 格：近处每帧、带粒子声音；到 FAR 为止隔帧算；再远不算
FAR_EVERY = 4
MAX_FRAME = 0.1
_state = {"on": False, "last": None, "tick": 0}
_scenes = {}                    # (维度, 坐标) -> PanScene


def enable():
    """前置包在场：从现在起煎锅按 HoD 的样子画。"""
    _state["on"] = True


def enabled():
    return _state["on"]


def sceneAt(dimensionId, pos):
    return _scenes.get((dimensionId, (int(pos[0]), int(pos[1]), int(pos[2]))))


def _currentDimension():
    return compFactory.CreateGame(levelId).GetCurrentDimension()


def ensure(dimensionId, pos):
    """这个位置的煎锅场景，没有就建（那里不是煎锅返回 None）。"""
    key = (dimensionId, (int(pos[0]), int(pos[1]), int(pos[2])))
    scene = _scenes.get(key)
    if scene is None:
        block = compFactory.CreateBlockInfo(levelId).GetBlock(key[1])
        if not block or block[0] != SKILLET_BLOCK:
            return None
        scene = _scenes[key] = PanScene(dimensionId, key[1], PanModelMath.facingOf(block[1]))
        BlockItems.hide(dimensionId, key[1], True)       # 锅里的东西从此由场景画
    return scene


def _drop(key, blockGone):
    scene = _scenes.pop(key, None)
    if scene is not None:
        scene.destroy(blockGone)
        if not blockGone:
            BlockItems.hide(key[0], key[1], False)


@Listen("ModBlockEntityLoadedClientEvent")
def OnBlockEntityLoaded(args):
    if not _state["on"] or args["blockName"] != SKILLET_BLOCK:
        return
    pos = (args["posX"], args["posY"], args["posZ"])
    known = sceneAt(args["dimensionId"], pos)
    scene = known or ensure(args["dimensionId"], pos)
    if scene is None:
        return
    if known is not None:
        scene.rebuilt()
    exData = blockEntityExData(pos)
    saved = dict((key, unwrapDeep(exData.get(key))) for key in ("cookingDict", "heatEnable", PanLookState.DEFAULT_PAN_KEY))
    scene.applyLook(PanLookState.fromBlockData(saved))


@Listen("ModBlockEntityRemoveClientEvent")
def OnBlockEntityRemoved(args):
    _drop((args["dimensionId"], (args["posX"], args["posY"], args["posZ"])), True)


@Listen("DimensionChangeClientEvent")
def OnDimensionChange(args=None):
    for key in list(_scenes):
        _drop(key, True)


@AllowCall
def OnPanLook(payload):
    # 服务端发给 32 格内的人；别的维度的、不是煎锅的直接丢
    if not _state["on"] or not isinstance(payload, dict) or payload.get("dimensionId") != _currentDimension():
        return
    pos = payload.get("pos")
    if not isinstance(pos, (list, tuple)) or len(pos) != 3:
        return
    scene = ensure(payload["dimensionId"], pos)
    if scene is None:
        return
    if payload.get("event"):
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
        if scene.show.focused or distance <= NEAR * NEAR:
            scene.frame(dt, True)
        elif distance <= FAR * FAR and slow:
            scene.frame(dt * FAR_EVERY, False)
