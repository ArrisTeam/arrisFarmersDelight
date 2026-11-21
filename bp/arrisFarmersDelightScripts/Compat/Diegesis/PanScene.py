# -*- coding: utf-8 -*-
"""PanScene - 一口煎锅在本客户端的场景：锅里的食物、颠锅、油膜、油星热气和声音，谁都看得见（客户端）

对应 Hands-On Delight 的 client/SkilletBehavior.frame：JE 的场景 idle_visible，32 格内每个客户端都按同步来的状态自己算全部动作。
这里每口加载着的煎锅一份（PanScenes.py 管登记和每帧调度）：状态来自服务端广播（Shared/Rules/PanLookState.py），动作是 HoD 的纯计算
（Shared/Rules/HandsOn/PanShow 一族，节点的姿态每帧在 show.nodes 里），画法是
- 方块实体模型：锅被颠时整只锅转着挪着、锅柄描边、油膜（PanModel.py；锅柄描边靠 handle_glow 骨骼的反面壳，油膜靠四片贴图方片 + 透明度）；
- 食物：客户端掉落物，平躺在锅里，跟着锅的转动走（PanPose）；蛋在锅沿敲开时手里的蛋是立着的；朝上那面半熟时上面叠一颗熟色粒子（FryTints）；
- 粒子、声音：PanFx.py。
全部用"场景坐标"（HoD 的 skillet.json：锅心 (8, 0, 8)，锅柄朝 +z），出手时经 PanModelMath 换到世界（锅柄永远朝方块的朝向）。
本人开着这口锅的站点时，PanView 把手交进来：focused、startsOf（一次放进好几件时从玩家屏幕底边飞来）、cursorAt（光标在某个高度的平面上的点）、
strokeAt（抓着锅柄时光标的高度，每帧读）、hovered（光标在锅柄上）、feel（触屏的轻震）。
每口加载着的锅在 32 格内每个渲染帧都过一遍 frame，所以静着的锅要歇着、道具没变不碰引擎（见 busy 和 Prop）：食物躺着不动的锅（凉的、生的）
歇着时道具原样留在世界里，一帧只做一次便宜的核对；歇着的锅被叫醒的路有六条：广播 / 方块实体数据来了、一次性的表现来了、方块实体在本端重建、
核对发现模型上的值丢了、本人开了站点（show.focused），和 busy 里别的任何一条成立。
"""
import random

from . import FryTints
from .PanFx import PanFx
from .PanModel import PanModel
from .TouchFeel import settled
from ...Client.Engine import addDropItem, compFactory, levelId
from ...Shared.Rules import ItemPose, PanLookState, PanModelMath, PanPose, PanStation
from ...Shared.Rules.HandsOn.PanShow import PanShow

CHECK_SECONDS = 0.5          # 多久核对一次模型上的值还在不在（方块实体重建会清掉）
AWAKE_SECONDS = 4.0          # 没动静之后再跑这么久就歇着（让最后一次变化的姿态、油膜收干都推到引擎里）
FLAT_LIFT = 0.5              # 平躺的掉落物离锅底再高这么多（半个像素厚），不然陷进锅底
PAN_CHILDREN = ("piece", "under", "lift")      # 锅的孩子：跟着锅转；hand / spill 是场景里最外层的节点，不跟锅


class Prop(object):
    """一件掉落物和它最近一次送给引擎的样子。位置和转角要连乘好几个矩阵，是每帧里最贵的一段（8 块食物 700 微秒）：
    节点的位置、转角和锅的转动都没变就不重算；缩放没变也不再调引擎。熟好的食物一鼓一鼓只变缩放，所以缩放单独记。
    matrix 是送给引擎的那个姿态（世界里的）：下一次的姿态接着它（ItemPose.steadied），所以和节点的姿态可以差贴图平面里的半圈。"""

    __slots__ = ("entityId", "kind", "orient", "center", "matrix", "euler", "scale")

    def __init__(self, entityId, kind):
        self.entityId, self.kind = entityId, kind
        self.orient = self.center = self.matrix = self.euler = self.scale = None


class PanScene(object):
    def __init__(self, dimensionId, pos, facing):
        self.dimensionId = dimensionId
        self.pos = (int(pos[0]), int(pos[1]), int(pos[2]))
        self.facing = facing
        self.show = PanShow(PanStation, random.random, self._fromPlayer, self._cursorOn)
        self.model = PanModel(self.pos)
        self.fx = PanFx(self.pos, facing)
        self.look = None
        self.onDrawn = None                   # 第一次真画出样子时调一次（PanScenes 让世界里原来的展示这时才收起：场景没画之前不能把它盖掉）
        self.clock = 0.0
        self.awake = 0.0
        self.sinceCheck = 0.0
        self.props = {}                       # 节点名 -> Prop
        self.tints = FryTints.TopTints()      # 朝上那面的熟色：叠在道具上的粒子，键也是节点名
        self.hovered = False                  # 光标在锅柄上（本人）
        self.offering = False                 # 本人手上的东西放得进锅：锅身描边
        self.startsOf = None                  # startsOf(高度, 第几个, 共几个) -> (dx, dz)：从玩家屏幕底边飞来的起点相对中心的偏移
        self.cursorAt = None                  # cursorAt(高度) -> 场景坐标的点或 None
        self.strokeAt = None                  # strokeAt() -> 抓着锅柄时光标此刻在竖直平面上的高度，没抓着 None（每帧读，帧间隔和场景的钟同源）
        self.feel = None                      # feel(种类)：本人开着站点时触屏的一下轻震（TouchFeel），服务端说放进来 / 被拒时调

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
        settled(self.feel, name)

    # ---------------------------------------------------------------- 每帧

    def busy(self):
        """还有什么在随时间变，锅就不能歇：热着（热浪、油星、油泡、滋滋声、油膜）、本人开着站点（描边、抓锅柄、飞入的起点）、
        熟好的食物在鼓（readyGlow：闪、冒汽，凉锅也一样）、排着队的小步骤（跳、落、声音）、油膜在收干、蛋在磕、颠锅这一阵。
        每个渲染帧、每口锅都问一遍，所以只看这几个字段。锅里躺着食物、有掉落物，都不算（没变的掉落物不碰引擎，见 _prop）。
        热着一定是 rate > 0 的前提（PanLook.rateOf），熟度外推不用另列。"""
        show = self.show
        return self.look.heated or show.focused or len(show.steps) > 0 or show.oil.amount > 0.0 or show.tossing() \
            or any(show.cracking) or show.heat.glows()

    def frame(self, dt, near=True):
        """推进一帧。near：离本人够近，粒子和声音才放。返回 False 表示这口锅歇着（什么都没动：掉落物和模型停在最后摆好的样子，
        这一帧只做了核对和 busy）。"""
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
            return False
        self.clock += dt
        self.show.progress(*PanLookState.progressAt(look, self.clock))
        self.show.frame(dt)
        y = self.strokeAt() if self.strokeAt is not None else None
        if y is not None:
            self.show.strokeMove(y)
        self._pose()
        self.tints.frame(dt, FryTints.panWanted(self.show, self.props))
        self.fx.play(self.show.drain(), near)
        if self.onDrawn is not None:
            drawn, self.onDrawn = self.onDrawn, None
            drawn()
        return True

    def _pose(self):
        show, model = self.show, self.model
        pan = show.nodes["pan"]
        panPos, panRot = pan.pos, pan.rot
        model.scene(True)
        model.pan(panRot[0], (panPos[0] - 8.0, panPos[1], panPos[2] - 8.0))
        model.glow(show.handleOutlined(self.hovered), self.offering)
        model.oil(show.oil.puddles())
        for name, node in show.nodes.items():
            if name != "pan" and (node.visible or name in self.props):      # 没画出来、本来也没有的节点（四十个里常常只有几个）不用看
                self._prop(name, panPos, panRot, node)

    # ---------------------------------------------------------------- 掉落物

    def _prop(self, name, panPos, panRot, node):
        item = node.item if node.visible else None
        kind = (item["newItemName"], item.get("newAuxValue") or 0) if item else None
        prop = self.props.get(name)
        if prop is not None and prop.kind != kind:
            compFactory.CreateItem(levelId).DeleteClientDropItemEntity(prop.entityId)
            del self.props[name]
            prop = None
        if kind is None:
            return
        orient = (node.pos, node.rot, panPos, panRot)
        scale = max(0.01, node.size * node.scale / ItemPose.ITEM_SPAN)
        if prop is not None and orient == prop.orient and scale == prop.scale:
            return                                  # 和引擎里的一模一样：不重算、不调引擎
        center, matrix = (prop.center, prop.matrix) if prop is not None else (None, None)
        if prop is None or orient != prop.orient:
            center, posed = self._placed(name, panPos, panRot, node)
            # 锅里躺着的接着上一次画的姿态：翻面到顶点换向时轴心不跳（ItemPose.steadied；引擎的位置晚到一两帧，跳了就闪到别处）。蛋的手、蛋液照原样
            center, matrix = self.world(center), ItemPose.steadied(PanPose.toWorld(self.facing, posed), matrix if name.split("_")[0] in PAN_CHILDREN else None)
        pivot = ItemPose.pivotFor(center, matrix, scale)
        if prop is None:
            entityId = addDropItem({"newItemName": kind[0], "newAuxValue": kind[1], "count": 1}, self.dimensionId, pivot)      # 一出生就在轴心该在的地方
            if not entityId:
                return
            prop = self.props[name] = Prop(entityId, kind)
        if matrix is not prop.matrix:
            prop.center, prop.matrix, prop.euler = center, matrix, ItemPose.engineEuler(matrix)
        sent = compFactory.CreateItem(levelId).SetDropItemTransform(prop.entityId, pivot, prop.euler, scale)
        prop.orient, prop.scale = (orient, scale) if sent else (None, None)         # 引擎没收下就下一帧再来（和每帧都调时一样）

    @staticmethod
    def _placed(name, panPos, panRot, node):
        """节点在场景里的中心和矩阵。锅的孩子经锅的转动，蛋的手立着，蛋液平躺。"""
        group = name.split("_")[0]
        x, y, z = node.pos
        if group in PAN_CHILDREN:
            return PanPose.inPan(panPos, panRot, (x, y + FLAT_LIFT, z)), PanPose.lying(node.rot, panRot)
        return (x, y, z), (PanPose.upright(node.rot) if group == "hand" else PanPose.lying(node.rot))

    def _clearProps(self):
        itemComp = compFactory.CreateItem(levelId)
        for prop in self.props.values():
            itemComp.DeleteClientDropItemEntity(prop.entityId)
        self.props = {}
        self.tints.clear()

    # ---------------------------------------------------------------- 收场

    def _rest(self):
        """场景停用、方块还在：锅放回原位、不描边、没有油。（场景歇着不走这里：歇着时模型已经是这个样子了，掉落物也要留着。）"""
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
