# -*- coding: utf-8 -*-
from threading import Thread
from Queue import Queue

class QThreadPool:
    def __init__(self, maxThreadCount=2, daemon=None):
        # type: (int, bool | None) -> None
        from threading import Event
        self.maxThreadCount = maxThreadCount
        self._closeEvent = Event()
        self.daemon = daemon
        self._taskQueue = Queue(maxsize=0)
        self._threadList = []   # type: list[Thread]
    
    def start(self):
        """ 启用线程并返回自己的实例 """
        if len(self._threadList) <= 0:
            self._createThread(self.maxThreadCount)
        return self

    def _createThread(self, count=1):
        for _ in range(count):
            thread = Thread(target=self._threadLoop)
            if self.daemon:
                thread.daemon = True
            self._threadList.append(thread)
            thread.start()

    def _threadLoop(self):
        while not self._closeEvent.is_set():
            item = None
            try:
                item = self._taskQueue.get(timeout=0.05)
            except:
                continue
            try:
                item()
            except Exception:
                import traceback
                traceback.print_exc()
    
    def addTask(self, func=lambda: None):
        """ 添加执行任务 """
        self._taskQueue.put(func)

    def free(self):
        """ 释放线程池 """
        self._closeEvent.set()