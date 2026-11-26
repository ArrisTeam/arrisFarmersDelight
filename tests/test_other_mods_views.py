# -*- coding: utf-8 -*-
# runner: both
"""取别的模组的模块：四个站点的客户端表现登记时取前置包的声明模块（arrisDiegesisScripts.Shared.Schema；BoardView / PotView / PanView /
GrillView 的 register 经 Compat/Diegesis/SchemaKit，再经 Compat/OtherMods）。前置包真的客户端 Api 上没有 Schema 这个名字，四个站点都去取它。
四种回答（抛 ImportError、抛别的异常、返回 None、返回正常的模块）：它导入出错或者不在，这个站点的表现不登记、这一步 skipped
（原来异常从 register 里抛出去、或者拿 None 去建声明时抛 AttributeError，这一步记 failed）；四个站点取的是同一个模块，日志只打一次；
正常的模块登记的和接口上带着 Schema 时一样。真的入口、真的站点模块和前置包（bootkit；旁边没有前置包工程就跳过）。
"""
from __future__ import print_function

import prereq  # noqa: F401 - 前置包不在这个仓库里：旁边没有它就跳过（tests/prereq.py）
import bootkit as B
import fdtest
import otherkit
from otherkit import Captured, Importer

STATIONS = ("board", "pot", "pan", "grill")
Engine = fdtest.load("Client.Engine")
SchemaKit = fdtest.load("Compat.Diegesis.SchemaKit")
NoSchemaApi = type("NoSchemaApi", (B.ClientApi,), {"Schema": None})      # 像前置包真的 Api/Client：没有 Schema 这个名字


def testTheKitAsksTheClientEngineOnlyWhenTheApiHasNoSchema():
    assert SchemaKit.clientApi is Engine.clientApi, "下面换的是这个 clientApi 的 ImportModule"
    importer = Importer()
    Engine.clientApi.ImportModule = importer
    assert SchemaKit.of(B.ClientApi) is B.Schema and importer.asked == [], "接口上带着 Schema：用它，不去取"


def testTheFourStationsTakeTheSchemaModuleThroughOtherMods():
    expected = B.bootClient().stations               # 接口上带着 Schema（替身）时登记的
    assert len(expected) == 4, expected
    for name, answer, absent in otherkit.kinds(B.Schema):
        otherkit.fresh()
        importer = Importer({SchemaKit.SCHEMA_MODULE: answer})
        Engine.clientApi.ImportModule = importer
        with Captured() as out:
            booted = B.bootClient(NoSchemaApi)
        assert importer.asked == [SchemaKit.SCHEMA_MODULE] * 4, (name, importer.asked)
        assert booted.stations == ([] if absent else expected), (name, booted.stations)
        assert [booted.steps[station] for station in STATIONS] == ["skipped" if absent else "ok"] * 4, (name, booted.steps)
        assert booted.looks == dict((look, not absent) for look in booted.looks), (name, booted.looks)
        raised = 1 if isinstance(answer, Exception) else 0
        assert out.logged(SchemaKit.SCHEMA_MODULE) == raised and out.tracebacks() == raised, (name, out.text)


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
