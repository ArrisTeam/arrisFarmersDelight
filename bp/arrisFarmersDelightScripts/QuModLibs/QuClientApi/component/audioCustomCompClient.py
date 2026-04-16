# -*- coding: utf-8 -*-


class AudioCustomComponentClient(object):
    def DisableOriginMusic(self, disable):
        # type: (bool) -> bool
        """
        停止原生背景音乐
        """
        pass

    def PlayGlobalCustomMusic(self, name, volume=1, loop=False):
        # type: (str, float, bool) -> bool
        """
        播放背景音乐
        """
        pass

    def PlayCustomMusic(self, name, pos=(0, 0, 0), volume=1, pitch=1, loop=False, entityId=None):
        # type: (str, tuple[float,float,float], float, float, bool, str) -> str
        """
        播放场景音效，包括原版音效及自定义音效
        """
        pass

    def StopCustomMusic(self, name, fadeOutTime=0.0):
        # type: (str, float) -> bool
        """
        停止音效，包括场景音效与背景音乐，将依据fadeOutTime触发OnMusicStopClientEvent事件
        """
        pass

    def StopCustomMusicById(self, musicId, fadeOutTime=0.0):
        # type: (str, float) -> bool
        """
        停止场景音效
        """
        pass

    def SetCustomMusicLoop(self, name, loop):
        # type: (str, bool) -> bool
        """
        设定指定音乐是否循环播放，包括场景音效与背景音乐
        """
        pass

    def SetCustomMusicLoopById(self, musicId, loop):
        # type: (str, bool) -> bool
        """
        设定指定音乐是否循环播放
        """
        pass


