# -*- coding: utf-8 -*-
"""HandsOnConfig - Hands-On Delight 的配置表：四个站点的开关、工作台合成、搅拌、食谱书、三种烹饪时间倍率（双端，纯数据）

照 HoD 的 config/handson_delight.properties（HandsOnConfig.java:15-77 的说明文字和缺省值）：键名、缺省值、含义和 JE 一致。
JE 说明文字里别的模组的键（keg、kettle、grill、basin、cuisine_board、youkai_*、kettle_time）本包没有对应的方块，不收。

改哪里：基岩版没有玩家自己改的配置文件，整合包作者 / 服主直接改下面 CONFIG 的值，重启游戏（服务器）后生效：
站点登记（Compat/Diegesis 步骤表里各站点的 register）只在启动时看一次，倍率和别的开关每次用到时现读。
这张表只在装了场景交互前置、联动了（Shared/Rules/HandsOnMode）时才生效；没装前置包或它太旧时 Hands-On Delight 不在，表里写什么都不看，农夫乐事走原样。
服务端和客户端是同一份脚本，客户端用的是服务端的包带过来的这个文件：JE 里"配方书里的时间照服务端"在这里自然成立，
站点开关也两端一致；JE 里 recipe_book 是每个玩家自己的偏好，这里是整个包统一的一个值。
这张表不经联动契约（Api/LegacyModAttr.py）交给下游模组。

值写 True / False 和数字就行。写错了由 Shared/Rules/HandsOnOptions.py 照 JE 的读法兜（HandsOnConfig.read / readTime）：
布尔认 true / yes / on / 1 和 false / no / off / 0（字符串、整数 1 / 0），别的当缺省；倍率夹进 0.1 ~ 10，读不成有限的数当缺省 1.0；
缺键当缺省。派生规则（站点关了它的倍率算 1.0、没有砧板站点就不拿掉工作台合成、没有厨锅站点就没有"要搅"）也在那里。
"""

CONFIG = {
    # cooking_pot、cutting_board、skillet、stove：这个方块的站点。关了，方块照农夫乐事原样用
    # （厨锅右键开经典界面，砧板 / 煎锅 / 炉灶右键放料取料，场景、广播、食谱书、工作台拦截都不开）。
    "cooking_pot": True,
    "cutting_board": True,
    "skillet": True,
    "stove": True,
    # remove_crafting_recipes：农夫乐事的食物合成（三明治、沙拉、卷、派、盛宴）只在砧板上做，工作台和背包里的 2x2 不出；
    # 没有砧板站点时不拿掉。机器（机械动力等）照样合成。
    "remove_crafting_recipes": True,
    # stirring_required：厨师在厨锅站点里放进锅的料，他在锅边时要等勺子；关了，不搅也自己煮（农夫乐事的煮法），
    # 搅了照样整批一起煮好、评星。只在厨锅站点开着时有意义。
    "stirring_required": True,
    # recipe_book：站点旁的食谱书。
    "recipe_book": True,
    # cooking_pot_time：料在锅里煮多久，是配方时间的几倍（0.1 ~ 10；1.0 照常，2.0 两倍长，0.5 一半）。
    # 锅的每种煮法都按它：搅着的、放着不管的、漏斗放进去的、农夫乐事自己的界面里放的。
    # skillet_time、stove_time：在站点里煎（手放进煎锅）、烤（手放上炉灶）的食物同理；农夫乐事自己的右键放进去的照旧用它的时间。
    # 对应的站点关了，这个倍率算 1.0。
    "cooking_pot_time": 1.0,
    "skillet_time": 1.0,
    "stove_time": 1.0,
}
