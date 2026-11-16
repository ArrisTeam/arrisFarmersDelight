# -*- coding: utf-8 -*-
"""PotHud - 厨锅站点里只给本人看的东西：右侧的徽章、悬停提示、悬在汤上的容器和它盛汤的动作（客户端）

对应 Hands-On Delight：client/PotBehavior.java 的 badge / drawDial / showGrade（873-950、1579-1660）、offerBowl / scoop（542-618）
和 KitchenMotions.Dip；数都在 Shared/Rules/HandsOn 的 PotBadge / PotServe 里，这里把它们交给前置包的像素牌、提示框和道具。
- 徽章：锅里有菜可做（或煮好了）就在锅右边把手上方立一块牌：开放的星、菜、进度条；没火时是一个空火苗；一批出锅后
  星一颗颗亮起（那颗星的图弹一下、冒几点闪光）、多送了份数时叮几声并显示 +N。光标在菜上时提示"N × 菜 / 菜 / 菜，还要 S 秒"。
  牌是内核的 view.plate：每样东西一张贴图（rp/textures/ui/pot_badge/），没亮满的星和没走完的条靠图片裁切；
- 悬着的容器：汤煮好了、手空着、背包里有盛它的容器，光标在锅心 5 像素内就悬出那只容器；点一下它浸进汤里、盛满、
  提起来滴着汤、朝屏幕下方端走（同时发 scoop，容器从背包里扣）。基岩版的掉落物不能半透明，悬着的容器是实的。
- 取回沉下去的东西（offerTakeBack）：没有悬着的碗、汤里有倒进去 / 打进去 / 化掉的料，整个汤面接点击（PotView 里薄薄的一层 sunk，
  漂着的料比它高、照旧点得到）；光标在汤面上时悬出要取回的那样（液体是它的空容器，蛋和糖是它自己），点一下取回最后放的。
"""
import math

from . import PotFx
from .PotSceneFx import play
from ...Client.Engine import clientApi, compFactory, levelId, playerId
from ...Shared.Data import Remainders
from ...Shared.Rules import PotStation as Rules
from ...Shared.Rules.HandsOn import PotBadge, PotServe

BADGE_AT = (-0.6, 14.5, 4.6)            # scenes/cooking_pot.json 的 badge 节点：锅右边把手上方（站点像素）
BADGE_TILT = math.radians(50.0)         # badge 节点朝镜头仰 50 度（rotation [-50, 0, 0]）：牌面上的"下"在场景里是往下、往镜头这边
APPEAR_FROM = 0.25                      # 镜头来了四分之一之后徽章才开始长出来
AWAY_LIFT = 6.0                         # 端走时朝屏幕底边在汤面上方这么高的那一点去（PB 548）
TIPS = {PotBadge.TIP_READY: "%d × %s", PotBadge.TIP_COOKING: "%s，还要 %d 秒", PotBadge.TIP_NAME: "%s"}
_names = {}


def nameOf(item):
    """物品的显示名（引擎给的是 utf-8 字节串，别和 unicode 混）。"""
    key = (item["newItemName"], int(item.get("newAuxValue") or 0))
    if key not in _names:
        info = compFactory.CreateItem(levelId).GetItemBasicInfo(key[0], key[1]) or {}
        _names[key] = info.get("itemName") or key[0]
    return _names[key]


def _carries(name):
    """本人的背包里有没有这种容器。"""
    posType = clientApi.GetMinecraftEnum().ItemPosType.INVENTORY
    for item in compFactory.CreateItem(playerId).GetPlayerAllItems(posType, False) or []:
        if item and item.get("newItemName") == name and (item.get("count") or 0) > 0:
            return True
    return False


class PotHud(object):
    def __init__(self, owner):
        self.owner = owner
        self.badge = PotBadge.PotBadge()
        self.offered = None                 # 悬着的容器：[掉落物 id, 物品名]
        self.offer = None                   # PotServe.offerOf 的结果
        self.takesBack = False              # 汤面接不接"取回"的点击（PotServe.takeBackOf 的 enabled）
        self.dip = None                     # 正在盛的那一下：[PotServe.Dip, 掉落物 id, 换成成品了没有]
        self.scoopedAt = -10.0

    # ---------------------------------------------------------------- 每帧

    def frame(self, dt):
        owner, view, scene = self.owner, self.owner.view, self.owner.scene
        data = view.data
        state = self._state(data)
        model, events = self.badge.step(dt, state)
        if model is None:
            view.plate(None)
        else:
            grown = max(0.0, min(1.0, (view.arrival - APPEAR_FROM) / (1.0 - APPEAR_FROM)))
            view.plate({"at": BADGE_AT, "unit": model["unit"], "scale": grown * grown * (3.0 - 2.0 * grown), "sprites": model["sprites"],
                        "item": data.get("meal") or data.get("dish"), "itemRect": model["itemRect"]})
        for event in events:
            if event["type"] == "sound":
                play(event["name"], scene.world(8.0, 14.0, 8.0), event["volume"], event["pitch"])
            elif event["type"] == "glint" and model is not None:
                self._glint(event, model["unit"])
        view.tooltip(self._tip(state))
        self._offer(dt)

    def _glint(self, event, unit):
        """亮起的那颗星冒几点闪光：牌面上的 (x, y)（图标像素，+x 向右、+y 向下）换到场景里——镜头从 -z 看过来，右是 -x。"""
        x, y = event["x"] * unit, event["y"] * unit
        at = (BADGE_AT[0] - x, BADGE_AT[1] - y * math.sin(BADGE_TILT), BADGE_AT[2] - y * math.cos(BADGE_TILT))
        PotFx.particle(PotFx.GLINT, self.owner.view.toWorld(*at), color=event["color"] & 0xFFFFFF, count=event["count"], velocity=event["rise"])

    def _state(self, data):
        dish, meal = data.get("dish") or None, data.get("meal") or None
        look = self.owner.scene.look
        control = self.owner.view.state.getControl
        return {"here": True, "dish": bool(dish or meal), "meal": bool(meal), "ingredients": any(look.items),
                "heated": control("heated") > 0.5, "stirring": control("stirring") > 0.5, "progress": control("progress"),
                "stars": control("stars"), "grade": data.get("grade") or 0, "bonus": data.get("bonus") or 0,
                "openStars": data.get("open_stars") or 1, "servings": meal["count"] if meal else 0,
                "mealName": nameOf(meal) if meal else None, "dishName": nameOf(dish) if dish else None,
                "cookLeft": data.get("cook_left") or 0.0}

    def _tip(self, state):
        """光标在徽章的菜上：那道菜的提示；在漂着的料上：它的名字和个数。"""
        view = self.owner.view
        if view.plateHover:
            tip = self.badge.tooltip(state)
            return [TIPS[tip[0]] % tip[1]] if tip else None
        key, slot = self.owner.hover
        look = self.owner.scene.look
        item = look.items[slot] if key == "item" and slot is not None else (look.served if key == "served" else None)
        if not item or view.hand is not None:
            return None
        return [nameOf(item) if item["count"] <= 1 else "%s ×%d" % (nameOf(item), item["count"])]

    # ---------------------------------------------------------------- 盛出

    def _vessel(self):
        """这锅煮好的菜要的容器的物品名；没有菜、不要容器、背包里没有都是 None。"""
        data = self.owner.view.data
        vessel = data.get("vessel") or {}
        if not data.get("meal") or not vessel.get("newItemName"):
            return None
        return vessel["newItemName"] if _carries(vessel["newItemName"]) else None

    def _offer(self, dt):
        owner, scene = self.owner, self.owner.scene
        surface = scene.liquid.surfaceY()
        if self.dip is not None:
            self._dipping(dt, surface)
        vessel = self._vessel() if self.dip is None else None
        aim = scene.aim
        cursor = (8.0 + aim[0], 8.0 + aim[1]) if aim is not None else None
        spoon = owner.gesture.stroking or owner.hover[0] == "ladle"
        carrying = owner.view.hand is not None
        self.offer = PotServe.offerOf(cursor, surface, owner.clock, self.scoopedAt, True, spoon, carrying, vessel is not None, False,
                                      self.dip is not None)
        shown, place = (vessel, self.offer) if vessel is not None else (None, None)
        back = self._sunkItem() if self.offer is None else None
        self.takesBack, hung = PotServe.takeBackOf(cursor, surface, owner.clock, self.scoopedAt, True, spoon, carrying, self.offer is not None,
                                                   back is not None, self.dip is not None, owner.hover[0] == "sunk")
        if hung is not None:
            shown, place = Remainders.potRemainderOf(back) or back, hung       # 液体悬的是它的空容器，蛋和糖是它自己
        if place is None or shown is None:
            self._dropOffered()
            return
        if self.offered is None or self.offered[1] != shown:
            self._dropOffered()
            entityId = self._prop(shown, place["pos"])
            if entityId is None:
                return
            self.offered = [entityId, shown]
        x, y, z = place["pos"]
        scene.placeProp(self.offered[0], x, y, z, 0.0, 0.0, 0.0, place["size"] / 3.2)

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
        return compFactory.CreateItem(levelId).AddDropItemToWorld(one, scene.dimensionId, scene.world(*pos), 0, 0) or None

    def _dropOffered(self):
        if self.offered is not None:
            self.owner.scene.removeProp(self.offered[0])
            self.offered = None

    def sunkClick(self):
        """手空着点汤面（没有悬着的碗）：取回最后放进去的那样沉下去的料。"""
        if not self.takesBack:
            return False
        self.owner.view.sendAction("take_back", {})
        self._dropOffered()
        return True

    def soupClick(self, event):
        """手空着点汤、悬着容器：盛一份（Shift 全盛）。"""
        view, scene = self.owner.view, self.owner.scene
        if self.offer is not None and self.offered is not None:
            view.sendAction("scoop", {"all": bool(event.quick), "from_inventory": True})
            away = self.owner._starts(1)[0] or (0.0, -8.0)
            dip = PotServe.Dip(self.offer["pos"], (8.0 + away[0], scene.liquid.surfaceY() + AWAY_LIFT, 8.0 + away[1]),
                               self.offer["scale"], self.offer["size"], scene.liquid.color)
            self.dip, self.offered, self.offer = [dip, self.offered[0], False], None, None
            self.scoopedAt = self.owner.clock
            return True
        return False

    def _dipping(self, dt, surface):
        scene = self.owner.scene
        dip, entityId, filled = self.dip
        pose, events = dip.step(dt, surface)
        for event in events:
            kind = event["type"]
            if kind == "ripple":
                scene.model.ripple(event["x"], event["z"], event["strength"])
            elif kind == "splash":
                PotFx.particle(PotFx.SPLASH, scene.world(*event["pos"]), color=scene.liquid.brothColor, count=event.get("count"))
            elif kind == "drip":
                PotFx.particle(PotFx.DROPLET, scene.world(*event["pos"]), color=scene.liquid.brothColor)
            elif kind == "sound":
                play(event["name"], scene.world(8.0, surface, 8.0), event["volume"], event["pitch"])
        meal = self.owner.view.data.get("meal") or scene.look.meal
        if pose.get("filled") and not filled and meal:
            scene.removeProp(entityId)          # 盛满了：换成那道菜
            entityId = self._prop(meal["newItemName"], pose["pos"])
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
        PotFx.particle(PotFx.SPLASH, scene.world(x, scene.liquid.surfaceY(), z), color=scene.liquid.brothColor, count=4)
        self.scoopedAt = self.owner.clock

    # ---------------------------------------------------------------- 事件与收场

    def effect(self, name, data):
        if name == "served":
            self.badge.flash(True)              # 一批出锅：星一颗颗亮起

    def close(self):
        view = self.owner.view
        view.plate(None)
        view.tooltip(None)
        if self.owner.scene is not None:
            self._dropOffered()
            if self.dip is not None and self.dip[1] is not None:
                self.owner.scene.removeProp(self.dip[1])
        self.dip = None
