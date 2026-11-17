# -*- coding: utf-8 -*-
"""GrillView - 炉灶站点里本人的那一层：JE 的机位、底部托盘拿放、点烤位翻面或取下、食谱书（客户端）

对应 Hands-On Delight：client/StoveBehavior.java 的 onEvent / onItemClick / onOpen 和 scenes/stove.json（机位、命中盒）。
烤架上的画面（六件、落下 / 翻面 / 取走的动作、热浪蒸汽烟、声音）是谁都看得见的世界场景（StoveScene.py），这里只把本人的手交给它，
并照 JE 的规矩把点击变成动作：
- 机位照场景文件：相机 (8, 50.5, -21) 看 (8, 16, 8)，视野 30 度，0.4 秒，窗口窄时保住左右；没有提示行、没有抽屉（chrome 是 java）；
- 底部托盘（前置包按 usable 列出背包里烤得了的食物）点一叠就拿到手上；拿着一叠点烤架：左键每个空位摆一件，右键只摆离光标最近的
  空位那一个；Shift 点托盘里的食物直接整叠摆上去（槽规则放行，内核自己做）；
- Shift 点托盘里的一叠（前置包 onInventoryShiftClick 钩子，空手时先问这里）：有营火配方的整叠摆上去，发 place {from: 背包格号}，
  服务端放进去回 placed、放不进（蛋、满了）回 refused，落下 / 弹开大家都看得见；前置包没有这个钩子的老版本走内核自己的 QUICK_MOVE；
- 手空着：点烤位上的一件，生的、半熟的左键翻面（它跳起转半圈）、右键取下；烤好的左键右键都是取下；
- 触屏没有右键 / Shift，按住不动的菜单在 GrillHold.py（onHold）。
- 烤位上的东西是客户端掉落物，描不了边。JE 的炉灶场景开了 hover_outline，但件在 Diegesis 看来不是可交互节点（没有 slot / grabbable 的角色），
  既不描边也不抬起、也没有提示，只有该翻的那件冒烟示意：这里也一样，悬停不给任何反馈。
站点朝哪：炉灶是 JE 的 Orientation.BLOCK，登记时给前置包 facing 钩子（facingOf）：站点的北面永远是炉灶方块的正面，镜头永远在正面，
从背面、侧面右键也一样（服务端的 GrillOpen.facingOf 说同一个答案）。所以站点空间就是炉灶朝向的空间，HoD 场景（stove.json）里的像素坐标
（六件的位置、命中盒）直接用，不用换；场景里的画面、世界里的展示（Shared/Rules/BlockDisplay）按同一个朝向转到世界（Shared/Rules/StoveFacing），
炉灶朝哪都对得上。
开站时场景交给本人的有两样：从屏幕下沿飞来的起点、"我开着站点"（自己翻的不重复演）。
"""
from . import BookSources, FlatSprites, GrillHold, StoveScenes, TouchFeel
from .GrillSpace import Space
from ...Client.Engine import clientApi, compFactory, levelId, playerId
from ...Shared.Rules import GrillStation as Rules, StoveCover, StoveFacing
from ...Shared.Rules import HandsOnOptions as Options
from ...Shared.Rules.HandsOn import StoveLayout

CAMERA = {"pos": StoveLayout.CAMERA["pos"], "target": StoveLayout.CAMERA["target"], "fov": StoveLayout.CAMERA["fov"],
          "keepWidth": 16.0 / 9.0}
FLIGHT_SECONDS = 0.4
SCHEMA_MODULE = "arrisDiegesisScripts.Shared.Schema"   # 前置包的声明模块（StationSchema / SlotRules）


class GrillViewMixin(object):
    """和前置包的 StationBehavior 拼成表现类（register 里用 type() 组装）。self.api 是前置包的 Api.Client。"""

    camera = CAMERA
    flightSeconds = FLIGHT_SECONDS
    chrome = "java"
    workPlane = StoveLayout.WORK_PLANE         # 手上的物品栈画在 work_plane + carry_lift（2.5）的高度，stove.json 里 work_plane 是 17

    def __init__(self, view):
        super(GrillViewMixin, self).__init__(view)
        self.space = None                      # onOpen 里建
        self.scene = None                      # 这座炉灶的场景：画面、动作、声音都在它那里（没装场景时是 None，只剩点击和托盘）

    # ---------------------------------------------------------------- 钩子

    def usable(self, item):
        return Rules.usable(item.get("newItemName"))

    def mayDrop(self, group, index, item):
        return group == Rules.GROUP_GRILL and Rules.mayPlace(item)

    def onOpen(self):
        wanted = facingOf(self.view.pos, self.view.dimensionId)
        if self.view.yaw != wanted:      # 站点的坐标按炉灶朝向写：前置包没按朝向钩子开站（服务端给了别的朝向）就不能用，关站比摆错位置强
            raise RuntimeError("炉灶站点的朝向 %s 和炉灶方块的 %s 对不上（前置包的朝向钩子没生效？）" % (self.view.yaw, wanted))
        self.space = Space(self.view)
        self.scene = StoveScenes.ensure(self.view.dimensionId, self.view.pos)
        if self.scene is not None:
            self.scene.focus(self.space.fromPlayer, lambda kind: TouchFeel.buzz(self.view, kind))
        BookSources.attach(self.view, "grill")

    def onClose(self):
        scene, self.scene = self.scene, None
        if scene is not None:
            scene.blur()

    def onState(self, changes):
        BookSources.refresh(self.view)

    def onInventoryShiftClick(self, slot, item):
        """空手 Shift 点托盘里背包槽 slot 的那一叠（StoveBehavior.onInventoryShiftClick）：有营火配方的（蛋也算，服务端再弹回）发 place {from}，
        返回真 = 自己处理了，内核不再发 QUICK_MOVE；没有配方的返回假。"""
        if not item or not Rules.hasRecipe(item.get("newItemName")):
            return False
        self.view.sendAction("place", {"from": slot})
        return True

    # ---------------------------------------------------------------- 拾取

    def pickables(self):
        """拿着东西时整个烤架面是一块（mouth）；手空着时只有烤位上的件能点（点件旁边什么也不发生）。"""
        if self.scene is None:
            return []
        if self.view.hand is not None:
            return [self.api.box("mouth", *StoveLayout.MOUTH_BOX)]
        boxes = []
        for place in range(StoveLayout.PLACES):
            if self.scene.pieces.shown[place] is not None:
                lo, hi = StoveLayout.pieceBox(place)
                boxes.append(self.api.box("piece", lo, hi, payload=place))
        return boxes

    # ---------------------------------------------------------------- 指针

    def onPointer(self, event):
        key = event.hit.node.key if event.hit is not None else None
        payload = event.hit.node.payload if event.hit is not None else None
        if event.kind != "down":
            return False
        if self.view.hand is not None:
            if key != "mouth":
                return False                   # 右键点在别处：内核把手上的放回背包
            self._place(event)
            return True
        if key == "piece":
            self._piece(event, payload)
            return True
        return False

    onHold = GrillHold.onHold                 # 触屏长按（前置包的 onHold 钩子）：手上的东西只放这一格、翻得动的一件取下

    def _free(self):
        """哪些烤位空着：照站点的状态（服务端说了算），不看画着什么（画面可能还在落下 / 取走的动作里）。"""
        return [self.view.state.getItem((Rules.GROUP_GRILL, place)) is None for place in range(StoveLayout.PLACES)]

    def _place(self, event):
        """拿着一叠点烤架（StoveBehavior.onItemClick）：左键每个空位一件；右键只放离光标最近的空位那一个。"""
        nearest = -1
        if event.button == 1:
            centers = [(x, z) for x, _, z in self.space.centers()]
            nearest = StoveLayout.nearestFree(self.space.cursor(event.ray), centers, self._free())
        self.view.sendAction("place", StoveLayout.placeRequest(event.button, nearest))

    def _piece(self, event, place):
        """点烤位上的一件（StoveBehavior.onEvent）：右键取下；烤好的取下；否则翻面，它在空中的那一下不发。"""
        pieces = self.scene.pieces
        item = pieces.shown[place]
        if item is None:
            return
        action = StoveLayout.pieceClick(event.button, Rules.isDone(item["newItemName"]), pieces.clock - pieces.turnedAt[place])
        if action == StoveLayout.TAKE:
            self.view.sendAction("take", {"place": place})
            TouchFeel.buzz(self.view, TouchFeel.PICK)          # 触屏的轻震：取下 / 翻面点下去这一刻就震（不等服务端）；放上去 / 放不上去等服务端回话（StoveScene.event）
        elif action == StoveLayout.TURN:
            self.view.sendAction("turn", {"place": place})
            TouchFeel.buzz(self.view, TouchFeel.FLIP)
            pieces.turned(place)


def opensStation(pos, dimensionId):
    """这一下右键开不开站点（规则在 GrillStation.opens）：上面盖着锅、手里拿着炉灶自己用得上的东西时不开，方块原本的用法照常走。"""
    above = compFactory.CreateBlockInfo(levelId).GetBlock((pos[0], pos[1] + 1, pos[2]))
    held = compFactory.CreateItem(playerId).GetCarriedItem() or {}
    name = held.get("newItemName")
    info = compFactory.CreateItem(levelId).GetItemBasicInfo(name, held.get("newAuxValue") or 0) if name else None
    return Rules.opens(name, (info or {}).get("itemType") or "", StoveCover.covers(above[0] if above else None))


def facingOf(pos, dimensionId):
    """registerBehavior 的 facing(pos, dimensionId)：这座炉灶的站点朝哪（度，北 0 / 东 90 / 南 180 / 西 270）：站点的北面是炉灶方块的正面。
    读的是客户端的引擎，规则（StoveFacing.yawOfAux）和服务端的 GrillOpen.facingOf 同一份。"""
    block = compFactory.CreateBlockInfo(levelId).GetBlock(pos)
    return StoveFacing.yawOfAux(block[1] if block else 0)


def register(api):
    """前置包在场时调用：把 mixin 和前置包的 StationBehavior 拼成表现类并登记（schema 和服务端同一份）。
    炉灶站点要前置包 API 2（托盘、手上的物品栈）和朝向钩子（FACING_HOOK，站点的北面是炉灶的正面：场景、命中盒、世界里的展示都按这个空间写）：
    太旧的前置包上什么也不登记，炉灶照旧走经典玩法，返回 None；配置里关了炉灶站点（stove）也一样，和服务端的 GrillLogic.register 同一个条件。"""
    if not Options.stove() or getattr(api, "API_VERSION", 0) < 2 or not getattr(api, "FACING_HOOK", False):
        return None
    behaviorClass = type("StoveBehavior", (GrillViewMixin, api.StationBehavior), FlatSprites.attrs(api, {"api": api}))
    kit = getattr(api, "Schema", None) or clientApi.ImportModule(SCHEMA_MODULE)
    api.registerBehavior(Rules.STATION_ID, Rules.STOVE_BLOCKS, behaviorClass, schema=Rules.buildSchema(kit), canOpen=opensStation,
                         facing=facingOf)
    return behaviorClass
