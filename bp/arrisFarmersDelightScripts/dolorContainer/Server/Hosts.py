# -*- coding: utf-8 -*-
"""
宿主（docs/ARCHITECTURE.md 第 3.1、3.13 节）：容器类型的实例放在什么东西上——玩家、物品、世界、方块、实体，
或什么都不放。宿主决定：打开时的实例键怎么来、谁能打开（游戏的规矩之外）、数据存在哪个后端、存储键的前缀、
实例收不收某件东西（物品不能放进它自己里面）、能不能有实例存储、一次操作之后存档存什么、机器的时钟；开着的界面
还有效没有（每刻查与失效事件）、有人在看时宿主的行为、哪些格子要锁住。登记表、服务端服务与机器只调用这里的方法，
不认识具体的宿主。
库带的宿主与时钟在 Std/Server/Hosts.py。本模块不依赖引擎。
"""
from ..Common.Collections import PLAYER_KIND


class Clock(object):
    """
    机器的时钟（设计稿 3.13）：机器什么时候走。时钟走起来时调用 manager.machines.resume((类型, 实例键))，
    停下时调用 pause（Server/Machines.py）。只有登记了用它的机器（容器类型的界面模型是机器）才会接上。
    """

    def attach(self, manager, containerType):
        """登记了一种用这个时钟的机器。"""

    def playerJoined(self, manager, playerId):
        """玩家进了游戏（手持物与临时格已经退回）。"""

    def playerLeft(self, manager, playerId):
        """玩家要离开（这时还能读他的状态）。"""

    def track(self, manager, handle):
        """
        机器实例 handle（(类型, 实例键)）被打开了（每次打开都调）：要跨存档记住机器实例的时钟（区块加载、实体存活、一直）
        在这里记下。
        """

    def untrack(self, manager, handle):
        """机器实例的宿主没了（Service.discard，内容已清空）：不再记着它；它的时钟停下，不推进。"""


class Host(object):
    """
    宿主的基类。类属性：clock 是放在它上面的机器的时钟（None 时不能放机器）；items 是绑定的物品名（手持这些物品使用时
    打开，见 Api.openHeld）；stores 为假时界面模型不能有实例存储（只放玩家临时格这类会话保管的东西）；cacheable 为假时
    实例没人看了就不留在最近用过的里（数据不只由本库改的，例如写在物品里、物品会被复制：下次打开重新从后端读）。
    游戏的规矩内核在问宿主之前先查：没有"打开容器"能力的玩家（访客、旁观模式、自定义权限里关掉的）不能打开，也不能执行
    动作，世界禁止打开容器时（Api.setContainersDisabled）谁都不能；visitors 为真时这两条都不查（只给人看的界面，例如配方
    查看）。access 是谁能打开的规矩（主人、受信名单），canOpen 缺省问它，库带的一份在 Std/Server/Access.py。
    一个宿主可以服务几个容器类型（同一只女仆的主页与设置页）：types 是它们的编号，按登记的先后（内核登记时经 registered
    记下）；对着宿主交互时打开哪一个由 typeFor 定，宿主没了（方块拆掉、实体死了）时每个类型的实例都清掉。
    """

    clock = None
    items = ()
    stores = True
    cacheable = True
    visitors = False
    access = None
    types = ()

    def __init__(self, access=None, visitors=False):
        self.access = access
        self.visitors = visitors

    def registered(self, containerType):
        """内核登记了一个用这个宿主的容器类型（Registry.register，登记成功之后调）：缺省记进 types。改写时要调基类的。"""
        if containerType.typeId not in self.types:
            self.types = tuple(self.types) + (containerType.typeId,)

    def typeFor(self, playerId, key):
        """
        玩家对着宿主交互（右键方块、与实体交互、手持绑定的物品使用）时打开哪个容器类型：缺省最先登记的；返回 None 时不开。
        key 是实例键（手持物品时还没定，为 None）。
        """
        return self.types[0] if self.types else None

    def keyFor(self, playerId, key):
        """玩家要打开时的实例键：key 是打开方给的（可以为 None）；打不开时返回 None。"""
        raise NotImplementedError

    def canOpen(self, playerId, key):
        """
        这位玩家能不能打开（主人、受信名单这类权限）：有 access 时问它（access.allows(宿主, 玩家, 实例键)），没有时都能开。
        动作执行前也再问一次（权限可能在界面开着时变了）。游戏的规矩不用在这里查（见类说明）。
        """
        return self.access is None or bool(self.access.allows(self, playerId, key))

    def stillValid(self, playerId, key):
        """
        实例 key 对这位玩家还有效没有（距离、存活、方块还在、物品还在那一格……）。开着的会话每刻问一次（只有改写了它的宿主），
        动作执行前也问；不再有效时关掉会话，手持物与临时格退回。
        """
        return True

    def watch(self, key, onInvalid):
        """
        实例 key 有人看着时盯着它的失效事件（方块被破坏、实体移除……），失效时调用 onInvalid()：看着它的会话都关掉。
        返回不再盯着时调用的函数（没有要撤的可以返回 None）。实例从没人看到有人看时调用，没人看了就调用返回的函数。
        """
        return None

    def onViewers(self, key, viewers):
        """看着实例 key 的人变了（viewers 是玩家 ID 的列表，没人看时为空）：有人在看时宿主的行为（女仆停下 AI 这类）。"""

    def forgetsOnLeave(self, playerId, key):
        """
        玩家 playerId 离开游戏时，最近用过（没人看、留着备用）的实例 key 要不要丢掉、下次从后端重读：数据放在这位玩家
        身上的宿主返回真（库带的按玩家存放的宿主：实例键就是这位玩家时）。缺省不丢。
        """
        return False

    def lockedSlot(self, playerId, key):
        """
        简单的写法：打开时这位玩家背包里要锁住的那一格（0–35），没有时为 None（缺省的 lockedCells 按它）。
        """
        return None

    def lockedCells(self, playerId, key):
        """
        打开时这位玩家要锁住的格子：[(容器种类, 格)]（玩家背包是 Collections.PLAYER_KIND 的 0–35；物品宿主是那件物品所在
        的格，也可以在身上穿戴的、模组自己的容器种类里）。界面里有那种容器的才锁那一格；锁住的格子不收不出：拿不走、
        数字键换不走、丢不出（效果与只读的格子一样）。缺省是 lockedSlot 给的背包那一格。
        """
        index = self.lockedSlot(playerId, key)
        return [(PLAYER_KIND, index)] if index is not None else []

    def backend(self, key):
        """实例的数据存在哪个后端（Server/Storage.Backend）。"""
        raise NotImplementedError

    def prefix(self, storageKey, key):
        """实例在后端里的键前缀：后端只属于这一个实例时用 storageKey 本身，几个实例共用后端时要接上实例键。"""
        return storageKey

    def accepts(self, key, stack):
        """实例 key 收不收 stack 这一件（收纳袋里一层层的东西逐件问）。"""
        return True

    def save(self, backend):
        """一次操作之后存档：存实例的后端（与玩家数据一起存的不用另存）。"""
        backend.save()

    def giveExperience(self, session, amount):
        """
        会话里的规则要给这位玩家 amount 点经验（Session.giveExperience：熔炉拿走产物、砂轮、交易）：缺省照原版在玩家身上
        生成经验球。改写它可以直接加给玩家、记在宿主上、给别人。
        """
        session.inventory.spawnExperience(amount)
