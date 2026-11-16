# -*- coding: utf-8 -*-
"""PotModel - 把厨锅场景算出来的样子推给方块实体模型：开盖、液面高度、汤色、勺子的姿态（客户端）

模型（rp/entity/cooking_pot.json）缺省是合着盖的农夫乐事原样；场景接管之后 mod_open = 1：盖子收起，液面那一层露出来。
- molang：variable.mod_open、mod_level（液面比锅底内面高多少像素，0..6.5）、mod_spoon_x/y/z 与 mod_spoon_rx/ry/rz
  （ladle 骨骼的位移和欧拉角，换算在 Shared/Rules/PotModelMath.py）、mod_spoon_lit（勺子描一圈亮边：光标在柄上、能抓）；
- 着色器（rp/shaders/glsl/arris_pot_broth_vertex.glsl / _fragment.glsl）的四组数经 SetBlockEntityExtraUniforms 给：
  1 = (r, g, b, a) 汤色与浓度，2 = (mottle 的 255 档 + edgeBoil 的小数, 汤转过的弧度, 碎料的钟, 液面比内胆中心高多少像素)，
  3 = 两个水波，每个两个数：位置（x + 128 z，各按 1/16 像素取整）和"强度的百分数 + 年龄（秒）"，
  4 = 煮好的汤里浮着的碎料的四个配料槽（碎料的钟和槽怎么打包见 Shared/Rules/PotPiecesLook.py）。
值没变就不调引擎。方块实体在本端重建之后（刚进世界、区块重载）引擎那边的值全丢了、模型回到合着盖的样子，而且不一定有
加载事件（实机：进世界十来秒后重建过一次，没有事件）：check() 隔一会儿读回 mod_open，对不上就 reset()，下一帧整份重推。
mod_food（锅里有东西）决定沸腾声归谁：有，场景自己放；空锅烧着，模型自带的水沸声照响（JE 的 CookingPotBlockMixin 同样只在有东西时才让农夫乐事的声音让位）。
"""
from ...Client.Engine import compFactory, levelId
from ...Shared.Rules import PotModelMath, PotPiecesLook

FLOOR_TOP = 2.0          # 锅底内面的高度（像素）
TANK_MIDDLE = 5.25       # 内胆（2 .. 8.5）的中心高度
EPSILON = 1.0e-3
MOTTLE_STEPS = 255.0     # mottle 取整到这么多档，edgeBoil 塞在它的小数里
WAVES = 2
WAVE_LIFE = 0.9          # 水波过了这么久就看不见了（着色器里 0.23 秒衰减到 1/e）


class PotModel(object):
    def __init__(self, pos, facing):
        self.pos = (int(pos[0]), int(pos[1]), int(pos[2]))
        self.facing = facing
        self._molang = {}
        self._uniforms = {}
        self._armed = False
        self._waves = []            # [x, z, 强度, 年龄]，最新的在后

    def reset(self):
        self._molang.clear()
        self._uniforms.clear()
        self._armed = False

    def check(self):
        """引擎那边还是我们推过的样子吗？不是（方块实体重建过）就整份重推。返回 True 表示重推了。"""
        wanted = self._molang.get("variable.mod_open")
        if wanted is None:
            return False
        actual = compFactory.CreateBlockInfo(levelId).GetBlockEntityMolangValue(self.pos, "variable.mod_open")
        if actual is not None and abs(float(actual) - wanted) < EPSILON:
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

    def _uniform(self, index, values):
        last = self._uniforms.get(index)
        if last is not None and all(abs(a - b) < EPSILON for a, b in zip(last, values)):
            return
        values = tuple(float(value) for value in values)
        if compFactory.CreateBlockInfo(levelId).SetBlockEntityExtraUniforms(self.pos, index, values):
            self._uniforms[index] = values

    def open(self, opened):
        self._set("variable.mod_open", 1.0 if opened else 0.0)

    def food(self, has):
        """锅里有没有东西：有，场景放沸腾声、模型自带的农夫乐事那条让位；没有（空锅烧着），模型自带的水沸声照响（rp/entity 的 boil_water）。"""
        self._set("variable.mod_food", 1.0 if has else 0.0)

    def liquid(self, surface, color, mottle, turned, edgeBoil, pieces=0.0):
        """surface：液面高度（像素，锅自己的坐标）；color：(r, g, b, a) 各 0..1（JE LiquidLook 的 ARGB）；turned：弧度；
        pieces：碎料的钟（PiecesClock.packed()）。"""
        self._set("variable.mod_level", surface - FLOOR_TOP)
        self._uniform(1, color)
        mottled = float(int(max(0.0, min(1.0, mottle)) * MOTTLE_STEPS + 0.5)) + max(0.0, min(0.99, edgeBoil))
        self._uniform(2, (mottled, turned % PotPiecesLook.TURN_WRAP, pieces, surface - TANK_MIDDLE))

    def slots(self, slots):
        """汤里的碎料是哪几种配料切的（PotPiecesLook.dishSlots 的四个数）。"""
        self._uniform(4, slots)

    def ladle(self, tip, turn=PotModelMath.IDENTITY):
        """tip：勺子下端在锅自己坐标里的位置（像素）；turn：相对靠着的样子又转了多少（3×3）。"""
        position, rotation = PotModelMath.ladleBone(tip, turn)
        for axis, value in zip("xyz", position):
            self._set("variable.mod_spoon_" + axis, value)
        for axis, value in zip("xyz", rotation):
            self._set("variable.mod_spoon_r" + axis, value)

    def glow(self, lit, pot=False):
        """勺子 / 锅身描不描亮边（Diegesis 的 hover outline：光标下能用的东西描出轮廓；这里是 ladle_glow / pot_glow 骨骼，
        比本体大 0.08 像素的一层只画反面的壳）。"""
        self._set("variable.mod_spoon_lit", 1.0 if lit else 0.0)
        self._set("variable.mod_pot_lit", 1.0 if pot else 0.0)

    def ripple(self, x, z, strength):
        """液面上 (x, z)（锅自己的坐标，像素）起一个水波，strength 是 JE 的水波高度（0.09 .. 0.5）。"""
        self._waves.append([x, z, min(1.0, strength), 0.0])
        del self._waves[:-WAVES]

    def waves(self, dt):
        """每帧：水波变老，打包推给着色器；都散了之后推一次全空的就不再推。"""
        for wave in self._waves:
            wave[3] += dt
        self._waves = [wave for wave in self._waves if wave[3] < WAVE_LIFE]
        packed = []
        for index in range(WAVES):
            if index < len(self._waves):
                x, z, strength, age = self._waves[index]
                cellX = max(0, min(127, int((x - 4.0) * 16.0)))
                cellZ = max(0, min(127, int((z - 4.0) * 16.0)))
                packed += [float(cellX + 128 * cellZ), float(int(strength * 100.0 + 0.5)) + min(age, 0.999)]
            else:
                packed += [0.0, 0.0]
        self._uniform(3, packed)

