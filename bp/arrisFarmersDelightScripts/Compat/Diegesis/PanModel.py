# -*- coding: utf-8 -*-
"""PanModel - 把煎锅场景算出来的样子推给方块实体模型：锅被颠时整只锅转着挪着、锅柄描边、锅底的油膜（客户端）

模型（rp/entity/skillet.json，几何 rp/models/entity/skillet.geo.json）缺省是 FD 原来的样子；场景接管之后给 molang 变量：
- mod_pan_rx / mod_pan_y / mod_pan_z：pan 骨骼（枢轴在锅心，带着锅身、锅柄和油膜）的转角（度）和位移（像素），换算在 Shared/Rules/PanModelMath；
- mod_handle_lit：锅柄描一圈亮边（Diegesis 的 hover outline：光标放上去、或食物等着翻面时；和厨锅的勺子同一个做法，handle_glow 骨骼的一层反面壳）；
- mod_oil_a（油的透明度 0..1）和 mod_oil_x0.. / mod_oil_z0.. / mod_oil_s0..（最多四摊：位置、大小，0 = 没有）：锅底每块食物下面的油膜；
- mod_scene：场景接管了（缺省 0）：check() 隔一会儿读回它，对不上就整份重推。
值没变就不调引擎。方块实体在本端重建之后（刚进世界、区块重载）引擎那边的值全丢了，而且不一定有加载事件（见厨锅 PotModel 的实机记录）。
"""
from ...Client.Engine import compFactory, levelId
from ...Shared.Rules import PanModelMath

EPSILON = 1.0e-3
PUDDLES = 4
MOST_ALPHA = 0.9      # 油膜最浓时的透明度（JE 的 alpha = 255 * amount * 光；方片本身的图带透明）


class PanModel(object):
    def __init__(self, pos):
        self.pos = (int(pos[0]), int(pos[1]), int(pos[2]))
        self._molang = {}
        self._armed = False

    def reset(self):
        self._molang.clear()
        self._armed = False

    def check(self):
        """引擎那边还是我们推过的样子吗？不是（方块实体重建过）就整份重推。返回 True 表示重推了。"""
        if "variable.mod_scene" not in self._molang:
            return False
        actual = compFactory.CreateBlockInfo(levelId).GetBlockEntityMolangValue(self.pos, "variable.mod_scene")
        if actual is not None and abs(float(actual) - self._molang["variable.mod_scene"]) < EPSILON:
            return False
        self.reset()
        return True

    def _set(self, name, value):
        last = self._molang.get(name)
        if last is not None and abs(last - value) < EPSILON:
            return
        blockInfo = compFactory.CreateBlockInfo(levelId)
        if not self._armed:
            blockInfo.SetEnableBlockEntityAnimations(self.pos, True)
            self._armed = True
        if blockInfo.SetBlockEntityMolangValue(self.pos, name, float(value)):
            self._molang[name] = value

    def scene(self, on):
        self._set("variable.mod_scene", 1.0 if on else 0.0)

    def pan(self, tilt, offset):
        """锅绕 x 转 tilt 度、位移 offset = (ox, oy, oz) 像素（场景坐标里相对原位）。"""
        position, rotation = PanModelMath.panBone(tilt, offset)
        self._set("variable.mod_pan_rx", rotation[0])
        self._set("variable.mod_pan_y", position[1])
        self._set("variable.mod_pan_z", position[2])

    def glow(self, lit):
        self._set("variable.mod_handle_lit", 1.0 if lit else 0.0)

    def oil(self, puddles):
        """puddles 是 PanOil.puddles() 的结果（场景坐标里离锅心的 x、z、半边长 half、透明度 0..255）；没有的几摊收起来（大小 0）。"""
        alpha = max([p["alpha"] for p in puddles] or [0]) / 255.0
        self._set("variable.mod_oil_a", min(1.0, alpha) * MOST_ALPHA)
        for index in range(PUDDLES):
            if index < len(puddles):
                puddle = puddles[index]
                position = PanModelMath.oilBone(puddle["x"], puddle["z"])
                self._set("variable.mod_oil_x%d" % index, position[0])
                self._set("variable.mod_oil_z%d" % index, position[2])
                self._set("variable.mod_oil_s%d" % index, puddle["half"])
            else:
                self._set("variable.mod_oil_s%d" % index, 0.0)
