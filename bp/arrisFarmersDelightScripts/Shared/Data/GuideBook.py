# -*- coding: utf-8 -*-
"""GuideBook - 农夫乐事指南书的分页内容（双端，纯数据）
"""
# 指南书界面的注册信息（客户端在 UiInitFinished 里 RegisterUI 时用）
uiGuideBookPath = "arrisFarmersDelightScripts.Client.Ui.GuideBook.guideBook"
uiGuideBookScreen = "guideBook.main"


config = {
    "食物": [
        {
            "title": "火腿",
            "namespace": "arris:ham",
            "auxValue": 0,
            "content": "使用小刀击杀猪概率掉落"
        },
        {
            "title": "烟熏火腿",
            "namespace": "arris:smoked_ham",
            "auxValue": 0,
            "content": "将火腿放置在 烟熏炉 中烹饪制成"
        },
        {
            "title": "奶瓶",
            "namespace": "arris:milk_bottle",
            "auxValue": 0,
            "content": "食用后随机清除一个效果，并返还一个空玻璃瓶"
        },
        {
            "title": "苹果酒",
            "namespace": "arris:apple_cider",
            "auxValue": 0,
            "content": "食用后获得1分钟的伤害吸收效果，并返还一个空玻璃瓶"
        },
        {
            "title": "西瓜汁",
            "namespace": "arris:melon_juice",
            "auxValue": 0,
            "content": "食用后瞬间恢复少量生命值，并返还一个空玻璃瓶"
        },
        {
            "title": "热可可",
            "namespace": "arris:hot_cocoa",
            "auxValue": 0,
            "content": "食用后随机清除一个负面效果，并返还一个空玻璃瓶"
        },
        {
            "title": "生意面",
            "namespace": "arris:raw_pasta",
            "auxValue": 0,
            "content": "将面团放置在砧板上，使用小刀切开获得"
        },
        {
            "title": "培根",
            "namespace": "arris:bacon",
            "auxValue": 0,
            "content": "将生猪排放置在砧板上，使用小刀切开获得"
        },
        {
            "title": "牛肉馅",
            "namespace": "arris:minced_beef",
            "auxValue": 0,
            "content": "将生牛肉放置在砧板上，使用小刀切开获得"
        },
        {
            "title": "生羊排",
            "namespace": "arris:mutton_chops",
            "auxValue": 0,
            "content": "将生羊肉放置在砧板上，使用小刀切开获得"
        },
        {
            "title": "生鸡肉丁",
            "namespace": "arris:chicken_cuts",
            "auxValue": 0,
            "content": "将生鸡肉放置在砧板上，使用小刀切开获得"
        },
        {
            "title": "生鳕鱼片",
            "namespace": "arris:cod_slice",
            "auxValue": 0,
            "content": "将生鱼放置在砧板上，使用小刀切开获得"
        },
        {
            "title": "生鲑鱼片",
            "namespace": "arris:salmon_slice",
            "auxValue": 0,
            "content": "将生鲑鱼放置在砧板上，使用小刀切开获得"
        }
    ],
    "工具": [
        {
            "title": "小刀",
            "namespace": "arris:iron_knife",
            "auxValue": 0,
            "content": "用于切割砧板上的食材\n使用小刀击杀鸡、牛时，可获取双倍战利品\n"
        },
        {
            "title": "砧板",
            "namespace": "arris:cutting_board",
            "auxValue": 0,
            "content": "用于切割食材以及给原木剥皮\n当砧板上方为食材时\n使用小刀进行切菜\n当砧板上方为原木时\n使用斧头进行剥皮\n\n空手点击砧板即可取下物品"
        },
        {
            "title": "厨锅",
            "namespace": "arris:cooking_pot",
            "auxValue": 0,
            "content": "用于烹饪农夫乐事内的大部分食材\n需要下方有火源方块"
        },
        {
            "title": "煎锅",
            "namespace": "arris:skillet_item",
            "auxValue": 0,
            "content": "用于烹饪食材\n一次最多可同时烹饪64个\n烹饪时长为7秒\n需要下方有火源方块"
        },
        {
            "title": "炉灶",
            "namespace": "arris:stove",
            "auxValue": 0,
            "content": "用于烹饪食材\n一次可同时烹饪6个\n烹饪时长为7秒"
        },
        {
            "title": "绳子",
            "namespace": "arris:rope",
            "auxValue": 0,
            "content": "类似于梯子,可攀爬\n当下方有番茄植物时，番茄藤蔓会顺着绳子攀爬"
        },
        {
            "title": "安全网",
            "namespace": "arris:safety_net",
            "auxValue": 0,
            "content": "当实体掉落在此方块上时\n可免疫摔落伤害"
        },
        {
            "title": "橱柜",
            "namespace": "arris:oak_cabinet",
            "auxValue": 0,
            "content": "类似于木桶，可储存物品等等"
        },
        {
            "title": "篮子",
            "namespace": "arris:basket",
            "auxValue": 0,
            "content": "类似于箱子与漏斗的结合体\n当有物品掉落在篮子内时\n会自动拾取至篮子内"
        }
    ],
    "植物": [
        {
            "title": "野生甜菜",
            "namespace": "arris:wild_beetroots",
            "auxValue": 0,
            "content": "生成群系: 海滩"
        },
        {
            "title": "野生卷心菜",
            "namespace": "arris:wild_cabbages",
            "auxValue": 0,
            "content": "生成群系: 海滩"
        },
        {
            "title": "野生胡萝卜",
            "namespace": "arris:wild_carrots",
            "auxValue": 0,
            "content": "生成群系: 温暖群系"
        },
        {
            "title": "野生洋葱",
            "namespace": "arris:wild_onions",
            "auxValue": 0,
            "content": "生成群系: 温暖群系\n如：草原、沙漠、热带草原..."
        },
        {
            "title": "野生马铃薯",
            "namespace": "arris:wild_potatoes",
            "auxValue": 0,
            "content": "生成群系: 寒冷群系\n如：冰原、云杉林..."
        },
        {
            "title": "野生番茄灌木",
            "namespace": "arris:wild_tomatoes",
            "auxValue": 0,
            "content": "生成群系: 温暖群系\n如：沙漠、热带草原..."
        },
        {
            "title": "野生稻米",
            "namespace": "arris:wild_rice",
            "auxValue": 0,
            "content": "生成群系: 沼泽、红树林以及河边"
        }
    ],
    "杂物": [
        {
            "title": "卷心菜种子",
            "namespace": "arris:cabbage_seeds",
            "auxValue": 0,
            "content": "需要种植在耕地以及沃土耕地上"
        },
        {
            "title": "番茄种子",
            "namespace": "arris:tomato_seeds",
            "auxValue": 0,
            "content": "需要种植在耕地以及沃土耕地上"
        },
        {
            "title": "洋葱",
            "namespace": "arris:onion",
            "auxValue": 0,
            "content": "需要种植在耕地以及沃土耕地上，可用于烹饪"
        },
        {
            "title": "稻米",
            "namespace": "arris:rice",
            "auxValue": 0,
            "content": "需要种植在1格高且静止的水中，可用于烹饪"
        },
        {
            "title": "树皮",
            "namespace": "arris:tree_bark",
            "auxValue": 0,
            "content": "由原木放置在砧板上，使用斧头剥皮获取"
        },
        {
            "title": "草秆",
            "namespace": "arris:straw",
            "auxValue": 0,
            "content": "破坏草、水稻等植物获得,可合成粗布以及绳子"
        },
        {
            "title": "烂番茄",
            "namespace": "arris:rotten_tomato",
            "auxValue": 0,
            "content": "无法食用，可以长按扔出去，类似于雪球"
        }
    ]
}
