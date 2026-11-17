# -*- coding: utf-8 -*-
"""molangkit - 测试里算粒子 / 动画文件里的 molang 表达式（离线测试公共小工具，不是测试本身）

只认粒子文件里实际写过的子集：数字、variable.名字（调用时用关键字参数给，不带前缀）、+ - * /、括号、一元负号和 !、比较、&& ||、
三元 a ? b : c，以及 math.sin / cos（molang 的角度用度）、pow、sqrt、max、min、abs、floor、clamp、lerp，和 math.random(低, 高)（要给 _random：
一个收 (低, 高) 返回数的函数，比如取最小 / 最大值看范围）。认不出的写法直接抛错：文件换了写法，这里就要跟着改，不要悄悄算错。

    value("(0.0047 + variable.particle_random_1 * 0.0047) * 2", particle_random_1=0.5)
    value("math.random(2.5, 4.95)", _random=lambda low, high: high)
"""
import math
import re

_TOKEN = re.compile(r"\s*(?:(\d+\.?\d*|\.\d+)|([A-Za-z_][A-Za-z_0-9.]*)|(&&|\|\||==|!=|>=|<=|[-+*/(),?:<>!]))")
_FUNCTIONS = {
    "math.sin": lambda a: math.sin(math.radians(a)),
    "math.cos": lambda a: math.cos(math.radians(a)),
    "math.pow": math.pow,
    "math.sqrt": math.sqrt,
    "math.max": max,
    "math.min": min,
    "math.abs": abs,
    "math.floor": lambda a: float(math.floor(a)),
    "math.clamp": lambda a, low, high: max(low, min(high, a)),
    "math.lerp": lambda a, b, t: a + (b - a) * t,
}

_OPERATORS = {
    "||": lambda a, b: float(bool(a) or bool(b)),
    "&&": lambda a, b: float(bool(a) and bool(b)),
    "==": lambda a, b: float(a == b),
    "!=": lambda a, b: float(a != b),
    "<": lambda a, b: float(a < b),
    "<=": lambda a, b: float(a <= b),
    ">": lambda a, b: float(a > b),
    ">=": lambda a, b: float(a >= b),
    "+": lambda a, b: a + b,
    "-": lambda a, b: a - b,
    "*": lambda a, b: a * b,
    "/": lambda a, b: a / b,
}


def _tokens(text):
    out, at = [], 0
    text = text.strip()
    while at < len(text):
        found = _TOKEN.match(text, at)
        if not found:
            raise ValueError("认不出的 molang：%r（位置 %d）" % (text, at))
        at = found.end()
        number, name, symbol = found.groups()
        out.append(("num", float(number)) if number else ("name", name) if name else ("sym", symbol))
    return out


class _Parser(object):
    def __init__(self, text, variables, rand):
        self.tokens, self.at, self.variables, self.text, self.rand = _tokens(text), 0, variables, text, rand

    def _peek(self):
        return self.tokens[self.at] if self.at < len(self.tokens) else (None, None)

    def _take(self, symbol=None):
        token = self._peek()
        if token[0] is None or (symbol is not None and token != ("sym", symbol)):
            raise ValueError("molang 写法不对：%r 想要 %r" % (self.text, symbol))
        self.at += 1
        return token

    def _accept(self, *symbols):
        token = self._peek()
        if token[0] == "sym" and token[1] in symbols:
            self.at += 1
            return token[1]
        return None

    def parse(self):
        result = self._ternary()
        if self.at != len(self.tokens):
            raise ValueError("molang 没读完：%r" % self.text)
        return result

    def _ternary(self):
        condition = self._binary(0)
        if not self._accept("?"):
            return condition
        yes = self._ternary()
        self._take(":")
        no = self._ternary()
        return yes if condition else no

    # 从低到高：|| && 比较 加减 乘除
    _LEVELS = (("||",), ("&&",), ("==", "!=", "<", "<=", ">", ">="), ("+", "-"), ("*", "/"))

    def _binary(self, level):
        if level == len(self._LEVELS):
            return self._unary()
        left = self._binary(level + 1)
        while True:
            op = self._accept(*self._LEVELS[level])
            if op is None:
                return left
            right = self._binary(level + 1)
            left = _OPERATORS[op](left, right)

    def _unary(self):
        if self._accept("-"):
            return -self._unary()
        if self._accept("!"):
            return float(not self._unary())
        return self._primary()

    def _primary(self):
        kind, token = self._take()
        if kind == "num":
            return token
        if kind == "sym" and token == "(":
            inner = self._ternary()
            self._take(")")
            return inner
        if kind == "name" and token.startswith("variable."):
            return self.variables[token[len("variable."):]]
        if kind == "name" and (token in _FUNCTIONS or token == "math.random"):
            self._take("(")
            args = [self._ternary()]
            while self._accept(","):
                args.append(self._ternary())
            self._take(")")
            if token == "math.random":
                if self.rand is None:
                    raise ValueError("math.random 要给 _random：%r" % self.text)
                return self.rand(*args)
            return _FUNCTIONS[token](*args)
        raise ValueError("认不出 %r（在 %r 里）" % (token, self.text))


def value(text, _random=None, **variables):
    """算一个 molang 表达式；variables 是 variable.<名字> 的值，名字不带前缀。表达式里用到而没给的变量抛 KeyError。"""
    if isinstance(text, (int, float)):
        return float(text)
    return _Parser(text, variables, _random).parse()
