# -*- coding: utf-8 -*-
"""PotScene - 一口厨锅在本客户端的场景：汤面、漂着的料、勺子、气泡蒸汽，谁都看得见（客户端）

对应 Hands-On Delight 的 client/PotBehavior.frame：JE 的场景 idle_visible，32 格内每个客户端都按同步来的状态自己算全部动作。
这里每口加载着的厨锅一份（PotScenes.py 管登记和每帧调度）：状态来自服务端广播（Shared/Rules/PotLookState.py），
动作照 HoD 的纯计算（Shared/Rules/HandsOn 的 PotLiquid / PotSpoonMotion / PotDrift），画法是
- 方块实体模型：开盖、液面高度与汤色（自定义着色器）、煮好的汤里浮着的碎料、勺子骨骼（PotModel.py）；
- 漂着的料：客户端掉落物，平躺在液面上绕圈；
- 粒子、声音、一批煮好的收尾：PotSceneFx.py。
全部用"锅自己的坐标"（像素，方块朝北时 +x 东、+z 南，锅心 (8, *, 8)），出手时按方块朝向换到世界。
本人开着这口锅的站点时，PotView 把手交进来：hand / aim（光标在液面上的点）/ onSend（勺尖该报给服务端了）。
"""
import random

from . import PotFx
from .PotModel import PotModel
from .PotSceneFx import SceneFx, play
from ...Client.Engine import compFactory, levelId
from ...Shared.Data.BrothColors import PouredColors
from ...Shared.Data.FoodColors import FoodColors
from ...Shared.Rules import ItemPose, PotLookState, PotModelMath, PotPiecesLook
from ...Shared.Rules.HandsOn import PotDrift, PotDriftExtras, PotLiquid, PotPiecesKinds, PotPiecesPiece, PotSpoonMotion

SLOTS = PotLookState.SLOTS
ITEM_SCALE = 3.2 / ItemPose.ITEM_SPAN       # JE 的料是 3.2 像素见方
INNER_LO, INNER_SPAN = 4.0, 8.0             # 内胆 x、z 从 4 到 12
CHECK_SECONDS = 0.5                         # 多久核对一次模型上的值还在不在（方块实体重建会清掉）
AWAKE_SECONDS = 4.0                         # 没动静之后再跑这么久就歇着（等水位、勺子、颜色都落定）
WATER = PotLiquid.waterColor()


def _colorOf(item):
    return FoodColors.get(item["newItemName"], PotLiquid.FALLBACK)


class PotScene(object):
    def __init__(self, dimensionId, pos, facing):
        self.dimensionId = dimensionId
        self.pos = (int(pos[0]), int(pos[1]), int(pos[2]))
        self.facing = facing
        self.model = PotModel(self.pos, facing)
        self.liquid = PotLiquid.PotLiquid()
        self.spoon = PotSpoonMotion.PotSpoonMotion()
        self.drift = PotDrift.PotDrift()
        self.fx = SceneFx(self)
        self.look = None
        self.key = None
        self.clock = 0.0
        self.awake = 0.0
        self.sinceCheck = 0.0
        self.progress = -1.0
        self.props = [None] * (SLOTS + 1)     # [掉落物 id, (物品名, aux)]：六格料，最后一个是产出格里装好的菜（浮在锅心）
        self.hand = False
        self.aim = None
        self.onSend = None
        self.startsOf = None                  # startsOf(件数) -> 一次放进好几件时各从哪飞进来（PotView 按屏幕底边算）
        self.brothOf = None                   # 菜名 -> 汤色 0xRRGGBB（PotScenes 装上）
        self.pieces = PotPiecesLook.PiecesClock()
        self.piecesShown = 0                  # 上回要浮几块：多出来的每块咕噜一声（PotBehavior.pieces）

    # ---------------------------------------------------------------- 状态

    def apply(self, payload):
        """服务端广播（或方块实体数据里存的静态部分）来了。"""
        old = self.look
        look = self.look = PotLookState.decode(payload, self.clock, old)
        self.awake = AWAKE_SECONDS
        key = look.staticKey()
        if key == self.key:
            return
        self.key = key
        emptied = PotLookState.emptiedBetween(old, look)
        if old is not None and PotLookState.servingsOf(look) > PotLookState.servingsOf(old):
            self.fx.batchDone([slot for slot in emptied if slot not in old.sunk])     # 煮掉的料：胀大、缩没、冒汽
        for slot in emptied:
            self.drift.clear(slot)
        arrived = PotLookState.arrivedBetween(old, look)
        if arrived:
            starts = self.startsOf(len(arrived)) if self.startsOf is not None and len(arrived) > 1 else None
            self.drift.arrive(arrived, starts, [slot in look.sunk for slot in arrived])
        self._retarget(PotLookState.progressAt(look, self.clock))
        if old is None:
            self.liquid.snap(self._amount())  # 刚看到这口锅：水不从锅底涨上来

    def _amount(self):
        return PotLiquid.tankAmount(PotLookState.filledOf(self.look), PotLookState.servingsOf(self.look))

    def _retarget(self, progress):
        look = self.look
        self.progress = progress
        dish = look.meal or look.dish
        broth = self.brothOf(dish["newItemName"]) if dish and self.brothOf else None
        poured = [PouredColors[look.items[slot]["newItemName"]] for slot in sorted(look.sunk)
                  if look.items[slot] is not None and look.items[slot]["newItemName"] in PouredColors]    # 倒进去的牛奶、打进去的蛋：染水
        self.liquid.retarget(WATER, [_colorOf(item) for item in PotLookState.foodOf(look)], look.meal is not None, progress, broth,
                             poured)

    def world(self, x, y, z):
        return PotModelMath.localPoint(self.facing, self.pos, x, y, z)

    def local(self, wx, wy, wz):
        """世界坐标 -> 锅自己的坐标（像素）。"""
        x, z = PotModelMath.worldToLocal(self.facing, (wx - self.pos[0] - 0.5) * 16.0, (wz - self.pos[2] - 0.5) * 16.0)
        return (8.0 + x, (wy - self.pos[1]) * 16.0, 8.0 + z)

    # ---------------------------------------------------------------- 每帧

    def frame(self, dt, near=True):
        """推进一帧。near：离本人够近，粒子和声音才放。返回 False 表示这口锅歇着（什么都没动）。"""
        look = self.look
        if look is None:
            return False
        self.sinceCheck += dt
        if self.sinceCheck >= CHECK_SECONDS:
            self.sinceCheck = 0.0
            if self.model.check():
                self.awake = AWAKE_SECONDS
        busy = self.hand or look.heated or look.stirring or look.rate > 0.0 or self.fx.busy
        self.awake = AWAKE_SECONDS if busy else self.awake - dt
        if self.awake <= 0.0:
            self.fx.silence()
            return False
        self.clock += dt
        progress = PotLookState.progressAt(look, self.clock)
        if abs(progress - self.progress) > 0.01:
            self._retarget(progress)
        liquid, spoon, drift = self.liquid, self.spoon, self.drift
        present = PotLookState.presentOf(look)
        mood = PotLiquid.potMood(look.heated, look.stirring, look.dish is not None, look.meal is not None)
        liquid.step(dt, self._amount(), mood, drift.current)
        synced = PotModelMath.worldToLocal(self.facing, look.spoon[0], look.spoon[1])
        spoon.step(dt, self.clock, self.hand, look.stirring, self.aim if self.hand else None, synced, liquid.surfaceY())
        drift.step(dt, self.clock, present, liquid.surfaceY(), spoon.throughX, spoon.throughZ, spoon.grip, spoon.swirl,
                   spoon.swirlSign, random.random)
        self._pieces(dt)
        self.model.open(True)
        self.model.liquid(liquid.drawnSurfaceY(), PotLiquid.toUnit(liquid.color), liquid.mottle, liquid.turned, liquid.edgeBoil,
                          self.pieces.packed())
        self.model.slots(self.pieces.slots)
        self.model.ladle((8.0 + spoon.tipX, spoon.spoonEnd, 8.0 + spoon.tipZ), (spoon.rot[0:3], spoon.rot[3:6], spoon.rot[6:9]))
        if spoon.ripple:
            self.model.ripple(8.0 + spoon.rippleX, 8.0 + spoon.rippleZ, PotSpoonMotion.RIPPLE_STRENGTH)
        for _ in range(liquid.boilCount):
            u, v, height = liquid.impulse(random.random)
            self.model.ripple(INNER_LO + INNER_SPAN * u, INNER_LO + INNER_SPAN * v, height)
        self._moveProps(present)
        self.fx.step(dt, near)
        self.model.waves(dt)
        if spoon.send and self.onSend is not None:
            wx, wz = PotModelMath.localToWorld(self.facing, spoon.sendX, spoon.sendZ)
            self.onSend(wx, wz, spoon.sendAt)
        return True

    def _pieces(self, dt):
        """煮好的汤里浮着的碎料：份数定块数，一块块冒上来，各敲一圈涟漪、咕噜一声；一批刚煮好时等料化完再冒。"""
        meal = self.look.meal
        name = meal["newItemName"] if meal else None
        slots = PotPiecesLook.dishSlots(name) if name else PotPiecesLook.EMPTY
        wanted = PotPiecesKinds.piecesCount(PotLookState.servingsOf(self.look)) if any(slots) else 0
        if self.fx.finishing:
            wanted = min(wanted, self.piecesShown)
        elif wanted != self.piecesShown:
            self.fx.sounds.blub(wanted - self.piecesShown)
            self.piecesShown = wanted
        for index in self.pieces.step(dt, wanted, name, slots):
            x, z = PotPiecesLook.wayOf(index, self.liquid.turned % PotPiecesLook.TURN_WRAP)
            self.model.ripple(8.0 + x, 8.0 + z, PotPiecesPiece.RISE_RING)

    def _moveProps(self, present):
        look, drift = self.look, self.drift
        itemComp = compFactory.CreateItem(levelId)
        for slot in range(SLOTS + 1):
            if slot < SLOTS:
                item = look.items[slot] if present[slot] and drift.visible[slot] else None
                pose = (drift.x[slot], drift.y[slot], drift.z[slot], drift.yaw[slot], drift.pitch[slot], drift.roll[slot])
            else:
                item, pose = look.served, PotDriftExtras.servedAt(self.liquid.surfaceY()) + (0.0, 0.0, 0.0)
            kind = (item["newItemName"], item["newAuxValue"]) if item else None
            prop = self.props[slot]
            if prop is not None and prop[1] != kind:
                itemComp.DeleteClientDropItemEntity(prop[0])
                prop = self.props[slot] = None
            if kind is None:
                continue
            if prop is None:
                one = {"newItemName": kind[0], "newAuxValue": kind[1], "count": 1}
                entityId = itemComp.AddDropItemToWorld(one, self.dimensionId, self.world(pose[0], pose[1], pose[2]), 0, 0)
                if not entityId:
                    continue
                prop = self.props[slot] = [entityId, kind]
            self.placeProp(prop[0], *pose)

    def placeProp(self, entityId, x, y, z, yaw, pitch, roll, scale=1.0):
        """把一件平躺的料摆在锅自己坐标的 (x, y, z)，按 JE 节点的欧拉角转；scale 是相对料的本来大小。"""
        size = ITEM_SCALE * max(scale, 0.01)
        matrix = ItemPose.lyingMatrix(PotModelMath.FACING_YAW[self.facing] + yaw, pitch, roll)
        pivot = ItemPose.pivotFor(self.world(x, y, z), matrix, size)
        compFactory.CreateItem(levelId).SetDropItemTransform(entityId, pivot, ItemPose.engineEuler(matrix), size)

    def removeProp(self, entityId):
        compFactory.CreateItem(levelId).DeleteClientDropItemEntity(entityId)

    def event(self, name, payload):
        """一次性的表现。盛出：锅心溅水、舀的一声（出锅时星星的闪在开着站点的人那边，见 PotView）。"""
        self.awake = AWAKE_SECONDS
        if name == "scooped":
            where = self.world(8.0, self.liquid.surfaceY(), 8.0)
            self.model.ripple(8.0, 8.0, 0.5)
            PotFx.particle(PotFx.SPLASH, where, color=self.liquid.brothColor, count=4)
            play("scoop", where, 0.55, 1.0)

    # ---------------------------------------------------------------- 收场

    def rebuilt(self):
        """方块实体在本端重建了（区块重载，加载事件也会重复来）：模型上的值全丢了，下一帧整份重推。
        道具是独立的客户端掉落物，还在：留着不动（实机：这里若只清记录不删实体，锅里会多出一份料）。"""
        self.model.reset()
        self.awake = AWAKE_SECONDS

    def destroy(self, blockGone=False):
        """锅没了，或者场景停用：清掉道具和声音；方块还在的话把盖子合回去。"""
        for prop in self.props:
            if prop is not None:
                self.removeProp(prop[0])
        self.props = [None] * (SLOTS + 1)
        self.fx.clear()
        if not blockGone:
            self.model.open(False)
