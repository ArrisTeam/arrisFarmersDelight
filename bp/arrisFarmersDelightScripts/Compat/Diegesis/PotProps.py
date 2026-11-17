# -*- coding: utf-8 -*-
"""PotProps - 厨锅场景里的客户端掉落物：漂着的六格料、产出格里装好的那份菜，摆法变了才碰引擎（客户端）

PotScene 每个渲染帧都叫它摆一遍（32 格内每口烧着的锅都这样）。漂着的料随波起伏、转圈，每帧都变；装好的那份菜、液面落定之后什么都不变：
摆法和上一次送给引擎的一模一样，就不重算矩阵、不调 SetDropItemTransform（炉灶的 GrillPieces.pose 同一个做法）。
手部动作、盛汤的碗、一批煮好时胀大缩没的道具也走 place / remove（PotScene.placeProp / removeProp 转过来），一并受益。
引擎没收下（返回假）就不记，下一帧再摆，和每帧都调时一样。
"""
from ...Client.Engine import addDropItem, compFactory, levelId
from ...Shared.Rules import ItemPose, PotLookState, PotModelMath
from ...Shared.Rules.HandsOn import PotDriftExtras

SLOTS = PotLookState.SLOTS
ITEM_SCALE = 3.2 / ItemPose.ITEM_SPAN       # JE 的料是 3.2 像素见方


class PotProps(object):
    def __init__(self, scene):
        self.scene = scene
        self.posed = {}                       # 掉落物 id -> 最近一次送给引擎的摆法 (x, y, z, yaw, pitch, roll, scale)

    def move(self, present):
        """每帧：六格漂着的料和产出格里装好的菜摆到该在的地方；换了东西的删掉重建。"""
        scene = self.scene
        look, drift, props = scene.look, scene.drift, scene.props
        for slot in range(SLOTS + 1):
            if slot < SLOTS:
                item = look.items[slot] if present[slot] and drift.visible[slot] else None
                pose = (drift.x[slot], drift.y[slot], drift.z[slot], drift.yaw[slot], drift.pitch[slot], drift.roll[slot])
            else:
                item, pose = look.served, PotDriftExtras.servedAt(scene.liquid.surfaceY()) + (0.0, 0.0, 0.0)
            kind = (item["newItemName"], item["newAuxValue"]) if item else None
            prop = props[slot]
            if prop is not None and prop[1] != kind:
                self.remove(prop[0])
                prop = props[slot] = None
            if kind is None:
                continue
            if prop is None:
                one = {"newItemName": kind[0], "newAuxValue": kind[1], "count": 1}
                entityId = addDropItem(one, scene.dimensionId, scene.world(pose[0], pose[1], pose[2]))
                if not entityId:
                    continue
                prop = props[slot] = [entityId, kind]
            self.place(prop[0], *scene.lift.raised(slot, pose))      # 抬起只动摆出来的位置；点哪里（PotPick 的盒子）用的是不含抬起的

    def place(self, entityId, x, y, z, yaw, pitch, roll, scale=1.0):
        """把一件平躺的料摆在锅自己坐标的 (x, y, z)，按 JE 节点的欧拉角转；scale 是相对料的本来大小。"""
        posed = (x, y, z, yaw, pitch, roll, scale)
        if self.posed.get(entityId) == posed:
            return
        scene = self.scene
        size = ITEM_SCALE * max(scale, 0.01)
        matrix = ItemPose.lyingMatrix(PotModelMath.FACING_YAW[scene.facing] + yaw, pitch, roll)
        pivot = ItemPose.pivotFor(scene.world(x, y, z), matrix, size)
        sent = compFactory.CreateItem(levelId).SetDropItemTransform(entityId, pivot, ItemPose.engineEuler(matrix), size)
        self.posed[entityId] = posed if sent else None

    def remove(self, entityId):
        self.posed.pop(entityId, None)
        compFactory.CreateItem(levelId).DeleteClientDropItemEntity(entityId)
