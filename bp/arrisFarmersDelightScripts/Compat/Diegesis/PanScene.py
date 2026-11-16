# -*- coding: utf-8 -*-
"""PanScene - 一口煎锅在本客户端的场景：锅里的食物、颠锅、油膜、油星热气和声音，谁都看得见（客户端）

对应 Hands-On Delight 的 client/SkilletBehavior.frame：JE 的场景 idle_visible，32 格内每个客户端都按同步来的状态自己算全部动作。
这里每口加载着的煎锅一份（PanScenes.py 管登记和每帧调度）：状态来自服务端广播（Shared/Rules/PanLookState.py），动作是 HoD 的纯计算
（Shared/Rules/HandsOn/PanShow 一族，节点的姿态每帧在 show.nodes 里），画法是
- 方块实体模型：锅被颠时整只锅转着挪着、锅柄描边、油膜（PanModel.py；锅柄描边靠 handle_glow 骨骼的反面壳，油膜靠四片贴图方片 + 透明度）；
- 食物：客户端掉落物，平躺在锅里，跟着锅的转动走（PanPose）；蛋在锅沿敲开时手里的蛋是立着的；
- 粒子、声音：PanFx.py。
全部用"场景坐标"（HoD 的 skillet.json：锅心 (8, 0, 8)，锅柄朝 +z），出手时经 PanModelMath 换到世界（锅柄永远朝方块的朝向）。
本人开着这口锅的站点时，PanView 把手交进来：focused、startsOf（一次放进好几件时从玩家屏幕底边飞来）、cursorAt（光标在某个高度的平面上的点）、
strokeAt（抓着锅柄时光标的高度，每帧读）、hovered（光标在锅柄上）。
"""
import random

from .PanFx import PanFx
from .PanModel import PanModel
from ...Client.Engine import addDropItem, compFactory, levelId
from ...Shared.Rules import ItemPose, PanLookState, PanModelMath, PanPose, PanStation
from ...Shared.Rules.HandsOn.PanShow import PanShow

CHECK_SECONDS = 0.5          # 多久核对一次模型上的值还在不在（方块实体重建会清掉）
AWAKE_SECONDS = 4.0          # 没动静之后再跑这么久就歇着
FLAT_LIFT = 0.5              # 平躺的掉落物离锅底再高这么多（半个像素厚），不然陷进锅底
PAN_CHILDREN = ("piece", "under", "lift")      # 锅的孩子：跟着锅转；hand / spill 是场景里最外层的节点，不跟锅


class PanScene(object):
    def __init__(self, dimensionId, pos, facing):
        self.dimensionId = dimensionId
        self.pos = (int(pos[0]), int(pos[1]), int(pos[2]))
        self.facing = facing
        self.show = PanShow(PanStation, random.random, self._fromPlayer, self._cursorOn)
        self.model = PanModel(self.pos)
        self.fx = PanFx(self.pos, facing)
        self.look = None
        self.clock = 0.0
        self.awake = 0.0
        self.sinceCheck = 0.0
        self.props = {}                       # 节点名 -> [掉落物 id, (物品名, aux)]
        self.hovered = False                  # 光标在锅柄上（本人）
        self.offering = False                 # 本人手上的东西放得进锅：锅身描边
        self.startsOf = None                  # startsOf(高度, 第几个, 共几个) -> (dx, dz)：从玩家屏幕底边飞来的起点相对中心的偏移
        self.cursorAt = None                  # cursorAt(高度) -> 场景坐标的点或 None
        self.strokeAt = None                  # strokeAt() -> 抓着锅柄时光标此刻在竖直平面上的高度，没抓着 None（每帧读，帧间隔和场景的钟同源）

    # ---------------------------------------------------------------- 回调

    def _fromPlayer(self, height, index, count):
        return self.startsOf(height, index, count) if self.startsOf is not None else (0.0, 0.0)

    def _cursorOn(self, height):
        return self.cursorAt(height) if self.cursorAt is not None else None

    def world(self, point):
        return PanModelMath.worldPoint(self.facing, self.pos, point)

    def scenePoint(self, wx, wy, wz):
        return PanModelMath.scenePoint(self.facing, self.pos, wx, wy, wz)

    # ---------------------------------------------------------------- 状态

    def apply(self, payload):
        """服务端广播（或方块实体数据里存的）来了：锅里的东西、热源、两面熟到哪。"""
        self.look = PanLookState.decode(payload, self.clock, self.look)
        self.awake = AWAKE_SECONDS
        self._sync()

    def applyLook(self, look):
        """区块晚加载：直接给一份按方块实体数据建好的样子。"""
        self.look = look
        self.look.stamp = self.clock
        self.awake = AWAKE_SECONDS
        self._sync()

    def _sync(self):
        look = self.look
        down, up = PanLookState.progressAt(look, self.clock)
        self.show.apply(look.item, look.byHand, look.heated, down, up)

    def event(self, name, payload):
        """一次性的表现：放进来、被拒、颠、取走、煎好。"""
        self.awake = AWAKE_SECONDS
        self.show.effect(name, payload)

    # ---------------------------------------------------------------- 每帧

    def busy(self):
        show = self.show
        return bool(self.look.item) or self.look.heated or show.focused or len(show.steps) > 0 or show.oil.amount > 0.0 \
            or any(show.cracking) or show.tossing() or bool(self.props)

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
        self.awake = AWAKE_SECONDS if self.busy() else self.awake - dt
        if self.awake <= 0.0:
            self._rest()
            return False
        self.clock += dt
        self.show.progress(*PanLookState.progressAt(look, self.clock))
        self.show.frame(dt)
        y = self.strokeAt() if self.strokeAt is not None else None
        if y is not None:
            self.show.strokeMove(y)
        self._pose()
        self.fx.play(self.show.drain(), near)
        return True

    def _pose(self):
        show, model = self.show, self.model
        pan = show.nodes["pan"]
        model.scene(True)
        model.pan(pan.rot[0], (pan.pos[0] - 8.0, pan.pos[1], pan.pos[2] - 8.0))
        model.glow(show.handleOutlined(self.hovered), self.offering)
        model.oil(show.oil.puddles())
        itemComp = compFactory.CreateItem(levelId)
        for name, node in show.nodes.items():
            if name != "pan":
                self._prop(itemComp, name, pan, node)

    # ---------------------------------------------------------------- 掉落物

    def _prop(self, itemComp, name, pan, node):
        item = node.item if node.visible else None
        kind = (item["newItemName"], item.get("newAuxValue") or 0) if item else None
        prop = self.props.get(name)
        if prop is not None and prop[1] != kind:
            itemComp.DeleteClientDropItemEntity(prop[0])
            del self.props[name]
            prop = None
        if kind is None:
            return
        if prop is None:
            entityId = addDropItem({"newItemName": kind[0], "newAuxValue": kind[1], "count": 1}, self.dimensionId,
                                   self.world(PanModelMath.SCENE_PAN))
            if not entityId:
                return
            prop = self.props[name] = [entityId, kind]
        center, matrix = self._placed(name, pan, node)
        scale = max(0.01, node.size * node.scale / ItemPose.ITEM_SPAN)
        world = PanPose.toWorld(self.facing, matrix)
        pivot = ItemPose.pivotFor(self.world(center), world, scale)
        itemComp.SetDropItemTransform(prop[0], pivot, ItemPose.engineEuler(world), scale)

    @staticmethod
    def _placed(name, pan, node):
        """节点在场景里的中心和矩阵。锅的孩子经锅的转动，蛋的手立着，蛋液平躺。"""
        group = name.split("_")[0]
        x, y, z = node.pos
        if group in PAN_CHILDREN:
            return PanPose.inPan(pan.pos, pan.rot, (x, y + FLAT_LIFT, z)), PanPose.lying(node.rot, pan.rot)
        return (x, y, z), (PanPose.upright(node.rot) if group == "hand" else PanPose.lying(node.rot))

    def _clearProps(self):
        itemComp = compFactory.CreateItem(levelId)
        for prop in self.props.values():
            itemComp.DeleteClientDropItemEntity(prop[0])
        self.props = {}

    # ---------------------------------------------------------------- 收场

    def _rest(self):
        """歇着：掉落物收起来，锅放回原位、不描边、没有油。"""
        self._clearProps()
        self.model.pan(0.0, (0.0, 0.0, 0.0))
        self.model.glow(False)
        self.model.oil([])

    def rebuilt(self):
        """方块实体在本端重建了（区块重载，加载事件也会重复来）：模型上的值全丢了，下一帧整份重推。道具是独立的客户端掉落物，还在。"""
        self.model.reset()
        self.awake = AWAKE_SECONDS

    def destroy(self, blockGone=False):
        """锅没了，或者场景停用：清掉道具；方块还在的话把模型放回原样。"""
        self._clearProps()
        if not blockGone:
            self._rest()
            self.model.scene(False)
