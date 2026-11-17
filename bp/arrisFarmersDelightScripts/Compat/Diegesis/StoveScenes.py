# -*- coding: utf-8 -*-
"""StoveScenes - 本客户端全部炉灶场景的登记与调度：方块实体加载 / 卸载、服务端广播、每帧推进（客户端）

装了场景交互前置才启用（ClientBoot 调 enable）；没装时炉灶照旧是农夫乐事原样（食物由 Client/BlockItems 摆），这里的监听什么都不做。
- 方块实体在本端加载：建场景，按方块实体数据里存的（六个烤位 "0".."5"、手放的进度 handGrill）先摆出来；重复加载（区块重载）当作重建；
- 服务端 Server/StoveLook.py 广播给 32 格内的人：OnStoveLook(payload)，带 event 的是一次性的表现（放上、被拒、翻、没翻成、取走、烤好）；
- 每个渲染帧：近的每帧算、放粒子声音，远的隔几帧算一次、不放粒子声音，太远的不算；每隔一会儿核对一下方块还在不在（炉灶被灭掉 / 拆了没收到移除事件时）。
场景接管烤架上食物的画法：Client/BlockItems 那份对炉灶不再画（hide），但要等场景真画出样子的那一帧（StoveScene.onDrawn）——场景刚建出来的时候
（被拒的虚影、开站点这类先到）还不知道烤架上有什么，这时把原来的展示收掉，烤架上就什么都没有了；场景没了、方块还在时还原。
"""
import time

from .StoveScene import StoveScene
from ...Client import BlockItems
from ...Client.Engine import compFactory, levelId, playerId, unwrapDeep, blockEntityExData
from ...QuModLibs.Client import AllowCall, Listen
from ...Shared.Rules import GrillBlocks, StoveFacing, StoveLookState

NEAR, FAR = 24.0, 48.0          # 格：近处每帧、带粒子声音；到 FAR 为止隔帧算；再远不算（同煎锅）
FAR_EVERY = 4
MAX_FRAME = 0.1
CHECK_SECONDS = 2.0             # 多久核对一次方块还在不在
_state = {"on": False, "last": None, "tick": 0, "check": 0.0}
_scenes = {}                    # (维度, 坐标) -> StoveScene


def enable():
    """前置包在场：从现在起炉灶按 HoD 的样子画。"""
    _state["on"] = True


def enabled():
    return _state["on"]


def _key(dimensionId, pos):
    return (dimensionId, (int(pos[0]), int(pos[1]), int(pos[2])))


def sceneAt(dimensionId, pos):
    return _scenes.get(_key(dimensionId, pos))


def _currentDimension():
    return compFactory.CreateGame(levelId).GetCurrentDimension()


def ensure(dimensionId, pos):
    """这个位置的炉灶场景，没有就建（那里不是炉灶返回 None）；场景记着炉灶的朝向（方块的 aux），件和动作都按它转，
    也记着炉灶点着没有（点着的 arris:stove 还是熄着的孪生方块，Shared/Rules/GrillBlocks：熄着没有热气和嗞嗞声）。"""
    key = _key(dimensionId, pos)
    block = compFactory.CreateBlockInfo(levelId).GetBlock(key[1])
    grill = bool(block) and GrillBlocks.isGrill(block[0])
    scene = _scenes.get(key)
    if scene is None:
        if not grill:
            return None
        scene = _scenes[key] = StoveScene(dimensionId, key[1], StoveFacing.yawOfAux(block[1]))
        scene.onDrawn = lambda: BlockItems.hide(dimensionId, key[1], True)       # 场景画出样子之后，烤架上的东西从此由场景画
    if grill:
        scene.setLit(GrillBlocks.isLit(block[0]))
    return scene


def _drop(key, blockGone):
    scene = _scenes.pop(key, None)
    if scene is not None:
        scene.destroy()
        if blockGone:
            BlockItems.release(key[0], key[1])
        else:
            BlockItems.hide(key[0], key[1], False)


@Listen("ModBlockEntityLoadedClientEvent")
def OnBlockEntityLoaded(args):
    if not _state["on"] or not GrillBlocks.isGrill(args["blockName"]):
        return
    pos = (args["posX"], args["posY"], args["posZ"])
    known = sceneAt(args["dimensionId"], pos)
    scene = known or ensure(args["dimensionId"], pos)
    if scene is None:
        return
    scene.setLit(GrillBlocks.isLit(args["blockName"]))                    # 点火 / 灭火换了方块：以这个事件的方块名为准
    if known is not None:
        block = compFactory.CreateBlockInfo(levelId).GetBlock(pos)
        scene.turn(StoveFacing.yawOfAux(block[1] if block else 0))       # 重建时方块的朝向可能不是建场景时那个
        scene.rebuilt()
    exData = blockEntityExData(pos)
    saved = dict((name, unwrapDeep(exData.get(name))) for name in [str(place) for place in range(StoveLookState.PLACES)] + [StoveLookState.SAVE_KEY])
    scene.applyLook(StoveLookState.fromBlockData(saved))


@Listen("ModBlockEntityRemoveClientEvent")
def OnBlockEntityRemoved(args):
    _drop(_key(args["dimensionId"], (args["posX"], args["posY"], args["posZ"])), True)


@Listen("DimensionChangeClientEvent")
def OnDimensionChange(args=None):
    for key in list(_scenes):
        _drop(key, True)


@AllowCall
def OnStoveLook(payload):
    # 服务端发给 32 格内的人；别的维度的、不是炉灶的直接丢
    if not _state["on"] or not isinstance(payload, dict) or payload.get("dimensionId") != _currentDimension():
        return
    pos = payload.get("pos")
    if not isinstance(pos, (list, tuple)) or len(pos) != 3 or not all(isinstance(value, StoveLookState.INTS) and not isinstance(value, bool) for value in pos):
        return
    scene = ensure(payload["dimensionId"], pos)
    if scene is None:
        return
    if payload.get("event"):
        scene.event(str(payload["event"]), StoveLookState.eventData(payload))
    else:
        scene.apply(payload)


def _stillThere(key):
    """那里还是炉灶（点着的或熄着的）；顺手把点着没有交给场景：点火 / 灭火换方块时没收到移除 / 加载事件，也最多慢一个核对间隔。"""
    block = compFactory.CreateBlockInfo(levelId).GetBlock(key[1])
    if not block or not GrillBlocks.isGrill(block[0]):
        return False
    _scenes[key].setLit(GrillBlocks.isLit(block[0]))
    return True


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
    _state["check"] += dt
    if _state["check"] >= CHECK_SECONDS:
        _state["check"] = 0.0
        for key in [key for key in _scenes if not _scenes[key].focused and not _stillThere(key)]:
            _drop(key, True)
    eye = compFactory.CreatePos(playerId).GetFootPos()
    if not eye:
        return
    slow = _state["tick"] % FAR_EVERY == 0
    for (_, pos), scene in list(_scenes.items()):
        dx, dy, dz = pos[0] + 0.5 - eye[0], pos[1] + 0.5 - eye[1], pos[2] + 0.5 - eye[2]
        distance = dx * dx + dy * dy + dz * dz
        if scene.focused or distance <= NEAR * NEAR:
            scene.frame(dt, True)
        elif distance <= FAR * FAR and slow:
            scene.frame(dt * FAR_EVERY, False)
