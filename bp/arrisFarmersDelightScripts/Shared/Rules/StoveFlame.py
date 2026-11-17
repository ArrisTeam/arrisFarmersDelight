# -*- coding: utf-8 -*-
"""StoveFlame - 点着的炉灶自己的火：火口的火星和烟、噼啪声、灶上每件东西冒的烟（双端，纯规则）

JE（FD 1.20）：
- StoveBlock.animateTick（StoveBlock.java:38-55，客户端动画刻）：点着时每次有 1/10 的概率在炉灶脚下放 block.stove.crackle（FD 的 sounds.json 把它指到原版
  block.campfire.crackle，音量音调都是 1），并且每次都在正面（FACING 那一侧，离方块中心 0.52 处）随机高度（0 ~ 6/16）、另一个水平方向 ±0.3 的地方放一颗 SMOKE 一颗 FLAME；
- StoveBlockEntity.particleTick / addSmokeParticles（StoveBlockEntity.java:19-46，客户端方块实体每刻）：灶上不空时每件东西每刻 20% 的概率在它头上
  （烤架面 y + 1，位置和 DefaultStoveRenderer 画它的一样）放 3 颗 SMOKE。Hands-On Delight 的 StoveSmokeMixin 在炉灶站点显示时取消这一个方法（animateTick 照旧）；
- 粒子离镜头超过 32 格不放（LevelRenderer.addParticleInternal 的 distanceToSqr > 1024）。
基岩版：火口的由方块 JSON 的 netease:block_animate_random_tick（trigger_rate 1，每次轮到都发 BlockAnimateRandomTickEvent）给出每次机会，灶上东西的烟由
netease:block_entity 的 client_tick（ModBlockEntityTickClientEvent，每秒 20 次）给出每刻；这里只管概率和位置，放粒子放声音在 Client/StoveFlame.py。
炉灶的正面朝哪、六个烤位在哪都是已有的规则（StoveFacing、BlockDisplay.STOVE_SLOTS），aux 怎么读成朝向只有 Placement.directionOfAux 一处。
"""
from . import StoveFacing
from .BlockDisplay import STOVE_SLOTS, isItem

BLOCK = "arris:stove"                     # 点着的炉灶；熄着的孪生方块不放（animateTick / particleTick 都只在 LIT 时）。下游的炉灶是别的模组的方块，写它们自己的 JSON
CRACKLE = "block.campfire.crackle"        # FD 的 block.stove.crackle 在 sounds.json 里就是原版营火噼啪声
FLAME = "arris:stove_flame"               # JE 的 ParticleTypes.FLAME：rp/particles/arris_stove_flame.json（原版的 basic_flame_particle 要手动发射，只 Create 不出粒子）
SMOKE = "arris:stove_smoke"               # JE 的 ParticleTypes.SMOKE：rp/particles/arris_stove_smoke.json（同上）
CRACKLE_CHANCE = 0.1                      # StoveBlock.java:43 random.nextInt(10) == 0
FRONT_REACH = 0.52                        # :50、:52 正面那一侧离方块中心多远
SIDE_SPREAD = 0.6                         # :49 random.nextDouble() * 0.6D - 0.3D：另一个水平方向 ±0.3
FRONT_HEIGHT = 6.0 / 16.0                 # :51 random.nextDouble() * 6.0D / 16.0D，从方块底算
ITEM_SMOKE_CHANCE = 0.2                   # StoveBlockEntity.java:30 nextFloat() >= 0.2F 就跳过
ITEM_SMOKE_PUFFS = 3                      # :42 每次 3 颗
ITEM_SMOKE_HEIGHT = 1.0                   # :39 worldPosition.getY() + 1.0
PARTICLE_RANGE = 32.0                     # 离镜头超过这么远（格）不放粒子


def frontOf(aux):
    """炉灶的正面朝哪：世界里的水平方向 (dx, dz)，+x 东、+z 南，各轴 -1 / 0 / 1。炉灶自己的坐标按"炉灶朝北"写，正面是北（-z），按方块的 aux 转到世界。"""
    dx, dz = StoveFacing.turnOffset(StoveFacing.yawOfAux(aux), 0.0, -1.0)
    return (int(round(dx)), int(round(dz)))


def crackleSpot(blockPos):
    """噼啪声放在哪：方块底面的中心（StoveBlock.java:40-42 的 x、y、z）。"""
    return (blockPos[0] + 0.5, float(blockPos[1]), blockPos[2] + 0.5)


def flameSpot(blockPos, aux, sideRoll, heightRoll):
    """正面那颗烟和火放在哪（StoveBlock.java:47-54）。sideRoll / heightRoll 是 [0, 1) 的随机数（JE 的两个 random.nextDouble()）：
    正面那一轴固定在 ±0.52，另一轴在 ±0.3 里，高度在方块底往上 0 ~ 6/16。"""
    front = frontOf(aux)
    side = sideRoll * SIDE_SPREAD - SIDE_SPREAD / 2.0
    x = blockPos[0] + 0.5 + (front[0] * FRONT_REACH if front[0] else side)
    z = blockPos[2] + 0.5 + (front[1] * FRONT_REACH if front[1] else side)
    return (x, blockPos[1] + heightRoll * FRONT_HEIGHT, z)


def occupiedSlots(items):
    """灶上有东西的那几格的序号（items 是 {"0".."5": 物品}，Client/BlockItems 记着的那份）。"""
    return [index for index in range(len(STOVE_SLOTS)) if isItem(items.get(str(index)))]


def itemSmokeSpot(blockPos, aux, index):
    """第 index 格上那件东西冒的烟放在哪（StoveBlockEntity.java:31-40）：烤架面 y + 1，水平位置就是它在烤架上的位置（炉灶朝哪都转到世界，
    tests/test_stove_facing.py 把 JE 那两段公式照抄下来逐格比过）。"""
    x, z = StoveFacing.turnFraction(StoveFacing.yawOfAux(aux), *STOVE_SLOTS[index])
    return (blockPos[0] + x, blockPos[1] + ITEM_SMOKE_HEIGHT, blockPos[2] + z)


def inRange(viewer, spot):
    """spot 离 viewer（玩家脚下）不超过 PARTICLE_RANGE 格。"""
    return sum((spot[axis] - viewer[axis]) ** 2 for axis in range(3)) <= PARTICLE_RANGE * PARTICLE_RANGE
