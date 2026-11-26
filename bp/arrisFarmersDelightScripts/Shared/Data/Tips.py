# -*- coding: utf-8 -*-
"""Tips - 服务端提示（物品栏上方那一行字）说的每一句：语言文件的键和那一句的中文（双端，纯数据）

提示原来是服务端拼好中文、SetOneTipMessage 发过去的，谁看都是中文。服务端不知道每个玩家用什么语言（服务端的 GetChinese 给的是服务端那边的语言），
所以现在只告诉那个玩家的客户端"哪一句、填什么"（Server/Helpers/Engine.ShowTip，线上写法 Shared/Rules/TipWire），客户端按自己的语言查出来再弹
（Client/Endpoints.OnTip：Client/Texts 查 rp/texts 的语言文件）。
一句 = (语言文件的键, 中文)：中文就是 rp/texts/zh_CN.lang 里的那一行，也是语言文件里找不到这一句（或者那里的写法填不上值）时客户端显示的那句——不露键名。
JE 的农夫乐事有的句子沿用它的键（block.farmersdelight.* / item.farmersdelight.*，英文照它的 en_us.json，中文是我们原来的写法，和它的 zh_cn.json 一样）；
移植时我们自己加的句子用 arris_fd.tip.*。句子里的 %d / %s 由调用的地方给值：ShowTip(玩家, Tips.BOARD_REMAINING, 还剩几个)；
值也可以是一个词 (键, 中文)，客户端一样按语言查（JE 的 feast.use_container 填的是容器的名字——这里是原版碗的键）。
加一句：写在这里、列进 SENTENCES，键和两种语言的那一行写进 rp/texts/zh_CN.lang、en_US.lang（tests/test_tips.py 核对键、中文、占位的个数和每一处调用）。
"""

# 砧板（JE CuttingBoardBlockEntity.processStoredItemUsingTool：板上的东西没有切法、手里的工具不对、切了一件还剩几个）
BOARD_INVALID_ITEM = ("block.farmersdelight.cutting_board.invalid_item", "这东西可不能切啊……")
BOARD_INVALID_TOOL = ("block.farmersdelight.cutting_board.invalid_tool", "或许得换个工具……")
BOARD_REMAINING = ("block.farmersdelight.cutting_board.remaining_items", "还剩%d个……")
# 物品的数据（附魔、改名……）存不进方块实体数据：放上去再取回会丢，所以不让放（JE 什么都能放，这一句是移植加的）
BOARD_UNSTORABLE = ("arris_fd.tip.board_unstorable", "这东西放不上砧板……")

# 煎锅：block. 的是放下去的锅（SkilletBlockEntity），item. 的是拿在手里煎（SkilletItem）
SKILLET_INVALID_ITEM = ("block.farmersdelight.skillet.invalid_item", "这东西可不能被烹饪……")
SKILLET_UNDERWATER = ("block.farmersdelight.skillet.underwater", "被水泡着可没法烹饪啊……")
SKILLET_HOW_TO_COOK = ("item.farmersdelight.skillet.how_to_cook", "用另一只手拿着原料！")
SKILLET_UNDERWATER_HAND = ("item.farmersdelight.skillet.underwater", "在水里可没法煎啊……")

# 炉灶：JE 的炉灶放不上去就什么也不说（StoveBlock.use 返回 PASS），这两句是移植加的。烤不了的那句和煎锅的是同一句话，用同一个键
STOVE_BLOCKED = ("arris_fd.tip.stove_blocked", "炉灶上方被挡住了……")
STOVE_INVALID_ITEM = SKILLET_INVALID_ITEM

# 盘装的菜（JE FeastBlock.takeServing）：%s 是盛菜用的容器的名字，这里的菜都用碗盛
FEAST_USE_CONTAINER = ("block.farmersdelight.feast.use_container", "你需要一个%s以食用它。")
BOWL = ("item.bowl.name", "碗")           # 一个词：原版碗的名字（基岩版原版语言文件里的键），客户端按语言查

# 稻米只能种在浅水里（JE RiceItem.useOn）
RICE_INVALID_PLACEMENT = ("block.farmersdelight.rice.invalid_placement", "这株作物很难在水洼外生存。")

# 沉浸式交互前置在场时，砧板上摆的菜工作台不出（Compat/Diegesis/DishCrafts.py）
DISH_ON_BOARD = ("arris_fd.tip.dish_on_board", "这道菜要在砧板上摆: 右键砧板，先放底座再一层层往上放")

# 拿展示实体删除器打掉了一个展示实体（Server/DisplayGuard.py）
DISPLAY_REMOVED = ("arris_fd.tip.display_removed", "§7物品展示实体 §a删除成功!")

# 能单独弹出来的句子（测试按它核对语言文件和每一处调用）；STOVE_INVALID_ITEM 就是 SKILLET_INVALID_ITEM，不另列
SENTENCES = (BOARD_INVALID_ITEM, BOARD_INVALID_TOOL, BOARD_REMAINING, BOARD_UNSTORABLE,
             SKILLET_INVALID_ITEM, SKILLET_UNDERWATER, SKILLET_HOW_TO_COOK, SKILLET_UNDERWATER_HAND,
             STOVE_BLOCKED, FEAST_USE_CONTAINER, RICE_INVALID_PLACEMENT, DISH_ON_BOARD, DISPLAY_REMOVED)
# 只填进句子里的词：键在原版的语言文件里，不在我们的
WORDS = (BOWL,)
