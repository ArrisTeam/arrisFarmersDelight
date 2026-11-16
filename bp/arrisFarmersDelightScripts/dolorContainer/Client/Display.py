# -*- coding: utf-8 -*-
"""
一个物品堆在格子里怎么画：图标参数、数量文字、耐久条与收纳袋容量条的数值。纯逻辑。

数量文字照原版：1 个不写，两位以内照写，三位起写成 "99+"。
耐久条照原版：可损坏且有损耗时显示，交给引擎的进度条渲染器（总量 = 最大耐久，当前 = 最大耐久 - 损耗），
颜色、阴影、取整都由渲染器按原版画。
收纳袋容量条照原版：装着东西时显示（总量 = 内容总重上限，当前 = 内容重量），满了由渲染器换成红色。
悬停文本的钩子（addHoverText）：模组在这份库的所有界面里给物品的悬停文本加字（价格、来历这类），按物品算、结果会缓存。
"""
from ..Common import Bundles, Items

_hoverHooks = []        # 悬停文本的钩子：hook(物品堆, 文字) -> 文字
_hoverVersion = [0]     # 钩子变了就加一（缓存的悬停文本按它作废）


def addHoverText(hook):
    """
    加一个悬停文本的钩子：hook(物品堆, 照常的悬停文本) -> 要显示的（追加一行写 text + "\n" + 那一行）。只在客户端调用；
    结果按物品缓存，所以只能看物品本身。按加的先后依次套。返回 hook（可以当装饰器用）。
    """
    _hoverHooks.append(hook)
    _hoverVersion[0] += 1
    return hook


def removeHoverText(hook):
    """去掉 addHoverText 加的钩子。"""
    if hook in _hoverHooks:
        _hoverHooks.remove(hook)
        _hoverVersion[0] += 1


def hoverTextVersion():
    """钩子的版本（缓存悬停文本时带上）。"""
    return _hoverVersion[0]


def applyHoverText(stack, text):
    """按加的先后套上悬停文本的钩子（没有钩子时原样）。"""
    for hook in _hoverHooks:
        text = hook(stack, text)
    return text


def hoverLiteral(text):
    """
    写进原版悬停文本（common.hover_text 的 #hover_text）的字照原样显示：网易版的悬停文本按语言文件的规则再处理一遍，"%" 后面
    的字当成键去查（查不到照写）、单独的 "%" 去掉，"%%" 才写出一个 "%"。库按格式串拼的悬停文本经它；引擎给的物品悬停文本
    照原版不经它（原版界面里药水的"+20%"也画成"+20"）。
    """
    return text.replace("%", "%%") if "%" in text else text


def _plain(value):
    return value["__value__"] if isinstance(value, dict) and "__value__" in value else value


def iconArgs(stack):
    """
    SetUiItem 的参数：(名字, aux, 是否附魔光效, userData)。附魔光效照原版：附加数据里有 ench 列表就算（空列表也算）；
    附魔金苹果这类按种类发光的由渲染器自己补上。
    """
    user = stack.get("userData") or None
    enchanted = isinstance(user, dict) and isinstance(user.get("ench"), list)
    return stack["newItemName"], stack.get("newAuxValue", 0), enchanted, user


_SECTION = u"§"   # 格式码的开头


def plainName(text):
    """
    物品的悬停名去掉引擎加的稀有度颜色：开头的格式码（可能有几个）与结尾的 §r；中间的（自定的名字里写的）留着。
    py2 下是 utf-8 的 str。
    """
    mark = _SECTION.encode("utf-8") if isinstance(text, bytes) else _SECTION
    step = len(mark) + 1
    while text.startswith(mark) and len(text) >= step:
        text = text[step:]
    end = mark + (b"r" if isinstance(mark, bytes) else u"r")
    return text[:-len(end)] if text.endswith(end) else text


def int32(value):
    """
    按有符号 32 位写进属性包的整数（原版界面绑定也是这样写颜色、追踪号）：属性包收到长整数（py2 在 Windows 上 C long 是 32 位，
    位运算常得到长整数）时引擎整次都不写，所以总是转回 int。
    """
    value = int(value) & 0xFFFFFFFF
    return int(value - (1 << 32) if value >= (1 << 31) else value)


def countText(stack):
    count = Items.count(stack)
    if count <= 1:
        return ""
    return str(count) if count < 100 else "99+"


class Context(object):
    """
    画物品堆要查的种类信息：rules 是 Items.ItemRules（最大耐久、最大堆叠数，收纳袋的重量按它算）；
    idAuxOf(name, aux) 给出物品编号（#item_id_aux 的写法：编号 << 16 | aux），没有时为 None。
    """

    def __init__(self, rules, idAuxOf=None):
        self.rules = rules
        self.idAuxOf = idAuxOf or (lambda name, aux: None)

    def iconExtras(self, stack):
        return iconExtras(stack, self.idAuxOf)

    def countText(self, stack):
        """格子右下角的数量字（原版：1 个不写，两位以内照写，三位起 99+）。"""
        return countText(stack)

    def durability(self, stack):
        return durability(stack, lambda name, aux: self.rules.maxDurability(stack))

    def storage(self, stack):
        return storage(stack, self.rules)


def _text(value):
    """属性包里的字符串：py2 的 unicode 转成 utf-8 的 str（引擎的文本接口只收 str）。"""
    value = _plain(value)
    return value if isinstance(value, str) else value.encode("utf-8")


# 原版界面按附加数据填进图标属性包的网易字段：(附加数据键, 属性包键, 转换)。渲染器拿 ModId / ModItemId 找物品定义，
# modvalue / ModExtendValue 只对老式模组物品生效，MicroBlockData 是微缩方块，Pose 是带姿势的方块物品（铜傀儡雕像等）
_USER_FIELDS = (("modvalue", "#item_mod_value", int), ("ModExtendValue", "#item_mod_extend_value", _text),
                ("ModId", "#item_mod_id", _text), ("ModItemId", "#item_mod_item_id", _text),
                ("MicroBlockData", "#item_micro_item_value", _text), ("Pose", "#serialized_actor_pose", int))


def iconExtras(stack, idAuxOf):
    """
    图标属性包里原版靠界面绑定填、脚本的 SetUiItem 不写的几项（SetUiItem 只照物品编号生成图标）：
    弩装着的东西（#charged_item = 编号 << 8 | aux）、盾牌的底色（#shield_base_color）、磁石指针的追踪号，
    以及 _USER_FIELDS 里的网易字段。附加数据里没有的不写（渲染器的缺省值与原版给的相同）。没有时为空字典。
    """
    user = stack.get("userData") if not Items.isEmpty(stack) else None
    if not isinstance(user, dict):
        return {}
    out = {}
    charged = user.get("chargedItem")
    if isinstance(charged, dict):
        name, aux = _plain(charged.get("Name")), int(_plain(charged.get("Damage")) or 0)
        idAux = idAuxOf(str(name), aux) if name else None
        if idAux:
            out["#charged_item"] = ((int(idAux) >> 16) << 8) | (aux & 0xFF)
    if "Base" in user:
        # 原版对任何物品都填，渲染器只在画盾牌时读；没有时缺省 -1，与原版给普通盾牌的值相同
        base = int(_plain(user["Base"]))
        out["#shield_base_color"] = base
        out["#shield_base_color_hovered"] = base
    if "trackingHandle" in user:
        out["#item_lodestone_tracking_handle"] = int32(_plain(user["trackingHandle"]))   # 照原版的绑定：有符号 32 位
    for key, bagKey, convert in _USER_FIELDS:
        if key in user:
            out[bagKey] = convert(_plain(user[key]))
    return out


_LAYER_KEYS = ("top_layer_3", "top_layer_2", "top_layer_1", "bottom_layer_1", "bottom_layer_2")


def hasItemLayers(userData):
    """附加数据里有网易的物品叠加贴图（SetItemLayer 写的 top_layer_1 等）。"""
    return isinstance(userData, dict) and any(key in userData for key in _LAYER_KEYS)


_LEGACY_MOD_ITEMS = ("minecraft:mod", "minecraft:mod_armor")


def flyingModValues(stack):
    """
    物品飞行渲染器的两项网易扩展 (flying_item_mod_value, flying_item_mod_extend_value)，照原版：老式模组物品
    （mod / mod_armor）给附加数据里的 modvalue，别的物品给 -1；ModExtendValue 照附加数据给，没有时为空串。
    渲染器用这两项覆盖飞行副本附加数据里的同名项，所以不能不写。
    """
    user = stack.get("userData")
    if not isinstance(user, dict):
        user = {}
    value = -1
    if stack.get("newItemName") in _LEGACY_MOD_ITEMS and "modvalue" in user:
        value = int(_plain(user["modvalue"]))
    extend = _plain(user.get("ModExtendValue")) or ""
    if not isinstance(extend, str):   # py2 的 unicode：引擎的文本接口只收 str
        extend = extend.encode("utf-8")
    return value, extend


def storage(stack, rules):
    """收纳袋容量条的 (总量, 当前)；不是收纳袋或空袋时为 None。"""
    spec = Bundles.specOf(stack)
    if spec is None:
        return None
    weight = Bundles.contentsWeight(stack, rules)
    return (float(spec.weightLimit), float(weight)) if weight > 0 else None


def durability(stack, maxDurabilityOf):
    """耐久条的 (总量, 当前)；不该显示耐久条时为 None。"""
    if Items.isEmpty(stack):
        return None
    maximum = maxDurabilityOf(stack["newItemName"], stack.get("newAuxValue", 0)) or 0
    user = stack.get("userData") if isinstance(stack.get("userData"), dict) else {}
    if maximum <= 0 or _plain(user.get("Unbreakable")):
        return None
    damage = _plain(user.get("Damage")) or 0
    if damage <= 0:
        return None
    return float(maximum), float(max(0, maximum - damage))
