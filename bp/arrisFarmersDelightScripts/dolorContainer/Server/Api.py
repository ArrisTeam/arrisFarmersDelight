# -*- coding: utf-8 -*-
"""
dolorContainer 服务端对外接口。

    from ..dolorContainer.Server import Api
    from ..dolorContainer.Std.Server import Hosts
    # 界面模型（两端都登记过，见 Common.Menus）与参数，标题，宿主（不存：格子都在玩家临时格上）：
    Api.registerContainerType(Api.ContainerType("mymod:table5", "5×5 工作台", "mymod:table5", host=Hosts.Transient()))
    Api.openContainer(playerId, "mymod:table5")

    # 按物品存放的机器（便携熔炉：物品宿主，带在身上时才烧）；玩家手持它使用时由使用方调用 openHeld：
    Api.registerContainerType(Api.ContainerType("mymod:portable_furnace", "container.furnace",
                                                menu="mymod:portable_furnace",
                                                host=Hosts.Item(("mymod:portable_furnace",))))
    Api.openHeld(playerId)

容器类型的参数见 Registry.ContainerType，宿主见 Server/Hosts.py 与 Std/Server/Hosts.py。
"""
from ..Common import Protocol
from .Registry import ContainerType  # noqa: F401
from . import Engine, Service


def registerContainerType(containerType):
    return Service.manager().register(containerType)


def addBehavior(typeId, behavior):
    """
    给容器类型加一个后台行为（Server/Machines.Behavior：磁铁、自动进食、搬运这类不在界面里的事）。实例的时钟走着时才跑：
    按间隔的每隔 interval 刻，按事件的在 events 里的引擎事件来了时（这时才开始监听）。宿主要有时钟。
    """
    Service.manager().addBehavior(typeId, behavior)


def containerTypes():
    """登记过的容器类型（Registry.ContainerType 的列表）。"""
    return Service.manager().registry.types()


def openHeld(playerId):
    """
    打开玩家手上那件物品绑定的容器（宿主绑定了这种物品的容器类型，例如 Std/Server/Hosts.Item）：实例键由宿主定，
    物品宿主在物品上还没有编号时先写上一个，内容跟着这一件物品走（丢给别人、放进箱子再拿出来，打开的还是这些东西）。
    返回是否打开。
    """
    return Service.manager().openHeld(playerId)


def openContainer(playerId, typeId, key=None, params=None):
    """
    为玩家打开容器。key 为 None 时由宿主定：按玩家存放、不存的用玩家 ID，物品宿主用手上那件的编号；
    按世界存放的要给实例键。params 是界面模型这一次的参数（不给时用登记时的）；同一个实例有人正用别的参数看着时不开。
    宿主不让开（权限）时不开。返回是否打开。
    """
    return Service.manager().open(playerId, typeId, key, params)


def switchContainer(playerId, typeId, key=None, params=None):
    """
    把玩家开着的容器换成另一个（另一个宿主或另一个界面模型，页签这类）：手持物跟过去；玩家临时格在新界面模型里有同名、
    同种、同样格数的就把东西交过去，没有的退回背包；客户端换界面，没有关上再打开的动画。没开着时就是打开，
    换到同一个实例就是重开。返回是否换了。动作里用 ctx.switchTo（回了应答再换）。
    """
    return Service.manager().switchTo(playerId, typeId, key, params)


def reopenContainer(playerId, params=None):
    """
    按新的参数重开玩家开着的容器（结构变了：装上升级、换页）：看着这个实例的人都重开，各自的手持物与临时格照
    switchContainer 的规矩交接。新参数建不出界面模型时什么都不动。返回是否重开了。动作里用 ctx.reopen。
    """
    return Service.manager().reopen(playerId, params)


def closeContainer(playerId, reason=Protocol.CLOSE_API):
    """关掉玩家开着的容器（手持物与临时格退回背包），通知客户端；reason 是 close 消息里的原因。没开着时返回 False。"""
    return Service.manager().close(playerId, reason, True)


def discardInstance(typeId, key, spill):
    """
    容器实例的宿主没了（方块被挖掉这类；库的方块宿主自己调用）：看着它的界面关上，实例存储里的东西逐件交给
    spill(物品堆)（让它们掉在原地这类），然后清空、忘掉这个实例。
    """
    Service.manager().discard(typeId, key, spill)


def updateInstance(typeId, key, change):
    """
    宿主在会话之外改一个容器实例（方块收到红石信号、漏斗往里送东西这类）：change(实例) 里改格子（instance.set(容器, 格号,
    物品堆)）与实例状态（instance.state），改完写回存储并推给看着的人；实例没加载时读出来改，机器先推进到现在。
    返回 change 的返回值。只在服务端调用。
    """
    return Service.manager().updateInstance(typeId, key, change)


def peekInstance(typeId, key, reader):
    """
    只读一个容器实例：reader(实例) 的返回值（实例没加载时读出来，用完放回缓存）。不推进机器、不写回、不推给看着的人：
    reader 里不要改实例（要改用 updateInstance）。只在服务端调用。
    """
    return Service.manager().peekInstance(typeId, key, reader)


def setRateLimit(capacity, rate):
    """
    每位玩家的请求限频（令牌桶）：最多攒 capacity 个令牌，每秒补 rate 个（缺省 60 与 30）。格子操作与动作每条花它声明的
    花费（Op.cost、Actions.action(..., cost=)，缺省 1），拉取与界面档的报告各花 0.25；用完时请求回 rate。
    """
    Service.setRateLimit(capacity, rate)


def setHurtClose(causes=None, cooldown=None):
    """
    受伤关界面的规矩（容器类型的 closeOnHurt 为真或给出 True 时关）：causes 是算"生物造成"的伤害来源（引擎受伤事件的
    cause），cooldown 是自动关闭之后多少秒内不再关（从最近一次这类伤害算起，缺省 5）。不给的不变。
    """
    Service.setHurtClose(causes, cooldown)


def setDropDisabled(disabled):
    """
    禁止（或重新允许）在容器界面里把东西丢进世界。引擎的"禁止丢弃物品"开关（SetDisableDropItem）也管原版容器界面，
    但脚本读不到它的状态：用那个开关的模组请同时调用这里。之后打开的界面按新的设置预测，服务端立即按新的设置处理。
    """
    Engine.setDropDisabled(disabled)


def setContainersDisabled(disabled):
    """
    禁止（或重新允许）打开容器。引擎的"禁止打开容器"开关（SetDisableContainers）管原版的容器界面与玩家背包，但脚本读不到
    它的状态，也管不到本库的界面：用那个开关的模组请同时调用这里。之后谁都打不开（宿主的 visitors 为真的除外），开着的界面里
    动作被拒；已经开着的界面不关。
    """
    Engine.setContainersDisabled(disabled)


def openedContainer(playerId):
    """玩家当前开着的容器：(类型编号, 实例键)，没有时为 None。"""
    session = Service.manager().sessions.get(playerId)
    if session is None:
        return None
    return session.instance.type.typeId, session.instance.key
