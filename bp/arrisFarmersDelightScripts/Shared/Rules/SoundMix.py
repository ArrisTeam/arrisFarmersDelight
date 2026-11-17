# -*- coding: utf-8 -*-
"""SoundMix - JE 的音量、音调换成交给引擎放声音的数（双端，纯规则）

引擎放一声：音量 = 声音定义里那个采样自带的 volume × 调用给的音量，音调 = 采样自带的 pitch × 调用给的音调（调用给的音量先钳在 0..1，
Strata 知识库 SOUND_ENGINE.md §0.2）。JE 的声音事件不带这些数，所以定义里自带了数的声音，调用要把那一份除掉，听到的才是 JE 的音量 / 音调：
    ambient.cutting_board.knife   本包的刀声，两个采样都是 volume 1.5（rp/sounds/sound_definitions.json）：FD 的 0.8 要给 0.8 / 1.5
    ambient.skillet.addfood       本包的下料声，两个采样都是 volume 2.0：FD 的 0.8 要给 0.4
    block.lantern.place           原版的挂灯放置声，每个采样 pitch 1.1（原版 sound_definitions.json）：JE 的 LANTERN_PLACE 音调 1.0 要给 1 / 1.1
改了声音定义里的 volume / pitch 要同步改这里（tests/test_sound_mix.py 对着 rp 里本包的两条核对）。
"""
BUILT_IN = {                                  # 声音名 -> (每个采样自带的音量, 每个采样自带的音调)
    "ambient.cutting_board.knife": (1.5, 1.0),
    "ambient.skillet.addfood": (2.0, 1.0),
    "block.lantern.place": (1.0, 1.1),
}


def engineArgs(name, volume, pitch):
    """JE 里这一声的 (音量, 音调) -> 交给 PlayCustomMusic 的 (音量, 音调)。"""
    builtVolume, builtPitch = BUILT_IN.get(name, (1.0, 1.0))
    return volume / builtVolume, pitch / builtPitch
