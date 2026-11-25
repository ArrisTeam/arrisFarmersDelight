# -*- coding: utf-8 -*-
"""gen_tags - 从词表 Shared/Data/Tags.py 生成行为包的 netease_tags/（开发工具，py -3 运行）

一个标签一个文件：{"type": "item" | "block", "identifier": 标签名, "items": [成员...]}，文件名照机械动力：
item_<标签名里的 : 和 / 换成 _>.json、block_<同上>.json。引擎把各模组登记的同名标签（type 和 identifier 都一样）合并去重。
原版自带的标签（VANILLA_TAGS）不生成。目录里不是这里生成的文件也算不一致（--check 失败，生成时删掉），词表是唯一的出处。
用法：py -3 tools/gen_tags.py            生成 / 更新 bp/netease_tags/
      py -3 tools/gen_tags.py --check    只比较，不一致时退出码 1（tests/test_netease_tags.py 也会比）
"""
import importlib.util
import io
import json
import os
import sys

sys.dont_write_bytecode = True      # 按路径加载词表时别在包里留 __pycache__

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "bp", "netease_tags")
SOURCE = os.path.join(ROOT, "bp", "arrisFarmersDelightScripts", "Shared", "Data", "Tags.py")


def vocabulary():
    spec = importlib.util.spec_from_file_location("fd_tags_vocabulary", SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fileName(kind, identifier):
    return "%s_%s.json" % (kind, identifier.replace(":", "_").replace("/", "_"))


def render(kind, identifier, members):
    body = json.dumps({"type": kind, "identifier": identifier, "items": list(members)}, indent=2, ensure_ascii=False)
    # 键的顺序照官方例子：type、identifier、items（json.dumps 不排序时按插入顺序，py3.7 起保证）
    return body + "\n"


def files(tags=None):
    """{文件名: 内容}"""
    tags = tags or vocabulary()
    found = {}
    for kind, table in (("item", tags.ITEM_TAGS), ("block", tags.BLOCK_TAGS)):
        for identifier, members in table.items():
            found[fileName(kind, identifier)] = render(kind, identifier, members)
    return found


def main(argv):
    want = files()
    check = "--check" in argv
    present = sorted(name for name in os.listdir(OUT)) if os.path.isdir(OUT) else []
    stale = [name for name in present if name not in want]
    changed = []
    for name, text in sorted(want.items()):
        path = os.path.join(OUT, name)
        current = io.open(path, encoding="utf-8").read() if os.path.exists(path) else None
        if current != text:
            changed.append(name)
            if not check:
                if not os.path.isdir(OUT):
                    os.makedirs(OUT)
                with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
                    handle.write(text)
    if check:
        for name in changed + stale:
            print("不一致：" + name)
        return 1 if changed or stale else 0
    for name in stale:
        os.remove(os.path.join(OUT, name))
    print("netease_tags：%d 个文件，改了 %d 个，删了 %d 个" % (len(want), len(changed), len(stale)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
