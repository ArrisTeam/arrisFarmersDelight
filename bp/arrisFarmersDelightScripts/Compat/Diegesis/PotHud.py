# -*- coding: utf-8 -*-
"""PotHud - 厨锅站点里只给本人看的东西：右侧的徽章和光标旁的提示（客户端）

对应 Hands-On Delight：client/PotBehavior.java 的 badge / drawDial / showGrade（873-950、1579-1660）和 tooltip（1113-1128）；
数都在 Shared/Rules/HandsOn/PotBadge.py 里，这里把它们交给前置包的像素牌和提示框。悬在汤上的容器和它浸汤的动作在 PotOffer.py。
- 徽章：锅里有菜可做（或煮好了）就在锅右边把手上方立一块牌：开放的星、菜、进度条；没火时是一个空火苗；一批出锅后
  星一颗颗亮起（那颗星的图弹一下、冒几点闪光）、多送了份数时叮几声并显示 +N。光标在菜上时提示"N × 菜 / 菜 / 菜，还要 S 秒"。
  牌是内核的 view.plate：每样东西一张贴图（rp/textures/ui/pot_badge/），没亮满的星和没走完的条靠图片裁切；
- 光标在漂着的料上：它的名字和个数；悬着容器 / 悬着要取回的东西时：这一下做什么（"盛出 …" / "取回 …"，JE 没有这行字）。
"""
import math

from . import PotFx
from .PotSceneFx import play
from ...Client.Engine import compFactory, levelId
from ...Shared.Rules.HandsOn import PotBadge

BADGE_AT = (-0.6, 14.5, 4.6)            # scenes/cooking_pot.json 的 badge 节点：锅右边把手上方（站点像素）
BADGE_TILT = math.radians(50.0)         # badge 节点朝镜头仰 50 度（rotation [-50, 0, 0]）：牌面上的"下"在场景里是往下、往镜头这边
APPEAR_FROM = 0.25                      # 镜头来了四分之一之后徽章才开始长出来
TIPS = {PotBadge.TIP_READY: "%d × %s", PotBadge.TIP_COOKING: "%s，还要 %d 秒", PotBadge.TIP_NAME: "%s"}
SCOOP_TIP, TAKE_TIP = "盛出 %s", "取回 %s"          # 悬着容器 / 悬着要取回的东西时，光标旁说这一下做什么
_names = {}


def nameOf(item):
    """物品的显示名（引擎给的是 utf-8 字节串，别和 unicode 混）。"""
    key = (item["newItemName"], int(item.get("newAuxValue") or 0))
    if key not in _names:
        info = compFactory.CreateItem(levelId).GetItemBasicInfo(key[0], key[1]) or {}
        _names[key] = info.get("itemName") or key[0]
    return _names[key]


class PotHud(object):
    def __init__(self, owner):
        self.owner = owner
        self.badge = PotBadge.PotBadge()

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
        if view.hand is not None:
            return None
        if not item:
            return self._offerTip(state)
        whole = getattr(view, "itemText", None)       # JE 是这件物品原版的整份提示；老版本的前置包没有这个接口，只写名字
        lines = list(whole(item)) if whole is not None else [nameOf(item)]
        if item["count"] > 1:
            lines[0] = "%s ×%d" % (lines[0], item["count"])
        return lines

    def _offerTip(self, state):
        """悬着容器 / 悬着要取回的东西：说这一下做什么。"""
        offered = self.owner.serve.offered
        if offered is None:
            return None
        back = offered[2]
        if back is not None:
            return [TAKE_TIP % nameOf({"newItemName": back})]
        return [SCOOP_TIP % state["mealName"]] if state["mealName"] else None

    # ---------------------------------------------------------------- 事件与收场

    def effect(self, name, data):
        if name == "served":
            self.badge.flash(True)              # 一批出锅：星一颗颗亮起

    def close(self):
        view = self.owner.view
        view.plate(None)
        view.tooltip(None)
