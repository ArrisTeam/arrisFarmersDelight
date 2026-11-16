# -*- coding: utf-8 -*-
"""BoardGlow - 砧板描一圈亮边：本人手上的东西放得上板的时候（客户端）

和厨锅的勺子、锅身同一个做法：方块实体模型（rp/models/entity/cutting_board.geo.json）里比板大 0.08 像素、只画反面的一层壳
（board_glow 骨骼，材质 arris_pot_glow），由 variable.mod_board_lit 开关。JE 的砧板场景关着描边（hover_outline: false），
这一圈是照厨锅的 pot.setOutlined(offering) 给砧板补的提示：手上这叠服务端会收（BoardPlace 的判定树）、光标在板上。
方块实体在本端重建后（进世界十来秒、区块重载）变量会丢，亮着的时候隔一会儿重推一次。
"""
from ...Client.Engine import compFactory, levelId
from ...Shared.Rules.HandsOn import BoardPlace

REPUSH = 0.5


def placeable(env, hand, board, layers):
    """手上这叠放得上板吗：服务端的 place 会收下至少一个（工具、板不收的东西都不算）。"""
    return hand is not None and BoardPlace.place(hand, board, layers, False, True, env).moved > 0


class BoardGlow(object):
    def __init__(self, pos):
        self.pos = (int(pos[0]), int(pos[1]), int(pos[2]))
        self.lit = None
        self.clock = 0.0

    def frame(self, dt, lit):
        lit = bool(lit)
        self.clock += dt
        if lit == self.lit and not (lit and self.clock >= REPUSH):
            return
        blockInfo = compFactory.CreateBlockInfo(levelId)
        if self.lit is None:
            blockInfo.SetEnableBlockEntityAnimations(self.pos, True)
        if blockInfo.SetBlockEntityMolangValue(self.pos, "variable.mod_board_lit", 1.0 if lit else 0.0):
            self.lit, self.clock = lit, 0.0
