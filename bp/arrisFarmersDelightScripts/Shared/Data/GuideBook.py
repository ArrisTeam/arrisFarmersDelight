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
            "content": "用小刀击杀猪或疣猪兽时可能掉落\n着火的猪掉的是烟熏火腿"
        },
        {
            "title": "烟熏火腿",
            "namespace": "arris:smoked_ham",
            "auxValue": 0,
            "content": "将火腿放进烟熏炉、熔炉或放在营火上烤熟"
        },
        {
            "title": "奶瓶",
            "namespace": "arris:milk_bottle",
            "auxValue": 0,
            "content": "饮用后清除1个效果，并返还空玻璃瓶"
        },
        {
            "title": "苹果酒",
            "namespace": "arris:apple_cider",
            "auxValue": 0,
            "content": "饮用后获得1分钟的伤害吸收，不饿也能喝，并返还空玻璃瓶"
        },
        {
            "title": "西瓜汁",
            "namespace": "arris:melon_juice",
            "auxValue": 0,
            "content": "饮用后瞬间恢复少量生命值，并返还空玻璃瓶"
        },
        {
            "title": "热可可",
            "namespace": "arris:hot_cocoa",
            "auxValue": 0,
            "content": "饮用后清除1个有害效果，并返还空玻璃瓶"
        },
        {
            "title": "生意面",
            "namespace": "arris:raw_pasta",
            "auxValue": 0,
            "content": "将面团放在砧板上，用小刀切开获得"
        },
        {
            "title": "生培根",
            "namespace": "arris:bacon",
            "auxValue": 0,
            "content": "将生猪排放在砧板上，用小刀切开获得"
        },
        {
            "title": "牛肉馅",
            "namespace": "arris:minced_beef",
            "auxValue": 0,
            "content": "将生牛肉放在砧板上，用小刀切开获得"
        },
        {
            "title": "生羊排",
            "namespace": "arris:mutton_chops",
            "auxValue": 0,
            "content": "将生羊肉放在砧板上，用小刀切开获得"
        },
        {
            "title": "生鸡肉丁",
            "namespace": "arris:chicken_cuts",
            "auxValue": 0,
            "content": "将生鸡肉放在砧板上，用小刀切开获得"
        },
        {
            "title": "生鳕鱼片",
            "namespace": "arris:cod_slice",
            "auxValue": 0,
            "content": "将生鳕鱼放在砧板上，用小刀切开获得"
        },
        {
            "title": "生鲑鱼片",
            "namespace": "arris:salmon_slice",
            "auxValue": 0,
            "content": "将生鲑鱼放在砧板上，用小刀切开获得"
        }
    ],
    "工具": [
        {
            "title": "小刀",
            "namespace": "arris:iron_knife",
            "auxValue": 0,
            "content": "轻巧的近战武器，也是砧板上切菜的工具\n用小刀破坏草、成熟的小麦和稻穗可以得到草秆\n用小刀击杀动物有额外掉落: 猪的火腿、牛的皮革、鸡的羽毛……"
        },
        {
            "title": "砧板",
            "namespace": "arris:cutting_board",
            "auxValue": 0,
            "content": "右键把手里的东西整叠放上去，再拿对的工具点它，一次处理一件:\n刀切食材，斧头剥原木、拆木制品，镐敲砖石，\n锹挖黏土和沙砾，锄拆运输船和矿车，剪刀剪皮革\n空手点击砧板取回物品"
        },
        {
            "title": "厨锅",
            "namespace": "arris:cooking_pot",
            "auxValue": 0,
            "content": "用于烹饪农夫乐事里的大部分菜肴\n下方需要热源（炉灶、营火、火、岩浆块等）\n盛出时要有对应的容器（碗、玻璃瓶等）"
        },
        {
            "title": "煎锅",
            "namespace": "arris:skillet_item",
            "auxValue": 0,
            "content": "放在热源上方，右键放入一叠食物\n一件一件地煎，每件6秒\n也能拿在手里当武器"
        },
        {
            "title": "炉灶",
            "namespace": "arris:stove",
            "auxValue": 0,
            "content": "有6个烤位，每件30秒烤熟\n上方不能被方块挡住\n也是厨锅、煎锅的热源"
        },
        {
            "title": "绳子",
            "namespace": "arris:rope",
            "auxValue": 0,
            "content": "可以攀爬\n番茄藤蔓会顺着上方的绳子往上长，最多高出3格"
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
            "title": "竹篮",
            "namespace": "arris:basket",
            "auxValue": 0,
            "content": "会自动收进落在里面和上面一格的掉落物\n接上红石信号时不再收"
        },
        {
            "title": "木篮",
            "namespace": "arris:wooden_basket",
            "auxValue": 0,
            "content": "会自动收进落在里面和上面一格的掉落物\n接上红石信号时不再收"
        }
    ],
    "植物": [
        {
            "title": "海甜菜",
            "namespace": "arris:wild_beetroots",
            "auxValue": 0,
            "content": "生成于沙滩、积雪沙滩"
        },
        {
            "title": "野生卷心菜",
            "namespace": "arris:wild_cabbages",
            "auxValue": 0,
            "content": "生成于沙滩、积雪沙滩"
        },
        {
            "title": "野生胡萝卜",
            "namespace": "arris:wild_carrots",
            "auxValue": 0,
            "content": "生成于温带: 平原、向日葵平原、森林、繁花森林、\n桦木森林、黑森林、沼泽、红树林沼泽、\n草甸、樱花树林、河流、沙滩"
        },
        {
            "title": "野生洋葱",
            "namespace": "arris:wild_onions",
            "auxValue": 0,
            "content": "生成于温带: 平原、向日葵平原、森林、繁花森林、\n桦木森林、黑森林、沼泽、红树林沼泽、\n草甸、樱花树林、河流、沙滩"
        },
        {
            "title": "野生马铃薯",
            "namespace": "arris:wild_potatoes",
            "auxValue": 0,
            "content": "生成于寒冷地区: 针叶林、原始针叶林、\n风袭丘陵、风袭森林、石岸"
        },
        {
            "title": "番茄灌木",
            "namespace": "arris:wild_tomatoes",
            "auxValue": 0,
            "content": "生成于干旱地区: 沙漠、风蚀恶地、热带草原、\n热带高原、裸岩山峰"
        },
        {
            "title": "蘑菇菌落",
            "namespace": "arris:brown_mushroom_colony",
            "auxValue": 0,
            "content": "生成于蘑菇岛；把蘑菇种在沃土上也会慢慢长成\n用剪刀可以把长满的菌落整块取下"
        },
        {
            "title": "野生稻米",
            "namespace": "arris:wild_rice",
            "auxValue": 0,
            "content": "生成于湿地的浅水里: 沼泽、红树林沼泽、\n丛林、竹林、沙滩"
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
            "content": "种在泥土、草方块、沃土或耕地上方一格深的水里\n可用于烹饪"
        },
        {
            "title": "树皮",
            "namespace": "arris:tree_bark",
            "auxValue": 0,
            "content": "把原木放在砧板上，用斧头剥皮获得"
        },
        {
            "title": "草秆",
            "namespace": "arris:straw",
            "auxValue": 0,
            "content": "用小刀破坏草、成熟的小麦和稻穗获得\n可合成粗布、绳子、拴绳"
        },
        {
            "title": "烂番茄",
            "namespace": "arris:rotten_tomato",
            "auxValue": 0,
            "content": "采番茄时偶尔得到；不能吃，可以扔出去，类似于雪球"
        }
    ]
}
