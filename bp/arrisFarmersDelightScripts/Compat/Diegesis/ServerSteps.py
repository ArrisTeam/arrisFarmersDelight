# -*- coding: utf-8 -*-
"""ServerSteps - 服务端的联动步骤表：前置包在场且够新时，Presence 按这个顺序一站一站联动（服务端，只放数据）

每一项 (步骤名, "相对脚本根的模块路径:函数名", 条件或 None)，约定见 Steps.py。本文件不导入任何业务模块
（模块在各自的步骤里才被导入；tests/test_architecture.py 守着，tests/test_presence_steps.py 按源码核对每个目标都存在）。
一个站点一步，顺序是原来 ServerBoot 登记的顺序：砧板、厨锅、煎锅、炉灶。每一步做原来这个站点在 ServerBoot 里做的全部：登记站点，
登记上了再打开它连带的东西（世界外观广播、砧板的旁观声音、工作台拦截）。
HoD 的配置（Shared/Data/HandsOnConfig.py）在这里只问一次站点开不开：每个站点的 register 在配置里关了就返回 None，这一步记成 skipped，
连带的东西也都不开，方块照农夫乐事原样用；客户端的 ClientSteps 同一个条件，两端一起有、一起没有。
炉灶要前置包接口的朝向钩子（FACING_HOOK，可选功能旗）：没有这面旗的前置包上炉灶照旧走经典玩法。
最后一步 table 不是本包的站点：前置包自己的原版工作台站点（脚本合成，不发引擎的合成事件）上登记本包的无序配方还容器（TableServerLink；
砧板菜不让做跟着砧板站点在 board 那一步登）；接口不在（前置包太旧、没装它的内容包）就 skipped。
"""
STEPS = [
    ("board", "Compat.Diegesis.BoardServerLink:link", None),
    ("pot", "Compat.Diegesis.PotServerLink:link", None),
    ("pan", "Compat.Diegesis.PanServerLink:link", None),
    ("grill", "Compat.Diegesis.GrillServerLink:link", "FACING_HOOK"),
    ("table", "Compat.Diegesis.TableServerLink:link", None),
]
