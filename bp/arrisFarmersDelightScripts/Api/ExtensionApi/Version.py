# -*- coding: utf-8 -*-
"""Version - 主包的版本号（双端，不碰引擎）

脚本读不到 manifest，所以版本号在这里另有一份，和 bp/manifest.json、rp/manifest.json 的 header.version 一样。
发版时由 tools/version.py 和两个 manifest 一起改写（它的 PYTHON_CONSTANTS），不要手改；tests/test_extension_api.py 和 tests/test_release_tools.py 核对。
别的模组经 ext.hostVersion 读它，判断农夫乐事够不够新（主包太旧时给玩家一句明确的提示）。它和 ext.apiVersion 不是一回事：
hostVersion 每次发版都变；apiVersion 只在公共接口有破坏性变更时才加一。
"""

HOST_VERSION = (1, 0, 2)
