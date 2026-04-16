# -*- coding: utf-8 -*-
class Events:
    ''' 服务端事件类 '''
    class InventoryItemChangedServerEvent:
        ''' 玩家背包物品变化时服务端抛出的事件。 '''
        def __init__(self, dic):
            self.playerId = dic.get("playerId")  # type: str
            ''' 玩家实体id '''
            self.slot = dic.get("slot")  # type: int
            ''' 背包槽位 '''
            self.oldItemDict = dic.get("oldItemDict")  # type: dict
            ''' 变化前槽位中的物品，格式参考物品信息字典 '''
            self.newItemDict = dic.get("newItemDict")  # type: dict
            ''' 变化后槽位中的物品，格式参考物品信息字典 '''

    class OnStandOnBlockServerEvent:
        ''' 触发时机：当实体站立到方块上时服务端持续触发'''
        def __init__(self, dic):
            self.entityId = dic.get("entityId")  # type: str
            ''' 实体id '''
            self.dimensionId = dic.get("dimensionId")  # type: int
            ''' 实体所在维度id '''
            self.posX = dic.get("posX")  # type: float
            ''' 实体位置x '''
            self.posY = dic.get("posY")  # type: float
            ''' 实体位置y '''
            self.posZ = dic.get("posZ")  # type: float
            ''' 实体位置z '''
            self.motionX = dic.get("motionX")  # type: float
            ''' 瞬时移动X方向的力 '''
            self.motionY = dic.get("motionY")  # type: float
            ''' 瞬时移动Y方向的力 '''
            self.motionZ = dic.get("motionZ")  # type: float
            ''' 瞬时移动Z方向的力 '''
            self.blockX = dic.get("blockX")  # type: int
            ''' 方块位置x '''
            self.blockY = dic.get("blockY")  # type: int
            ''' 方块位置y '''
            self.blockZ = dic.get("blockZ")  # type: int
            ''' 方块位置z '''
            self.blockName = dic.get("blockName")  # type: str
            ''' 方块的identifier，包含命名空间及名称 '''
            self.cancel = dic.get("cancel")  # type: bool
            ''' 可由脚本层回传True给引擎，阻止触发后续原版逻辑 '''

    class BlockNeighborChangedServerEvent:
        ''' 触发时机：自定义方块周围的方块发生变化时，需要配置netease:neighborchanged_sendto_script，详情请查阅《自定义农作物》文档 '''
        def __init__(self, dic):
            self.dimensionId = dic.get("dimensionId")  # type: int
            ''' 维度 '''
            self.posX = dic.get("posX")  # type: int
            ''' 方块x坐标 '''
            self.posY = dic.get("posY")  # type: int
            ''' 方块y坐标 '''
            self.posZ = dic.get("posZ")  # type: int
            ''' 方块z坐标 '''
            self.blockName = dic.get("blockName")  # type: str
            ''' 方块的identifier，包含命名空间及名称 '''
            self.auxValue = dic.get("auxValue")  # type: int
            ''' 方块附加值 '''
            self.neighborPosX = dic.get("neighborPosX")  # type: int
            ''' 变化方块x坐标 '''
            self.neighborPosY = dic.get("neighborPosY")  # type: int
            ''' 变化方块y坐标 '''
            self.neighborPosZ = dic.get("neighborPosZ")  # type: int
            ''' 变化方块z坐标 '''
            self.fromBlockName = dic.get("fromBlockName")  # type: str
            ''' 方块变化前的identifier，包含命名空间及名称 '''
            self.fromAuxValue = dic.get("fromAuxValue")  # type: int
            ''' 方块变化前附加值 '''
            self.toBlockName = dic.get("toBlockName")  # type: str
            ''' 方块变化后的identifier，包含命名空间及名称 '''
            self.toAuxValue = dic.get("toAuxValue")  # type: int
            ''' 方块变化后附加值 '''

    class BlockRandomTickServerEvent:
        ''' 触发时机：自定义方块随机tick '''
        def __init__(self, dic):
            self.posX = dic.get("posX")  # type: int
            ''' 方块x坐标 '''
            self.posY = dic.get("posY")  # type: int
            ''' 方块y坐标 '''
            self.posZ = dic.get("posZ")  # type: int
            ''' 方块z坐标 '''
            self.blockName = dic.get("blockName")  # type: str
            ''' 方块名称 '''
            self.fullName = dic.get("fullName")  # type: str
            ''' 方块的identifier，包含命名空间及名称 '''
            self.auxValue = dic.get("auxValue")  # type: int
            ''' 方块附加值 '''
            self.dimensionId = dic.get("dimensionId")  # type: int
            ''' 实体维度 '''

    class BlockStrengthChangedServerEvent:
        ''' 触发时机：自定义机械元件方块红石信号量发生变化时触发 '''
        def __init__(self, dic):
            self.posX = dic.get("posX")  # type: int
            ''' 方块x坐标 '''
            self.posY = dic.get("posY")  # type: int
            ''' 方块y坐标 '''
            self.posZ = dic.get("posZ")  # type: int
            ''' 方块z坐标 '''
            self.blockName = dic.get("blockName")  # type: str
            ''' 方块的identifier，包含命名空间及名称 '''
            self.auxValue = dic.get("auxValue")  # type: int
            ''' 方块附加值 '''
            self.newStrength = dic.get("newStrength")  # type: int
            ''' 变化后的红石信号量 '''
            self.dimensionId = dic.get("dimensionId")  # type: int
            ''' 维度 '''

    class ChestBlockTryPairWithServerEvent:
        ''' 触发时机：两个并排的小箱子方块准备组合为一个大箱子方块时 '''
        def __init__(self, dic):
            self.cancel = dic.get("cancel")  # type: bool
            ''' 是否允许触发，默认为False，若设为True，可阻止小箱子组合成为一个大箱子 '''
            self.blockX = dic.get("blockX")  # type: int
            ''' 小箱子方块x坐标 '''
            self.blockY = dic.get("blockY")  # type: int
            ''' 小箱子方块y坐标 '''
            self.blockZ = dic.get("blockZ")  # type: int
            ''' 小箱子方块z坐标 '''
            self.otherBlockX = dic.get("otherBlockX")  # type: int
            ''' 将要与之组合的另外一个小箱子方块x坐标 '''
            self.otherBlockY = dic.get("otherBlockY")  # type: int
            ''' 将要与之组合的另外一个小箱子方块y坐标 '''
            self.otherBlockZ = dic.get("otherBlockZ")  # type: int
            ''' 将要与之组合的另外一个小箱子方块z坐标 '''
            self.dimensionId = dic.get("dimensionId")  # type: int
            ''' 维度id '''

    class DestroyBlockEvent:
        ''' 触发时机：当方块已经被玩家破坏时触发该事件。 '''
        def __init__(self, dic):
            self.x = dic.get("x")  # type: int
            ''' 方块x坐标 '''
            self.y = dic.get("y")  # type: int
            ''' 方块y坐标 '''
            self.z = dic.get("z")  # type: int
            ''' 方块z坐标 '''
            self.face = dic.get("face")  # type: int
            ''' 方块被敲击的面向id，参考Facing '''
            self.fullName = dic.get("fullName")  # type: str
            ''' 方块的identifier，包含命名空间及名称 '''
            self.auxData = dic.get("auxData")  # type: int
            ''' 方块附加值 '''
            self.playerId = dic.get("playerId")  # type: str
            ''' 破坏方块的玩家ID '''
            self.dimensionId = dic.get("dimensionId")  # type: int
            ''' 维度id '''

    class EntityPlaceBlockAfterServerEvent:
        ''' 触发时机：当生物成功放置方块后触发 '''
        def __init__(self, dic):
            self.x = dic.get("x")  # type: int
            ''' 方块x坐标 '''
            self.y = dic.get("y")  # type: int
            ''' 方块y坐标 '''
            self.z = dic.get("z")  # type: int
            ''' 方块z坐标 '''
            self.fullName = dic.get("fullName")  # type: str
            ''' 方块的identifier，包含命名空间及名称 '''
            self.auxData = dic.get("auxData")  # type: int
            ''' 方块附加值 '''
            self.entityId = dic.get("entityId")  # type: str
            ''' 试图放置方块的生物ID '''
            self.dimensionId = dic.get("dimensionId")  # type: int
            ''' 维度id '''
            self.face = dic.get("face")  # type: int
            ''' 点击方块的面，参考Facing '''

    class HopperTryPullInServerEvent:
        ''' 触发时机：漏斗放在容器下方，放置成功时触发事件 '''
        def __init__(self, dic):
            self.x = dic.get("x")  # type: int
            ''' 漏斗位置x '''
            self.y = dic.get("y")  # type: int
            ''' 漏斗位置y '''
            self.z = dic.get("z")  # type: int
            ''' 漏斗位置z '''
            self.abovePosX = dic.get("abovePosX")  # type: int
            ''' 交互的容器位置x '''
            self.abovePosY = dic.get("abovePosY")  # type: int
            ''' 交互的容器位置y '''
            self.abovePosZ = dic.get("abovePosZ")  # type: int
            ''' 交互的容器位置z '''
            self.dimensionId = dic.get("dimensionId")  # type: int
            ''' 维度id '''
            self.canHopper = dic.get("canHopper")  # type: int
            ''' 是否允许容器往漏斗加东西(要关闭此交互，需先监听此事件再放置容器) '''

    class HopperTryPullOutServerEvent:
        ''' 触发时机：漏斗放在容器旁边，放置成功时触发事件 '''
        def __init__(self, dic):
            self.x = dic.get("x")  # type: int
            ''' 漏斗位置x '''
            self.y = dic.get("y")  # type: int
            ''' 漏斗位置y '''
            self.z = dic.get("z")  # type: int
            ''' 漏斗位置z '''
            self.attachedPosX = dic.get("attachedPosX")  # type: int
            ''' 交互的容器位置x '''
            self.attachedPosY = dic.get("attachedPosY")  # type: int
            ''' 交互的容器位置y '''
            self.attachedPosZ = dic.get("attachedPosZ")  # type: int
            ''' 交互的容器位置z '''
            self.dimensionId = dic.get("dimensionId")  # type: int
            ''' 维度id '''
            self.canHopper = dic.get("canHopper")  # type: int
            ''' 是否允许漏斗往容器加东西(要关闭此交互，需先监听此事件再放置容器) '''

    class PistonActionServerEvent:
        ''' 触发时机：活塞或者粘性活塞推送/缩回影响附近方块时 '''
        def __init__(self, dic):
            self.cancel = dic.get("cancel")  # type: bool
            ''' 是否允许触发，默认为False，若设为True，可阻止触发后续的事件 '''
            self.action = dic.get("action")  # type: str
            ''' 推送时=expanding；缩回时=retracting '''
            self.pistonFacing = dic.get("pistonFacing")  # type: int
            ''' 活塞的朝向，参考Facing '''
            self.pistonMoveFacing = dic.get("pistonMoveFacing")  # type: int
            ''' 活塞的运动方向，参考Facing '''
            self.dimensionId = dic.get("dimensionId")  # type: int
            ''' 活塞方块所在的维度 '''
            self.pistonX = dic.get("pistonX")  # type: int
            ''' 活塞方块的x坐标 '''
            self.pistonY = dic.get("pistonY")  # type: int
            ''' 活塞方块的y坐标 '''
            self.pistonZ = dic.get("pistonZ")  # type: int
            ''' 活塞方块的z坐标 '''
            self.blockList = dic.get("blockList")  # type: list
            ''' 活塞运动影响到产生被移动效果的方块坐标(x,y,z)，均为int类型 '''
            self.breakBlockList = dic.get("breakBlockList")  # type: list
            ''' 活塞运动影响到产生被破坏效果的方块坐标(x,y,z)，均为int类型 '''
            self.entityList = dic.get("entityList")  # type: list
            ''' 活塞运动影响到产生被移动或被破坏效果的实体的ID列表 '''

    class ServerBlockEntityTickEvent:
        ''' 触发时机：自定义方块配置了netease:block_entity组件并设tick为true，玩家进入该方块的tick范围时触发 '''
        def __init__(self, dic):
            self.blockName = dic.get("blockName")  # type: str
            ''' 该方块名称 '''
            self.dimension = dic.get("dimension")  # type: int
            ''' 该方块所在的维度 '''
            self.posX = dic.get("posX")  # type: int
            ''' 该方块的x坐标 '''
            self.posY = dic.get("posY")  # type: int
            ''' 该方块的y坐标 '''
            self.posZ = dic.get("posZ")  # type: int
            ''' 该方块的z坐标 '''

    class ServerBlockUseEvent:
        ''' 触发时机：玩家右键点击新版自定义方块（或者通过接口AddBlockItemListenForUseEvent增加监听的MC原生游戏方块）时服务端抛出该事件（该事件tick执行，需要注意效率问题）。 '''
        def __init__(self, dic):
            self.playerId = dic.get("playerId")  # type: str
            ''' 玩家Id '''
            self.blockName = dic.get("blockName")  # type: str
            ''' 方块的identifier，包含命名空间及名称 '''
            self.aux = dic.get("aux")  # type: int
            ''' 方块附加值 '''
            self.cancel = dic.get("cancel")  # type: bool
            ''' 设置为True可拦截与方块交互的逻辑。 '''
            self.x = dic.get("x")  # type: int
            ''' 方块x坐标 '''
            self.y = dic.get("y")  # type: int
            ''' 方块y坐标 '''
            self.z = dic.get("z")  # type: int
            ''' 方块z坐标 '''
            self.dimensionId = dic.get("dimensionId")  # type: int
            ''' 维度id '''

    class ServerEntityTryPlaceBlockEvent:
        ''' 触发时机：当生物试图放置方块时触发该事件。 '''
        def __init__(self, dic):
            self.x = dic.get("x")  # type: int
            ''' 方块x坐标 '''
            self.y = dic.get("y")  # type: int
            ''' 方块y坐标 '''
            self.z = dic.get("z")  # type: int
            ''' 方块z坐标 '''
            self.fullName = dic.get("fullName")  # type: str
            ''' 方块的identifier，包含命名空间及名称 '''
            self.auxData = dic.get("auxData")  # type: int
            ''' 方块附加值 '''
            self.entityId = dic.get("entityId")  # type: str
            ''' 试图放置方块的生物ID '''
            self.dimensionId = dic.get("dimensionId")  # type: int
            ''' 维度id '''
            self.face = dic.get("face")  # type: int
            ''' 点击方块的面，参考Facing '''
            self.cancel = dic.get("cancel")  # type: bool
            ''' 默认为False，在脚本层设置为True就能取消该方块的放置 '''

    class ServerExplosionBlockEvent:
        ''' 游戏内爆炸发生时方块爆炸事件 '''
        def __init__(self, dic):
            self.entityId = dic.get("entityId")  # type: str
            ''' 爆炸源头的生物唯一ID，找不到是可能为-1 '''
            self.data = dic.get("data")  # type: list
            ''' 爆炸涉及到的方块坐标(x,y,z)，cancel是一个bool值 '''

    class ServerPlaceBlockEntityEvent:
        ''' 触发时机：手动放置或通过接口创建含自定义方块实体的方块时触发，此时可向该方块实体中存放数据 '''
        def __init__(self, dic):
            self.blockName = dic.get("blockName")  # type: str
            ''' 该方块名称 '''
            self.dimension = dic.get("dimension")  # type: int
            ''' 该方块所在的维度 '''
            self.posX = dic.get("posX")  # type: int
            ''' 该方块的x坐标 '''
            self.posY = dic.get("posY")  # type: int
            ''' 该方块的y坐标 '''
            self.posZ = dic.get("posZ")  # type: int
            ''' 该方块的z坐标 '''

    class ServerPlayerTryDestroyBlockEvent:
        ''' 当玩家即将破坏方块时，服务端线程触发该事件。 '''
        def __init__(self, dic):
            self.x = dic.get("x")  # type: int
            ''' 方块x坐标 '''
            self.y = dic.get("y")  # type: int
            ''' 方块y坐标 '''
            self.z = dic.get("z")  # type: int
            ''' 方块z坐标 '''
            self.face = dic.get("face")  # type: int
            ''' 方块被敲击的面向id，参考Facing '''
            self.fullName = dic.get("fullName")  # type: str
            ''' 方块的identifier，包含命名空间及名称 '''
            self.auxData = dic.get("auxData")  # type: int
            ''' 方块附加值 '''
            self.playerId = dic.get("playerId")  # type: str
            ''' 试图破坏方块的玩家ID '''
            self.dimensionId = dic.get("dimensionId")  # type: int
            ''' 维度id '''
            self.cancel = dic.get("cancel")  # type: bool
            ''' 默认为False，在脚本层设置为True就能取消该方块的破坏 '''
            self.spawnResources = dic.get("spawnResources")  # type: bool
            ''' 是否生成掉落物，默认为True，在脚本层设置为False就能取消生成掉落物 '''

    class ServerPostBlockPatternEvent:
        ''' 触发时机：用方块组合生成生物，生成生物之后触发该事件。 '''
        def __init__(self, dic):
            self.entityId = dic.get("entityId")  # type: str
            ''' 生成生物的id '''
            self.entityGenerated = dic.get("entityGenerated")  # type: str
            ''' 生成生物的名字，如"minecraft:pig" '''
            self.x = dic.get("x")  # type: int
            ''' 方块x坐标 '''
            self.y = dic.get("y")  # type: int
            ''' 方块y坐标 '''
            self.z = dic.get("z")  # type: int
            ''' 方块z坐标 '''
            self.dimensionId = dic.get("dimensionId")  # type: int
            ''' 维度id '''

    class ServerPreBlockPatternEvent:
        ''' 触发时机：用方块组合生成生物，在放置最后一个组成方块时触发该事件。 '''
        def __init__(self, dic):
            self.enable = dic.get("enable")  # type: bool
            ''' 是否允许继续生成。若设为False，可阻止生成生物 '''
            self.x = dic.get("x")  # type: int
            ''' 方块x坐标 '''
            self.y = dic.get("y")  # type: int
            ''' 方块y坐标 '''
            self.z = dic.get("z")  # type: int
            ''' 方块z坐标 '''
            self.dimensionId = dic.get("dimensionId")  # type: int
            ''' 维度id '''
            self.entityWillBeGenerated = dic.get("entityWillBeGenerated")  # type: str
            ''' 即将生成生物的名字，如"minecraft:pig" '''

    class StepOnBlockServerEvent:
        ''' 触发时机：生物脚踩压力板、踩红石矿、踩拌线钩。 '''
        def __init__(self, dic):
            self.cancel = dic.get("cancel")  # type: bool
            ''' 是否允许触发，默认为False，若设为True，可阻止触发后续物理交互事件 '''
            self.blockX = dic.get("blockX")  # type: int
            ''' 方块x坐标 '''
            self.blockY = dic.get("blockY")  # type: int
            ''' 方块y坐标 '''
            self.blockZ = dic.get("blockZ")  # type: int
            ''' 方块z坐标 '''
            self.entityId = dic.get("entityId")  # type: str
            ''' 触发的entity的唯一ID '''
            self.blockName = dic.get("blockName")  # type: str
            ''' 方块的identifier，包含命名空间及名称 '''
            self.dimensionId = dic.get("dimensionId")  # type: int
            ''' 维度id '''

    class ProjectileCritHitEvent:
        ''' 触发时机：当抛射物与头部碰撞时触发该事件。注：需调用OpenPlayerCritBox开启玩家暴头后才能触发。 '''
        def __init__(self, dic):
            self.id = dic.get("id")  # type: str
            ''' 子弹id '''
            self.targetId = dic.get("targetId")  # type: str
            ''' 碰撞目标id '''

    class ProjectileDoHitEffectEvent:
        ''' 触发时机：当抛射物碰撞时触发该事件 '''
        def __init__(self, dic):
            self.id = dic.get("id")  # type: str
            ''' 子弹id '''
            self.hitTargetType = dic.get("hitTargetType")  # type: str
            ''' 碰撞目标类型,'ENTITY'或是'BLOCK' '''
            self.targetId = dic.get("targetId")  # type: str
            ''' 碰撞目标id '''
            self.hitFace = dic.get("hitFace")  # type: int
            ''' 撞击在方块上的面id，参考Facing '''
            self.x = dic.get("x")  # type: float
            ''' 碰撞x坐标 '''
            self.y = dic.get("y")  # type: float
            ''' 碰撞y坐标 '''
            self.z = dic.get("z")  # type: float
            ''' 碰撞z坐标 '''
            self.blockPosX = dic.get("blockPosX")  # type: int
            ''' 碰撞是方块时，方块x坐标 '''
            self.blockPosY = dic.get("blockPosY")  # type: int
            ''' 碰撞是方块时，方块y坐标 '''
            self.blockPosZ = dic.get("blockPosZ")  # type: int
            ''' 碰撞是方块时，方块z坐标 '''
            self.srcId = dic.get("srcId")  # type: str
            ''' 创建者id '''

    class SpawnProjectileServerEvent:
        ''' 触发时机：抛射物生成时触发 '''
        def __init__(self, dic):
            self.projectileId = dic.get("projectileId")  # type: str
            ''' 抛射物的实体id '''
            self.projectileIdentifier = dic.get("projectileIdentifier")  # type: str
            ''' 抛射物的identifier '''
            self.spawnerId = dic.get("spawnerId")  # type: str
            ''' 发射者的实体id，没有发射者时为-1 '''

    class ChunkAcquireDiscardedServerEvent:
        ''' 触发时机：通过AddChunkPosWhiteList接口添加监听的服务端区块即将被卸载时 '''
        def __init__(self, dic):
            self.dimension = dic.get("dimension")  # type: int
            ''' 区块所在维度 '''
            self.chunkPosX = dic.get("chunkPosX")  # type: int
            ''' 区块的x坐标，对应方块X坐标区间为[x * 16, x * 16 + 15] '''
            self.chunkPosZ = dic.get("chunkPosZ")  # type: int
            ''' 区块的z坐标，对应方块Z坐标区间为[z * 16, z * 16 + 15] '''

    class ChunkGeneratedServerEvent:
        ''' 触发时机：区块创建完成时触发 '''
        def __init__(self, dic):
            self.dimension = dic.get("dimension")  # type: int
            ''' 该区块所在的维度 '''
            self.blockEntityData = dic.get("blockEntityData")  # type: object
            ''' 该区块中的自定义方块实体列表，通常是由自定义特征生成的自定义方块，没有自定义方块实体时该值为None '''

    class ChunkLoadedServerEvent:
        ''' 触发时机：通过AddChunkPosWhiteList接口添加监听的服务端区块加载完成时 '''
        def __init__(self, dic):
            self.dimension = dic.get("dimension")  # type: int
            ''' 区块所在维度 '''
            self.chunkPosX = dic.get("chunkPosX")  # type: int
            ''' 区块的x坐标，对应方块X坐标区间为[x * 16, x * 16 + 15] '''
            self.chunkPosZ = dic.get("chunkPosZ")  # type: int
            ''' 区块的z坐标，对应方块Z坐标区间为[z * 16, z * 16 + 15] '''

    class ExplosionServerEvent:
        ''' 当发生爆炸时触发。 '''
        def __init__(self, dic):
            self.blocks = dic.get("blocks")  # type: list
            ''' 爆炸涉及到的方块坐标(x,y,z)，cancel是一个bool值 '''
            self.victims = dic.get("victims")  # type: list|None
            ''' 受伤实体id列表，当该爆炸创建者id为None时，victims也为None '''
            self.sourceId = dic.get("sourceId")  # type: str|None
            ''' 爆炸创建者id '''
            self.explodePos = dic.get("explodePos")  # type: list
            ''' 爆炸位置[x,y,z] '''
            self.dimensionId = dic.get("dimensionId")  # type: int
            ''' 维度id '''

    class GameTypeChangedServerEvent:
        ''' 个人游戏模式发生变化时服务端触发。 '''
        def __init__(self, dic):
            self.playerId = dic.get("playerId")  # type: str
            ''' 玩家Id，SetDefaultGameType接口改变游戏模式时该参数为空字符串 '''
            self.oldGameType = dic.get("oldGameType")  # type: int
            ''' 切换前的游戏模式 '''
            self.newGameType = dic.get("newGameType")  # type: int
            ''' 切换后的游戏模式 '''

    class LoadServerAddonScriptsAfter:
        ''' 服务器加载完mod时触发 '''
        def __init__(self, dic):
            pass

    class OnCommandOutputServerEvent:
        ''' Command命令执行成功事件 '''
        def __init__(self, dic):
            self.command = dic.get("command")  # type: str
            ''' 命令名称 '''
            self.message = dic.get("message")  # type: str
            ''' 命令返回的消息 '''

    class OnScriptTickServer:
        ''' 服务器tick时触发,1秒有30个tick '''
        def __init__(self, dic):
            pass

    class PlaceNeteaseStructureFeatureEvent:
        ''' 触发时机：首次生成地形时，结构特征即将生成时服务端抛出该事件。 '''
        def __init__(self, dic):
            self.structureName = dic.get("structureName")  # type: str
            ''' 结构名称 '''
            self.x = dic.get("x")  # type: int
            ''' 结构坐标最小方块所在的x坐标 '''
            self.y = dic.get("y")  # type: int
            ''' 结构坐标最小方块所在的y坐标 '''
            self.z = dic.get("z")  # type: int
            ''' 结构坐标最小方块所在的z坐标 '''
            self.biomeType = dic.get("biomeType")  # type: int
            ''' 该feature所放置区块的生物群系类型 '''
            self.biomeName = dic.get("biomeName")  # type: str
            ''' 该feature所放置区块的生物群系名称 '''
            self.dimensionId = dic.get("dimensionId")  # type: int
            ''' 维度id '''
            self.cancel = dic.get("cancel")  # type: bool
            ''' 设置为True时可阻止该结构的放置 '''

    class ActorHurtServerEvent:
        ''' 触发时机：生物（包括玩家）受伤时触发 '''
        def __init__(self, dic):
            self.entityId = dic.get("entityId")  # type: str
            ''' 生物Id '''
            self.cause = dic.get("cause")  # type: str
            ''' 伤害来源，详见Minecraft枚举值文档的ActorDamageCause '''
            self.damage = dic.get("damage")  # type: int
            ''' 伤害值 '''
            self.absorbedDamage = dic.get("absorbedDamage")  # type: int
            ''' 吸收的伤害值（原始伤害减去damage） '''

    class ActuallyHurtServerEvent:
        ''' 实体实际受到伤害时触发，相比于DamageEvent，该伤害为经过护甲及buff计算后，实际的扣血量 '''
        def __init__(self, dic):
            self.srcId = dic.get("srcId")  # type: str
            ''' 伤害源id '''
            self.projectileId = dic.get("projectileId")  # type: str
            ''' 投射物id '''
            self.entityId = dic.get("entityId")  # type: str
            ''' 被伤害id '''
            self.damage = dic.get("damage")  # type: int
            ''' 伤害值，允许修改，设置为0则此次造成的伤害为0 '''
            self.cause = dic.get("cause")  # type: str
            ''' 伤害来源，详见Minecraft枚举值文档的ActorDamageCause '''

    class AddEffectServerEvent:
        ''' 触发时机：实体获得状态效果时 '''
        def __init__(self, dic):
            self.entityId = dic.get("entityId")  # type: str
            ''' 实体id '''
            self.effectName = dic.get("effectName")  # type: str
            ''' 实体获得状态效果的名字 '''
            self.effectDuration = dic.get("effectDuration")  # type: int
            ''' 状态效果的持续时间，单位秒 '''
            self.effectAmplifier = dic.get("effectAmplifier")  # type: int
            ''' 状态效果的放大倍数 '''
            self.damage = dic.get("damage")  # type: int
            ''' 状态造成的伤害值，如药水 '''

    class AddEntityServerEvent:
        ''' actor实体增加，事件触发，对应客户端AddEntityEvent '''
        def __init__(self, dic):
            self.id = dic.get("id")  # type: str
            ''' 实体id '''
            self.posX = dic.get("posX")  # type: float
            ''' 位置x '''
            self.posY = dic.get("posY")  # type: float
            ''' 位置y '''
            self.posZ = dic.get("posZ")  # type: float
            ''' 位置z '''
            self.dimensionId = dic.get("dimensionId")  # type: int
            ''' 实体维度 '''
            self.isBaby = dic.get("isBaby")  # type: bool
            ''' 是否为幼儿 '''
            self.engineTypeStr = dic.get("engineTypeStr")  # type: str
            ''' 实体类型 '''
            self.itemName = dic.get("itemName")  # type: str
            ''' 物品identifier（仅当物品实体时存在该字段） '''
            self.auxValue = dic.get("auxValue")  # type: int
            ''' 物品附加值（仅当物品实体时存在该字段） '''

    class AttackAnimBeginServerEvent:
        ''' 当攻击动作开始时触发 '''
        def __init__(self, dic):
            self.id = dic.get("id")  # type: str
            ''' 实体id '''

    class AttackAnimEndServerEvent:
        ''' 当攻击动作结束时触发 '''
        def __init__(self, dic):
            self.id = dic.get("id")  # type: str
            ''' 实体id '''

    class BlockRemoveServerEvent:
        ''' 触发时机：监听该事件的方块在销毁时触发，可以通过ListenOnBlockRemoveEvent方法进行监听，或者通过json组件netease:listen_block_remove进行配置 '''
        def __init__(self, dic):
            self.x = dic.get("x")  # type: int
            ''' 方块位置x '''
            self.y = dic.get("y")  # type: int
            ''' 方块位置y '''
            self.z = dic.get("z")  # type: int
            ''' 方块位置z '''
            self.fullName = dic.get("fullName")  # type: str
            ''' 方块的identifier，包含命名空间及名称 '''
            self.auxValue = dic.get("auxValue")  # type: int
            ''' 方块的附加值 '''
            self.dimension = dic.get("dimension")  # type: int
            ''' 该方块所在的维度 '''

    class ChangeSwimStateServerEvent:
        ''' 触发时机：实体开始或者结束游泳时 '''
        def __init__(self, dic):
            self.entityId = dic.get("entityId")  # type: str
            ''' 实体的唯一ID '''
            self.formState = dic.get("formState")  # type: bool
            ''' 事件触发前，实体是否在游泳状态 '''
            self.toState = dic.get("toState")  # type: bool
            ''' 事件触发后，实体是否在游泳状态 '''

    class EntityChangeDimensionServerEvent:
        ''' 实体维度改变时服务端抛出 '''
        def __init__(self, dic):
            self.entityId = dic.get("entityId")  # type: str
            ''' 实体id '''
            self.fromDimensionId = dic.get("fromDimensionId")  # type: int
            ''' 维度改变前的维度 '''
            self.toDimensionId = dic.get("toDimensionId")  # type: int
            ''' 维度改变后的维度 '''
            self.fromX = dic.get("fromX")  # type: float
            ''' 改变前的位置x '''
            self.fromY = dic.get("fromY")  # type: float
            ''' 改变前的位置Y '''
            self.fromZ = dic.get("fromZ")  # type: float
            ''' 改变前的位置Z '''
            self.toX = dic.get("toX")  # type: float
            ''' 改变后的位置x '''
            self.toY = dic.get("toY")  # type: float
            ''' 改变后的位置Y '''
            self.toZ = dic.get("toZ")  # type: float
            ''' 改变后的位置Z '''

    class EntityEffectDamageServerEvent:
        ''' 生物受到状态伤害/回复事件。 '''
        def __init__(self, dic):
            self.entityId = dic.get("entityId")  # type: str
            ''' 实体id '''
            self.damage = dic.get("damage")  # type: int
            ''' 伤害值（负数表示生命回复） '''
            self.attributeBuffType = dic.get("attributeBuffType")  # type: int
            ''' 状态类型，参考AttributeBuffType '''
            self.duration = dic.get("duration")  # type: float
            ''' 状态持续时间，单位秒（s） '''
            self.lifeTimer = dic.get("lifeTimer")  # type: float
            ''' 状态生命时间，单位秒（s） '''
            self.isInstantaneous = dic.get("isInstantaneous")  # type: bool
            ''' 是否为立即生效状态 '''

    class EntityLoadScriptEvent:
        ''' 数据库加载实体自定义数据时触发 '''
        def __init__(self, dic):
            self.args = dic.get("args")  # type: list
            ''' 该事件的参数为长度为2的list，而非dict，其中list的第一个元素为实体id '''

    class EntityRemoveEvent:
        ''' 实体被删除时触发 '''
        def __init__(self, dic):
            self.id = dic.get("id")  # type: str
            ''' 实体id '''

    class EntityStartRidingEvent:
        ''' 当实体骑乘上另一个实体时触发 '''
        def __init__(self, dic):
            self.id = dic.get("id")  # type: str
            ''' 乘骑者实体id '''
            self.rideId = dic.get("rideId")  # type: str
            ''' 被乘骑者实体id '''

    class EntityStopRidingEvent:
        ''' 触发时机：当实体停止骑乘时 '''
        def __init__(self, dic):
            self.id = dic.get("id")  # type: str
            ''' 实体id '''
            self.rideId = dic.get("rideId")  # type: str
            ''' 坐骑id '''
            self.exitFromRider = dic.get("exitFromRider")  # type: bool
            ''' 是否下坐骑 '''
            self.entityIsBeingDestroyed = dic.get("entityIsBeingDestroyed")  # type: bool
            ''' 坐骑是否将要销毁 '''
            self.switchingRides = dic.get("switchingRides")  # type: bool
            ''' 是否换乘坐骑 '''
            self.cancel = dic.get("cancel")  # type: bool
            ''' 设置为True可以取消（需要与客户端事件一同取消） '''

    class EntityTickServerEvent:
        ''' 实体tick时触发。该事件为20帧每秒。需要使用AddEntityTickEventWhiteList添加触发该事件的实体类型白名单。 '''
        def __init__(self, dic):
            self.entityId = dic.get("entityId")  # type: str
            ''' 实体id '''

    class JumpAnimBeginServerEvent:
        ''' 当跳跃动作开始时触发 '''
        def __init__(self, dic):
            self.id = dic.get("id")  # type: str
            ''' 实体id '''

    class MobDieEvent:
        ''' 实体被玩家杀死时触发 '''
        def __init__(self, dic):
            self.id = dic.get("id")  # type: str
            ''' 实体id '''
            self.attacker = dic.get("attacker")  # type: str
            ''' 伤害来源id '''

    class OnEntityAreaEvent:
        ''' 触发时机：通过RegisterEntityAOIEvent注册过AOI事件后，当有实体进入或离开注册感应区域时触发该事件。 '''
        def __init__(self, dic):
            self.name = dic.get("name")  # type: str
            ''' 注册感应区域名称 '''
            self.enteredEntities = dic.get("enteredEntities")  # type: list
            ''' 进入该感应区域的实体id列表 '''
            self.leftEntities = dic.get("leftEntities")  # type: list
            ''' 离开该感应区域的实体id列表 '''

    class OnKnockBackServerEvent:
        ''' 实体被击退时触发 '''
        def __init__(self, dic):
            self.id = dic.get("id")  # type: str
            ''' 实体id '''

    class RefreshEffectServerEvent:
        ''' 触发时机：实体身上状态效果更新时触发，更新条件1、新增状态等级较高，更新状态等级及时间；2、新增状态等级不变，时间较长，更新状态持续时间 '''
        def __init__(self, dic):
            self.entityId = dic.get("entityId")  # type: str
            ''' 实体id '''
            self.effectName = dic.get("effectName")  # type: str
            ''' 更新状态效果的名字 '''
            self.effectDuration = dic.get("effectDuration")  # type: int
            ''' 更新后状态效果剩余持续时间，单位秒 '''
            self.effectAmplifier = dic.get("effectAmplifier")  # type: int
            ''' 更新后的状态效果放大倍数 '''
            self.damage = dic.get("damage")  # type: int
            ''' 状态造成的伤害值，如药水 '''

    class RemoveEffectServerEvent:
        ''' 触发时机：实体身上状态效果被移除时 '''
        def __init__(self, dic):
            self.entityId = dic.get("entityId")  # type: str
            ''' 实体id '''
            self.effectName = dic.get("effectName")  # type: str
            ''' 被移除状态效果的名字 '''
            self.effectDuration = dic.get("effectDuration")  # type: int
            ''' 被移除状态效果的剩余持续时间，单位秒 '''
            self.effectAmplifier = dic.get("effectAmplifier")  # type: int
            ''' 被移除状态效果的放大倍数 '''

    class StartRidingServerEvent:
        ''' 触发时机：一个实体即将骑乘另外一个实体 '''
        def __init__(self, dic):
            self.cancel = dic.get("cancel")  # type: bool
            ''' 是否允许触发，默认为False，若设为True，可阻止触发后续的实体交互事件 '''
            self.actorId = dic.get("actorId")  # type: str
            ''' 骑乘者的唯一ID '''
            self.victimId = dic.get("victimId")  # type: str
            ''' 被骑乘实体的唯一ID '''

    class WalkAnimBeginServerEvent:
        ''' 当走路动作开始时触发 '''
        def __init__(self, dic):
            self.id = dic.get("id")  # type: str
            ''' 实体id '''

    class WalkAnimEndServerEvent:
        ''' 当走路动作结束时触发 '''
        def __init__(self, dic):
            self.id = dic.get("id")  # type: str
            ''' 实体id '''

    class WillAddEffectServerEvent:
        ''' 触发时机：实体即将获得状态效果前 '''
        def __init__(self, dic):
            self.entityId = dic.get("entityId")  # type: str
            ''' 实体id '''
            self.effectName = dic.get("effectName")  # type: str
            ''' 实体获得状态效果的名字 '''
            self.effectDuration = dic.get("effectDuration")  # type: int
            ''' 状态效果的持续时间，单位秒 '''
            self.effectAmplifier = dic.get("effectAmplifier")  # type: int
            ''' 状态效果的放大倍数 '''
            self.cancel = dic.get("cancel")  # type: bool
            ''' 设置为True可以取消 '''
            self.damage = dic.get("damage")  # type: int
            ''' 状态造成的伤害值，如药水 '''

    class WillTeleportToServerEvent:
        ''' 触发时机：一个实体即将传送/被传送前 '''
        def __init__(self, dic):
            self.cancel = dic.get("cancel")  # type: bool
            ''' 是否允许触发，默认为False，若设为True，可阻止触发后续的传送 '''
            self.entityId = dic.get("entityId")  # type: str
            ''' 实体的唯一ID '''
            self.fromDimensionId = dic.get("fromDimensionId")  # type: int
            ''' 传送前所在的维度 '''
            self.toDimensionId = dic.get("toDimensionId")  # type: int
            ''' 传送后的目标维度，假如目标维度尚未在内存中创建（即服务器启动之后，到传送之前，没有玩家进入过这个维度 '''
            self.fromX = dic.get("fromX")  # type: int
            ''' 传送前所在的x坐标 '''
            self.fromY = dic.get("fromY")  # type: int
            ''' 传送前所在的y坐标 '''
            self.fromZ = dic.get("fromZ")  # type: int
            ''' 传送前所在的z坐标 '''
            self.toX = dic.get("toX")  # type: int
            ''' 传送目标地点的x坐标，假如目标维度尚未在内存中创建（即服务器启动之后，到传送之前，没有玩家进入过这个维度 '''
            self.toY = dic.get("toY")  # type: int
            ''' 传送目标地点的y坐标，假如目标维度尚未在内存中创建（即服务器启动之后，到传送之前，没有玩家进入过这个维度 '''
            self.toZ = dic.get("toZ")  # type: int
            ''' 传送目标地点的z坐标，假如目标维度尚未在内存中创建（即服务器启动之后，到传送之前，没有玩家进入过这个维度 '''
            self.cause = dic.get("cause")  # type: str
            ''' 传送理由，详情见MinecraftEnum.EntityTeleportCause '''

    class DamageEvent:
        ''' 实体被攻击时触发 '''
        def __init__(self, dic):
            self.srcId = dic.get("srcId")  # type: str
            ''' 伤害源id '''
            self.projectileId = dic.get("projectileId")  # type: str
            ''' 投射物id '''
            self.entityId = dic.get("entityId")  # type: str
            ''' 被伤害id '''
            self.damage = dic.get("damage")  # type: int
            ''' 伤害值，允许修改，设置为0则此次造成的伤害为0 '''
            self.absorption = dic.get("absorption")  # type: int
            ''' 伤害吸收生命值，详见Minecraft枚举值文档的ABSORPTION '''
            self.cause = dic.get("cause")  # type: str
            ''' 伤害来源，详见Minecraft枚举值文档的ActorDamageCause '''
            self.knock = dic.get("knock")  # type: bool
            ''' 是否击退被攻击者，允许修改，设置该值为False则不产生击退 '''
            self.ignite = dic.get("ignite")  # type: bool
            ''' 是否点燃被伤害者，允许修改，设置该值为True产生点燃效果，反之亦然 '''

    class EntityDefinitionsEventServerEvent:
        ''' 触发时机：生物定义json文件中设置的event触发时同时触发。生物行为变更事件 '''
        def __init__(self, dic):
            self.entityId = dic.get("entityId")  # type: str
            ''' 生物id '''
            self.eventName = dic.get("eventName")  # type: str
            ''' 触发的事件名称 '''

    class MobGriefingBlockServerEvent:
        ''' 环境生物改变方块时触发，触发的时机与mobgriefing游戏规则影响的行为相同 '''
        def __init__(self, dic):
            self.cancel = dic.get("cancel")  # type: bool
            ''' 是否允许触发，默认为False，若设为True，可阻止触发后续物理交互事件 '''
            self.blockX = dic.get("blockX")  # type: int
            ''' 方块x坐标 '''
            self.blockY = dic.get("blockY")  # type: int
            ''' 方块y坐标 '''
            self.blockZ = dic.get("blockZ")  # type: int
            ''' 方块z坐标 '''
            self.entityId = dic.get("entityId")  # type: str
            ''' 触发的entity的唯一ID '''
            self.blockName = dic.get("blockName")  # type: str
            ''' 方块的identifier，包含命名空间及名称 '''
            self.dimensionId = dic.get("dimensionId")  # type: int
            ''' 维度id '''

    class OnFireHurtEvent:
        ''' 生物受到火焰伤害时触发 '''
        def __init__(self, dic):
            self.victim = dic.get("victim")  # type: str
            ''' 受伤实体id '''
            self.src = dic.get("src")  # type: str
            ''' 火焰创建者id '''
            self.fireTime = dic.get("fireTime")  # type: float
            ''' 着火时间，单位秒 '''
            self.cancel = dic.get("cancel")  # type: bool
            ''' 是否取消此处火焰伤害 '''

    class ServerSpawnMobEvent:
        ''' 游戏内自动生成怪物时触发 '''
        def __init__(self, dic):
            self.identifier = dic.get("identifier")  # type: str
            ''' 生成实体的命名空间 '''
            self.type = dic.get("type")  # type: int
            ''' 生成实体的类型，参考EntityType '''
            self.baby = dic.get("baby")  # type: bool
            ''' 生成怪物是否是幼年怪 '''
            self.x = dic.get("x")  # type: float
            ''' 生成实体坐标x '''
            self.y = dic.get("y")  # type: float
            ''' 生成实体坐标y '''
            self.z = dic.get("z")  # type: float
            ''' 生成实体坐标z '''
            self.dimensionId = dic.get("dimensionId")  # type: int
            ''' 生成实体的维度，默认值为0（0为主世界，1为地狱，2为末地） '''
            self.cancel = dic.get("cancel")  # type: bool
            ''' 是否生成该实体 '''

    class AddExpEvent:
        ''' 触发时机：当玩家增加经验时触发该事件。 '''
        def __init__(self, dic):
            self.id = dic.get("id")  # type: str
            ''' 玩家id '''
            self.addExp = dic.get("addExp")  # type: int
            ''' 增加的经验值 '''

    class AddLevelEvent:
        ''' 触发时机：当玩家升级时触发该事件。 '''
        def __init__(self, dic):
            self.id = dic.get("id")  # type: str
            ''' 玩家id '''
            self.addLevel = dic.get("addLevel")  # type: int
            ''' 增加的等级值 '''
            self.newLevel = dic.get("newLevel")  # type: int
            ''' 新的等级 '''

    class AddServerPlayerEvent:
        ''' 触发时机：玩家加入时触发该事件。 '''
        def __init__(self, dic):
            self.id = dic.get("id")  # type: str
            ''' 玩家id '''
            self.isTransfer = dic.get("isTransfer")  # type: bool
            ''' 是否是切服时进入服务器，仅用于Apollo。如果是True，则表示切服时加入服务器，若是False，则表示登录进入网络游戏 '''
            self.transferParam = dic.get("transferParam")  # type: str
            ''' 切服传入参数，仅用于Apollo。调用【TransferToOtherServer】或【TransferToOtherServerById】传入的切服参数 '''
            self.uid = dic.get("uid")  # type: int
            ''' 玩家的netease uid，玩家的唯一标识，仅用于Apollo '''

    class ChangeLevelUpCostServerEvent:
        ''' 触发时机：获取玩家下一个等级升级经验时，用于重载玩家的升级经验，每个等级在重置之前都只会触发一次 '''
        def __init__(self, dic):
            self.level = dic.get("level")  # type: int
            ''' 玩家当前等级 '''
            self.levelUpCostExp = dic.get("levelUpCostExp")  # type: int
            ''' 当前等级升级到下个等级需要的经验值，当设置为0时表示维持原版升级经验不变 '''
            self.changed = dic.get("changed")  # type: bool
            ''' 设置为True，重载玩家升级经验才会生效 '''

    class ClientLoadAddonsFinishServerEvent:
        ''' 触发时机：客户端mod加载完成时，服务端触发此事件。服务器可以使用此事件，往客户端发送数据给其初始化。 '''
        def __init__(self, dic):
            self.playerId = dic.get("playerId")  # type: str
            ''' 玩家id '''

    class CommandEvent:
        ''' 玩家请求执行指令时触发 '''
        def __init__(self, dic):
            self.entityId = dic.get("entityId")  # type: str
            ''' 玩家ID '''
            self.command = dic.get("command")  # type: str
            ''' 指令字符串 '''
            self.cancel = dic.get("cancel")  # type: bool
            ''' 是否取消 '''

    class DelServerPlayerEvent:
        ''' 触发时机：删除玩家时触发该事件。 '''
        def __init__(self, dic):
            self.id = dic.get("id")  # type: str
            ''' 玩家id '''
            self.isTransfer = dic.get("isTransfer")  # type: bool
            ''' 是否是切服时退出服务器，仅用于Apollo。如果是True，则表示切服时退出服务器；若是False，则表示退出网络游戏 '''
            self.uid = dic.get("uid")  # type: int
            ''' 玩家的netease uid，玩家的唯一标识 '''

    class DimensionChangeFinishServerEvent:
        ''' 玩家维度改变完成后服务端抛出 '''
        def __init__(self, dic):
            self.playerId = dic.get("playerId")  # type: str
            ''' 玩家实体id '''
            self.fromDimensionId = dic.get("fromDimensionId")  # type: int
            ''' 维度改变前的维度 '''
            self.toDimensionId = dic.get("toDimensionId")  # type: int
            ''' 维度改变后的维度 '''
            self.toPos = dic.get("toPos")  # type: tuple(float,float,float)
            ''' 改变后的位置x,y,z,其中y值为脚底加上角色的身高值 '''

    class DimensionChangeServerEvent:
        ''' 玩家维度改变时服务端抛出 '''
        def __init__(self, dic):
            self.playerId = dic.get("playerId")  # type: str
            ''' 玩家实体id '''
            self.fromDimensionId = dic.get("fromDimensionId")  # type: int
            ''' 维度改变前的维度 '''
            self.toDimensionId = dic.get("toDimensionId")  # type: int
            ''' 维度改变后的维度 '''
            self.fromX = dic.get("fromX")  # type: float
            ''' 改变前的位置x '''
            self.fromY = dic.get("fromY")  # type: float
            ''' 改变前的位置Y '''
            self.fromZ = dic.get("fromZ")  # type: float
            ''' 改变前的位置Z '''
            self.toX = dic.get("toX")  # type: float
            ''' 改变后的位置x '''
            self.toY = dic.get("toY")  # type: float
            ''' 改变后的位置Y '''
            self.toZ = dic.get("toZ")  # type: float
            ''' 改变后的位置Z '''

    class ExtinguishFireServerEvent:
        ''' 玩家扑灭火焰时触发。下雨，倒水等方式熄灭火焰不会触发。 '''
        def __init__(self, dic):
            self.pos = dic.get("pos")  # type: tuple(float,float,float)
            ''' 火焰方块的坐标 '''
            self.playerId = dic.get("playerId")  # type: str
            ''' 玩家id '''
            self.cancel = dic.get("cancel")  # type: bool
            ''' 修改为True时，可阻止玩家扑灭火焰。需要与ExtinguishFireClientEvent一起修改。 '''

    class OnCarriedNewItemChangedServerEvent:
        ''' 触发时机：玩家切换主手物品时触发该事件 '''
        def __init__(self, dic):
            self.oldItemDict = dic.get("oldItemDict")  # type: dict|None
            ''' 旧物品信息字典，当旧物品为空时，此项属性为None '''
            self.newItemDict = dic.get("newItemDict")  # type: dict|None
            ''' 新物品信息字典，当新物品为空时，此项属性为None '''
            self.playerId = dic.get("playerId")  # type: str
            ''' 玩家 entityId '''

    class OnNewArmorExchangeServerEvent:
        ''' 触发时机：玩家切换盔甲时触发该事件 '''
        def __init__(self, dic):
            self.slot = dic.get("slot")  # type: int
            ''' 槽位id '''
            self.oldArmorDict = dic.get("oldArmorDict")  # type: dict|None
            ''' 旧装备信息字典，当旧物品为空时，此项属性为None '''
            self.newArmorDict = dic.get("newArmorDict")  # type: dict|None
            ''' 新装备信息字典，当新物品为空时，此项属性为None '''
            self.playerId = dic.get("playerId")  # type: str
            ''' 玩家 entityId '''

    class OnOffhandItemChangedServerEvent:
        ''' 触发时机：玩家切换副手物品时触发该事件 '''
        def __init__(self, dic):
            self.oldItemName = dic.get("oldItemName")  # type: str
            ''' 旧物品 物品名称 '''
            self.oldItemAuxValue = dic.get("oldItemAuxValue")  # type: int
            ''' 旧物品 物品附加值 '''
            self.oldItemModExtralId = dic.get("oldItemModExtralId")  # type: str
            ''' 旧物品 物品自定义标识符 '''
            self.oldItemDict = dic.get("oldItemDict")  # type: dict|None
            ''' 旧物品信息字典，当旧物品为空时，此项属性为None '''
            self.newItemName = dic.get("newItemName")  # type: str
            ''' 新物品 物品名称 '''
            self.newItemAuxValue = dic.get("newItemAuxValue")  # type: int
            ''' 新物品 物品附加值 '''
            self.newItemModExtralId = dic.get("newItemModExtralId")  # type: str
            ''' 新物品 物品自定义标识符 '''
            self.newItemDict = dic.get("newItemDict")  # type: dict|None
            ''' 新物品信息字典，当新物品为空时，此项属性为None '''
            self.playerId = dic.get("playerId")  # type: str
            ''' 玩家 entityId '''

    class OnPlayerHitBlockServerEvent:
        ''' 触发时机：通过OpenPlayerHitBlockDetection打开方块碰撞检测后，当玩家碰撞到方块时触发该事件。监听玩家着地请使用客户端的OnGroundClientEvent。客户端和服务端分别作碰撞检测，可能两个事件返回的略有差异。 '''
        def __init__(self, dic):
            self.playerId = dic.get("playerId")  # type: str
            ''' 碰撞到方块的玩家Id '''
            self.posX = dic.get("posX")  # type: int
            ''' 碰撞方块x坐标 '''
            self.posY = dic.get("posY")  # type: int
            ''' 碰撞方块y坐标 '''
            self.posZ = dic.get("posZ")  # type: int
            ''' 碰撞方块z坐标 '''
            self.blockId = dic.get("blockId")  # type: str
            ''' 碰撞方块的identifier '''
            self.auxValue = dic.get("auxValue")  # type: int
            ''' 碰撞方块的附加值 '''
            self.dimensionId = dic.get("dimensionId")  # type: int
            ''' 维度id '''

    class OnPlayerHitMobServerEvent:
        ''' 触发时机：通过OpenPlayerHitMobDetection打开生物碰撞检测后，当有生物与玩家碰撞时触发该事件。注：客户端和服务端分别作碰撞检测，可能两个事件返回的略有差异。 '''
        def __init__(self, dic):
            self.playerList = dic.get("playerList")  # type: list
            ''' 生物碰撞到的玩家id的list '''

    class PlayerAttackEntityEvent:
        ''' 触发时机：当玩家攻击时触发该事件。 '''
        def __init__(self, dic):
            self.playerId = dic.get("playerId")  # type: str
            ''' 玩家id '''
            self.victimId = dic.get("victimId")  # type: str
            ''' 受击者id '''
            self.damage = dic.get("damage")  # type: int
            ''' 伤害值：引擎传过来的值是0 允许脚本层修改为其他数 '''
            self.isValid = dic.get("isValid")  # type: int
            ''' 脚本是否设置伤害值：1表示是；0 表示否 '''
            self.cancel = dic.get("cancel")  # type: bool
            ''' 是否取消该次攻击，默认不取消 '''
            self.isKnockBack = dic.get("isKnockBack")  # type: bool
            ''' 是否支持击退效果，默认支持，当不支持时将屏蔽武器击退附魔效果 '''

    class PlayerDieEvent:
        ''' 触发时机：当玩家死亡时触发该事件。 '''
        def __init__(self, dic):
            self.id = dic.get("id")  # type: str
            ''' 玩家id '''
            self.attacker = dic.get("attacker")  # type: str
            ''' 伤害来源id '''

    class PlayerEatFoodServerEvent:
        ''' 触发时机：玩家吃下食物时触发 '''
        def __init__(self, dic):
            self.playerId = dic.get("playerId")  # type: str
            ''' 玩家Id '''
            self.itemDict = dic.get("itemDict")  # type: dict
            ''' 食物物品的物品信息字典 '''

    class PlayerHurtEvent:
        ''' 触发时机：当玩家受伤害前触发该事件。 '''
        def __init__(self, dic):
            self.id = dic.get("id")  # type: str
            ''' 受击玩家id '''
            self.attacker = dic.get("attacker")  # type: str
            ''' 伤害来源实体id，若没有实体攻击，例如高空坠落，id为-1 '''

    class PlayerInteractServerEvent:
        ''' 触发时机：玩家即将和某个实体交互 '''
        def __init__(self, dic):
            self.cancel = dic.get("cancel")  # type: bool
            ''' 是否允许触发，默认为False，若设为True，可阻止触发后续的实体交互事件 '''
            self.playerId = dic.get("playerId")  # type: str
            ''' 主动与实体互动的玩家的唯一ID '''
            self.itemDict = dic.get("itemDict")  # type: dict
            ''' 当前玩家手持物品的物品信息字典 '''
            self.victimId = dic.get("victimId")  # type: str
            ''' 被动的实体的唯一ID '''

    class PlayerJoinMessageEvent:
        ''' 触发时机：准备显示“xxx加入游戏”的玩家登录提示文字时服务端抛出的事件。 '''
        def __init__(self, dic):
            self.id = dic.get("id")  # type: str
            ''' 玩家实体id '''
            self.name = dic.get("name")  # type: str
            ''' 玩家昵称 '''
            self.cancel = dic.get("cancel")  # type: bool
            ''' 是否显示提示文字，允许修改。True：不显示提示 '''
            self.message = dic.get("message")  # type: str
            ''' 玩家加入游戏的提示文字，允许修改 '''

    class PlayerLeftMessageServerEvent:
        ''' 触发时机：准备显示“xxx离开游戏”的玩家离开提示文字时服务端抛出的事件。 '''
        def __init__(self, dic):
            self.id = dic.get("id")  # type: str
            ''' 玩家实体id '''
            self.name = dic.get("name")  # type: str
            ''' 玩家昵称 '''
            self.cancel = dic.get("cancel")  # type: bool
            ''' 是否显示提示文字，允许修改。True：不显示提示 '''
            self.message = dic.get("message")  # type: str
            ''' 玩家加入游戏的提示文字，允许修改 '''

    class PlayerRespawnEvent:
        ''' 触发时机：玩家复活时触发该事件。 '''
        def __init__(self, dic):
            self.id = dic.get("id")  # type: str
            ''' 玩家id '''

    class PlayerRespawnFinishServerEvent:
        ''' 触发时机：玩家复活完毕时触发 '''
        def __init__(self, dic):
            self.playerId = dic.get("playerId")  # type: str
            ''' 玩家id '''

    class PlayerTeleportEvent:
        ''' 触发时机：当玩家传送时触发该事件，如：玩家使用末影珍珠或tp指令时。 '''
        def __init__(self, dic):
            self.id = dic.get("id")  # type: str
            ''' 玩家id '''

    class ServerChatEvent:
        ''' 玩家发送聊天信息时触发 '''
        def __init__(self, dic):
            self.username = dic.get("username")  # type: str
            ''' 玩家名称 '''
            self.playerId = dic.get("playerId")  # type: str
            ''' 玩家id '''
            self.message = dic.get("message")  # type: str
            ''' 玩家发送的聊天消息内容 '''
            self.cancel = dic.get("cancel")  # type: bool
            ''' 是否取消这个聊天事件，若取消可以设置为True '''
            self.bChatById = dic.get("bChatById")  # type: bool
            ''' 是否把聊天消息发送给指定在线玩家，而不是广播给所有在线玩家，若只发送某些玩家可以设置为True '''
            self.bForbid = dic.get("bForbid")  # type: bool
            ''' 是否禁言。true：被禁言，玩家聊天会提示“你已被管理员禁言”。当前版本仅Apollo可用 '''
            self.toPlayerIds = dic.get("toPlayerIds")  # type: list(str)
            ''' 接收聊天消息的玩家id列表，bChatById为True时生效 '''

    class ServerPlayerGetExperienceOrbEvent:
        ''' 触发时机：玩家获取经验球时触发的事件 '''
        def __init__(self, dic):
            self.playerId = dic.get("playerId")  # type: str
            ''' 玩家id '''
            self.experienceValue = dic.get("experienceValue")  # type: int
            ''' 经验球经验值 '''
            self.cancel = dic.get("cancel")  # type: bool
            ''' 是否取消（开发者传入） '''

    class StartDestroyBlockServerEvent:
        ''' 玩家开始挖方块时触发。创造模式下不触发。 '''
        def __init__(self, dic):
            self.pos = dic.get("pos")  # type: tuple(float,float,float)
            ''' 方块的坐标 '''
            self.blockName = dic.get("blockName")  # type: str
            ''' 方块的identifier，包含命名空间及名称 '''
            self.auxValue = dic.get("auxValue")  # type: int
            ''' 方块的附加值 '''
            self.playerId = dic.get("playerId")  # type: str
            ''' 玩家id '''
            self.dimensionId = dic.get("dimensionId")  # type: int
            ''' 维度id '''
            self.cancel = dic.get("cancel")  # type: bool
            ''' 修改为True时，可阻止玩家进入挖方块的状态。需要与StartDestroyBlockClientEvent一起修改。 '''

    class StoreBuySuccServerEvent:
        ''' 触发时机:玩家游戏内购买商品时服务端抛出的事件 '''
        def __init__(self, dic):
            self.playerId = dic.get("playerId")  # type: str
            ''' 购买商品的玩家实体id '''

    class ActorAcquiredItemServerEvent:
        ''' 触发时机：玩家获得物品时服务端抛出的事件（有些获取物品方式只会触发客户端事件，有些获取物品方式只会触发服务端事件，在使用时注意一点。） '''
        def __init__(self, dic):
            self.actor = dic.get("actor")  # type: str
            ''' 获得物品玩家实体id '''
            self.secondaryActor = dic.get("secondaryActor")  # type: str
            ''' 物品给予者玩家实体id，如果不存在给予者的话，这里为空字符串 '''
            self.itemDict = dic.get("itemDict")  # type: dict
            ''' 获得的物品的物品信息字典 '''
            self.acquireMethod = dic.get("acquireMethod")  # type: int
            ''' 获得物品的方法，详见ItemAcquisitionMethod '''

    class ActorUseItemServerEvent:
        ''' 触发时机：玩家使用物品生效之前服务端抛出的事件（比较特殊不走该事件的例子：1）喝牛奶；2）染料对有水的炼药锅使用；3）盔甲架装备盔甲） '''
        def __init__(self, dic):
            self.playerId = dic.get("playerId")  # type: str
            ''' 玩家实体id '''
            self.itemDict = dic.get("itemDict")  # type: dict
            ''' 使用的物品的物品信息字典 '''
            self.useMethod = dic.get("useMethod")  # type: int
            ''' 使用物品的方法，详见ItemUseMethodEnum '''

    class EntityDieLoottableServerEvent:
        ''' 触发时机：生物死亡掉落物品时 '''
        def __init__(self, dic):
            self.dieEntityId = dic.get("dieEntityId")  # type: str
            ''' 死亡实体的entityId '''
            self.attacker = dic.get("attacker")  # type: str
            ''' 伤害来源的entityId '''
            self.itemList = dic.get("itemList")  # type: list(dict)
            ''' 掉落物品列表，每个元素为一个itemDict，格式可参考物品信息字典 '''
            self.dirty = dic.get("dirty")  # type: bool
            ''' 默认为False，如果需要修改掉落列表需将该值设为True '''

    class ItemReleaseUsingServerEvent:
        ''' 触发时机：释放正在使用的物品时 '''
        def __init__(self, dic):
            self.playerId = dic.get("playerId")  # type: str
            ''' 玩家id '''
            self.durationLeft = dic.get("durationLeft")  # type: float
            ''' 蓄力剩余时间 '''
            self.itemDict = dic.get("itemDict")  # type: dict
            ''' 使用的物品的物品信息字典 '''
            self.maxUseDuration = dic.get("maxUseDuration")  # type: int
            ''' 最大蓄力时长 '''
            self.cancel = dic.get("cancel")  # type: bool
            ''' 设置为True可以取消 '''

    class ItemUseAfterServerEvent:
        ''' 玩家在使用物品之后服务端抛出的事件。 '''
        def __init__(self, dic):
            self.entityId = dic.get("entityId")  # type: str
            ''' 玩家实体id '''
            self.itemDict = dic.get("itemDict")  # type: dict
            ''' 使用的物品的物品信息字典 '''

    class ItemUseOnAfterServerEvent:
        ''' 玩家在对方块使用物品之后服务端抛出的事件。 '''
        def __init__(self, dic):
            self.entityId = dic.get("entityId")  # type: str
            ''' 玩家实体id '''
            self.itemDict = dic.get("itemDict")  # type: dict
            ''' 使用的物品的物品信息字典 '''
            self.x = dic.get("x")  # type: int
            ''' 方块 x 坐标值 '''
            self.y = dic.get("y")  # type: int
            ''' 方块 y 坐标值 '''
            self.z = dic.get("z")  # type: int
            ''' 方块 z 坐标值 '''
            self.face = dic.get("face")  # type: int
            ''' 点击方块的面，参考Facing '''
            self.clickX = dic.get("clickX")  # type: float
            ''' 点击点的x比例位置 '''
            self.clickY = dic.get("clickY")  # type: float
            ''' 点击点的y比例位置 '''
            self.clickZ = dic.get("clickZ")  # type: float
            ''' 点击点的z比例位置 '''
            self.blockName = dic.get("blockName")  # type: str
            ''' 方块的identifier '''
            self.blockAuxValue = dic.get("blockAuxValue")  # type: int
            ''' 方块的附加值 '''
            self.dimensionId = dic.get("dimensionId")  # type: int
            ''' 维度id '''

    class OnContainerFillLoottableServerEvent:
        ''' 触发时机：随机奖励箱第一次打开根据loottable生成物品时 '''
        def __init__(self, dic):
            self.loottable = dic.get("loottable")  # type: str
            ''' 奖励箱子所读取的loottable的json路径 '''
            self.playerId = dic.get("playerId")  # type: str
            ''' 打开奖励箱子的玩家的playerId '''
            self.itemList = dic.get("itemList")  # type: list
            ''' 掉落物品列表，每个元素为一个itemDict，格式可参考物品信息字典 '''
            self.dirty = dic.get("dirty")  # type: bool
            ''' 默认为False，如果需要修改掉落列表需将该值设为True '''

    class PlayerDropItemServerEvent:
        ''' 触发时机：玩家丢弃物品时触发 '''
        def __init__(self, dic):
            self.playerId = dic.get("playerId")  # type: str
            ''' 玩家id '''
            self.itemEntityId = dic.get("itemEntityId")  # type: str
            ''' 物品entityId '''

    class ServerItemTryUseEvent:
        ''' 玩家点击右键尝试使用物品时服务端抛出的事件 '''
        def __init__(self, dic):
            self.playerId = dic.get("playerId")  # type: str
            ''' 玩家id '''
            self.itemDict = dic.get("itemDict")  # type: dict
            ''' 使用的物品的物品信息字典 '''
            self.cancel = dic.get("cancel")  # type: bool
            ''' 设为True可取消物品的使用 '''

    class ServerItemUseOnEvent:
        ''' 玩家在对方块使用物品之前服务端抛出的事件。注：如果需要取消物品的使用需要同时在ClientItemUseOnEvent和ServerItemUseOnEvent中将ret设置为True才能正确取消。 '''
        def __init__(self, dic):
            self.entityId = dic.get("entityId")  # type: str
            ''' 玩家实体id '''
            self.itemDict = dic.get("itemDict")  # type: dict
            ''' 使用的物品的物品信息字典 '''
            self.x = dic.get("x")  # type: int
            ''' 方块 x 坐标值 '''
            self.y = dic.get("y")  # type: int
            ''' 方块 y 坐标值 '''
            self.z = dic.get("z")  # type: int
            ''' 方块 z 坐标值 '''
            self.blockName = dic.get("blockName")  # type: str
            ''' 方块的identifier '''
            self.blockAuxValue = dic.get("blockAuxValue")  # type: int
            ''' 方块的附加值 '''
            self.face = dic.get("face")  # type: int
            ''' 点击方块的面，参考Facing '''
            self.dimensionId = dic.get("dimensionId")  # type: int
            ''' 维度id '''
            self.clickX = dic.get("clickX")  # type: float
            ''' 点击点的x比例位置 '''
            self.clickY = dic.get("clickY")  # type: float
            ''' 点击点的y比例位置 '''
            self.clickZ = dic.get("clickZ")  # type: float
            ''' 点击点的z比例位置 '''
            self.ret = dic.get("ret")  # type: bool
            ''' 设为True可取消物品的使用 '''

    class ServerPlayerTryTouchEvent:
        ''' 触发时机：玩家触碰/捡起物品时触发 '''
        def __init__(self, dic):
            self.playerId = dic.get("playerId")  # type: str
            ''' 玩家Id '''
            self.entityId = dic.get("entityId")  # type: str
            ''' 物品实体的Id '''
            self.itemDict = dic.get("itemDict")  # type: dict
            ''' 触碰的物品的物品信息字典 '''
            self.cancel = dic.get("cancel")  # type: bool
            ''' 设置为True时将取消本次拾取 '''
            self.pickupDelay = dic.get("pickupDelay")  # type: int
            ''' 取消拾取后重新设置该物品的拾取cd，小于15帧将视作15帧，大于等于97813帧将视作无法拾取 '''
