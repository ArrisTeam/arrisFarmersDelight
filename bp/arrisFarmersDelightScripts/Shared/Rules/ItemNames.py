# -*- coding: utf-8 -*-
"""ItemNames - 物品的显示名：界面用到时问引擎（两端各装一个口），要到了记住（双端，纯规则）

经典厨锅界面里没写 text 的配方（JE 的配方 JSON 本来就没有 text）显示成品的显示名，搜索也按它搜（CookingPotBook.titleOf）。
引擎的 GetItemBasicInfo(名, aux)["itemName"] 进了世界之后两端都给显示名（utf-8 字节串，aux 也认）；物品没有语言条目时给的是键本身
（item.xxx.name），物品不存在时整个返回 None；在 ready 广播那一刻服务端对自定义物品给的也是键（2026-11-26 实机）。
所以不在登记时写进表里，界面用到时才问：
- setPort(port)：port(物品名, aux) -> 显示名或 None。服务端 Server/CookingPotHost.py、客户端 Client/CookingPotUi.py 导入时各装一个
  （单机时两端在同一个进程里，后装的那个算数，两端的答案一样）；没装口（离线、沙箱）时什么都要不到。
- nameOf(物品名, aux)：要到了的（是文字、不空、不是没翻出来的语言键）记住并返回；要不到返回 None、不记，隔 RETRY_EVERY 次再问引擎
  （世界还没进完时会要不到；物品真没有名字时也别每次都去问）。
- remembered()：已经记了几个名字；misses()：装着口时要不到的次数（含隔着没问的）。经典界面的搜索把前者算进签名，
  一次过滤里有要不到的（后者变了）就不记这次的结果、下次重算：后来才要到的名字不会被早先的记忆挡住。
"""
try:
    _TEXT = (str, unicode)  # noqa: F821 - py2
except NameError:
    _TEXT = (str, bytes)

_KEY_HEADS = ("item.", "tile.")
_KEY_TAIL = ".name"
RETRY_EVERY = 16     # 要不到的名字，再问引擎之前先跳过这么多次（界面每次刷新要问好几遍）
_state = {"port": None, "misses": 0}
_names = {}          # (物品名, aux) -> 显示名（引擎给的原样：py2 是 utf-8 字节串）
_skips = {}          # (物品名, aux) -> 再问之前还要跳过几次


def setPort(port):
    """装上显示名的口（None 是卸下）。"""
    _state["port"] = port


def isLangKey(text):
    """item.xxx.name / tile.xxx.name：引擎没翻出来的语言键（物品没有语言条目，或者世界还没进完），当没要到。"""
    if isinstance(text, bytes) and not isinstance(text, str):
        text = text.decode("utf-8", "ignore")
    return isinstance(text, _TEXT) and text.startswith(_KEY_HEADS) and text.endswith(_KEY_TAIL)


def nameOf(name, aux=0):
    """这件物品的显示名；要不到是 None。"""
    key = (name, aux or 0)
    found = _names.get(key)
    if found is not None:
        return found
    port = _state["port"]
    if port is None or not name:
        return None
    if _skips.get(key, 0) > 0:
        _skips[key] -= 1
        _state["misses"] += 1
        return None
    try:
        answer = port(name, aux or 0)
    except Exception:  # noqa: BLE001 - 引擎的口出什么错都当要不到，界面照常画
        answer = None
    if not isinstance(answer, _TEXT) or not answer or isLangKey(answer):
        _skips[key] = RETRY_EVERY
        _state["misses"] += 1
        return None
    _skips.pop(key, None)
    _names[key] = answer
    return answer


def remembered():
    """已经记了几个名字。"""
    return len(_names)


def misses():
    """装着口时要不到的次数（含隔着没问的）。"""
    return _state["misses"]


def forget():
    """测试用：忘掉记着的名字和要不到的记录。"""
    _names.clear()
    _skips.clear()
