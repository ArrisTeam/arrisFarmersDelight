# -*- coding: utf-8 -*-
"""RecipeFiles - 行为包里 farmersdelight_recipes/ 下的配方 JSON：一个文件定一个配方 ID、交给 ext.recipes 登记（双端代码，只在服务端用；不碰引擎）

任何行为包根下的 farmersdelight_recipes/**.json 都是一条配方，写法见 docs/RECIPE-JSON.md（JE 农夫乐事的配方 JSON，物品名写网易的）。
服务端在 ready 广播之后读一遍（Server/ExtensionReady.py；跨包读文件的是 Server/Helpers/PackJson.py）：
- 配方 ID：写了 "id" 用它；没写按路径 farmersdelight_recipes/<命名空间>/<其余>.json -> "<命名空间>:<其余>"
  （farmersdelight_recipes/mymod/cooking/tomato_soup.json -> mymod:cooking/tomato_soup）。
  直接放在 farmersdelight_recipes/ 下、又没写 "id" 的不收（不知道算谁的，no_id）。
  引擎给的路径带不带 farmersdelight_recipes/ 这一层、用不用反斜杠都认（机械动力也是两种都认；游戏里给的是哪一种没核过）。
- 登记走 ext.recipes.registerFromJson：和别的模组在代码里登记同一套规矩（命名空间、同 ID 覆盖、格式检查）。
- 按路径排好的先后一个一个登记（同一个 ID 写了两份时后读的覆盖先读的）；没登记上的记下 (路径, 原因)，不耽误别的文件。
"""
import json

from ...Shared.Rules.RecipeJson import text

DIRECTORY = "farmersdelight_recipes"
SUFFIX = ".json"


def _parts(path):
    """包里的路径 -> farmersdelight_recipes/ 下面的各层（不带这一层）；引擎给的路径不带这一层时就是整个路径的各层。"""
    parts = [part for part in text(path).replace("\\", "/").split("/") if part and part != "."]
    if DIRECTORY in parts:
        parts = parts[parts.index(DIRECTORY) + 1:]
    return parts


def idOf(path, data):
    """这个文件的配方 ID："id" 优先；没写按路径派生；两样都没有是 None。"""
    if isinstance(data, dict) and data.get("id") is not None:
        return text(data.get("id"))
    parts = _parts(path)
    if len(parts) < 2 or not parts[-1].endswith(SUFFIX) or len(parts[-1]) == len(SUFFIX):
        return None
    return "%s:%s" % (parts[0], "/".join(parts[1:-1] + [parts[-1][:-len(SUFFIX)]]))


def _reason(answer):
    """登记的回答 -> 一句原因：错误码，后面跟着回答里别的说明（message、by、current……）。"""
    extra = ["%s=%s" % (key, text(answer[key])) for key in sorted(answer) if key not in ("ok", "error", "id")]
    return " ".join([str(answer.get("error"))] + extra)


def load(files, register):
    """files：[(包里的路径, 文本)]，按这个先后登记；register(数据, 配方 ID) 就是服务端的 ext.recipes.registerFromJson。
    返回 (登记上的配方 ID 列表, 没登记上的 [(路径, 原因)])：原因是 invalid_json、no_id 或登记的错误码（带说明）。"""
    loaded, problems = [], []
    for path, source in files:
        try:
            data = json.loads(source)
        except (TypeError, ValueError) as error:
            problems.append((text(path), "invalid_json：%s" % (error,)))
            continue
        recipeId = idOf(path, data)
        if recipeId is None:
            problems.append((text(path), "no_id：没写 \"id\"，也不在 %s/<命名空间>/ 下面" % DIRECTORY))
            continue
        answer = register(data, recipeId)
        if answer.get("ok"):
            loaded.append(answer.get("id"))
        else:
            problems.append((text(path), _reason(answer)))
    return loaded, problems
