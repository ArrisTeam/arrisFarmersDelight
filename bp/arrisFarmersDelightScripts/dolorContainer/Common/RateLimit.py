# -*- coding: utf-8 -*-
"""令牌桶限频：每个键（玩家）最多攒 capacity 个令牌，每秒补 rate 个。纯逻辑，时间由调用方给出。"""


class TokenBucket(object):

    def __init__(self, capacity, rate):
        self.capacity = float(capacity)
        self.rate = float(rate)
        self._state = {}

    def allow(self, key, now, cost=1.0):
        tokens, last = self._state.get(key, (self.capacity, now))
        tokens = min(self.capacity, tokens + max(0.0, now - last) * self.rate)
        if tokens < cost:
            self._state[key] = (tokens, now)
            return False
        self._state[key] = (tokens - cost, now)
        return True

    def forget(self, key):
        self._state.pop(key, None)
