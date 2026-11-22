# -*- coding: utf-8 -*-
"""BoardCutter - 砧板站点里本人的刀：悬在食物上跟着光标、吸附到下一刀的虚线、点一下落刀；刀以外的工具点一下开始一个动作（客户端）

对应 Hands-On Delight：client/BoardBehavior.java 的 moveKnife / moveTool / drawMarks / chop / startStroke / impact（834-1060、1142-1194、1257-1279）。
数和状态机都在 Shared/Rules/HandsOn（BoardMarks 刀口线、BoardKnife 刀的走法和点下去等回话、BoardStroke 别的工具的动作），这里只把它们接到道具上：
- 虚线：下一刀的那一条，平躺在食物顶面上，只画在图标的实心像素上（半透明的白，一段一颗粒子，0.18 秒从无渐显，BoardMarkLine）；
  有工具可用（光标栈上切得了的，或手空着背包里有刀）才显示；
- 刀：光标栈上拿着的、或手空着借背包里的，光标在食物上时画一把立着的刀（刀尖朝下，顺着这一刀的线转），悬在光标处、吸附到线上、
  点一下下去 0.05 秒上来 0.14 秒；画着的时候 drawn 为真，BoardView 据此把内核画在光标上的那一份缩到看不见（JE 的 setCarriedHidden）；
  借来的（手空着）半透明，落下去那一下变实，拿在手里的一直是实的（BoardStand）；
- 点在线上才发 chop；没吸附上只敲一声；刀以外的工具点一下开始动作，到接触那一刻才发（BoardStroke.Run）；
- 触屏（JE 没有，给手机的适配）：没有悬停，刀没有先吸附到线上的机会，手指又盖着线——点在食物上就按这一刻的落点现算：落在下一刀的线上（离线多远都算，
  刀当场站到线上离手指最近的一点），第一下就是一刀，不是只敲一声。别的工具一样（吸附带也放宽）。服务端只认序号（BoardChop），位置只用来放碎屑。
"""
import math

from . import BoardFx, TouchFeel
from .BoardMarkLine import MarkLine
from .BoardStand import Stand
from ...Shared.Rules.HandsOn import BoardDashes as Dashes
from ...Shared.Rules.HandsOn import BoardKnife as Knife
from ...Shared.Rules.HandsOn import BoardMarks as Marks
from ...Shared.Rules.HandsOn import BoardScene as Scene
from ...Shared.Rules.HandsOn import BoardStroke as Stroke
from ...Shared.Rules.HandsOn import Cutting


class Cutter(object):
    def __init__(self, owner):
        self.owner = owner                          # BoardViewMixin：要它的 view、api、draw、screen、board()、layers()、sendChop
        self.knife = Knife.Knife()
        self.pending = Knife.Pending()
        self.run = None                             # 正在进行的别的工具的动作（BoardStroke.Run）
        self.drawn = False                          # 本端正把刀 / 工具画在食物上（光标栈上的那份该收起来）
        self.stands = {"knife": Stand(owner.view), "tool": Stand(owner.view)}
        self.line = None                            # MarkLine：现在画着的那一条虚线
        self.clock = 0.0
        self.place = [0.0, Knife.REST_Z, 0.0]       # 别的工具悬在哪：x、z、朝向（弧度）
        self.snap = -1                              # 别的工具吸附着的那一刀（方块类在方块上任何地方都算）
        self.next = (-1, None, None)                # 下一刀：(序号, 线, 虚线两端)
        self.snipRange = (-0.5, 0.5)

    # ---------------------------------------------------------------- 这一帧要的东西

    def _geometry(self):
        """板上的东西的几何：(图标, 是不是方块类, 主轴, 一共几刀)；没有要切的东西返回 None。"""
        board, owner = self.owner.board(), self.owner
        if board is None or owner.layers() or not owner.view.data.get("plan"):
            return None
        isBlock = owner.draw.kindOf(board) == "block"
        icon = None if isBlock else Marks.iconOf(board["newItemName"])
        return icon, isBlock, Marks.axisOf(icon, isBlock), int(owner.view.data["plan"])

    def _touch(self):
        return self.owner.view.input == self.owner.api.TOUCH

    def _reach(self):
        """刀 / 工具离下一刀的线多近算吸附：键鼠照 JE 的 SNAP；触屏点在食物上就落在线上（TAP_SNAP）。"""
        return Marks.TAP_SNAP if self._touch() else Marks.SNAP

    def over(self):
        """光标在食物上的点（离食物中心，夹进 REACH），不在食物上是 None（overItem）。"""
        owner = self.owner
        ray = owner.draw.cursor
        if ray is None or owner.board() is None or owner.view.overUi(owner.screen):
            return None
        found = owner.api.Geometry.planeAtHeight(ray, owner.draw.surface())
        return None if found is None else Marks.overItem(found[0] - owner.draw.cx, found[2] - owner.draw.cz)

    def _next(self, geo, whole):
        """下一刀：服务端说的已切刀数加上等着回话的，取第一条没切的线。whole（方块类、一下切整件的工具）没有线、只有序号（HoD 的 nextMark：
        overMark = next，工具落在方块上哪里都算这一刀）。"""
        if geo is None:
            return (-1, None, None)
        data = self.owner.view.data
        index = self.pending.next(int(data.get("marks") or 0), geo[3])
        if index < 0 or whole:
            return (index, None, None)
        cut = Marks.markOf(geo[2], data.get("style"), data.get("spots") or [], data.get("angles") or [], index, geo[3])
        return (index, cut, Marks.dashOf(cut, geo[0], geo[1]))

    # ---------------------------------------------------------------- 每帧

    def frame(self, dt, tool):
        """tool 是现在用的工具（物品，光标栈上的或背包里借的）或 None。画刀 / 工具 / 虚线。"""
        owner = self.owner
        self.clock += dt
        geo = self._geometry() if tool is not None else None
        stroke = owner.view.data.get("stroke") or Cutting.TOOL_CUT
        moves = Stroke.isStroke(stroke) and stroke != Cutting.TOOL_CUT
        self.next = self._next(geo, geo is not None and geo[1] and moves)
        self._marks(dt, geo)
        over = self.over() if geo is not None else None
        top = owner.draw.surface() - Scene.TOP
        if geo is None or not moves:
            self._drop("tool")
            pose = self.knife.frame(dt, over, self.next[1], self.next[0], top, geo is not None, self._reach())
            self._knife(tool, pose)
            self.drawn = pose is not None and tool is not None
        else:
            self._drop("knife")
            self.drawn = self._tool(dt, tool, stroke, geo, over, top)

    # ---------------------------------------------------------------- 虚线

    def _marks(self, dt, geo):
        """下一刀的虚线：换了一条就重画（新的一条从透明渐显）。key 里有食物顶面的高度（JE 的 itemHeight：叠数变了线要跟着升降）。"""
        index, cut, ends = self.next
        draw = self.owner.draw
        key = (index, round(cut.x, 3), round(cut.z, 3), round(cut.angle, 3), self.owner.board()["newItemName"], round(draw.surface(), 3)) if ends is not None else None
        if self.line is not None and self.line.key != key:
            self.line.remove()
            self.line = None
        if key is None:
            return
        if self.line is None:
            a, b = ((draw.cx + end[0], draw.cz + end[1]) for end in ends)
            self.line = MarkLine(self.owner.view, key, a, b, draw.surface())
        else:
            self.line.frame(dt)

    # ---------------------------------------------------------------- 画道具

    def _drop(self, name):
        self.stands[name].remove()

    def _stand(self, name, tool, center, facing, roll, striking):
        """立着的一把工具（刀或别的）：手空着悬着的是背包里借来的，半透明，落下去那一下（striking）变实；光标栈上拿着的是实的（BoardBehavior 868、932）。"""
        alpha = None if self.owner.view.hand is not None else Dashes.offeredAlpha(striking)
        self.stands[name].show(tool, center, facing, roll, alpha)

    def _knife(self, tool, pose):
        """悬在食物上的刀：刀尖朝下，顺着这一刀的线。"""
        if pose is None or tool is None:
            self._drop("knife")
            return
        x, y, z, angle = pose
        draw = self.owner.draw
        self._stand("knife", tool, (draw.cx + x, Scene.TOP + y + Scene.KNIFE_TIP, draw.cz + z), (math.sin(angle), -math.cos(angle)), Scene.KNIFE_ROLL,
                    self.knife.chopping)

    # ---------------------------------------------------------------- 别的工具

    def _tool(self, dt, tool, kind, geo, over, top):
        """斧、镐、锹、锄、剪刀：悬在活上，点一下开始动作，动作到接触才发 chop。返回有没有把工具画出来。"""
        if self.run is None and over is not None:
            self._aim(dt, kind, geo[1], over)
        if self.run is not None:
            for event in self.run.step(dt):
                if event == "snip":
                    BoardFx.play(BoardFx.snipBite(), self.owner.view.toWorld(*self._at(0.0, 3.0)))
                elif event == "impact":
                    self._impact()
                elif event == "done":
                    self.run = None
        if tool is None or (over is None and self.run is None):
            self._drop("tool")
            return False
        posed = Stroke.pose(kind, self.run.age if self.run is not None else None, (0.0, Stroke.workHeight(kind, top)), top, *self.snipRange)
        yaw = self.place[2]
        self._stand("tool", tool, self._at(posed["center"][0], posed["center"][1], yaw), (math.sin(yaw), -math.cos(yaw)), posed["roll"], self.run is not None)
        return True

    def _at(self, u, y, yaw=0.0):
        """工具平面里的 (沿线 u, 高 y) -> 站点像素。平面在 (place.x, place.z) 处、顺着 yaw。"""
        draw = self.owner.draw
        return (draw.cx + self.place[0] + u * math.cos(yaw), Scene.TOP + y, draw.cz + self.place[1] + u * math.sin(yaw))

    def _aim(self, dt, kind, isBlock, over, jump=False):
        """工具悬在哪（aim，965-992）：方块在方块上任何地方，食物吸附到线上、握柄朝厨师。jump：触屏点下去的这一下，工具当场到位（没有悬停，
        不从原来的地方慢慢追过来）。"""
        index, cut, _ends = self.next
        x, z = Stroke.aimOnBlock(kind, over[0], over[1]) if isBlock else over
        self.snap = index if isBlock else -1
        if isBlock:
            self.place[2] = 0.0
        elif cut is not None:
            self.place[2] = Stroke.towardsCook(cut.angle)
            offset = Marks.snapOffset(cut, x, z, self._reach())
            if offset is not None:
                x, z, self.snap = x - cut.normalX() * offset, z - cut.normalZ() * offset, index
        follow = 1.0 if jump else 1.0 - math.exp(-Knife.FOLLOW * dt)
        self.place[0] += (x - self.place[0]) * follow
        self.place[1] += (z - self.place[1]) * follow

    def _impact(self):
        """接触（impact，1040-1060）：除削皮、剪刀以外活抖一下；落在线上才发 chop；没吸附上只敲一声。"""
        if (self.owner.view.data.get("stroke") or Cutting.TOOL_CUT) not in (Cutting.TOOL_STRIP, Cutting.TOOL_SNIP):
            self.owner.draw.shake()
        if self.run is None or self.run.mark < 0:
            BoardFx.play(BoardFx.KNOCK, self.owner.view.toWorld(*self._at(0.0, 2.0)))
            TouchFeel.buzz(self.owner.view, TouchFeel.REFUSE)
            return
        self.pending.add(self.clock)
        self.owner.sendChop(self.place[0], self.place[1], self.run.mark)

    # ---------------------------------------------------------------- 点一下

    def _tap(self, moves, stroke, over):
        """触屏的一下点按（点在食物上）：没有悬停，下一刀和吸附都按这一刻的落点现算——frame 里算的是上一帧的光标和上一帧的下一刀，
        手指落下的这一下总是还没吸附上、只会敲一声。刀当场站到下一刀的线上、工具当场到位。"""
        geo = self._geometry()
        if geo is None:
            return
        self.next = self._next(geo, geo[1] and moves)
        if moves:
            self._aim(0.0, stroke, geo[1], over, jump=True)
        else:
            self.knife.land(over, self.next[1], self.next[0], self._reach())

    def click(self):
        """本人点了板、要落刀（chop，1257-1279）：刀按线落（吸附上了才发），别的工具开始一个动作。"""
        owner = self.owner
        stroke = owner.view.data.get("stroke") or Cutting.TOOL_CUT
        over = self.over()
        moves = Stroke.isStroke(stroke) and stroke != Cutting.TOOL_CUT
        if self._touch() and over is not None and (not moves or self.run is None):
            self._tap(moves, stroke, over)
        if moves:
            if over is not None and self.run is None:
                self.run = Stroke.Run(stroke, self.snap)
                if stroke == Cutting.TOOL_SNIP and self.snap >= 0 and self.next[1] is not None and self.next[2] is not None:
                    cut, ends = self.next[1], self.next[2] or ()       # 上面已查过不是 None；`or ()` 是让网易机审（pylint）不把迭代判成迭代 None
                    along = [(p[0] - cut.x) * math.cos(cut.angle) + (p[1] - cut.z) * math.sin(cut.angle) for p in ends]
                    self.snipRange = Stroke.snipRange(self.place[0], self.place[1], self.place[2], cut, along)
            return
        result = self.knife.click(over)
        if result is None:
            return
        if result[0] == Knife.KNOCK:
            BoardFx.play(BoardFx.KNOCK, owner.view.toWorld(owner.draw.cx, owner.draw.surface(), owner.draw.cz))
            TouchFeel.buzz(owner.view, TouchFeel.REFUSE)
            return
        self.pending.add(self.clock)
        owner.sendChop(self.knife.x, result[2], result[1])

    def close(self):
        for name in self.stands:
            self._drop(name)
        if self.line is not None:
            self.line.remove()
            self.line = None
        self.run = None
        self.drawn = False
        self.pending.reset()
        self.knife.reset()
