# -*- coding: utf-8 -*-
"""
dolorContainer 的公共界面文件拷进使用方时只留用到的模板（docs/ARCHITECTURE.md 第 2.2 节）。库仓库的 tools/vendor.py 与
装进使用方的守卫测试 tests/test_dolor_vendor.py 共用这一份（vendor 把它装成使用方的 tests/dolor_uiprune.py），不要在使用方改。

用到的模板：编译出的布局引用到的（键里的 @命名空间.名字、值里的 命名空间.名字），拷进去的库模块在运行时按名字建或挂的
（模块级 UI_TEMPLATES 列出），再按模板之间的引用补齐。裁剪后的内容用占位的命名空间（dolor_container）算哈希，命名空间与
文件名用 dolor_container_<哈希>：与 tools/gen_ui.py 的算法一样，什么都不裁时还是原来的名字；几个模组用到的模板一样时
是同一个文件。
"""
from __future__ import print_function

import ast
import hashlib
import io
import json
import re

BASE_NS = "dolor_container"


def render(data):
    """与 tools/gen_ui.py 写界面文件的格式一样。"""
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def load(path):
    with io.open(path, encoding="utf-8") as handle:
        return json.load(handle)


def nameOf(key):
    """模板的键（名字@继承的模板）里的名字。"""
    return key.split("@", 1)[0]


def _pattern(namespace):
    return re.compile(r"(?<![\w.])%s\.([A-Za-z_]\w*)" % re.escape(namespace))


def references(value, namespace):
    """一段界面定义（键与值）里引用的 namespace 下的模板名。"""
    pattern = _pattern(namespace)
    found = set()
    todo = [value]
    while todo:
        item = todo.pop()
        if isinstance(item, dict):
            for key, child in item.items():
                found.update(pattern.findall(key))
                todo.append(child)
        elif isinstance(item, list):
            todo.extend(item)
        elif isinstance(item, str):
            found.update(pattern.findall(item))
    return found


def uiTemplates(path):
    """库模块里模块级 UI_TEMPLATES = (...) 列的模板名（运行时按名字建或挂的）。"""
    with io.open(path, encoding="utf-8") as handle:
        tree = ast.parse(handle.read(), path)
    out = []
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "UI_TEMPLATES"
                                                for target in node.targets):
            out.extend(ast.literal_eval(node.value))
    return out


def closure(data, roots):
    """
    从 roots（[(来源, 模板名)]）出发按模板之间的引用补齐。返回 (用到的模板名集合, 问题列表)：问题是 (来源, 模板名)——
    引用的模板界面文件里没有。
    """
    namespace = data["namespace"]
    keys = dict((nameOf(key), key) for key in data if key != "namespace")
    kept, problems = set(), []
    todo = list(roots)
    while todo:
        source, name = todo.pop()
        if name in kept:
            continue
        if name not in keys:
            problems.append((source, name))
            continue
        kept.add(name)
        key = keys[name]
        todo.extend((name, found) for found in references({key: data[key]}, namespace))
    return kept, sorted(set(problems))


def renamed(value, old, new):
    """把界面定义里的命名空间 old 换成 new（只换 old.名字 这种引用与命名空间本身）。"""
    pattern = re.compile(r"(?<![\w.])%s(?=\.|$)" % re.escape(old))
    if isinstance(value, dict):
        return dict((pattern.sub(new, key), renamed(child, old, new)) for key, child in value.items())
    if isinstance(value, list):
        return [renamed(child, old, new) for child in value]
    if isinstance(value, str):
        return pattern.sub(new, value)
    return value


def pruned(data, kept):
    """
    只留 kept 里的模板（照原来的先后），返回 (命名空间, 界面文件的相对路径, 内容)。命名空间按占位命名空间下的内容算哈希。
    """
    namespace = data["namespace"]
    out = {"namespace": BASE_NS}
    for key, value in data.items():
        if key != "namespace" and nameOf(key) in kept:
            placeholder = renamed({key: value}, namespace, BASE_NS)
            out.update(placeholder)
    digest = hashlib.sha1(render(out).encode("utf-8")).hexdigest()[:8]
    newNamespace = "%s_%s" % (BASE_NS, digest)
    return newNamespace, "ui/%s.json" % newNamespace, renamed(out, BASE_NS, newNamespace)
