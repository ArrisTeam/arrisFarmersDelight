# -*- coding: utf-8 -*-
"""Steps - 联动步骤表的执行器：一步一步导入、调用、记结果，一步失败不拦着别的步骤（双端，不碰引擎）

步骤表（ServerSteps.py / ClientSteps.py）的每一项是 (步骤名, "相对脚本根的模块路径:函数名", 条件或 None)，和机械动力系列附属包的写法一样：
- 目标模块在这一步执行时才导入：没联动时 Compat/Diegesis 里除了两个入口、Presence、Steps、两张步骤表，别的模块一个也不会被导入，
  它们的 @Listen / @AllowCall 也就不存在；一个站点的模块导入失败，只有它的这一步失败；
- 条件是前置包接口模块上的可选功能旗（比如 FACING_HOOK），接口没有它这一步记成 skipped，连模块都不导入；
- 目标函数收一个 Context（side、api、apiVersion，done：前面几步的状态 {步骤名: ok / skipped / failed}）。返回 False 表示这一步没有东西可联动
  （比如这个站点在 HoD 的配置里关了），记成 skipped；返回别的（包括 None）记成 ok；抛异常记成 failed、打印 traceback，后面的步骤照常执行。
每个目标都存在、条件的名字都对，由 tests/test_presence_steps.py 按源码核对。
"""
import traceback

OK, SKIPPED, FAILED = "ok", "skipped", "failed"
SCRIPT_ROOT = __name__.rsplit(".", 3)[0]       # 本包脚本根的包名（本模块是 <脚本根>.Compat.Diegesis.Steps）


class Context(object):
    """传给每个步骤函数的东西：这一端、握过手的前置包接口、它的 API_VERSION、前面几步的状态（done：步骤名 -> ok / skipped / failed；
    客户端的 table 一步要看 board 那一步登上了没有）。"""

    def __init__(self, side, api):
        self.side = side
        self.api = api
        self.apiVersion = getattr(api, "API_VERSION", 0)
        self.done = {}


def run(side, steps, api, load):
    """按表的顺序执行 steps，返回 [(步骤名, 状态, 说明)]，和表同序。load(模块的完整路径) 导入那个模块，导不到就抛异常。"""
    ctx = Context(side, api)
    results = []
    for name, target, requires in steps:
        status, note = _one(ctx, name, target, requires, load)
        ctx.done[name] = status
        results.append((name, status, note))
    return results


def _one(ctx, name, target, requires, load):
    if requires is not None and not getattr(ctx.api, requires, False):
        return SKIPPED, "前置包的接口没有 %s" % requires
    try:
        modulePath, _, funcName = target.partition(":")
        outcome = getattr(load("%s.%s" % (SCRIPT_ROOT, modulePath)), funcName)(ctx)
    except Exception as e:  # noqa: BLE001 - 一步失败不能拖垮后面的步骤
        print("[arrisFarmersDelight] 联动（%s 端）：步骤 %s 出错" % (ctx.side, name))
        traceback.print_exc()
        return FAILED, repr(e)
    return (SKIPPED, "这一步没有东西可联动") if outcome is False else (OK, "")
