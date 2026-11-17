# -*- coding: utf-8 -*-
"""BoardEffects - 站点里本人收到的服务端表现事件：声音、碎屑、撤回刀口、弹回、拿走、做成（客户端）

对应 Hands-On Delight：client/BoardBehavior.java 的 onEffect（1350-1389）和 chopped（1395-1453）。声音按 Shared/Rules/BoardSounds 的表放
（旁观的人在 BoardWatch 里按同一张表放，所以两边听到的一样）；动画在 BoardDraw，碎屑在 BoardFx。
"""
from . import BoardFx
from ...Shared.Rules import BoardSounds as Sounds
from ...Shared.Rules.HandsOn import BoardScene as Scene
from ...Shared.Rules.HandsOn import Cutting


def onEffect(owner, name, data):
    """owner 是 BoardViewMixin：要它的 draw、cutter、view、board()、layers()。"""
    draw, view = owner.draw, owner.view
    world = view.toWorld(draw.cx, Scene.TOP, draw.cz)
    for sound in ([] if name == "assembled" else Sounds.soundsOf(name, data)):         # 做成的声音等各层落完（assembled 里放）
        BoardFx.play(sound, world)
    if name == "chopped":
        _chopped(owner, data)
    elif name == "refused":
        if owner.cutter.pending.refused():
            owner.redraw()
        if data.get("stack"):
            draw.bounced(data["stack"])
    elif name == "taken":
        if (data.get("stack") or {}).get("newItemName"):
            draw.taken(data["stack"], int(data.get("at", -1)), bool(data.get("carved")))
    elif name == "assembled":
        arrive = draw.assembled([layer for layer in data.get("layers") or [] if layer])
        if arrive > 0.0:
            draw.after(arrive, lambda: _popped(owner, data))
        else:
            _popped(owner, data)


def _popped(owner, data):
    """层都落完、开始沉进去、菜弹出来的那一刻：做成的两声、面粉（冰棒是霜；拌 / 摆 / 一起切开的菜不飞）和一点闪光。"""
    draw, view = owner.draw, owner.view
    if draw is None:
        return
    for sound in Sounds.soundsOf("assembled", data):
        BoardFx.play(sound, view.toWorld(draw.cx, Scene.TOP, draw.cz))
    BoardFx.finishPuff(owner.api.Geometry, int(view.yaw), view.pos, draw.cx, draw.cz, data.get("finish"), view)
    BoardFx.glintAt(view, (draw.cx, Scene.TOP + 1.0, draw.cz))


def _chopped(owner, data):
    """一刀（所有看得见板的人）：碎屑（起点和初速是操作者那边的站点像素，按他的朝向转到世界，BoardFx.chopPuffs）；最后一刀：切开的食物飘走，
    方块类不飘——削皮切出东西的，削出来的去皮原木从方块的位置升起，别的在方块中心炸开（碎屑里已经有了）。"""
    draw, view = owner.draw, owner.view
    stroke, yields = BoardFx.chopPuffs(owner.api.Geometry, view.pos, data, view)
    if not data.get("done"):
        return
    if not data.get("block"):
        draw.gone({"newItemName": data.get("item") or "", "newAuxValue": 0, "count": 1})
    elif stroke == Cutting.TOOL_STRIP and yields:
        draw.stripped({"newItemName": yields[0], "newAuxValue": 0, "count": 1})
