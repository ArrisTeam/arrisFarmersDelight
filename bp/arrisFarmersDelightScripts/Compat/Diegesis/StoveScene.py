# -*- coding: utf-8 -*-
"""StoveScene - 一座炉灶在本客户端的场景：烤架上的东西、落下 / 翻面 / 取走的动作、热浪蒸汽和该翻了的烟，谁都看得见（客户端）

对应 Hands-On Delight 的 client/StoveBehavior：JE 的炉灶场景 idle_visible，32 格内每个客户端都按同步来的状态自己演全部动作，
不用开站点：厨师关了站点走开，烤着的东西照样冒汽，该翻了的那件照样冒烟、嗞嗞叫，别人翻面 / 取走 / 烤好的动作也看得见。
这里每座加载着的炉灶一份（StoveScenes.py 管登记和每帧调度）：状态来自服务端广播（Server/StoveLook.py，Shared/Rules/StoveLookState.py 解），
动作、画法、粒子声音都是 GrillPieces.Pieces 的（站点里原来画在前置包的站点空间，现在画在炉灶朝向的站点空间里，StoveWorld.py）：
站点的北面是炉灶的正面（JE 的 Orientation.BLOCK），六件的位置、动作、粒子声音的位置都按炉灶的朝向转到世界（Shared/Rules/StoveFacing），
和开着站点的人看到的是同一套，谁站在哪边看都一样。炉灶方块自己不动，没有模型要推：件、虚影、粒子就是全部。
本人开着这座炉灶的站点时，GrillView 把手交进来（focus）：一次放好几件时从玩家屏幕下沿飞来、"自己刚翻过的"那一下不重复演
（服务端的 turned 到的时候已经演过了）；被拒的虚影谁看都往炉灶的正面弹。
"""
from .GrillPieces import Pieces
from .GrillSpace import WorldSpace
from .StoveWorld import WorldView
from ...Shared.Rules import StoveLookState

AGAIN = 0.6              # 本人刚翻过的这一下：服务端说"翻了"的 0.6 秒内不重复演（JE 的 EFFECT_TURNED：clock - turnedAt > 0.6）


class StoveScene(object):
    def __init__(self, dimensionId, pos, yaw):
        self.dimensionId = dimensionId
        self.pos = (int(pos[0]), int(pos[1]), int(pos[2]))
        self.yaw = yaw                        # 炉灶朝向（度，StoveFacing.yawOfAux）
        self.view = WorldView(dimensionId, self.pos, yaw)
        self.space = WorldSpace(self.pos, yaw)
        self.pieces = Pieces(self.view, self.space)
        self.known = False                    # 收到过一份状态了（之前不推进：刚建好第一份状态来之前不能把"刚加载不演落下"用掉）
        self.focused = False                  # 本人开着这座炉灶的站点

    # ---------------------------------------------------------------- 状态

    def apply(self, payload):
        """服务端广播来了：六个烤位各是什么、手放的吗、贴灶面和朝上面烤到哪。"""
        self.applyLook(StoveLookState.decode(payload))

    def applyLook(self, look):
        """换一份样子（广播解出来的，或区块晚加载时按方块实体数据建的）：下一帧照它画。"""
        self.view.show(look)
        self.known = True

    def event(self, name, payload):
        """一次性的表现：放上去、放不上去、翻、没翻成、取走、烤好。payload 是 StoveLookState.eventData 清过的。"""
        pieces, place = self.pieces, payload["place"]
        if name == "placed":
            pieces.placed()
        elif name == "refused":
            pieces.refused(payload["stack"])
        elif name == "turned" and place is not None and not (self.focused and pieces.clock - pieces.turnedAt[place] <= AGAIN):
            pieces.turned(place, payload["up"])
        elif name == "unturned" and place is not None:
            pieces.unturned(place)
        elif name == "taken" and place is not None:
            pieces.taken(place, payload["stack"])
        elif name == "grilled" and place is not None:
            pieces.grilled(place)

    def turn(self, yaw):
        """炉灶方块的朝向和场景记的不一样（区块里的方块实体重建时读到的）：已经画出来的件都是按旧朝向摆的，全收掉，下一帧照新朝向重画
        （样子还在，所以不演落下）。"""
        if yaw != self.yaw:
            self.yaw = self.space.yaw = yaw
            self.view.turn(yaw)
            self.pieces.clear()

    # ---------------------------------------------------------------- 本人

    def focus(self, starts):
        """本人开了站点：starts(index, count) 是飞入的起点（GrillSpace.Space.fromPlayer）。"""
        self.focused = True
        self.space.focus(starts)

    def blur(self):
        self.focused = False
        self.space.focus(None)

    # ---------------------------------------------------------------- 每帧

    def frame(self, dt, near=True):
        """推进一帧。near：离本人够近，粒子和声音才放。第一份状态来之前什么都不画，返回 False。"""
        if not self.known:
            return False
        self.pieces.frame(dt, near or self.focused)
        return True

    # ---------------------------------------------------------------- 收场

    def rebuilt(self):
        """方块实体在本端重建了（区块重载，加载事件也会重复来）：件全收掉，接着来的那份状态按"刚加载"重画，不演落下。"""
        self.pieces.clear()
        self.known = False

    def destroy(self):
        """炉灶没了、换了维度或场景停用：道具全收掉。"""
        self.pieces.clear()
        self.view.props.clear()
        self.known = False
