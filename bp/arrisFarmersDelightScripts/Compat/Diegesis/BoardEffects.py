# -*- coding: utf-8 -*-
"""BoardEffects - 站点里本人收到的服务端表现事件：声音、碎屑、撤回刀口、弹回、拿走、做成（客户端）

对应 Hands-On Delight：client/BoardBehavior.java 的 onEffect（1350-1389）和 chopped（1395-1453）。声音按 Shared/Rules/BoardSounds 的表放
（旁观的人在 BoardWatch 里按同一张表放，所以两边听到的一样）；动画在 BoardDraw，碎屑在 BoardFx。
"""
from . import BoardFx
from ...Shared.Rules import BoardDust as Dust
from ...Shared.Rules import BoardSounds as Sounds
from ...Shared.Rules.HandsOn import Assembly
from ...Shared.Rules.HandsOn import BoardScene as Scene


def onEffect(owner, name, data):
    """owner 是 BoardViewMixin：要它的 draw、cutter、view、board()、layers()。"""
    draw, view = owner.draw, owner.view
    world = view.toWorld(draw.cx, Scene.TOP, draw.cz)
    for sound in Sounds.soundsOf(name, data):
        BoardFx.play(sound, world)
    if name == "chopped":
        _chopped(owner, data)
    elif name == "refused":
        if owner.cutter.pending.refused():
            draw.refresh(owner.board(), owner.layers())
        if data.get("stack"):
            draw.bounced(data["stack"])
        BoardFx.play(Sounds.BOUNCE, world)
    elif name == "taken":
        if (data.get("stack") or {}).get("newItemName"):
            draw.taken(data["stack"], int(data.get("at", -1)), bool(data.get("carved")))
    elif name == "assembled":
        draw.assembled([layer for layer in data.get("layers") or [] if layer])
        frost = data.get("finish") == Assembly.FINISH_FREEZE
        BoardFx.puffAt(owner.api.Geometry, int(view.yaw), view.pos, Dust.flourPuff(draw.cx, draw.cz, frost), BoardFx.FROST if frost else BoardFx.FLOUR, view)
        BoardFx.flourAt(view, (draw.cx, Scene.TOP + 1.0, draw.cz))


def _chopped(owner, data):
    """一刀（所有看得见板的人）：碎屑（起点和初速是操作者那边的站点像素，按他的朝向转到世界，BoardFx.chopPuffs）；最后一刀切开的食物飘走。"""
    draw, view = owner.draw, owner.view
    BoardFx.chopPuffs(owner.api.Geometry, view.pos, data, view)
    if data.get("done"):
        draw.gone({"newItemName": data.get("item") or "", "newAuxValue": 0, "count": 1})
