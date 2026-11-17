# -*- coding: utf-8 -*-
"""PotOffer - 悬在汤上"点一下就做"的东西：盛汤的容器、要取回的那样，和它浸进汤里的动作（客户端）

对应 Hands-On Delight：client/PotBehavior.java 的 offerBowl / offerTakeBack / dipOffered（541-666）和 KitchenMotions.Dip；
数都在 Shared/Rules/HandsOn/PotServe.py 里。
- 悬着的容器：汤煮好了、手空着、背包里有盛它的容器，光标在锅心 5 像素内就悬出那只容器；点一下它浸进汤里、盛满、
  提起来滴着汤、朝屏幕下方端走（同时发 scoop，容器从背包里扣）。
- 方块容器（南瓜盅用的南瓜，isFilledNotDipped）不浸进汤里：缩小了悬在锅沿上方（FILLED_SCALE / FILLED_LIFT），点一下汤从锅心朝它
  溅 8 滴、舀进去；
- 取回沉下去的东西（offerTakeBack）：没有悬着的碗、汤里有倒进去 / 打进去 / 化掉的料，整个汤面接点击（PotView 里薄薄的一层 sunk，
  漂着的料比它高、照旧点得到）；光标在汤面上时悬出要取回的那样（液体是它的空容器，蛋和糖是它自己），点一下它浸下去、
  舀回来（变回装满的桶 / 瓶）、端给厨师（dipOffered），东西回背包。倒进去的桶和瓶在锅里留到这一锅煮好才把空的还回背包。
悬着的东西是"点一下就做"的提议，不是拿在手上的：JE 把它画成半透明（OFFERED）。客户端掉落物染不了色也透不了明，所以用内核的
view.ghost（界面上一件半透明的物品，钉在那个点的投影上，锅挡不住它）；点下去之后浸进汤里的那只才是世界里的掉落物。
光标旁写一行这一下做什么（"盛出 …" / "取回 …"，JE 没有这行字）。触屏没有悬停：第一下点在汤面上只是让它悬出来，再点一下才做。
"""
from . import PotFx, PotPick
from .PotSceneFx import play
from ...Client.Engine import addDropItem, clientApi, compFactory, levelId, playerId
from ...Shared.Data import Remainders
from ...Shared.Rules import PotStation as Rules
from ...Shared.Rules.HandsOn import PotServe, PotSounds

AWAY_LIFT = 6.0                         # 端走时朝屏幕底边在汤面上方这么高的那一点去（PB 548）


def _carries(name):
    """本人的背包里有没有这种容器。"""
    posType = clientApi.GetMinecraftEnum().ItemPosType.INVENTORY
    for item in compFactory.CreateItem(playerId).GetPlayerAllItems(posType, False) or []:
        if item and item.get("newItemName") == name and (item.get("count") or 0) > 0:
            return True
    return False


class PotOffer(object):
    def __init__(self, owner):
        self.owner = owner
        self.offered = None                 # 悬着的东西：(画成什么物品, PotServe 给的位置大小, 取回的是什么物品 / 盛汤时 None)
        self.offer = None                   # PotServe.offerOf 的结果
        self.takesBack = False              # 汤面接不接"取回"的点击（PotServe.takeBackOf 的 enabled）
        self.dip = None                     # 正在浸的那一下：[PotServe.Dip, 掉落物 id, 换成装满的了没有, 装满是什么物品]
        self.scoopedAt = -10.0
        self.scoopedHere = -10.0            # 手上拿着容器点汤的那一下（碗落进去的地方已经敲过水波）
        self.ladled = None                  # 刚往方块容器里舀：它悬在哪（锅自己的坐标），等服务端说盛了就朝它溅几滴
        self._blocks = {}

    def _vessel(self):
        """这锅煮好的菜要的容器的物品名；没有菜、不要容器、背包里没有都是 None。"""
        data = self.owner.view.data
        vessel = data.get("vessel") or {}
        if not data.get("meal") or not vessel.get("newItemName"):
            return None
        return vessel["newItemName"] if _carries(vessel["newItemName"]) else None

    def frame(self, dt):
        owner, scene = self.owner, self.owner.scene
        surface = scene.liquid.surfaceY()
        if self.dip is not None:
            self._dipping(dt, surface)
        vessel = self._vessel() if self.dip is None else None
        cursor = self.cursorOn(surface + PotServe.OFFER_LIFT)
        spoon = owner.gesture.stroking or owner.hover[0] == "ladle"
        carrying = owner.view.hand is not None
        self.offer = PotServe.offerOf(cursor, surface, owner.clock, self.scoopedAt, True, spoon, carrying, vessel is not None,
                                      vessel is not None and self._isBlock(vessel), self.dip is not None)
        shown, place = (vessel, self.offer) if vessel is not None else (None, None)
        back = self._sunkItem() if self.offer is None else None
        self.takesBack, hung = PotServe.takeBackOf(cursor, surface, owner.clock, self.scoopedAt, True, spoon, carrying, self.offer is not None,
                                                   back is not None, self.dip is not None, owner.hover[0] == "sunk")
        if hung is not None:
            shown, place = Remainders.potRemainderOf(back) or back, hung       # 液体悬的是它的空容器，蛋和糖是它自己
        if place is None or shown is None:
            self._dropOffered()
            return
        self.offered = (shown, place, back if hung is not None else None)
        owner.view.ghost({"item": {"newItemName": shown, "newAuxValue": 0, "count": 1}, "at": owner.toStation(*place["pos"]),
                          "size": place["size"]})

    def _isBlock(self, name):
        """这个容器是方块（南瓜）：往里舀，不浸下去（PotBehavior.isFilledNotDipped）。"""
        if name not in self._blocks:
            info = compFactory.CreateItem(levelId).GetItemBasicInfo(name, 0) or {}
            self._blocks[name] = info.get("itemType") == "block"
        return self._blocks[name]

    def scooped(self):
        """服务端说盛了一份（scooped 效果）。返回"本人这一下已经敲过水波了"（正浸着碗，或刚拿着碗点过汤）：场景就只放声音。
        刚往方块容器里舀的，汤从锅心朝它溅 8 滴（PotBehavior.onEffect）。"""
        owner, scene = self.owner, self.owner.scene
        if self.ladled is not None:
            surface = scene.liquid.surfaceY()
            rise = (self.ladled[0] - 8.0, self.ladled[1] - surface, self.ladled[2] - 8.0)
            a, b = scene.world(8.0, surface, 8.0), scene.world(8.0 + rise[0], surface + rise[1], 8.0 + rise[2])
            PotFx.particle(PotFx.DROPLET, a, color=scene.liquid.brothColor, count=PotServe.LADLED_DROPS,
                           velocity=tuple((b[i] - a[i]) * 16.0 for i in range(3)))
            self.ladled = None
        return self.dip is not None or owner.clock - self.scoopedHere <= PotServe.BYSTANDER_WINDOW

    def cursorOn(self, height):
        """光标射线落在这个高度的水平面上的哪一点（锅自己的坐标 (x, z)，PotBehavior 的 view.cursorOn）：悬着的东西正好在光标底下。
        没有光标（触屏点完之后）None。"""
        owner = self.owner
        point = owner.api.Geometry.planeAtHeight(owner.ray, height) if owner.ray is not None else None
        if point is None:
            return None
        x, _, z = owner.toLocal(point)
        return (x, z)

    def overSoup(self):
        """光标在不在汤上（锅心 5 像素内，PotBehavior.bowlOverSoup）。"""
        cursor = self.cursorOn(self.owner.scene.liquid.surfaceY())
        half, centre = PotServe.POT_HALF, PotServe.POT_CENTER
        return cursor is not None and abs(cursor[0] - centre) < half and abs(cursor[1] - centre) < half

    def offering(self):
        """锅身描不描边（PotBehavior 的 offering）：手上的东西放得进、光标在锅口上；拿着盛这道菜的容器、光标在汤上；悬着碗。
        触屏没有悬停：手上拿着放得进的东西（或那只容器）就描。"""
        owner, view = self.owner, self.owner.view
        hand, touch = view.hand, view.input == owner.api.TOUCH
        if hand is None:
            return self.offered is not None and self.offered[2] is None
        if PotPick.holdsVessel(view):
            return touch or self.overSoup()
        return (touch or owner.hover[0] == "mouth") and view.fits(Rules.GROUP_INGREDIENTS) is not None

    def _sunkItem(self):
        """最后一个装着沉下去的料的格子里是什么（物品名），没有是 None。"""
        look = self.owner.scene.look
        for slot in sorted(self.owner.view.data.get("sunk") or [], reverse=True):
            item = look.items[slot] if 0 <= slot < len(look.items) else None
            if item:
                return item["newItemName"]
        return None

    def _prop(self, name, pos):
        scene = self.owner.scene
        one = {"newItemName": name, "newAuxValue": 0, "count": 1}
        return addDropItem(one, scene.dimensionId, scene.world(*pos))

    def _dropOffered(self):
        if self.offered is not None:
            self.offered = None
            self.owner.view.ghost(None)

    def sunkClick(self):
        """手空着点汤面、悬着要取回的那样：取回最后放进去的沉下去的料。还没悬出来（触屏的第一下）不算，先让它悬出来。"""
        if not self.takesBack or self.offered is None or self.offered[2] is None:
            return False
        shown, place, back = self.offered
        self.owner.view.sendAction("take_back", {})
        self._dipOffered(shown, place, back, PotSounds.shotOf("scoopBack"))
        return True

    def soupClick(self, event):
        """手空着点汤、悬着容器：盛一份（Shift 全盛）。"""
        view = self.owner.view
        if self.offer is None or self.offered is None:
            return False
        meal = view.data.get("meal") or self.owner.scene.look.meal
        view.sendAction("scoop", {"all": bool(event.quick), "from_inventory": True})
        if self.offer["block"]:              # 方块容器不浸：记下它悬在哪，等服务端说盛了朝它溅几滴
            self.ladled, self.offer, self.scoopedAt = self.offer["pos"], None, self.owner.clock
            self._dropOffered()
            return True
        self._dipOffered(self.offered[0], self.offer, meal["newItemName"] if meal else None)
        return True

    def _dipOffered(self, shown, place, filled, sound=None):
        """悬着的那样在原地浸进汤里、装满（换成 filled）、提起来滴着汤、朝屏幕下方端给厨师（PotBehavior.dipOffered）。
        从这一刻起它是世界里的一件掉落物，半透明的那件收起。"""
        scene = self.owner.scene
        away = self.owner._starts(1)[0] or (0.0, -8.0)
        dip = PotServe.Dip(place["pos"], (8.0 + away[0], scene.liquid.surfaceY() + AWAY_LIFT, 8.0 + away[1]),
                           place["scale"], place["size"], scene.liquid.color, sound)
        self.dip = [dip, self._prop(shown, place["pos"]), False, filled]
        self.offer = None
        self._dropOffered()
        self.scoopedAt = self.owner.clock

    def _dipping(self, dt, surface):
        scene = self.owner.scene
        dip, entityId, filled, full = self.dip
        pose, events = dip.step(dt, surface)
        for event in events:
            kind = event["type"]
            if kind == "ripple":
                scene.model.ripple(event["x"], event["z"], event["strength"])
            elif kind == "splash":
                PotFx.particle(PotFx.SPLASH, scene.world(*event["pos"]), color=scene.liquid.brothColor, count=event.get("count"),
                               velocity=event["rise"])
            elif kind == "drip":
                PotFx.particle(PotFx.DROPLET, scene.world(*event["pos"]), color=scene.liquid.brothColor)
            elif kind == "sound":
                play(event["name"], scene.world(8.0, surface, 8.0), event["volume"], event["pitch"])
        if pose.get("filled") and not filled and full:
            scene.removeProp(entityId)          # 装满了：换成那道菜 / 取回的那样
            entityId = self._prop(full, pose["pos"])
            self.dip[1], self.dip[2] = entityId, True
        if dip.done or entityId is None or not pose.get("visible", True):
            if entityId is not None:
                scene.removeProp(entityId)
            self.dip = None
            return
        x, y, z = pose["pos"]
        size = dip.half / 0.3 * pose["scale"] / max(dip.scale, 1.0e-6)      # 此刻画多大（像素）
        scene.placeProp(entityId, x, y, z, 0.0, pose["rot"][0], 0.0, size / 3.2)

    def bowlWentIn(self, point):
        """手上拿着容器点了汤：容器下去的地方一圈水波、溅几点（PotServe.carriedBowlOn）。"""
        scene = self.owner.scene
        if point is None:
            return
        x, _, z = self.owner.toLocal(point)
        scene.model.ripple(x, z, 0.45)
        PotFx.particle(PotFx.SPLASH, scene.world(x, scene.liquid.surfaceY(), z), color=scene.liquid.brothColor, count=PotServe.SPLASHES,
                       velocity=PotServe.SPLASH_RISE)
        self.scoopedAt = self.scoopedHere = self.owner.clock

    def close(self):
        self._dropOffered()
        if self.owner.scene is not None and self.dip is not None and self.dip[1] is not None:
            self.owner.scene.removeProp(self.dip[1])
        self.dip = None
