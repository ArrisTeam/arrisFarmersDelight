# -*- coding: utf-8 -*-
"""BoardFinishPlay - 做成一道菜之前的收尾动画怎么演：把 BoardFinish.plan 排好的动作按时刻放到板上的层、声音和粒子上（客户端）

对应 Hands-On Delight：client/BoardBehavior.java assembled 里 then(arrive, ...) 之后的 toss / roll / skewer / knead / arrange / sandwich / shape / freeze / chopTogether
（1546-1561、1657-1961）。每一种怎么动、动多久、什么时候响什么是纯规则（Shared/Rules/HandsOn/BoardFinish*，逐条对着 Java 测过），这里只管放：
- 层动：Thing 的 Mover 走位置 / 缩放 / 转角（平躺的东西按 JE 节点的欧拉角摆，BoardThing）；夹的盖子是借来的替身（JE 的 ghost()：面包的又一份）；
- 声音经 BoardFx.play，碎屑经 BoardFx.puffAt、闪光经前置包的 view.particles（起点是离板面中心的偏移，加上板面中心 (cx, cz)）。
掉落物染不了色，JE 冻的时候把各层染成霜色（setTint(FROST)）这一步没有；夹的面包切不开（Icon.half），底座和盖子都是整块。
"""
from . import BoardFx
from ...Shared.Rules.HandsOn import BoardFinishKit as Kit
from ...Shared.Rules.HandsOn import BoardScene as Scene


def run(draw, plan, wait, lend):
    """从现在起 wait 秒（等层都落定）之后开始演 plan：每个动作排进 draw 的钟，时刻是 wait 加上它自己的。draw 是 BoardDraw.Draw；
    lend() 在第一次要用夹的盖子时借一个替身（返回 Thing），用不到的收尾不会调。"""
    stage = {}
    for cue in plan.ordered():
        delay = wait + cue[0]
        if delay > 0.0:
            draw.after(delay, lambda cue=cue: _apply(draw, stage, lend, cue))
        else:
            _apply(draw, stage, lend, cue)


def _thing(draw, stage, lend, target):
    if target != Kit.LID:
        return draw.layers[target]
    if Kit.LID not in stage:
        stage[Kit.LID] = lend()
    return stage[Kit.LID]


def _apply(draw, stage, lend, cue):
    _at, op, target, args = cue
    view = draw.view
    if op == Kit.SOUND:
        BoardFx.play(args, view.toWorld(draw.cx, Scene.TOP, draw.cz))
    elif op == Kit.DUST:
        puff, color = args
        (x, y, z), velocity, spread, count = puff
        BoardFx.puffAt(draw.geometry, int(view.yaw), view.pos, ((draw.cx + x, y, draw.cz + z), velocity, spread, count), color, view)
    elif op == Kit.GLINT:
        (x, y, z), color, count = args
        view.particles(BoardFx.GLINT, (draw.cx + x, y, draw.cz + z), color, count)
    elif op == Kit.SHOW:
        _thing(draw, stage, lend, target).show(args)
    elif op == Kit.MOVE:
        (x, y, z), seconds, hop = args
        _thing(draw, stage, lend, target).moveTo(x, y, z, seconds, hop)
    elif op == Kit.ROTATE:
        (x, y, z), seconds = args
        _thing(draw, stage, lend, target).rotateTo(x, y, z, seconds)
    elif op == Kit.SCALE:
        factor, seconds = args
        _thing(draw, stage, lend, target).scaleTo(factor, seconds)
