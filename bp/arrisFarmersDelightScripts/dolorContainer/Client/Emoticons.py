# -*- coding: utf-8 -*-
"""
物品悬停文本里的表情：把 :名字: 换成表情字形，规则与原版一致——
从左往右找冒号，两个冒号之间只能是英文字母、数字、下划线；名字在表里就整段换成对应的字符，
从换好的字符后面接着找；不在表里时后一个冒号当作新的开头。

TABLE 由 tools/gen_emoticons.py 从游戏自带的 font/emoticons.json 生成，不手改。
"""

TABLE = {
    "armor": 0xE101,
    "camera": 0xE10D,
    "code_builder_button": 0xE103,
    "craftable_toggle_off": 0xE0A1,
    "craftable_toggle_on": 0xE0A0,
    "crafting_table": 0xE10A,
    "furnace": 0xE10B,
    "heart": 0xE10C,
    "hollow_star": 0xE106,
    "immersive_reader_button": 0xE104,
    "light_mouse_button": 0xE073,
    "light_mouse_left_button": 0xE070,
    "light_mouse_middle_button": 0xE072,
    "light_mouse_right_button": 0xE071,
    "minecoin": 0xE102,
    "mouse_button": 0xE063,
    "mouse_left_button": 0xE060,
    "mouse_middle_button": 0xE062,
    "mouse_right_button": 0xE061,
    "nbsp": 0xE0FF,
    "ps4_bumper_left": 0xE024,
    "ps4_bumper_right": 0xE025,
    "ps4_dpad_down": 0xE02E,
    "ps4_dpad_left": 0xE02D,
    "ps4_dpad_right": 0xE02F,
    "ps4_dpad_up": 0xE02C,
    "ps4_face_button_down": 0xE020,
    "ps4_face_button_left": 0xE022,
    "ps4_face_button_right": 0xE021,
    "ps4_face_button_up": 0xE023,
    "ps4_left_stick_down": 0xE0D2,
    "ps4_left_stick_left": 0xE0D1,
    "ps4_left_stick_right": 0xE0D3,
    "ps4_left_stick_up": 0xE0D0,
    "ps4_select": 0xE028,
    "ps4_start": 0xE029,
    "ps4_stick_left": 0xE02A,
    "ps4_stick_right": 0xE02B,
    "ps4_trigger_left": 0xE026,
    "ps4_trigger_right": 0xE027,
    "rift_0": 0xE0E0,
    "rift_A": 0xE0E1,
    "rift_B": 0xE0E2,
    "rift_X": 0xE0E9,
    "rift_Y": 0xE0EA,
    "rift_left_grab": 0xE0E3,
    "rift_left_stick": 0xE0E5,
    "rift_left_trigger": 0xE0E7,
    "rift_right_grab": 0xE0E4,
    "rift_right_stick": 0xE0E6,
    "rift_right_trigger": 0xE0E8,
    "shank": 0xE100,
    "solid_star": 0xE107,
    "switch_bumper_left": 0xE044,
    "switch_bumper_right": 0xE045,
    "switch_dpad_down": 0xE04E,
    "switch_dpad_left": 0xE04D,
    "switch_dpad_right": 0xE04F,
    "switch_dpad_up": 0xE04C,
    "switch_face_button_down": 0xE040,
    "switch_face_button_left": 0xE042,
    "switch_face_button_right": 0xE041,
    "switch_face_button_up": 0xE043,
    "switch_left_stick_down": 0xE0D2,
    "switch_left_stick_left": 0xE0D1,
    "switch_left_stick_right": 0xE0D3,
    "switch_left_stick_up": 0xE0D0,
    "switch_select": 0xE048,
    "switch_start": 0xE049,
    "switch_stick_left": 0xE04A,
    "switch_stick_right": 0xE04B,
    "switch_trigger_left": 0xE046,
    "switch_trigger_right": 0xE047,
    "tip_crosshair": 0xE017,
    "tip_face_button_down": 0xE010,
    "tip_face_button_left": 0xE012,
    "tip_face_button_right": 0xE011,
    "tip_face_button_up": 0xE013,
    "tip_left_stick": 0xE075,
    "tip_left_trigger": 0xE06E,
    "tip_right_stick": 0xE076,
    "tip_right_trigger": 0xE06F,
    "tip_touch_back": 0xE067,
    "tip_touch_fly_down": 0xE06D,
    "tip_touch_fly_up": 0xE06C,
    "tip_touch_forward": 0xE065,
    "tip_touch_inventory": 0xE06B,
    "tip_touch_jump": 0xE069,
    "tip_touch_left": 0xE066,
    "tip_touch_right": 0xE068,
    "tip_touch_sneak": 0xE06A,
    "tip_virtual_button_action_attack_or_destroy": 0xE015,
    "tip_virtual_button_action_build_or_use": 0xE018,
    "tip_virtual_button_dismount": 0xE01D,
    "tip_virtual_button_fly_down": 0xE01C,
    "tip_virtual_button_fly_up": 0xE01B,
    "tip_virtual_button_jump": 0xE014,
    "tip_virtual_button_sneak": 0xE019,
    "tip_virtual_button_sprint": 0xE01A,
    "tip_virtual_joystick": 0xE016,
    "token": 0xE102,
    "touch_attack": 0xE015,
    "touch_back": 0xE082,
    "touch_chat": 0xE08A,
    "touch_fly_down": 0xE087,
    "touch_fly_up": 0xE086,
    "touch_forward": 0xE080,
    "touch_inventory": 0xE01E,
    "touch_jump": 0xE084,
    "touch_left": 0xE081,
    "touch_right": 0xE083,
    "touch_sneak": 0xE085,
    "touch_sprint": 0xE01A,
    "touch_sprint_double_tap": 0xE064,
    "touch_stop_flying": 0xE088,
    "touch_use": 0xE018,
    "touch_virtual_joystick_back": 0xE08E,
    "touch_virtual_joystick_forward": 0xE08C,
    "touch_virtual_joystick_left": 0xE08D,
    "touch_virtual_joystick_right": 0xE08F,
    "windowsmr_left_grab": 0xE0C0,
    "windowsmr_left_stick": 0xE0C3,
    "windowsmr_left_touchpad": 0xE0C5,
    "windowsmr_left_touchpad_horizontal": 0xE0C6,
    "windowsmr_left_touchpad_vertical": 0xE0C7,
    "windowsmr_left_trigger": 0xE0CB,
    "windowsmr_menu": 0xE0C2,
    "windowsmr_right_grab": 0xE0C1,
    "windowsmr_right_stick": 0xE0C4,
    "windowsmr_right_touchpad": 0xE0C8,
    "windowsmr_right_touchpad_horizontal": 0xE0C9,
    "windowsmr_right_touchpad_vertical": 0xE0CA,
    "windowsmr_right_trigger": 0xE0CC,
    "windowsmr_windows": 0xE0CD,
    "wood_pickaxe": 0xE108,
    "wood_sword": 0xE109,
    "xbox_bumper_left": 0xE004,
    "xbox_bumper_right": 0xE005,
    "xbox_dpad_down": 0xE00E,
    "xbox_dpad_left": 0xE00D,
    "xbox_dpad_right": 0xE00F,
    "xbox_dpad_up": 0xE00C,
    "xbox_face_button_down": 0xE000,
    "xbox_face_button_left": 0xE002,
    "xbox_face_button_right": 0xE001,
    "xbox_face_button_up": 0xE003,
    "xbox_left_stick_down": 0xE0D2,
    "xbox_left_stick_left": 0xE0D1,
    "xbox_left_stick_right": 0xE0D3,
    "xbox_left_stick_up": 0xE0D0,
    "xbox_select": 0xE008,
    "xbox_start": 0xE009,
    "xbox_stick_left": 0xE00A,
    "xbox_stick_right": 0xE00B,
    "xbox_trigger_left": 0xE006,
    "xbox_trigger_right": 0xE007,
}

_NAME_CHARS = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_")
_NAME_BYTES = frozenset(char.encode("utf-8") for char in _NAME_CHARS)   # 游戏里的 Python 只有 utf-8 编解码可用

try:
    _unichr = unichr  # noqa: F821  py2
except NameError:
    _unichr = chr


def emoticonify(text):
    """text 可以是 utf-8 字节串（py2 的 str）或文本，返回同一种类型。"""
    if not text:
        return text
    binary = isinstance(text, bytes)
    colon = b":" if binary else ":"
    if colon not in text:
        return text
    names = _NAME_BYTES if binary else _NAME_CHARS
    pieces = []
    start = 0
    opened = None
    for index in range(len(text)):
        char = text[index:index + 1]
        if char == colon:
            if opened is None:
                opened = index
                continue
            name = text[opened + 1:index]
            code = TABLE.get(name.decode("utf-8") if binary else name)
            if code:
                glyph = _unichr(code)
                pieces.append(text[start:opened])
                pieces.append(glyph.encode("utf-8") if binary else glyph)
                start = index + 1
                opened = None
            else:
                opened = index
        elif opened is not None and char not in names:
            opened = None
    pieces.append(text[start:])
    return (b"" if binary else "").join(pieces)
