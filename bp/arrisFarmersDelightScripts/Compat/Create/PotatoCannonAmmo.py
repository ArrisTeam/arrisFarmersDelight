# -*- coding: utf-8 -*-
"""PotatoCannonAmmo - 机械动力的土豆加农炮认农夫乐事的七种弹药（双端，不碰引擎）

照 JE 农夫乐事的 data/farmersdelight/create/potato_projectile/type/*.json（7 个文件，字段原样搬，物品 / 方块换成本包的名字，
类型 id 是 JE 的文件名换成 arris 命名空间）。机械动力（arrisCreate）的门面 ext.potatoCannon.registerAmmoType
（它的 docs/EXTENSION-API.md §15.52，能力 potato_cannon_ammo）两端各登记一次：服务端管开火和命中，客户端管弹丸怎么画。
门面从它的 ready 事件拿（命名空间 arrisCreate、系统 ExtensionApi）；这个模块被导入时它已经广播过，就从它的 ExtensionApi 模块
取那一端的门面晚接一次（§3.3：弹药是现查的表，冻结之后登记照样生效）。没装机械动力、或者它没有这项能力：什么都不做。
碰引擎的那两样（加载器系统、ImportModule）由两端的入口 PotatoCannonServer / PotatoCannonClient 传进来。
"""
CAPABILITY = "potato_cannon_ammo"
NAMESPACE, SYSTEM_NAME = "arrisCreate", "ExtensionApi"
READY_EVENTS = {"server": "ServerExtensionApiReady", "client": "ClientExtensionApiReady"}
FACADE_MODULE = "arrisCreateScripts.Api.ExtensionApi"
READY_METHOD = "arrisFarmersDelightPotatoCannonReady"     # 挂在本包加载器系统上的监听方法名（同一个系统上只挂一次）


def _tumble():
    return {"type": "create:tumble"}


def ammoTypes():
    """[(类型 id, 字段)]，每次给一份新的（门面拿去随便改也碰不到这里）。"""
    return [
        ("arris:cabbage", {"items": ["arris:cabbage"], "damage": 7, "reload_ticks": 15, "knockback": 2, "sound_pitch": 0.8,
                           "velocity_multiplier": 1.1, "render_mode": _tumble()}),
        ("arris:fd_pie", {"items": ["arris:apple_pie_item", "arris:sweet_berry_cheesecake_item", "arris:chocolate_pie_item"],
                          "damage": 7, "reload_ticks": 15, "knockback": 0.05, "velocity_multiplier": 1.1, "sticky": True,
                          "sound_pitch": 1.1, "render_mode": _tumble()}),
        ("arris:fd_pie_slice", {"items": ["arris:cake_slice", "arris:apple_pie_slice", "arris:sweet_berry_cheesecake_slice",
                                          "arris:chocolate_pie_slice"],
                                "damage": 4, "reload_ticks": 8, "knockback": 0.05, "velocity_multiplier": 1.4, "sticky": True,
                                "sound_pitch": 1.5, "render_mode": _tumble()}),
        ("arris:onion", {"items": ["arris:onion"], "damage": 4, "knockback": 0.3,
                         "on_block_hit": {"type": "create:plant_crop", "block": "arris:onions_stage0"}, "reload_ticks": 12,
                         "render_mode": {"type": "create:toward_motion", "spin": 1.0, "sprite_angle_offset": 140},
                         "sound_pitch": 1.5, "velocity_multiplier": 1.45}),
        ("arris:pumpkin_slice", {"items": ["arris:pumpkin_slice"], "damage": 4, "reload_ticks": 8, "knockback": 0.1,
                                 "velocity_multiplier": 1.45, "sound_pitch": 1.5, "render_mode": _tumble()}),
        ("arris:rotten_tomato", {"items": ["arris:rotten_tomato"], "damage": 2, "reload_ticks": 10, "knockback": 0.8,
                                 "velocity_multiplier": 1.5, "sticky": True, "sound_pitch": 1.0}),
        ("arris:tomato", {"items": ["arris:tomato"], "damage": 2, "reload_ticks": 10, "knockback": 0.8, "velocity_multiplier": 1.5,
                          "sound_pitch": 1.2}),
    ]


def register(facade):
    """门面有这项能力就登记七种，返回登记上的个数；没有能力（或者不是门面）返回 None。"""
    hasCapability = getattr(facade, "hasCapability", None)
    if hasCapability is None or not hasCapability(CAPABILITY):
        return None
    done = 0
    for typeId, fields in ammoTypes():
        result = facade.potatoCannon.registerAmmoType(typeId, fields)
        if isinstance(result, dict) and result.get("ok"):
            done += 1
        else:
            print("[arrisFarmersDelight] 土豆加农炮弹药 %s 没登记上：%r" % (typeId, result))
    return done


_attached = {}


def attach(side, facade):
    """这一端接上（ready 事件或晚接）：接过了不再接。返回接上了没有。"""
    if _attached.get(side):
        return True
    count = register(facade)
    if count is None:
        print("[arrisFarmersDelight] 机械动力没有 %s（%s 端）：土豆加农炮不认农夫乐事的弹药" % (CAPABILITY, side))
        return False
    _attached[side] = True
    print("[arrisFarmersDelight] 土豆加农炮弹药登记了 %d 种（%s 端）" % (count, side))
    return True


def hook(side, system, api):
    """side 是 "server" / "client"，system 是本包这一端的加载器系统，api 是那一端的 extraServerApi / extraClientApi。
    在 system 上听机械动力的 ready 事件；它已经广播过（它的 ExtensionApi 系统在）就当场晚接。没装机械动力只问一次引擎。"""
    if getattr(system, READY_METHOD, None) is None:
        def onReady(args):
            attach(side, (args or {}).get("extension"))
        onReady.__name__ = READY_METHOD
        setattr(system, READY_METHOD, onReady)
        system.ListenForEvent(NAMESPACE, SYSTEM_NAME, READY_EVENTS[side], system, onReady)
    if not api.GetSystem(NAMESPACE, SYSTEM_NAME):
        return False
    module = api.ImportModule(FACADE_MODULE)
    getter = getattr(module, "getExtensionApi", None) if module is not None else None
    facade = getter(side) if getter is not None else None
    return attach(side, facade) if facade is not None else False
