# -*- coding: utf-8 -*-
from collections import OrderedDict

class QOrderedSet(object):
    """ 有序集合 """
    def __init__(self, iterable=None):
        # type: (list | tuple | None) -> None
        self._data = OrderedDict()
        if iterable:
            for item in iterable:
                self.add(item)

    def add(self, item):
        # type: (object) -> None
        self._data[item] = None
    
    def append(self, item):
        # type: (object) -> None
        return self.add(item)

    def remove(self, item):
        # type: (object) -> None
        """ 尝试移除特定元素 若不存在则抛出异常 """
        self._data.pop(item, None)

    def discard(self, item):
        # type: (object) -> bool
        """ 安全的移除特定元素 """
        if self.hasValue(item):
            self.remove(item)
            return True
        return False

    def _getMapRef(self):
        return self._data

    def hasValue(self, item):
        return item in self._data

    def __contains__(self, item):
        return item in self._data

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)

    def __repr__(self):
        return "{}<{}>".format(self.__class__.__name__, list(self._data))