# -*- coding: utf-8 -*-
"""AnimalFood - 原版猫 / 鸡 / 猪 / 兔子 / 鹦鹉 / 狼认农夫乐事的食物：运行时给实体加组件（服务端）

不覆盖原版的实体文件（同路径的文件整份替换、游戏升级后要重新生成，别的包也覆盖时只有一份生效），照森罗物语（厨房）的做法：
1. 读包栈里生效的实体定义：entities/<短名>.json（几个包都有这个路径时是优先级最高的那份；identifier 对不上时退一步扫 entities/ 找），
   经 Helpers/PackJson（引擎内部的 server_resource）。别的包改过的定义就在它上面追加。读不到、看不懂：这只动物不做，记一次日志，不再试。
2. Shared/Rules/AnimalFood.plan 按定义算出每个组件在每个出处（顶层或某个组件组）追加本包条目以后的 JSON 串，按实体类型记着。
3. 实体出现（AddEntityServerEvent，读档、区块加载也来）、定义里会加减这些组件组的事件（EntityDefinitionsEventServerEvent，
   事件名从定义里读：出生、长大、驯服……）之后都晚两拍（DELAY），按 GetEntityDefinitions 的定义栈算出实体现在真有的那几个组件，
   再对着 GetComponents 读回的现值（Rules.merged）：本包的条目都在了就不发；要发的接上别的模组加的条目再发。
   晚是因为加减组件组下一帧才生效（官方 TriggerCustomEvent 的备注；森罗物语实机复现过：只在出现那一拍打，小鸡的 ageable 还是原版的）；
   晚两拍是排在森罗物语厨房后面：它也在下一帧照定义整份打鸡的那几个组件，我们读回它的、合并以后再打，两家的东西都在。
   换组以后组件回到定义里的值，所以换组事件之后都再看一遍。重复 AddActorComponent 同一个组件是覆盖（官方文档）。
不相干的实体零开销：AddEntityServerEvent 按实体类型匹配，EntityDefinitionsEventServerEvent 按事件名匹配（读过的定义里的事件名）。
数据 Shared/Data/Mobs.ANIMAL_FOOD；马饲料 / 狗粮、马和狼的吸引 / 讨食是 Server/Livestock.py。
"""
from .EventRegistry import registerHandler
from .Helpers import PackJson
from .Helpers.Engine import compFactory, levelId, GetEngineTypeStr
from ..Shared.Data.Mobs import ANIMAL_FOOD
from ..Shared.Rules import AnimalFood as Rules

DELAY = 0.1         # 晚两拍：森罗物语厨房在下一帧（AddTimer 0）照定义整份打鸡的 tempt / ageable / breedable，我们排在它后面读回、合并
_plans = {}         # 实体类型 -> Rules.Plan，读不到 / 看不懂的是 None（记一次，不再试）
_events = set()     # 读过的定义里会换这几个组件所在组件组的事件名（活的：EntityDefinitionsEventServerEvent 按它匹配）
_unread = set()     # 定义栈读不懂、已经记过日志的实体类型


def _scan(entityType):
    """entities/<短名>.json 不是这只动物时退一步：列 entities/ 下的全部文件（子目录也进去），文本里有这个 identifier 的才解析。"""
    pending, seen = list(PackJson.listing(Rules.ENTITIES) or ()), set()
    while pending:
        path = pending.pop(0)
        if path in seen:
            continue
        seen.add(path)
        if not path.endswith(".json"):
            pending.extend(PackJson.listing(path) or ())
            continue
        text = PackJson.read(path)
        if text and ('"%s"' % entityType) in text:
            definition = Rules.parse(text, entityType)
            if definition is not None:
                return definition
    return None


def planOf(entityType):
    """这种动物的补丁（第一次用时读定义、算好记着）；读不到 / 看不懂是 None。"""
    if entityType in _plans:
        return _plans[entityType]
    definition = Rules.parse(PackJson.read(Rules.definitionPath(entityType)), entityType) or _scan(entityType)
    plan = Rules.plan(definition, ANIMAL_FOOD[entityType]) if definition is not None else None
    if plan is None:
        print("[arrisFarmersDelight] %s：%s，不认农夫乐事的食物" % (entityType, "读不到实体定义" if definition is None else "定义里没有能补的组件"))
    else:
        if plan.missing or plan.unreadable:
            print("[arrisFarmersDelight] %s：定义里没有 %r、看不懂 %r，这几处不补" % (entityType, plan.missing, plan.unreadable))
        _events.update(plan.events)
    _plans[entityType] = plan
    return plan


def apply(entityId):
    """按实体现在的组件组、对着它现在的组件值下发补过的组件；实体没了、不是这几种动物、本包的条目都在了：什么都不发。"""
    entityType = GetEngineTypeStr(entityId)
    plan = _plans.get(entityType) if entityType else None
    if plan is None:
        return
    stack = compFactory.CreateEntityDefinitions(entityId).GetEntityDefinitions()
    if Rules.current(plan, stack) is None and entityType not in _unread:
        _unread.add(entityType)
        print("[arrisFarmersDelight] %s 的定义栈读不懂（%r）：只下发顶层的组件" % (entityType, stack))
    sends = Rules.send(plan, stack)
    if not sends:
        return
    eventComp = compFactory.CreateEntityEvent(entityId)
    for name, value in Rules.merged(plan, sends, eventComp.GetComponents()):
        eventComp.AddActorComponent(name, value)


@registerHandler("AddEntityServerEvent", match=ANIMAL_FOOD)
def OnAnimalAdded(args):
    if planOf(args["engineTypeStr"]) is not None:
        compFactory.CreateGame(levelId).AddTimer(DELAY, apply, args["id"])


@registerHandler("EntityDefinitionsEventServerEvent", match=_events)
def OnAnimalGroupsChanged(args):
    entityId = args["entityId"]
    plan = _plans.get(GetEngineTypeStr(entityId))
    if plan is not None and args["eventName"] in plan.events:
        compFactory.CreateGame(levelId).AddTimer(DELAY, apply, entityId)
