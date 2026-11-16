# -*- coding: utf-8 -*-
"""
客户端界面状态记在客户端配置里（docs/DESIGN.md 第 3 节"客户端界面状态"）：界面模型的 savedClientState 列出的那几项
（子窗口位置、页签、搜索词、折叠……），按界面模型名存进这台设备上的一份配置，下次进游戏还在。

读写经注入的 read() -> 字典、write(字典)（客户端服务接引擎的本地配置；测试接内存）。这次游戏里第一次打开某种界面时读回来，
会话结束时写回去（拖子窗口时每帧都在变，不每次都写）；写回的跟记着的一样时不写。值按字段类型编码成简单值存，读回时按字段类型
解码，解不开的（字段类型改过）不要。纯逻辑，不依赖引擎。
"""


class Remembered(object):

    def __init__(self, read, write, log=None):
        self._read = read
        self._write = write
        self._log = log
        self._saved = None   # 界面模型名 -> {名字: 线上写法}：第一次用到时从配置读

    def _all(self):
        if self._saved is None:
            try:
                data = self._read()
            except Exception as error:  # noqa: BLE001  配置读不出来就当没有
                data = None
                if self._log is not None:
                    self._log("cannot read saved client state: %r" % (error,))
            self._saved = dict(data) if isinstance(data, dict) else {}
        return self._saved

    def restore(self, menu, values):
        """把记着的那几项写进 values（界面模型 menu 的客户端界面状态 {名字: 值}）。"""
        names = menu.savedClientState
        if not names:
            return
        saved = self._all().get(menu.menuName)
        if not isinstance(saved, dict):
            return
        for name in names:
            if name in saved:
                try:
                    values[name] = menu.clientState[name].decode(saved[name])
                except (TypeError, ValueError, KeyError, IndexError, AttributeError):
                    continue

    def save(self, menu, values):
        """会话结束：values 里要记的那几项写回配置（与记着的一样时不写）。返回写没写。"""
        names = menu.savedClientState
        if not names:
            return False
        entry = dict((name, menu.clientState[name].encode(values[name])) for name in names if name in values)
        saved = self._all()
        if saved.get(menu.menuName) == entry:
            return False
        saved[menu.menuName] = entry
        try:
            self._write(dict(saved))
        except Exception as error:  # noqa: BLE001  写不进去下次再写
            if self._log is not None:
                self._log("cannot save client state: %r" % (error,))
            return False
        return True
