# -*- coding: utf-8 -*-
"""ClientSteps - 客户端的联动步骤表：前置包在场且够新时，Presence 按这个顺序一站一站联动（客户端，只放数据）

写法同 ServerSteps：一个站点一步，每一步做原来这个站点在 ClientBoot 里做的全部——登记站点的表现，登记上了再开它连带的场景和旁观的声音
（砧板的 BoardWatch、厨锅 / 煎锅 / 炉灶的 Scenes，炉灶还让出灶上东西的烟）。本文件不导入任何业务模块。
HoD 的配置（Shared/Data/HandsOnConfig.py，和服务端是同一份）里关了的站点，它的 View.register 返回 None（和服务端的 Logic.register 同一个条件），
这一步记成 skipped：不登记它、也不开它的场景和旁观的声音，方块照农夫乐事原样用，右键开经典界面或放料取料。
炉灶要前置包接口的朝向钩子（FACING_HOOK）：和服务端的 grill 步骤同一个条件。
"""
STEPS = [
    ("board", "Compat.Diegesis.BoardClientLink:link", None),
    ("pot", "Compat.Diegesis.PotClientLink:link", None),
    ("pan", "Compat.Diegesis.PanClientLink:link", None),
    ("grill", "Compat.Diegesis.GrillClientLink:link", "FACING_HOOK"),
]
