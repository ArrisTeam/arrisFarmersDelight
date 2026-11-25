# -*- coding: utf-8 -*-
# runner: both
"""新联动接口的对外文档和代码对得上（docs/EXTENSION-API.md、RECIPE-JSON.md、API-CHANGELOG.md、linkage.md）。

- EXTENSION-API.md §3 的能力名表 = Events 里两端登记的能力名（端写对；还没登记的那一行写明"还没登记"，Events 里也确实没有）；
- 每个登记了的能力名在 API-CHANGELOG.md 里出现过；
- 代码里会返回的每个错误码都在 EXTENSION-API.md §4 的表里，读行为包文件多出来的两个在 RECIPE-JSON.md 里；
- §2 的常量表和 Events 一样；linkage.md 开头指向新文档和 TAGS.md。
"""
from __future__ import print_function

import io
import os
import re

import fdtest

Events = fdtest.load("Api.ExtensionApi.Events")
DOCS = os.path.join(fdtest.ROOT, "docs")
API = os.path.join(fdtest.BP, fdtest.SCRIPTS, "Api", "ExtensionApi")


def _read(*parts):
    with io.open(os.path.join(*parts), encoding="utf-8") as handle:
        return handle.read()


def _section(text, start, end):
    """text 里从标题 start 起、到标题 end 之前的那一段。"""
    begin = text.index(start)
    return text[begin:text.index(end, begin)]


def _capabilityRows():
    table = _section(_read(DOCS, "EXTENSION-API.md"), u"## 3. ", u"## 4. ")
    return [(match.group(1), match.group(2).strip()) for match in re.finditer(u"^\\| `([a-z_]+)` \\| ([^|]+)\\|", table, re.M)]


def testTheCapabilityTableIsWhatEventsRegisters():
    rows = _capabilityRows()
    assert len(rows) == len(set(name for name, _side in rows)), "一个能力名一行"
    pending = set(str(name) for name, side in rows if u"还没登记" in side)
    server = set(str(name) for name, side in rows if name not in pending and side in (u"服务端", u"两端"))
    client = set(str(name) for name, side in rows if name not in pending and side in (u"客户端", u"两端"))
    assert server == set(Events.SERVER_CAPABILITIES), sorted(server ^ set(Events.SERVER_CAPABILITIES))
    assert client == set(Events.CLIENT_CAPABILITIES), sorted(client ^ set(Events.CLIENT_CAPABILITIES))
    assert not pending & (Events.SERVER_CAPABILITIES | Events.CLIENT_CAPABILITIES), "写着还没登记的，Events 里就不能有"
    assert pending == (set() if Events.RECIPE_JSON_FILES_VERIFIED else set(["recipe_json_files"])), pending
    changelog = _read(DOCS, "API-CHANGELOG.md")
    missing = [name for name in sorted(Events.SERVER_CAPABILITIES | Events.CLIENT_CAPABILITIES | pending) if u"`%s`" % name not in changelog]
    assert not missing, "API-CHANGELOG.md 里没写的能力名：%r" % missing


def _codes():
    found = set()
    for name in os.listdir(API):
        if name.endswith(".py"):
            found.update(re.findall(u"answer\\(False, \"([a-z_]+)\"", _read(API, name)))
    return found


def testEveryErrorCodeIsDocumented():
    codes = _codes()
    assert set(["server_only", "invalid_id", "invalid_recipe", "input_taken", "invalid_name", "invalid_chance"]) <= codes, sorted(codes)
    table = _section(_read(DOCS, "EXTENSION-API.md"), u"## 4. ", u"## 5. ")
    documented = set(re.findall(u"^\\| `([a-z_]+)` \\|", table, re.M))
    assert codes <= documented, sorted(codes - documented)
    recipeJson = _read(DOCS, "RECIPE-JSON.md")
    for code in ("invalid_json", "no_id"):
        assert u"`%s`" % code in recipeJson, code


def testTheProtocolTableAndTheLinks():
    protocol = _section(_read(DOCS, "EXTENSION-API.md"), u"## 2. ", u"## 3. ")
    for constant in ("EXTENSION_API_VERSION", "EXTENSION_API_NAMESPACE", "EXTENSION_API_SYSTEM_NAME",
                     "SERVER_EXTENSION_API_READY_EVENT", "CLIENT_EXTENSION_API_READY_EVENT"):
        value = getattr(Events, constant)
        shown = u"`%d`" % value if isinstance(value, int) else u'`"%s"`' % value
        assert u"| `%s` | %s |" % (constant, shown) in protocol, constant
    linkage = _read(fdtest.ROOT, "linkage.md")
    head = linkage[:linkage.index(u"## 功能描述")]
    for target in (u"docs/EXTENSION-API.md", u"docs/RECIPE-JSON.md", u"docs/COMPATIBILITY.md", u"docs/TAGS.md"):
        assert target in head, target
    assert u"## 标签（netease_tags，网易 3.10 起）" in linkage


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
