# -*- coding: utf-8 -*-
from Util import Queue
from ..Services.Client import BaseService
from ...Util import TRY_EXEC_FUN

@BaseService.Init
class _MAIN_THREAD_SERVER(BaseService):
    _TASK_QUEUE = Queue(maxsize=0)

    def onServiceUpdate(self):
        BaseService.onServiceUpdate(self)
        _TASK_QUEUE = _MAIN_THREAD_SERVER._TASK_QUEUE
        while not _MAIN_THREAD_SERVER._TASK_QUEUE.empty():
            TRY_EXEC_FUN(_TASK_QUEUE.get())

def RUN_IN_MAIN_THREAD(taskFunc=lambda: None):
    """ 在对应的系统端线程运行特定任务 用于解决游戏API调用问题 """
    _MAIN_THREAD_SERVER._TASK_QUEUE.put(taskFunc)