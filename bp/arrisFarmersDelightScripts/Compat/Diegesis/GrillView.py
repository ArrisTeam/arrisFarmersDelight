# -*- coding: utf-8 -*-
"""GrillView - 炉灶站点里本人的那一层：JE 的机位、底部托盘拿放、点烤位翻面或取下、食谱书（客户端）

对应 Hands-On Delight：client/StoveBehavior.java 的 onEvent / onItemClick / onOpen / onEffect 和 scenes/stove.json（机位、命中盒）。
烤架上的画面（六件、落下 / 翻面 / 取走的动作、热气蒸汽烟、声音）在 GrillPieces.py，这里把本人的手交给它，并照 JE 的规矩把点击变成动作：
- 机位、飞入照场景文件：相机 (8, 50.5, -21) 看 (8, 16, 8)，视野 30 度，0.4 秒，窗口窄时保住左右；没有提示行、没有抽屉（chrome 是 java）；
- 底部托盘（前置包按 usable 列出背包里烤得了的食物）点一叠就拿到手上；拿着一叠点烤架：左键每个空位摆一件，右键只摆离光标最近的
  空位那一个；Shift 点托盘里的食物直接整叠摆上去（槽规则放行，内核自己做）；
- 手空着：点烤位上的一件，生的、半熟的左键翻面（它跳起转半圈）、右键取下；烤好的左键右键都是取下；
- 烤位上的东西是客户端掉落物，描不了边。JE 的炉灶场景开了 hover_outline，但件在 Diegesis 看来不是可交互节点（没有 slot / grabbable 的角色），
  既不描边也不抬起，只有该翻的那件冒烟示意；这里补两样朴素的：光标悬着的那件抬起一点（Diegesis 给可交互节点的悬停抬起，0.6 px），
  旁边写出它的名字。HOVER_NAME 改成 False 就不写名字。
坐标：件的位置固定在方块里，按玩家所在的一侧换到站点空间（GrillSpace.py）；命中盒、世界里的展示和这里画的对得上。
"""
from . import BookSources
from .GrillPieces import Pieces
from .GrillSpace import Space
from ...Client import BlockItems
from ...Client.Engine import clientApi, compFactory, levelId, playerId
from ...Shared.Rules import GrillStation as Rules
from ...Shared.Rules.HandsOn import StoveLayout

CAMERA = {"pos": StoveLayout.CAMERA["pos"], "target": StoveLayout.CAMERA["target"], "fov": StoveLayout.CAMERA["fov"],
          "keepWidth": 16.0 / 9.0}
FLIGHT_SECONDS = 0.4
SCHEMA_MODULE = "arrisDiegesisScripts.Shared.Schema"   # 前置包的声明模块（StationSchema / SlotRules）
HOVER_NAME = True                                      # 悬着一件时旁边写它的名字（JE 没有；去掉就是 False）
AGAIN = 0.6                                            # 自己翻的这一下已经演过了：服务端说"翻了"的 0.6 秒内不重复演（onEffect 里 TURNED）
_names = {}


def nameOf(item):
    """物品的显示名（引擎给的是 utf-8 字节串，别和 unicode 混）。"""
    key = (item["newItemName"], int(item.get("newAuxValue") or 0))
    if key not in _names:
        info = compFactory.CreateItem(levelId).GetItemBasicInfo(key[0], key[1]) or {}
        _names[key] = info.get("itemName") or key[0]
    return _names[key]


def _place(data):
    """服务端发来的位置序号：0..5 的整数才算，别的是 None。"""
    value = data.get("place") if isinstance(data, dict) else None
    return int(value) if isinstance(value, (int, type(2 ** 64))) and not isinstance(value, bool) and 0 <= value < StoveLayout.PLACES else None


class GrillViewMixin(object):
    """和前置包的 StationBehavior 拼成表现类（register 里用 type() 组装）。self.api 是前置包的 Api.Client。"""

    camera = CAMERA
    flightSeconds = FLIGHT_SECONDS
    chrome = "java"
    workPlane = StoveLayout.WORK_PLANE         # 手上的物品栈画在 work_plane + carry_lift（2.5）的高度，stove.json 里 work_plane 是 17

    def __init__(self, view):
        super(GrillViewMixin, self).__init__(view)
        self.space = Space(view)
        self.pieces = Pieces(view, self.space)
        self.hover = None                      # 光标悬着的那一件（序号），没有是 None

    # ---------------------------------------------------------------- 钩子

    def usable(self, item):
        return Rules.usable(item.get("newItemName"))

    def mayDrop(self, group, index, item):
        return group == Rules.GROUP_GRILL and Rules.mayPlace(item)

    def onOpen(self):
        BlockItems.hide(self.view.dimensionId, self.view.pos, True)     # 开站期间本端不画世界里的那份，关站时还原
        self.pieces.refresh()
        BookSources.attach(self.view, "grill")

    def onClose(self):
        BlockItems.hide(self.view.dimensionId, self.view.pos, False)
        self.view.tooltip(None)

    def onState(self, changes):
        self.pieces.refresh()
        BookSources.refresh(self.view)

    def onEffect(self, name, data):
        pieces, place = self.pieces, _place(data)
        if name == "placed":
            pieces.placed(data.get("places") if isinstance(data, dict) else None)
        elif name == "refused":
            pieces.refused(data.get("stack"))
        elif name == "turned" and place is not None and pieces.clock - pieces.turnedAt[place] > AGAIN:
            pieces.turned(place, data.get("up"))       # 自己翻的已经演过了
        elif name == "unturned" and place is not None:
            pieces.unturned(place)
        elif name == "taken" and place is not None:
            pieces.taken(place, data.get("stack"))
        elif name == "grilled" and place is not None:
            pieces.grilled(place)

    def frame(self, dt):
        self.pieces.frame(dt, self.hover)
        item = self.pieces.shown[self.hover] if self.hover is not None else None
        self.view.tooltip([nameOf(item)] if HOVER_NAME and item is not None and self.view.hand is None else None)

    # ---------------------------------------------------------------- 拾取

    def pickables(self):
        """拿着东西时整个烤架面是一块（mouth）；手空着时只有烤位上的件能点（点件旁边什么也不发生）。"""
        if self.view.hand is not None:
            return [self.space.box(self.api, "mouth", *StoveLayout.MOUTH_BOX)]
        boxes = []
        for place in range(StoveLayout.PLACES):
            if self.pieces.shown[place] is not None:
                lo, hi = StoveLayout.pieceBox(place)
                boxes.append(self.space.box(self.api, "piece", lo, hi, place))
        return boxes

    # ---------------------------------------------------------------- 指针

    def onPointer(self, event):
        key = event.hit.node.key if event.hit is not None else None
        payload = event.hit.node.payload if event.hit is not None else None
        if event.kind == "move":
            self.hover = payload if key == "piece" and self.view.hand is None else None
            return False
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

    def _place(self, event):
        """拿着一叠点烤架（StoveBehavior.onItemClick）：左键每个空位一件；右键只放离光标最近的空位那一个。"""
        nearest = -1
        if event.button == 1:
            centers = [(x, z) for x, _, z in self.space.centers()]
            nearest = StoveLayout.nearestFree(self.space.cursor(event.ray), centers, self.pieces.free())
        self.view.sendAction("place", StoveLayout.placeRequest(event.button, nearest))

    def _piece(self, event, place):
        """点烤位上的一件（StoveBehavior.onEvent）：右键取下；烤好的取下；否则翻面，它在空中的那一下不发。"""
        pieces = self.pieces
        item = pieces.shown[place]
        if item is None:
            return
        action = StoveLayout.pieceClick(event.button, Rules.isDone(item["newItemName"]), pieces.clock - pieces.turnedAt[place])
        if action == StoveLayout.TAKE:
            self.view.sendAction("take", {"place": place})
        elif action == StoveLayout.TURN:
            self.view.sendAction("turn", {"place": place})
            pieces.turned(place)


def opensStation(pos, dimensionId):
    """这一下右键开不开站点（规则在 GrillStation.opens）：上面盖着锅、手里拿着炉灶自己用得上的东西时不开，方块原本的用法照常走。"""
    above = compFactory.CreateBlockInfo(levelId).GetBlock((pos[0], pos[1] + 1, pos[2]))
    held = compFactory.CreateItem(playerId).GetCarriedItem() or {}
    name = held.get("newItemName")
    info = compFactory.CreateItem(levelId).GetItemBasicInfo(name, held.get("newAuxValue") or 0) if name else None
    return Rules.opens(name, (info or {}).get("itemType") or "", bool(above and above[0] != "minecraft:air"))


def register(api):
    """前置包在场时调用：把 mixin 和前置包的 StationBehavior 拼成表现类并登记（schema 和服务端同一份）。
    炉灶站点要前置包 API 2（托盘、手上的物品栈）：太旧的前置包上什么也不登记，炉灶照旧走经典玩法，返回 None。"""
    if getattr(api, "API_VERSION", 0) < 2:
        return None
    behaviorClass = type("StoveBehavior", (GrillViewMixin, api.StationBehavior), {"api": api})
    kit = getattr(api, "Schema", None) or clientApi.ImportModule(SCHEMA_MODULE)
    api.registerBehavior(Rules.STATION_ID, Rules.STOVE_BLOCKS, behaviorClass, schema=Rules.buildSchema(kit), canOpen=opensStation)
    return behaviorClass
