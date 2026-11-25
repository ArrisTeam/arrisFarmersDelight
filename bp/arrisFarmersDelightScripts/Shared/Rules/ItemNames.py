# -*- coding: utf-8 -*-
"""ItemNames - 物品的显示名：界面用到时问引擎（两端各装一个口），要到了记住（双端，纯规则）

经典厨锅界面里没写 text 的配方（JE 的配方 JSON 本来就没有 text）显示成品的显示名，搜索也按它搜（CookingPotBook.titleOf）。
引擎的 GetItemBasicInfo(名, aux)["itemName"] 进了世界之后两端都给显示名（utf-8 字节串，aux 也认）；物品没有语言条目时给的是键本身
（item.xxx.name），物品不存在时整个返回 None；在 ready 广播那一刻服务端对自定义物品给的也是键（2026-11-26 实机）。
所以不在登记时写进表里，界面用到时才问：
- setPort(port)：再装一个口，port(物品名, aux) -> 显示名或 None（同一个不重复装；None 是卸下全部，测试用；removePort 卸下一个）。
  服务端 Server/CookingPotHost.py、客户端 Client/CookingPotUi.py 导入时各装一个。单机时两端共用这一份模块，两个口都在，而引擎的
  GetItemBasicInfo 只在自己那一端的线程里答得出（2026-11-26 实机：服务端线程里 serverApi 的给 铁锭 / 番茄、clientApi 的两样都给 None；
  客户端线程里反过来）——所以真去问时挨个问，第一个给出像样名字的算数。远端客户端只有客户端的口，专用服务器只有服务端的口。
  要到的名字两端共用（同一个进程、同一种语言）。没装口（离线、沙箱）时什么都要不到。
- nameOf(物品名, aux)：要到了的（是文字、不空、不是没翻出来的语言键）记住并返回；哪个口都要不到返回 None、不记，隔 RETRY_EVERY 次
  再问（世界还没进完时会要不到；物品真没有名字时也别每次都去问）。
- remembered()：已经记了几个名字；misses()：装着口时真去问了、没要到的次数（隔着没问的不算）。经典界面的搜索把前者算进签名，
  一次过滤里真去问了又没要到（后者变了）就不记这次的结果；下一次过滤多半是隔着没问，就记住了（物品真没有名字时，不会每次都把整张表
  重新过滤一遍）。后来才要到的名字（选中那道菜的标题每次刷新都在问，倒数完会再真问一次）让前者变了、签名跟着变，搜索重算。
"""
try:
    _TEXT = (str, unicode)  # noqa: F821 - py2
except NameError:
    _TEXT = (str, bytes)

_KEY_HEADS = ("item.", "tile.")
_KEY_TAIL = ".name"
RETRY_EVERY = 16     # 要不到的名字，再问引擎之前先跳过这么多次（界面每次刷新要问好几遍）
_state = {"ports": [], "misses": 0}
_names = {}          # (物品名, aux) -> 显示名（引擎给的原样：py2 是 utf-8 字节串）
_skips = {}          # (物品名, aux) -> 再问之前还要跳过几次


def setPort(port):
    """再装一个显示名的口（同一个不重复装）；None 是卸下全部（测试用）。"""
    if port is None:
        del _state["ports"][:]
    elif port not in _state["ports"]:
        _state["ports"].append(port)


def removePort(port):
    """卸下一个口（没装着的不管）。"""
    if port in _state["ports"]:
        _state["ports"].remove(port)


def isLangKey(text):
    """item.xxx.name / tile.xxx.name：引擎没翻出来的语言键（物品没有语言条目，或者世界还没进完），当没要到。"""
    if isinstance(text, bytes) and not isinstance(text, str):
        text = text.decode("utf-8", "ignore")
    return isinstance(text, _TEXT) and text.startswith(_KEY_HEADS) and text.endswith(_KEY_TAIL)


def _ask(port, name, aux):
    """问一个口：给的是像样的名字（文字、不空、不是没翻出来的语言键）就是它，别的（None、语言键、抛异常……）都是 None。"""
    try:
        answer = port(name, aux)
    except Exception:  # noqa: BLE001 - 引擎的口出什么错都当要不到，界面照常画
        return None
    return answer if isinstance(answer, _TEXT) and answer and not isLangKey(answer) else None


def nameOf(name, aux=0):
    """这件物品的显示名；要不到是 None。真去问时挨个问装着的口，第一个给出像样名字的算数。"""
    key = (name, aux or 0)
    found = _names.get(key)
    if found is not None:
        return found
    ports = list(_state["ports"])
    if not ports or not name:
        return None
    if _skips.get(key, 0) > 0:
        _skips[key] -= 1             # 隔着没问：不算 misses（不然一条永远没名字的配方会让经典界面的搜索永远记不住）
        return None
    for port in ports:
        answer = _ask(port, name, aux or 0)
        if answer is not None:
            _skips.pop(key, None)
            _names[key] = answer
            return answer
    _skips[key] = RETRY_EVERY
    _state["misses"] += 1
    return None


def remembered():
    """已经记了几个名字。"""
    return len(_names)


def misses():
    """装着口时真去问了、没要到的次数（隔着没问的不算）。"""
    return _state["misses"]


def forget():
    """测试用：忘掉记着的名字和要不到的记录。"""
    _names.clear()
    _skips.clear()
