# -*- coding: utf-8 -*-
"""FryTints - 煎锅 / 炉灶上煎着的东西朝上那面的熟色：每件叠一颗同一图标的半透明粒子（客户端）

对应 Hands-On Delight：SkilletBehavior.drawPiece（327 行）/ StoveBehavior.draw（206 行）的 node.setTint(KitchenLooks.fryingTint(...))——JE 把整件乘上一个颜色：
朝上那面没熟时画生的图、往熟色走（肉和鱼再带一点焦色，最多染到七成），熟了换成熟的图、不染。基岩版的客户端掉落物染不了色，所以给每件要染的、
躺着不动的食物在它朝上那面上叠一颗粒子 arris:fry_tint（rp/particles/arris_fry_tint.json：平躺的四边形 emitter_transform_xz、particles_blend、
贴图是物品图集 atlas.items，图标在图集里的位置由 GetIconInfo 给；颜色、不透明度、半边长、图标 UV 都是变量；跟着环境光），一个发射器只发一颗、
活到被删（同前置包画影子的 Client/Shade.py）。颜色在 Shared/Rules/FryingTint（生熟两张图的主色、肉和鱼、alpha 混合怎么近似整件相乘），
摆在哪、什么时候亮在 Shared/Rules/TopOverlay。场景（PanScene、StoveScene）每帧把"这一帧要染的件"交进来（panWanted / stoveWanted）。
- 掉落物一动（落下、颠起、翻面、挪位、换了大小）粒子就收着（不透明度 0，粒子留着），停稳 TopOverlay.SETTLE 秒再摆好、亮出来：掉落物的位置按游戏刻插值、
  晚到一两帧，粒子不晚，动着的时候对不齐；斜着的件不染（停着的件都平躺朝上）；
- 不用染了（件拿走了、熟了换成熟的图、朝上那面还生着、换成别的东西、场景收掉）：粒子删掉；
- 没变的不碰引擎：每帧只比一下掉落物的样子和要染的颜色，变了的才发；
- 进世界头几秒图集和粒子系统还没好（GetIconInfo 回 None、Create 回 0）：这一帧不画，下一帧再试；老引擎没有 GetIconInfo（3.10 之前）：一件都不染。
和 JE 不一样的：只染朝上那面的顶面（JE 连底面、四边一起乘），只在停着时染（JE 飞着、翻着也染着）。蛋是 EggLook 那几件预染色的显示物品，不叠；
物品类型是方块的（画成立方体的、画成平面却按方块抬高的，Shared/Data/FlatBlockItems）不叠，营火配方里没有（海带实机看过：itemType 是空串、
掉落物是普通的平面贴图，照染）；下游追加、表里没有颜色的不染。实机核对（2026-11-22，测试的会话 tint）：俯视、斜 30°、四个炉灶朝向都盖得严，
白天 / 夜里 / 方块光下受光和掉落物一样，颠锅、翻面时收起、落稳 0.1 秒后按翻上来那面的颜色再亮。
"""
from ...Client.Engine import compFactory, levelId
from ...Shared.Rules import FryingTint, GrillStation, PanStation, TopOverlay

PARTICLE = "arris:fry_tint"
DIGITS = 4                    # 位置、变量比到小数点后几位，没变的不重发（图集里一个像素约 0.001，颜色一档 1/255 约 0.004）
TINTED = ("piece", "under")   # 煎锅里要染的节点：上面的、垫在下面的（lift 是走的替身、hand / spill 是磕蛋的手和蛋液：JE 给替身染白）
_icons = {}                   # (物品名, aux) -> 图标在 atlas.items 里的 (u, v, 宽, 高)：只记问到了的
_blocks = {}                  # (物品名, aux) -> 物品类型是不是方块：只记问到了的
_engine = {"icons": None}     # 这台引擎有没有 GetIconInfo（第一次问的时候记下；None = 还没问）


def _iconOf(kind):
    """这件物品的图标在 atlas.items 里的位置；问不到（老引擎、进世界头几秒图集还没好）返回 None，没问到的不记，下次再问。"""
    found = _icons.get(kind)
    if found is None and _engine["icons"] is not False:
        ask = getattr(compFactory.CreateItem(levelId), "GetIconInfo", None)      # 3.10 起才有：老引擎上一件都不染
        _engine["icons"] = ask is not None
        found = ask({"itemName": kind[0], "auxValue": kind[1]}) if ask is not None else None
        if not found:
            return None
        found = _icons[kind] = tuple(float(value) for value in found)
    return found


def _isBlock(kind):
    """物品类型是方块（GetItemBasicInfo 的 itemType）：掉落物不是一张贴图物品，图标也不在 atlas.items 里。"""
    found = _blocks.get(kind)
    if found is None:
        info = compFactory.CreateItem(levelId).GetItemBasicInfo(kind[0], kind[1])
        if not info:
            return True                       # 还问不到：这一帧先不画
        found = _blocks[kind] = info.get("itemType") == "block"
    return found


class TopTint(object):
    """一件掉落物朝上那面叠的那颗粒子。follow 每帧调一次；remove 删掉。"""

    __slots__ = ("particleId", "still", "lit", "color", "sent")

    def __init__(self):
        self.particleId = None
        self.still = TopOverlay.Stillness()
        self.lit = False                      # 亮着（不透明度不是 0）
        self.color = None                     # 亮着的那个 (r, g, b, a)
        self.sent = {}                        # 送给引擎的最后一份：位置、转角、每个变量

    def follow(self, dt, kind, center, matrix, scale, color):
        """kind：画的物品 (名字, aux)；center / matrix / scale：这件掉落物这一帧的中心、姿态（世界）和缩放（引擎没收下是 None）；
        color：FryingTint.overlay 的 (r, g, b, a)。停稳了、颜色也没变就什么都不做。"""
        if not self.still.step(dt, (kind, center, matrix, scale)) or scale is None:
            self._dim()
            return
        if self.lit and color == self.color:
            return
        frame = TopOverlay.frameOf(center, matrix, scale)
        uv = None if frame is None or _isBlock(kind) else _iconOf(kind)
        if uv is None or not self._made(frame["pos"]):
            self._dim()
            return
        system = compFactory.CreateParticleSystem(None)
        pos = tuple(round(value, DIGITS) for value in frame["pos"])
        if self.sent.get("pos") != pos:
            self.sent["pos"] = pos
            system.SetPos(self.particleId, pos)
        if self.sent.get("rot") != frame["rot"]:
            self.sent["rot"] = frame["rot"]
            system.SetRot(self.particleId, frame["rot"])
        for name, value in zip(("u", "v", "w", "h", "half", "r", "g", "b", "alpha"), uv + (frame["half"],) + tuple(color)):
            self._send(system, "variable." + name, value)
        self.lit, self.color = True, color

    def _made(self, pos):
        """粒子在不在（不在就建）；建不出来（进世界头几秒 Create 回 0）返回 False，下一帧再试。"""
        if self.particleId is None:
            pos = tuple(round(value, DIGITS) for value in pos)
            self.particleId = compFactory.CreateParticleSystem(None).Create(PARTICLE, pos) or None
            self.sent = {"pos": pos} if self.particleId is not None else {}
        return self.particleId is not None

    def _send(self, system, name, value):
        value = round(float(value), DIGITS)
        if self.sent.get(name) != value:
            self.sent[name] = value
            system.SetVariable(self.particleId, name, value)

    def _dim(self):
        """收着：不透明度写 0，粒子留着（停稳了再亮，不用重建）。"""
        if self.lit:
            self.lit, self.color = False, None
            self._send(compFactory.CreateParticleSystem(None), "variable.alpha", 0.0)

    def remove(self):
        if self.particleId is not None:
            compFactory.CreateParticleSystem(None).Remove(self.particleId)
        self.particleId, self.lit, self.color, self.sent = None, False, None, {}


class TopTints(object):
    """一个场景里全部的叠层，键是节点名（煎锅）或烤位（炉灶）。"""

    def __init__(self):
        self._tints = {}

    def frame(self, dt, wanted):
        """wanted：{键: (物品, 中心, 姿态, 缩放, 颜色)}，这一帧要染的件（panWanted / stoveWanted）；不在里面的删掉。"""
        for key in [key for key in self._tints if key not in wanted]:
            self._tints.pop(key).remove()
        for key, entry in wanted.items():
            tint = self._tints.get(key)
            if tint is None:
                tint = self._tints[key] = TopTint()
            tint.follow(dt, *entry)

    def clear(self):
        for tint in self._tints.values():
            tint.remove()
        self._tints = {}

    def __len__(self):
        return len(self._tints)


def _colorOf(name, cookedName, up):
    return FryingTint.overlay(FryingTint.tintOf(name, cookedName or name, up))


def panWanted(show, props):
    """一口煎锅（PanScene 的 show、props）这一帧要染的件：{节点名: (物品, 中心, 姿态, 缩放, 颜色)}。JE 的 drawPiece 给锅里每一块（piece_N、under_N）
    同一个颜色：锅里那一份朝上那面画到哪（shownUp，每 1/12 才变）；蛋不叠。"""
    shown = show.shown
    if shown is None or show.isCracked(shown):
        return {}
    name = shown["newItemName"]
    color = _colorOf(name, PanStation.friedOf(name), show.shownUp)
    if color is None:
        return {}
    return dict((key, (prop.kind, prop.center, prop.matrix, prop.scale, color)) for key, prop in props.items() if key.split("_")[0] in TINTED)


def stoveWanted(pieces):
    """一座炉灶（StoveScene 的 GrillPieces.Pieces）这一帧要染的件：{烤位: (物品, 中心, 姿态, 缩放, 颜色)}。每件按自己朝上那面画到哪（Pieces.up，
    StoveBehavior.draw 的 shownUp[place]）；单面的（蛋：EggLook 的显示物品）、掉落物没建成的（引擎没给实体，WorldProp 没有姿态）不叠。"""
    wanted = {}
    for place, entry in enumerate(pieces.props):
        item = pieces.shown[place]
        if entry is None or not entry[1].alive or item is None or GrillStation.isOneSided(item["newItemName"]):
            continue
        color = _colorOf(item["newItemName"], GrillStation.grilledOf(item["newItemName"]), pieces.up[place])
        if color is not None:
            kind, prop = entry
            wanted[place] = (kind, prop.worldCenter(), prop.drawn, prop.scale, color)
    return wanted
