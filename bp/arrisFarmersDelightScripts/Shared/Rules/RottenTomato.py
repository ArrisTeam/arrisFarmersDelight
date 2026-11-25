# -*- coding: utf-8 -*-
"""RottenTomato - 烂番茄扔出去、砸中东西的声音（双端，纯规则）

照 JE 的 RottenTomatoItem.use / RottenTomatoEntity（FD 1.3.4）：
- 扔：entity.rotten_tomato.throw 指向原版 entity.snowball.throw（JE 的采样是 random/bow，基岩同一个采样的声音叫 random.bow），
  音量 0.5，音调 0.4 / (random × 0.4 + 0.8)，在玩家脚下放；
- 砸中：entity.rotten_tomato.hit 指向原版 entity.slime.attack（基岩 mob.slime.attack），音量 1，音调 (random − random) × 0.2 + 1；
  onHitEntity 放一声、onHit 又放一声，所以砸中实体是两声，砸中方块一声。
飞多快、往下掉多快照基岩原版雪球（entities/rotten_tomato.json：power 1.5、gravity 0.03；JE 也是 shootFromRotation(..., 1.5F, 1.0F)、
ThrowableProjectile 的重力 0.03）。
"""
ITEM = "arris:rotten_tomato"
THROW_SOUND = "random.bow"
THROW_VOLUME = 0.5
HIT_SOUND = "mob.slime.attack"
HIT_VOLUME = 1.0


def throwPitch(r):
    """r 是 [0, 1) 的随机数。"""
    return 0.4 / (r * 0.4 + 0.8)


def hitPitch(r1, r2):
    return (r1 - r2) * 0.2 + 1.0


def hitSounds(hitTargetType):
    """砸中一次放几声：引擎的 hitTargetType 是 "ENTITY" 时两声（onHitEntity + onHit），别的（"BLOCK"）一声。"""
    return 2 if hitTargetType == "ENTITY" else 1
